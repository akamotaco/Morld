#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// EventSystem - 게임 이벤트 수집 및 Python 전달
	/// - 위치 변경 감지 (OnReach)
	/// - 유닛 만남 감지 (OnMeet)
	/// - 이벤트 배치 처리 후 Python on_event_list() 호출
	/// </summary>
	public class EventSystem : ECS.System
	{
		// 이번 Step에서 발생한 이벤트 큐
		private readonly List<GameEvent> _pendingEvents = new();

		private MetaActionHandler? _metaActionHandler;

		// 이전 상태 추적 (OnReach 감지용)
		private readonly Dictionary<int, LocationRef> _lastLocations = new();

		// 이동 시작 감지용 (이전 Step에서 이동 중이었는지)
		private readonly HashSet<int> _wasMoving = new();

		// OnMeet 중복 방지
		private readonly HashSet<string> _lastMeetings = new();
		// 역방향 인덱스: 유닛 ID → 해당 유닛이 포함된 만남 키 집합
		private readonly Dictionary<int, HashSet<string>> _unitToMeetings = new();

		// 초기화 완료 여부 (첫 Step에서 위치 초기화용)
		private bool _initialized = false;

		// 다이얼로그 시간 경과 (set_npc_time_consume에서 누적)
		private int _dialogTimeConsumed = 0;

		// ExcessTime: 다이얼로그가 NextStepDuration을 초과한 시간
		// PlayerSystem에서 ConsumeExcessTime()으로 가져가서 적용
		private int _excessTime = 0;

		public EventSystem()
		{
		}

		/// <summary>
		/// 모든 상태 초기화 (챕터 전환 시 사용)
		/// </summary>
		public void ClearState()
		{
			_pendingEvents.Clear();
			_lastLocations.Clear();
			_wasMoving.Clear();
			_lastMeetings.Clear();
			_unitToMeetings.Clear();
			_initialized = false;
			_dialogTimeConsumed = 0;
			_excessTime = 0;
			GD.Print("[EventSystem] State cleared.");
		}

		/// <summary>
		/// MetaActionHandler 참조 설정 (Generator 처리용)
		/// GameEngine._Ready에서 MetaActionHandler 생성 후 호출
		/// </summary>
		public void SetMetaActionHandler(MetaActionHandler metaActionHandler)
		{
			_metaActionHandler = metaActionHandler;
		}

		/// <summary>
		/// 이벤트 등록 (외부에서 호출)
		/// </summary>
		public void Enqueue(GameEvent evt)
		{
			_pendingEvents.Add(evt);
#if DEBUG_LOG
			GD.Print($"[EventSystem] Enqueued: {evt}");
#endif
		}

		/// <summary>
		/// 위치 초기화 (게임 시작 시 호출)
		/// 현재 모든 유닛의 위치를 기록하여 첫 Step에서 OnReach 발생 방지
		/// </summary>
		public void InitializeLocations()
		{
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
			_lastLocations.Clear();
			foreach (var unit in _unitSystem.Units.Values)
			{
				if (unit.GeneratesEvents)
				{
					_lastLocations[unit.Id] = unit.CurrentLocation;
				}
			}
			_initialized = true;

#if DEBUG_LOG
			GD.Print($"[EventSystem] Initialized locations for {_lastLocations.Count} units");
#endif
		}

		/// <summary>
		/// 다이얼로그 시간 경과 추가 (set_npc_time_consume에서 호출)
		/// </summary>
		/// <param name="duration">경과할 시간 (분)</param>
		public void AddDialogTimeConsumed(int duration)
		{
			_dialogTimeConsumed += duration;
#if DEBUG_LOG
			GD.Print($"[EventSystem] AddDialogTimeConsumed: +{duration} (total: {_dialogTimeConsumed})");
#endif
		}

		/// <summary>
		/// ExcessTime 계산 (Proc 끝에서 호출)
		/// lastDialogTime이 NextStepDuration을 초과하면 초과분 저장
		/// </summary>
		/// <param name="lastDialogTime">마지막 다이얼로그 종료 시점 (상대 시간)</param>
		public void CalculateExcessTime(int lastDialogTime)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

			var nextStepDuration = _playerSystem.NextStepDuration;
			_excessTime = Math.Max(0, lastDialogTime - nextStepDuration);

#if DEBUG_LOG
			if (_excessTime > 0)
				GD.Print($"[EventSystem] ExcessTime 계산: {lastDialogTime} - {nextStepDuration} = {_excessTime}분");
#endif
		}

		/// <summary>
		/// ExcessTime 반환 및 리셋
		/// PlayerSystem에서 호출하여 _remainingDuration에 추가
		/// </summary>
		/// <returns>초과 시간 (분)</returns>
		public int ConsumeExcessTime()
		{
			var result = _excessTime;
			_excessTime = 0;
#if DEBUG_LOG
			if (result > 0)
				GD.Print($"[EventSystem] ConsumeExcessTime: {result}분");
#endif
			return result;
		}

		/// <summary>
		/// 이벤트 처리 완료 후 호출 - ExcessTime 계산 및 DialogTimeConsumed 리셋
		/// _dialogTimeConsumed를 lastDialogTime으로 사용하여 ExcessTime 계산
		/// </summary>
		public void FinalizeDialogTime()
		{
			// _dialogTimeConsumed가 이번 Step의 lastDialogTime 역할
			CalculateExcessTime(_dialogTimeConsumed);

			// 다음 Step을 위해 리셋
			_dialogTimeConsumed = 0;
		}

		/// <summary>
		/// 위치 변경 감지 및 OnReach 이벤트 생성
		/// 플레이어 위치를 떠난 NPC는 액션 로그로 알림
		/// 이동 시작한 NPC도 "떠났다" 알림 (화면에서 사라지므로)
		/// </summary>
		public void DetectLocationChanges()
		{
			// 초기화 안 됐으면 먼저 초기화
			if (!_initialized)
			{
				InitializeLocations();
				return;
			}

			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

			var playerId = _playerSystem.PlayerId;
			var player = playerId >= 0 ? _unitSystem.FindUnit(playerId) : null;
			var playerLocation = player.CurrentLocation;

			foreach (var unit in _unitSystem.Units.Values)
			{
				// 이벤트 비활성 유닛은 스킵
				if (!unit.GeneratesEvents) continue;

				var currentLoc = unit.CurrentLocation;
				var isMoving = unit.CurrentEdge != null;
				var wasMovingBefore = _wasMoving.Contains(unit.Id);

				if (_lastLocations.TryGetValue(unit.Id, out var lastLoc))
				{
					if (currentLoc != lastLoc)
					{
						// 위치가 변경됨 → OnReach 이벤트 생성
						Enqueue(GameEvent.OnReach(unit.Id, currentLoc.RegionId, currentLoc.LocalId));

						// 해당 유닛의 만남 상태 리셋
						ClearMeetingsForUnit(unit.Id);

						// 플레이어 위치를 떠난 NPC → 액션 로그
						if (unit.Id != playerId && lastLoc == playerLocation)
						{
							NotifyNpcDeparture(unit);
						}
					}
					// 위치는 같지만 이동을 시작한 경우 (화면에서 사라짐)
					else if (isMoving && !wasMovingBefore)
					{
						// 이동 시작 시 만남 상태 리셋 (다음에 다시 만나면 OnMeet 발생)
						ClearMeetingsForUnit(unit.Id);

						// 플레이어와 같은 위치에서 이동 시작 → "떠났다" 알림
						if (unit.Id != playerId && currentLoc == playerLocation)
						{
							NotifyNpcDeparture(unit);
						}
					}
				}

				_lastLocations[unit.Id] = currentLoc;

				// 이동 상태 갱신
				if (isMoving)
					_wasMoving.Add(unit.Id);
				else
					_wasMoving.Remove(unit.Id);
			}
		}

		/// <summary>
		/// NPC가 플레이어 위치를 떠났음을 액션 로그로 알림
		/// 이동 중인 경우 Edge의 목적지, 아니면 현재 위치를 사용
		/// </summary>
		private void NotifyNpcDeparture(Unit unit)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var terrain = worldSystem.GetTerrain();

			// 이동 중이면 Edge의 목적지, 아니면 현재 위치
			LocationRef destination;
			if (unit.CurrentEdge != null)
			{
				destination = unit.CurrentEdge.To;
			}
			else
			{
				destination = unit.CurrentLocation;
			}

			var destLocation = terrain.GetLocation(destination);
			var destRegion = destLocation != null ? terrain.GetRegion(destLocation.RegionId) : null;

			string destName = destLocation.Name ?? "어딘가";
			if (destRegion != null && destRegion.Name != "unknown")
			{
				destName = $"{destRegion.Name} {destLocation.Name}";
			}

			var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;
			_textUISystem.AddActionLog($"{unit.Name}(이)가 {destName}(으)로 이동했다.");
		}

		/// <summary>
		/// 같은 위치에 있는 유닛들의 OnMeet 이벤트 생성
		/// StayDuration으로 경유지에서 체류하므로, 현재 위치만 체크하면 됨
		/// </summary>
		public void DetectMeetings()
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

			var playerId = _playerSystem.PlayerId;
			var player = _unitSystem.FindUnit(playerId);
			if (player == null) return;

			var playerLocation = player.CurrentLocation;

			// 플레이어와 같은 위치에 있는 유닛 수집
			// 이동 중인 유닛(CurrentEdge != null)은 제외 (화면에 표시되지 않음)
			var unitsToMeet = _unitSystem.Units.Values
				.Where(u => u.Id != playerId
						 && u.GeneratesEvents
						 && u.CurrentLocation == playerLocation
						 && u.CurrentEdge == null)  // 이동 중이 아닌 유닛만
				.Select(u => u.Id)
				.OrderBy(id => id)  // 정렬하여 키 정규화
				.ToList();

