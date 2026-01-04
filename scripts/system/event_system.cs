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

		// 시스템 참조
		private ScriptSystem? _scriptSystem;
		private TextUISystem? _textUISystem;
		private UnitSystem? _unitSystem;
		private PlayerSystem? _playerSystem;

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

		public EventSystem()
		{
		}

		/// <summary>
		/// 시스템 참조 설정
		/// </summary>
		public void SetSystemReferences(
			ScriptSystem? scriptSystem,
			TextUISystem? textUISystem,
			UnitSystem? unitSystem,
			PlayerSystem? playerSystem)
		{
			_scriptSystem = scriptSystem;
			_textUISystem = textUISystem;
			_unitSystem = unitSystem;
			_playerSystem = playerSystem;
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
			if (_unitSystem == null) return;

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
		/// 위치 변경 감지 및 OnReach 이벤트 생성
		/// 플레이어 위치를 떠난 NPC는 액션 로그로 알림
		/// 이동 시작한 NPC도 "떠났다" 알림 (화면에서 사라지므로)
		/// </summary>
		public void DetectLocationChanges()
		{
			if (_unitSystem == null) return;

			// 초기화 안 됐으면 먼저 초기화
			if (!_initialized)
			{
				InitializeLocations();
				return;
			}

			var playerId = _playerSystem?.PlayerId ?? -1;
			var player = playerId >= 0 ? _unitSystem.GetUnit(playerId) : null;
			var playerLocation = player?.CurrentLocation;

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
						if (unit.Id != playerId && playerLocation.HasValue && lastLoc == playerLocation.Value)
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
						if (unit.Id != playerId && playerLocation.HasValue && currentLoc == playerLocation.Value)
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
			var worldSystem = _hub?.FindSystem("worldSystem") as WorldSystem;
			var terrain = worldSystem?.GetTerrain();

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

			var destLocation = terrain?.GetLocation(destination);
			var destRegion = destLocation != null ? terrain?.GetRegion(destLocation.RegionId) : null;

			string destName = destLocation?.Name ?? "어딘가";
			if (destRegion != null && destRegion.Name != "unknown")
			{
				destName = $"{destRegion.Name} {destLocation?.Name}";
			}

			_textUISystem?.AddActionLog($"{unit.Name}(이)가 {destName}(으)로 이동했다.");
		}

		/// <summary>
		/// 같은 위치에 있는 유닛들의 OnMeet 이벤트 생성
		/// StayDuration으로 경유지에서 체류하므로, 현재 위치만 체크하면 됨
		/// </summary>
		public void DetectMeetings()
		{
			if (_unitSystem == null || _playerSystem == null) return;

			var playerId = _playerSystem.PlayerId;
			var player = _unitSystem.GetUnit(playerId);
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

			if (unitsToMeet.Count == 0) return;

			// 만남 키 생성 (플레이어 + 다른 유닛들, 정렬됨)
			var allIds = new List<int> { playerId };
			allIds.AddRange(unitsToMeet);
			allIds.Sort();
			var meetingKey = string.Join(",", allIds);

			// 이미 발생한 만남인지 확인
			if (_lastMeetings.Contains(meetingKey)) return;

			// 새로운 만남 기록 및 이벤트 생성
			AddMeetingKey(meetingKey, allIds.ToArray());
			Enqueue(GameEvent.OnMeet(allIds.ToArray()));
		}

		/// <summary>
		/// 이벤트 큐 플러시 및 Python 호출
		/// </summary>
		/// <returns>처리 결과 (모놀로그 표시 시 true)</returns>
		public bool FlushEvents()
		{
			if (_pendingEvents.Count == 0) return false;

#if DEBUG_LOG
			GD.Print($"[EventSystem] Flushing {_pendingEvents.Count} events");
#endif

			// Python에 이벤트 리스트 전달
			var result = _scriptSystem?.CallEventHandler(_pendingEvents);
			_pendingEvents.Clear();

			// 결과 처리 (모놀로그 등)
			return ProcessEventResult(result);
		}

		/// <summary>
		/// 이벤트 결과 처리
		/// </summary>
		private bool ProcessEventResult(ScriptResult? result)
		{
			if (result == null) return false;

			switch (result.Type)
			{
				case "monologue":
					if (result is MonologueScriptResult monoResult)
					{
						// npc_jobs: 지정된 유닛들에게 Job 적용
						if (monoResult.NpcJobs.Count > 0)
						{
							ApplyNpcJobs(monoResult.NpcJobs);
						}

						// 모놀로그 아래에 Situation이 있어야 Pop 후 정상 동작
						// 스택이 비어있으면 먼저 Situation Push
						if (_textUISystem != null && _textUISystem.IsStackEmpty())
						{
							_textUISystem.ShowSituation();
						}

						_textUISystem?.ShowMonologue(
							monoResult.Pages,
							monoResult.TimeConsumed,
							monoResult.ButtonType,
							monoResult.DoneCallback,
							monoResult.CancelCallback);
						return true;
					}
					break;
			}

			return false;
		}

		/// <summary>
		/// 지정된 유닛들에게 Job 적용
		/// JobList 맨 앞에 Job을 삽입하여 즉시 실행되도록 함
		/// </summary>
		/// <param name="npcJobs">unit_id → NpcJobInfo 매핑</param>
		private void ApplyNpcJobs(System.Collections.Generic.Dictionary<int, SE.NpcJobInfo> npcJobs)
		{
			if (_unitSystem == null || _playerSystem == null) return;

			foreach (var kvp in npcJobs)
			{
				var unitId = kvp.Key;
				var jobInfo = kvp.Value;

				var unit = _unitSystem.GetUnit(unitId);
				if (unit == null || unit.IsObject) continue;

				// 이동 중이었다면 중단
				unit.CurrentEdge = null;
				unit.RemainingStayTime = 0;

				// 이동 추적 상태 동기화 (DetectLocationChanges에서 "이동했다" 로그 방지)
				// NPC Job이 적용되면 현재 위치에서 새 행동을 시작하므로
				// 이전 이동 상태를 무효화
				_wasMoving.Remove(unitId);
				_lastLocations[unitId] = unit.CurrentLocation;

				// JobList 클리어 후 새 Job 삽입
				var job = new Morld.Job
				{
					Name = jobInfo.Action == "follow" ? "따라가기" : "대기",
					Action = jobInfo.Action,  // "follow", "stay" 등
					Duration = jobInfo.Duration,
					TargetId = jobInfo.Action == "follow" ? _playerSystem.PlayerId : null
				};
				unit.JobList.InsertWithClear(job);
			}
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
