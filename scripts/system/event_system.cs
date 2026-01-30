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
	/// - 유닛 만남 감지 (OnMeet) - 같은 Location 기준
	/// - 유닛 접촉 감지 (OnContact) - 2D 충돌 반경 기준
	/// - 이벤트 배치 처리 후 Python on_event_list() 호출
	/// - Pi-World: 2D 좌표 기반 충돌 감지
	/// </summary>
	public class EventSystem : ECS.System
	{
		// Pi-World: 2D 충돌 감지 반경 (단위) - OnContact용
		private const float COLLISION_RADIUS = 5f;

		// 이번 Step에서 발생한 이벤트 큐
		private readonly List<GameEvent> _pendingEvents = new();

		private MetaActionHandler? _metaActionHandler;

		// 이전 상태 추적 (OnReach 감지용)
		private readonly Dictionary<int, LocationRef> _lastLocations = new();

		// 이동 시작 감지용 (이전 Step에서 이동 중이었는지)
		// Pi-World: CurrentMovement가 있으면 이동 중
		private readonly HashSet<int> _wasMoving = new();

		// OnMeet 중복 방지
		private readonly HashSet<string> _lastMeetings = new();
		// 역방향 인덱스: 유닛 ID → 해당 유닛이 포함된 만남 키 집합
		private readonly Dictionary<int, HashSet<string>> _unitToMeetings = new();

		// OnContact 중복 방지
		private readonly HashSet<string> _lastContacts = new();
		private readonly Dictionary<int, HashSet<string>> _unitToContacts = new();

		// 초기화 완료 여부 (첫 Step에서 위치 초기화용)
		private bool _initialized = false;

		// 다이얼로그 시간 경과 (set_npc_time_consume에서 누적, 밀리초)
		private int _dialogTimeConsumed = 0;

		// ExcessTime: 다이얼로그가 NextStepDuration을 초과한 시간 (밀리초)
		// PlayerSystem에서 ConsumeExcessTime()으로 가져가서 적용
		private int _excessTime = 0;

		// on_time_elapsed 이벤트 누적 (여러 Step의 시간을 합쳐서 한 번에 전달, 밀리초)
		private int _accumulatedTimeElapsed = 0;

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
			_lastContacts.Clear();
			_unitToContacts.Clear();
			_initialized = false;
			_dialogTimeConsumed = 0;
			_excessTime = 0;
			_accumulatedTimeElapsed = 0;
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
		/// on_time_elapsed 이벤트는 누적하여 FlushEvents 시 한 번에 전달
		/// </summary>
		public void Enqueue(GameEvent evt)
		{
			// on_time_elapsed 이벤트는 누적 처리
			if (evt.Type == EventType.OnTimeElapsed && evt.Args.Count > 0 && evt.Args[0] is int millis)
			{
				_accumulatedTimeElapsed += millis;
				return;
			}

			_pendingEvents.Add(evt);
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
		/// <param name="duration">경과할 시간 (밀리초)</param>
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
			{
				int exMin = _excessTime / GameTime.MillisPerMinute;
				GD.Print($"[EventSystem] ExcessTime 계산: {lastDialogTime} - {nextStepDuration} = {_excessTime}ms ({exMin}분)");
			}
#endif
		}

		/// <summary>
		/// ExcessTime 반환 및 리셋
		/// PlayerSystem에서 호출하여 _remainingDuration에 추가
		/// </summary>
		/// <returns>초과 시간 (밀리초)</returns>
		public int ConsumeExcessTime()
		{
			var result = _excessTime;
			_excessTime = 0;
#if DEBUG_LOG
			if (result > 0)
			{
				int resMin = result / GameTime.MillisPerMinute;
				GD.Print($"[EventSystem] ConsumeExcessTime: {resMin}분 ({result}ms)");
			}
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
		/// Pi-World: CurrentMovement도 이동 상태로 처리
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
				// Pi-World: CurrentMovement가 있으면 이동 중
				var isMoving = unit.CurrentMovement != null;
				var wasMovingBefore = _wasMoving.Contains(unit.Id);

				if (_lastLocations.TryGetValue(unit.Id, out var lastLoc))
				{
					if (currentLoc != lastLoc)
					{
						// 위치가 변경됨 → OnReach 이벤트 생성
						Enqueue(GameEvent.OnReach(unit.Id, currentLoc.RegionId, currentLoc.LocalId));

						// 해당 유닛의 만남/접촉 상태 리셋
						ClearMeetingsForUnit(unit.Id);
						ClearContactsForUnit(unit.Id);

						// 플레이어 위치를 떠난 NPC → 액션 로그
						if (unit.Id != playerId && lastLoc == playerLocation)
						{
							NotifyNpcDeparture(unit);
						}
					}
					// 위치는 같지만 이동을 시작한 경우 (화면에서 사라짐)
					else if (isMoving && !wasMovingBefore)
					{
						// 이동 시작 시 만남/접촉 상태 리셋 (다음에 다시 만나면 이벤트 발생)
						ClearMeetingsForUnit(unit.Id);
						ClearContactsForUnit(unit.Id);

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
		/// 이동 중인 경우 Gate의 목적지, 아니면 현재 위치를 사용
		/// Pi-World: CurrentMovement의 TargetGateId로 목적지 확인
		/// </summary>
		private void NotifyNpcDeparture(Unit unit)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var terrain = worldSystem.GetTerrain();

			// 이동 중이면 목적지, 아니면 현재 위치
			LocationRef destination;
			if (unit.CurrentMovement != null && unit.CurrentMovement.TargetGateId.HasValue)
			{
				// Pi-World: Gate 통과 이동 중이면 연결된 Location
				var region = terrain.GetRegion(unit.CurrentLocation.RegionId);
				var gate = region?.GetGate(unit.CurrentLocation.LocalId, unit.CurrentMovement.TargetGateId.Value);
				destination = gate?.ConnectedLocation ?? unit.CurrentLocation;
			}
			else
			{
				destination = unit.CurrentLocation;
			}

			var destLocation = terrain.GetLocation(destination);
			var destRegion = destLocation != null ? terrain.GetRegion(destLocation.RegionId) : null;

			string destName = destLocation?.Name ?? "어딘가";
			if (destRegion != null && destRegion.Name != "unknown")
			{
				destName = $"{destRegion.Name} {destLocation.Name}";
			}

			var _actionLogSystem = this._hub.GetSystem("actionLogSystem") as ActionLogSystem;
			_actionLogSystem?.AddLog($"{unit.Name}(이)가 {destName}(으)로 이동했다.");
		}

		/// <summary>
		/// 같은 Location에 있는 유닛들의 OnMeet 이벤트 생성
		///
		/// 만남 조건: 같은 Location에 있으면 트리거 (Pi-World/Legacy 공통)
		/// - 정지 상태 (CurrentMovement == null)
		/// - 또는 방금 도착 (이전 위치 != 현재 위치, 경유지 통과)
		///
		/// 시간 정지 상태에서는 스킵 (NPC와 상호작용 불가)
		/// </summary>
		public void DetectMeetings()
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

			// 시간 정지 상태에서는 on_meet 이벤트 스킵
			if (_worldSystem.IsTimeFrozen())
				return;

			var playerId = _playerSystem.PlayerId;
			var player = _unitSystem.FindUnit(playerId);
			if (player == null) return;

			var playerLocation = player.CurrentLocation;

			// 플레이어와 같은 Location에 있는 유닛 수집
			var unitsToMeet = new List<int>();

			foreach (var unit in _unitSystem.Units.Values)
			{
				if (unit.Id == playerId) continue;
				if (!unit.GeneratesEvents) continue;
				if (unit.CurrentLocation != playerLocation) continue;

				// 정지 상태면 만남
				if (unit.CurrentMovement == null)
				{
					unitsToMeet.Add(unit.Id);
					continue;
				}

				// 방금 도착 (이동 중이지만 이전 위치와 다름 = 경유지 통과)
				if (_lastLocations.TryGetValue(unit.Id, out var lastLoc))
				{
					if (lastLoc != unit.CurrentLocation)
					{
						unitsToMeet.Add(unit.Id);
					}
				}
			}

			unitsToMeet.Sort();  // 정렬하여 키 정규화

			if (unitsToMeet.Count == 0)
				return;

			// 만남 키 생성 (플레이어 + 다른 유닛들, 정렬됨)
			var allIds = new List<int> { playerId };
			allIds.AddRange(unitsToMeet);
			allIds.Sort();
			var meetingKey = string.Join(",", allIds);

			// 이미 발생한 만남인지 확인
			if (_lastMeetings.Contains(meetingKey))
				return;

			// 새로운 만남 기록 및 이벤트 생성
			AddMeetingKey(meetingKey, allIds.ToArray());
			Enqueue(GameEvent.OnMeet(allIds.ToArray()));

#if DEBUG_LOG
			var unitNames = allIds.Select(id => _unitSystem.FindUnit(id)?.Name ?? id.ToString());
			GD.Print($"[EventSystem] OnMeet: [{string.Join(", ", unitNames)}] at {playerLocation}");
#endif
		}

		/// <summary>
		/// 2D 충돌 반경 내 접촉한 유닛들의 OnContact 이벤트 생성 (Pi-World 전용)
		///
		/// 접촉 조건:
		/// - 같은 Location에 있어야 함
		/// - 2D 좌표 거리가 COLLISION_RADIUS 이내
		/// - 정지 상태 또는 이동 중 모두 포함
		///
		/// 시간 정지 상태에서는 스킵
		/// </summary>
		public void DetectContacts()
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

			// 시간 정지 상태에서는 on_contact 이벤트 스킵
			if (_worldSystem.IsTimeFrozen())
				return;

			var playerId = _playerSystem.PlayerId;
			var player = _unitSystem.FindUnit(playerId);
			if (player == null) return;

			var playerLocation = player.CurrentLocation;

			// Pi-World 2D 모드 확인
			var terrain = _worldSystem.GetTerrain();
			var location = terrain?.GetLocation(playerLocation);
			if (location == null) return;  // Legacy 모드에서는 on_contact 미지원

			// 플레이어와 같은 Location에서 충돌 반경 내 유닛 수집
			var unitsInContact = new List<int>();

			float playerX = player.CurrentMovement?.CurrentX ?? player.PositionX;

			foreach (var unit in _unitSystem.Units.Values)
			{
				if (unit.Id == playerId) continue;
				if (!unit.GeneratesEvents) continue;
				if (unit.CurrentLocation != playerLocation) continue;

				float unitX = unit.CurrentMovement?.CurrentX ?? unit.PositionX;
				float distance = location.CalculateDistance(playerX, unitX);

				if (distance <= COLLISION_RADIUS)
				{
					unitsInContact.Add(unit.Id);
#if DEBUG_LOG
					GD.Print($"[EventSystem] OnContact: {player.Name}(X={playerX:F1}) - {unit.Name}(X={unitX:F1}), dist={distance:F1}");
#endif
				}
			}

			// Pi-World: 이동 중 교차 충돌 감지 (같은 Location)
			if (player.CurrentMovement != null)
			{
				var movement2DContacts = Detect2DMovementContacts(player, _unitSystem, location);
				foreach (var unitId in movement2DContacts)
				{
					if (!unitsInContact.Contains(unitId))
					{
						unitsInContact.Add(unitId);
					}
				}
			}

			// Pi-World: Gate 교차 충돌 감지 (서로 다른 Location에서 같은 Gate 쌍으로 이동)
			if (terrain != null && player.CurrentMovement?.TargetGateId != null)
			{
				var gateCrossingContacts = DetectGateCrossingContacts(player, _unitSystem, terrain);
				foreach (var unitId in gateCrossingContacts)
				{
					if (!unitsInContact.Contains(unitId))
					{
						unitsInContact.Add(unitId);
					}
				}
			}

			unitsInContact.Sort();

			if (unitsInContact.Count == 0)
				return;

			// 접촉 키 생성 (플레이어 + 다른 유닛들, 정렬됨)
			var allIds = new List<int> { playerId };
			allIds.AddRange(unitsInContact);
			allIds.Sort();
			var contactKey = string.Join(",", allIds);

			// 이미 발생한 접촉인지 확인
			if (_lastContacts.Contains(contactKey))
				return;

			// 새로운 접촉 기록 및 이벤트 생성
			AddContactKey(contactKey, allIds.ToArray());
			Enqueue(GameEvent.OnContact(allIds.ToArray()));
		}

		/// <summary>
		/// Pi-World: 2D 이동 중 접촉 감지
		/// 플레이어와 같은 Location에서 이동 중인 유닛 중 교차/근접하는 유닛 반환
		/// </summary>
		private List<int> Detect2DMovementContacts(Unit player, UnitSystem unitSystem, Location location)
		{
			var result = new List<int>();
			var playerMovement = player.CurrentMovement;
			if (playerMovement == null) return result;

			foreach (var unit in unitSystem.Units.Values)
			{
				if (unit.Id == player.Id) continue;
				if (unit.IsObject) continue;
				if (!unit.GeneratesEvents) continue;
				if (unit.CurrentLocation != player.CurrentLocation) continue;

				// 현재 위치 기준 거리 계산
				float playerCurrentX = playerMovement.CurrentX;
				float unitCurrentX = unit.CurrentMovement?.CurrentX ?? unit.PositionX;

				float distance = location.CalculateDistance(playerCurrentX, unitCurrentX);
				if (distance <= COLLISION_RADIUS)
				{
#if DEBUG_LOG
					GD.Print($"[EventSystem] 2D movement contact: {player.Name}(X={playerCurrentX:F1}) - {unit.Name}(X={unitCurrentX:F1}), dist={distance:F1}");
#endif
					result.Add(unit.Id);
				}
			}

			return result;
		}

		/// <summary>
		/// Pi-World: Gate 교차 접촉 감지 (플레이어 전용)
		/// 플레이어가 Gate를 통해 이동 중일 때, 반대편 Location에서 같은 Gate 쌍을 통해
		/// 반대 방향으로 이동 중인 NPC를 감지
		///
		/// 예시:
		///   Location A -- Gate --> Location B
		///   P: A에서 Gate로 이동 중 (→ B로 갈 예정)
		///   N: B에서 Gate로 이동 중 (→ A로 갈 예정)
		///   → 두 유닛이 Gate에서 교차 → on_contact 발생
		///
		/// ※ 플레이어 전용 특수 처리:
		///   다이얼로그 이벤트는 플레이어 중심이므로, 플레이어-NPC 교차 시에만
		///   NPC를 플레이어의 목적지(B)로 이동시킴.
		///   → 다이얼로그 종료 후 P와 N이 같은 Location(B)에 있음
		///
		/// ※ NPC끼리 교차하는 경우:
		///   이 메서드는 플레이어 기준으로만 동작하므로 NPC끼리의 교차는 감지하지 않음.
		///   NPC끼리 교차 시에는 각자 원래 목적지로 이동 (N1→B, N2→A)
		/// </summary>
		private List<int> DetectGateCrossingContacts(Unit player, UnitSystem unitSystem, Terrain terrain)
		{
			var result = new List<int>();
			var playerMovement = player.CurrentMovement;

			// 플레이어가 Gate로 이동 중이어야 함
			if (playerMovement?.TargetGateId == null) return result;

			// 플레이어가 향하는 Gate 정보 가져오기
			var playerRegion = terrain.GetRegion(player.CurrentLocation.RegionId);
			var playerGate = playerRegion?.GetGate(player.CurrentLocation.LocalId, playerMovement.TargetGateId.Value);
			if (playerGate == null) return result;

			// 플레이어가 도착할 Location (Gate의 연결 대상)
			var connectedLocation = playerGate.ConnectedLocation;

			// 연결된 Location에 있는 NPC 중, 플레이어 Location으로 연결된 Gate로 이동 중인 NPC 찾기
			foreach (var unit in unitSystem.Units.Values)
			{
				if (unit.Id == player.Id) continue;
				if (unit.IsObject) continue;
				if (!unit.GeneratesEvents) continue;

				// NPC가 플레이어의 목적지 Location에 있어야 함
				if (unit.CurrentLocation != connectedLocation) continue;

				// NPC도 Gate로 이동 중이어야 함
				if (unit.CurrentMovement?.TargetGateId == null) continue;

				// NPC가 향하는 Gate 정보 가져오기
				var unitRegion = terrain.GetRegion(unit.CurrentLocation.RegionId);
				var unitGate = unitRegion?.GetGate(unit.CurrentLocation.LocalId, unit.CurrentMovement.TargetGateId.Value);
				if (unitGate == null) continue;

				// NPC의 Gate가 플레이어의 현재 Location으로 연결되어 있는지 확인
				if (unitGate.ConnectedLocation == player.CurrentLocation)
				{
					// Gate 교차 발생!
					// ※ 다이얼로그는 플레이어 중심이므로, NPC를 플레이어의 목적지(B)로 이동시킴
					//   이렇게 하면 다이얼로그 종료 후 P와 N이 같은 Location에 있음
					unit.CurrentMovement = null;  // 이동 취소
					unit.SetLocation(connectedLocation);  // 플레이어 목적지로 이동
					unit.PositionX = playerGate.ArrivalX;  // Gate 도착 위치

#if DEBUG_LOG
					GD.Print($"[EventSystem] Gate crossing contact: {player.Name}({player.CurrentLocation} → Gate{playerGate.Id}) × {unit.Name} → moved to {connectedLocation}(X={playerGate.ArrivalX:F1})");
#endif
					result.Add(unit.Id);
				}
			}

			return result;
		}

		/// <summary>
		/// 이벤트 큐 플러시 및 Python 호출 (순차 처리)
		/// 각 이벤트를 하나씩 처리하고, 다이얼로그가 발생하면 나머지는 큐에 유지
		/// 누적된 on_time_elapsed는 먼저 처리
		/// </summary>
		/// <returns>처리 결과 (모놀로그 표시 시 true)</returns>
		public bool FlushEvents()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			// 1. 누적된 on_time_elapsed 이벤트 먼저 처리
			if (_accumulatedTimeElapsed > 0)
			{
				var timeEvent = GameEvent.OnTimeElapsed(_accumulatedTimeElapsed);
				_accumulatedTimeElapsed = 0;

				var timeResult = _scriptSystem.CallSingleEventHandler(timeEvent);
				// on_time_elapsed는 다이얼로그를 발생시키지 않으므로 결과 무시
			}

			if (_pendingEvents.Count == 0) return false;

			// 2. 나머지 이벤트 순차 처리
			while (_pendingEvents.Count > 0)
			{
				var evt = _pendingEvents[0];
				_pendingEvents.RemoveAt(0);

				var result = _scriptSystem.CallSingleEventHandler(evt);

				// 다이얼로그가 발생하면 처리하고 중단 (나머지 이벤트는 큐에 유지)
				if (ProcessEventResult(result))
				{
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

				// Dialog 표시 (PyDialogRequest.TimeFlows를 Focus에 전달)
				bool timeFlows = genResult.DialogRequest?.TimeFlows ?? false;
				_textUISystem.PushDialog(genResult.DialogText, timeConsumed: 0, timeFlows: timeFlows);
				return true;
			}

			return false;
		}

		#region Meeting Key Management

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

		#endregion

		#region Contact Key Management

		/// <summary>
		/// 접촉 키 등록 (역방향 인덱스도 갱신)
		/// </summary>
		private void AddContactKey(string contactKey, int[] unitIds)
		{
			_lastContacts.Add(contactKey);
			foreach (var id in unitIds)
			{
				if (!_unitToContacts.ContainsKey(id))
					_unitToContacts[id] = new HashSet<string>();
				_unitToContacts[id].Add(contactKey);
			}
		}

		/// <summary>
		/// 특정 유닛의 접촉 상태 제거 (역방향 인덱스 활용)
		/// </summary>
		private void ClearContactsForUnit(int unitId)
		{
			if (_unitToContacts.TryGetValue(unitId, out var keys))
			{
				foreach (var key in keys)
					_lastContacts.Remove(key);
				_unitToContacts.Remove(unitId);
			}
		}

		#endregion

		/// <summary>
		/// Focus 시 on_meet 이벤트 체크 및 발동
		/// 플레이어가 캐릭터를 Focus할 때 호출됩니다.
		/// 조건: 같은 Location, 시간 정지가 아닐 것
		/// </summary>
		/// <param name="focusedUnitId">Focus된 유닛 ID</param>
		/// <returns>on_meet 이벤트가 발동되었으면 true</returns>
		public bool TriggerOnMeetForFocus(int focusedUnitId)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

			// 시간 정지 상태에서는 on_meet 이벤트 스킵
			if (_worldSystem.IsTimeFrozen())
				return false;

			var playerId = _playerSystem.PlayerId;
			var player = _unitSystem.FindUnit(playerId);
			if (player == null) return false;

			var focusedUnit = _unitSystem.FindUnit(focusedUnitId);
			if (focusedUnit == null) return false;
			if (focusedUnit.Id == playerId) return false;
			if (!focusedUnit.GeneratesEvents) return false;

			// 같은 Location인지 확인
			if (focusedUnit.CurrentLocation != player.CurrentLocation)
				return false;

			// 만남 키 생성 및 중복 체크
			var allIds = new List<int> { playerId, focusedUnitId };
			allIds.Sort();
			var meetingKey = string.Join(",", allIds);

			if (_lastMeetings.Contains(meetingKey))
			{
#if DEBUG_LOG
				GD.Print($"[EventSystem] Focus on_meet skipped: already met {focusedUnit.Name}");
#endif
				return false;
			}

			// 새로운 만남 기록 및 이벤트 생성
			AddMeetingKey(meetingKey, allIds.ToArray());
			Enqueue(GameEvent.OnMeet(allIds.ToArray()));

#if DEBUG_LOG
			GD.Print($"[EventSystem] Focus on_meet triggered: {player.Name} - {focusedUnit.Name}");
#endif

			return true;
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