#if DEBUG_LOG
			// 플레이어 위치에 있는 모든 NPC 확인 (이동 중 포함)
			var allUnitsAtLocation = _unitSystem.Units.Values
				.Where(u => u.Id != playerId && u.GeneratesEvents && u.CurrentLocation == playerLocation)
				.ToList();
			if (allUnitsAtLocation.Count > 0)
			{
				GD.Print($"[EventSystem] DetectMeetings at {playerLocation}: {allUnitsAtLocation.Count} units here");
				foreach (var u in allUnitsAtLocation)
				{
					GD.Print($"  - Unit {u.Id} ({u.Name}): Edge={u.CurrentEdge != null}, toMeet={unitsToMeet.Contains(u.Id)}");
				}
			}
#endif

			if (unitsToMeet.Count == 0) return;

			// 만남 키 생성 (플레이어 + 다른 유닛들, 정렬됨)
			var allIds = new List<int> { playerId };
			allIds.AddRange(unitsToMeet);
			allIds.Sort();
			var meetingKey = string.Join(",", allIds);

			// 이미 발생한 만남인지 확인
			if (_lastMeetings.Contains(meetingKey))
			{
#if DEBUG_LOG
				GD.Print($"[EventSystem] Meeting already happened: {meetingKey}");
#endif
				return;
			}

			// 새로운 만남 기록 및 이벤트 생성
#if DEBUG_LOG
			GD.Print($"[EventSystem] New meeting detected: {meetingKey}");
#endif
			AddMeetingKey(meetingKey, allIds.ToArray());
			Enqueue(GameEvent.OnMeet(allIds.ToArray()));
		}

		/// <summary>
		/// 이벤트 큐 플러시 및 Python 호출 (순차 처리)
		/// 각 이벤트를 하나씩 처리하고, 다이얼로그가 발생하면 나머지는 큐에 유지
		/// </summary>
		/// <returns>처리 결과 (모놀로그 표시 시 true)</returns>
		public bool FlushEvents()
		{
			if (_pendingEvents.Count == 0) return false;

#if DEBUG_LOG
			GD.Print($"[EventSystem] Flushing {_pendingEvents.Count} events (sequential)");
#endif

			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			// 이벤트를 하나씩 순차 처리
			while (_pendingEvents.Count > 0)
			{
				var evt = _pendingEvents[0];
				_pendingEvents.RemoveAt(0);

#if DEBUG_LOG
				GD.Print($"[EventSystem] Processing event: {evt}");
#endif

				var result = _scriptSystem.CallSingleEventHandler(evt);

				// 다이얼로그가 발생하면 처리하고 중단 (나머지 이벤트는 큐에 유지)
				if (ProcessEventResult(result))
				{
#if DEBUG_LOG
					GD.Print($"[EventSystem] Dialog triggered, {_pendingEvents.Count} events remaining in queue");
#endif
					return true;
				}
			}

			return false;
		}

		/// <summary>
		/// 이벤트 결과 처리
		/// </summary>
		private bool ProcessEventResult(ScriptResult? result)
		{
			if (result == null) return false;

			var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;

			// Generator가 Dialog를 yield한 경우만 처리
			if (result.Type == "generator_dialog" && result is GeneratorScriptResult genResult)
			{
				// MetaActionHandler에 Generator와 DialogRequest 설정
				_metaActionHandler.SetPendingGenerator(genResult.Generator, genResult.DialogRequest);

				// 다이얼로그 아래에 Situation이 있어야 Pop 후 정상 동작
				if (_textUISystem != null && _textUISystem.IsStackEmpty())
				{
					_textUISystem.ShowSituation();
				}

				// Dialog 표시
				_textUISystem.PushDialog(genResult.DialogText);
#if DEBUG_LOG
				GD.Print($"[EventSystem] Generator dialog: {genResult.DialogText.Substring(0, System.Math.Min(50, genResult.DialogText.Length))}...");
#endif
				return true;
			}

			return false;
		}

		/// <summary>
		/// 만남 키 등록 (역방향 인덱스도 갱신)
		/// </summary>
		private void AddMeetingKey(string meetingKey, int[] unitIds)
		{
			_lastMeetings.Add(meetingKey);
			foreach (var id in unitIds)
			{
				if (!_unitToMeetings.ContainsKey(id))
					_unitToMeetings[id] = new HashSet<string>();
				_unitToMeetings[id].Add(meetingKey);
			}
		}

		/// <summary>
		/// 특정 유닛의 만남 상태 제거 (역방향 인덱스 활용)
		/// </summary>
		private void ClearMeetingsForUnit(int unitId)
		{
			if (_unitToMeetings.TryGetValue(unitId, out var keys))
			{
				foreach (var key in keys)
					_lastMeetings.Remove(key);
				_unitToMeetings.Remove(unitId);
			}
		}

		/// <summary>
		/// Proc은 빈 구현 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
