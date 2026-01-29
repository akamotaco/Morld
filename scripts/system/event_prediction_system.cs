using System;
using System.Collections.Generic;
using System.Linq;
using ECS;
using Godot;
using Morld;

namespace SE
{
	/// <summary>
	/// EventPredictionSystem - 이벤트 예측 및 시간 조정 시스템
	///
	/// 역할:
	/// 1. 플레이어/NPC 이동 경로 분석하여 만남 예측
	/// 2. 시간 중단 이벤트 중 가장 빠른 것 찾기
	/// 3. PlayerSystem.NextStepDuration 조정
	///
	/// 실행 순서: ThinkSystem → EventPredictionSystem → JobBehaviorSystem → EventSystem
	/// </summary>
	public class EventPredictionSystem : ECS.System
	{
		/// <summary>
		/// 예측된 이벤트 목록
		/// </summary>
		private List<PredictedEvent> _predictedEvents = new();

		/// <summary>
		/// 마지막으로 조정된 시간 (디버그용)
		/// </summary>
		public int LastAdjustedDuration { get; private set; } = 0;


		/// <summary>
		/// 매 Step마다 호출
		///
		/// 만남 및 도착 이벤트를 예측하고, 가장 빠른 시간 중단 이벤트에 맞춰
		/// NextStepDuration을 조정합니다.
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

			// 시간 진행 대기 중이 아니면 스킵
			if (!_playerSystem.HasPendingTime)
				return;

			int pendingDuration = _playerSystem.NextStepDuration;
			if (pendingDuration <= 0)
				return;

			// 이벤트 예측 (만남, 도착, Gate 교차)
			_predictedEvents.Clear();
			PredictMeetings(pendingDuration);
			PredictArrivals(pendingDuration);
			PredictGateCrossings(pendingDuration);

			// 시간 중단 이벤트 중 가장 빠른 것 찾기
			var earliestInterrupt = FindEarliestInterrupt();

			if (earliestInterrupt != null && earliestInterrupt.TriggerMinutes < pendingDuration)
			{
				// 시간 조정 (최소 1분)
				int adjustedDuration = Math.Max(1, earliestInterrupt.TriggerMinutes);
				_playerSystem.AdjustNextStepDuration(adjustedDuration);
				LastAdjustedDuration = adjustedDuration;
			}
			else
			{
				LastAdjustedDuration = 0;
			}
		}

		/// <summary>
		/// 만남 이벤트 예측
		/// 플레이어와 NPC가 같은 위치에 도달하는 시점 계산
		/// </summary>
		private void PredictMeetings(int duration)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

			var player = _playerSystem.FindPlayerUnit();
			var terrain = _worldSystem.GetTerrain();

			// 플레이어 경로 계산
			var playerRoute = GetMovementRoute(player, duration, terrain);
			if (playerRoute == null || playerRoute.Count == 0) return;

			// 모든 NPC 체크
			foreach (var unit in _unitSystem!.Units.Values)
			{
				if (unit.Id == player.Id) continue;
				if (unit.IsObject) continue;
				if (!unit.GeneratesEvents) continue;

				// NPC 경로 계산
				var npcRoute = GetMovementRoute(unit, duration, terrain);
				if (npcRoute == null || npcRoute.Count == 0) continue;

				// 만남 시점 계산
				int? meetingTime = FindMeetingTime(playerRoute, npcRoute, duration);

				if (meetingTime.HasValue && meetingTime.Value < duration)
				{
					_predictedEvents.Add(new PredictedEvent
					{
						Type = "on_meet",
						TriggerMinutes = meetingTime.Value,
						InvolvedUnitIds = new List<int> { player.Id, unit.Id },
						InterruptsTime = true,
						Data = new Dictionary<string, object>
						{
							["npc_name"] = unit.Name ?? "Unknown"
						}
					});
				}
			}
		}

		/// <summary>
		/// 도착 이벤트 예측
		/// 플레이어가 새 위치에 도착하는 시점
		/// </summary>
		private void PredictArrivals(int duration)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

			var player = _playerSystem.FindPlayerUnit();
			if (player == null) return;

			// Pi-World: 현재 이동 중이 아니면 스킵
			if (player.CurrentMovement == null) return;

			var terrain = _worldSystem.GetTerrain();
			if (terrain == null) return;

			// 플레이어 경로 계산
			var playerRoute = GetMovementRoute(player, duration, terrain);
			if (playerRoute == null) return;

			foreach (var waypoint in playerRoute)
			{
				if (waypoint.ArrivalTime <= 0 || waypoint.ArrivalTime >= duration)
					continue;

				// 도착 이벤트 추가 (중요 위치 체크는 EventSystem에서 처리)
				_predictedEvents.Add(new PredictedEvent
				{
					Type = "on_reach",
					TriggerMinutes = waypoint.ArrivalTime,
					InvolvedUnitIds = new List<int> { player.Id },
					InterruptsTime = false, // 기본적으로 도착은 중단하지 않음
					Data = new Dictionary<string, object>
					{
						["region_id"] = waypoint.Location.RegionId,
						["location_id"] = waypoint.Location.LocalId
					}
				});
			}
		}

		/// <summary>
		/// 유닛의 이동 경로 계산
		///
		/// 경유지(StayDuration)를 포함한 전체 경로 시뮬레이션:
		/// 1. 현재 이동 완료 시점
		/// 2. 경유지 체류 시간 적용
		/// 3. 다음 이동 계산 (Job 목적지 기준)
		/// 4. duration 내에서 반복
		///
		/// 각 Waypoint에는 도착 시간과 체류 시간이 포함됨
		/// </summary>
		private List<RouteWaypoint>? GetMovementRoute(Unit unit, int duration, Terrain terrain)
		{
			var route = new List<RouteWaypoint>();

			// Job에서 최종 목적지 가져오기
			var currentJob = unit.CurrentJob;
			var goalLocation = (currentJob != null && currentJob.Action == "move")
				? currentJob.GetLocationRef()
				: (LocationRef?)null;

			// Pi-World: 현재 위치에서 정지 상태인지 판단
			bool isStationary = unit.CurrentMovement == null &&
				(goalLocation == null || unit.CurrentLocation == goalLocation);

			// 현재 위치 추가 (ArrivalTime=0)
			route.Add(new RouteWaypoint
			{
				Location = unit.CurrentLocation,
				ArrivalTime = 0,
				StayDuration = isStationary ? duration : 0,  // 정지 상태면 전체 duration 동안 체류
				IsFinalDestination = isStationary
			});

			// move Job이 없으면 현재 위치만 반환 (Pi-World: Gate 통과 시 즉시 이동)
			if (goalLocation == null)
			{
				// Pi-World: 현재 이동 중이면 남은 시간 계산
				if (unit.CurrentMovement != null)
				{
					int remainingTime = unit.CurrentMovement.RemainingTime;
					if (remainingTime > 0 && remainingTime <= duration)
					{
						// 이동 완료 후 현재 Location에 도착 (Gate 통과는 즉시)
						route.Add(new RouteWaypoint
						{
							Location = unit.CurrentLocation,
							ArrivalTime = remainingTime,
							StayDuration = duration - remainingTime,
							IsFinalDestination = true
						});
					}
				}
				return route;
			}

			// 이미 목적지에 있으면 현재 위치만 반환
			if (unit.CurrentLocation == goalLocation)
				return route;

			// Pi-World: Gate 기반 이동 시뮬레이션
			// 현재 이동 중이면 완료 시간 예측
			var currentLocation = unit.CurrentLocation;
			int elapsedTime = 0;
			int remainingStayTime = unit.RemainingStayTime;

			// 현재 이동 완료 시간 계산
			if (unit.CurrentMovement != null)
			{
				int moveTime = unit.CurrentMovement.RemainingTime;
				elapsedTime += moveTime;

				// 이동 완료 후 Gate 통과 시 다음 Location
				if (unit.CurrentMovement.TargetGateId.HasValue)
				{
					var region = terrain.GetRegion(currentLocation.RegionId);
					var gate = region?.GetGate(currentLocation.LocalId, unit.CurrentMovement.TargetGateId.Value);
					if (gate != null)
					{
						currentLocation = gate.ConnectedLocation;
					}
				}

				route.Add(new RouteWaypoint
				{
					Location = currentLocation,
					ArrivalTime = elapsedTime,
					StayDuration = 0,
					IsFinalDestination = (currentLocation == goalLocation)
				});
			}

			// TODO: Pi-World 경로 예측 구현 (Gate 기반)
			// 현재는 단순화하여 현재 이동만 예측

			return route;
		}

		/// <summary>
		/// 두 경로가 만나는 시점 계산
		///
		/// 만남 판정 기준: 두 유닛이 같은 위치에 동시에 존재하는 시간 범위가 있는지 확인
		/// - 각 Waypoint는 [ArrivalTime, DepartureTime] 범위 동안 해당 위치에 존재
		/// - 두 범위가 겹치면 만남 발생
		/// - 겹침의 시작 시점이 만남 시간
		///
		/// 예시:
		/// - 플레이어: B에서 [0, 10] 동안 체류
		/// - NPC: A→B→C, B에서 [5, 5] (경유, StayDuration=0)
		/// - 겹침: [5, 5] → 만남 시간 = 5
		///
		/// - 플레이어: B에서 [0, 10] 동안 체류
		/// - NPC: A→B, B에서 [8, ∞] (도착 후 정지)
		/// - 겹침: [8, 10] → 만남 시간 = 8
		/// </summary>
		private int? FindMeetingTime(List<RouteWaypoint> playerRoute, List<RouteWaypoint> npcRoute, int duration)
		{
			int? earliestMeeting = null;

			foreach (var playerWp in playerRoute)
			{
				foreach (var npcWp in npcRoute)
				{
					// 같은 위치인지 확인
					if (playerWp.Location.RegionId != npcWp.Location.RegionId) continue;
					if (playerWp.Location.LocalId != npcWp.Location.LocalId) continue;

					// 시간 범위 계산
					// [ArrivalTime, DepartureTime] 또는 [ArrivalTime, ArrivalTime] (통과 시)
					int playerStart = playerWp.ArrivalTime;
					int playerEnd = playerWp.IsFinalDestination || playerWp.StayDuration > 0
						? playerWp.DepartureTime
						: playerWp.ArrivalTime;  // 경유 통과는 순간

					int npcStart = npcWp.ArrivalTime;
					int npcEnd = npcWp.IsFinalDestination || npcWp.StayDuration > 0
						? npcWp.DepartureTime
						: npcWp.ArrivalTime;  // 경유 통과는 순간

					// 케이스 1: 둘 다 이미 같은 위치에 있음 (시작 시점) → 스킵
					// 실제 on_meet 이벤트는 EventSystem.DetectMeetings()에서 별도로 감지됨
					if (playerStart == 0 && npcStart == 0)
						continue;

					// 시간 범위 겹침 확인
					// 두 구간 [a1, a2]와 [b1, b2]가 겹치려면: max(a1, b1) <= min(a2, b2)
					int overlapStart = Math.Max(playerStart, npcStart);
					int overlapEnd = Math.Min(playerEnd, npcEnd);

					if (overlapStart <= overlapEnd)
					{
						// 겹침 발생 → 만남 시간 = 겹침 시작 시점
						int meetingTime = overlapStart;

						// 가장 빠른 만남 시간 기록
						if (earliestMeeting == null || meetingTime < earliestMeeting)
						{
							earliestMeeting = meetingTime;
						}
					}
				}
			}

			return earliestMeeting;
		}

		/// <summary>
		/// Pi-World: Gate 교차 충돌 예측
		/// 플레이어와 NPC가 서로 다른 Location에서 같은 Gate 쌍을 반대 방향으로 통과할 때 예측
		///
		/// 예시:
		///   Location A -- Gate --> Location B
		///   P: A에서 Gate로 이동 중 (→ B로 갈 예정), 남은 시간 3분
		///   N: B에서 Gate로 이동 중 (→ A로 갈 예정), 남은 시간 5분
		///   → 교차 시점 = max(3, 5) = 5분
		/// </summary>
		private void PredictGateCrossings(int duration)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

			var player = _playerSystem?.FindPlayerUnit();
			if (player == null) return;

			// 플레이어가 Gate로 이동 중이어야 함
			if (player.CurrentMovement?.TargetGateId == null) return;

			var terrain = _worldSystem.GetTerrain();
			if (terrain == null) return;

			// 플레이어가 Gate에 도달하는 시간
			int playerTimeToGate = player.CurrentMovement.RemainingTime;
			if (playerTimeToGate > duration) return;

			// 플레이어가 향하는 Gate 정보
			var playerRegion = terrain.GetRegion(player.CurrentLocation.RegionId);
			var playerGate = playerRegion?.GetGate(player.CurrentLocation.LocalId, player.CurrentMovement.TargetGateId.Value);
			if (playerGate == null) return;

			var connectedLocation = playerGate.ConnectedLocation;

			// 연결된 Location에서 플레이어 방향으로 이동 중인 NPC 찾기
			foreach (var unit in _unitSystem!.Units.Values)
			{
				if (unit.Id == player.Id) continue;
				if (unit.IsObject) continue;
				if (!unit.GeneratesEvents) continue;

				// NPC가 플레이어의 목적지 Location에 있어야 함
				if (unit.CurrentLocation != connectedLocation) continue;

				// NPC도 Gate로 이동 중이어야 함
				if (unit.CurrentMovement?.TargetGateId == null) continue;

				// NPC의 Gate 정보
				var unitRegion = terrain.GetRegion(unit.CurrentLocation.RegionId);
				var unitGate = unitRegion?.GetGate(unit.CurrentLocation.LocalId, unit.CurrentMovement.TargetGateId.Value);
				if (unitGate == null) continue;

				// NPC의 Gate가 플레이어 Location으로 연결되어 있는지 확인
				if (unitGate.ConnectedLocation != player.CurrentLocation) continue;

				// NPC가 Gate에 도달하는 시간
				int npcTimeToGate = unit.CurrentMovement.RemainingTime;

				// 둘 다 duration 내에 Gate에 도달하면 교차 예측
				// 교차 시점은 둘 중 나중에 Gate에 도달하는 시점 (둘 다 도착해야 교차)
				int crossingTime = Math.Max(playerTimeToGate, npcTimeToGate);

				if (crossingTime <= duration)
				{
					_predictedEvents.Add(new PredictedEvent
					{
						Type = "on_meet",
						TriggerMinutes = crossingTime,
						InvolvedUnitIds = new List<int> { player.Id, unit.Id },
						InterruptsTime = true,
						Data = new Dictionary<string, object>
						{
							["gate_crossing"] = true,
							["player_gate_id"] = playerGate.Id,
							["npc_gate_id"] = unitGate.Id,
							["npc_name"] = unit.Name ?? "Unknown"
						}
					});

#if DEBUG_LOG
					Godot.GD.Print($"[EventPredictionSystem] Gate crossing predicted: {player.Name}(→Gate{playerGate.Id}) × {unit.Name}(→Gate{unitGate.Id}) at t={crossingTime}min");
#endif
				}
			}
		}

		/// <summary>
		/// 시간 중단 이벤트 중 가장 빠른 것 찾기
		/// </summary>
		private PredictedEvent? FindEarliestInterrupt()
		{
			PredictedEvent? earliest = null;

			foreach (var evt in _predictedEvents)
			{
				if (!evt.InterruptsTime)
					continue;

				if (earliest == null || evt.TriggerMinutes < earliest.TriggerMinutes)
				{
					earliest = evt;
				}
			}

			return earliest;
		}

		/// <summary>
		/// 예측된 이벤트 목록 반환 (디버그/UI용)
		/// </summary>
		public IReadOnlyList<PredictedEvent> GetPredictedEvents() => _predictedEvents;

		/// <summary>
		/// 예측된 이벤트 초기화 (테스트용)
		/// </summary>
		public void ClearPredictedEvents()
		{
			_predictedEvents.Clear();
		}
	}

	/// <summary>
	/// 예측된 이벤트
	/// </summary>
	public class PredictedEvent
	{
		/// <summary>
		/// 이벤트 타입 (on_meet, on_reach, on_action, on_collision 등)
		/// </summary>
		public string Type { get; set; } = "";

		/// <summary>
		/// 트리거 시간 (현재로부터 경과 분)
		/// </summary>
		public int TriggerMinutes { get; set; } = 0;

		/// <summary>
		/// 관련된 유닛 ID들
		/// </summary>
		public List<int> InvolvedUnitIds { get; set; } = new();

		/// <summary>
		/// 시간 중단 여부
		/// </summary>
		public bool InterruptsTime { get; set; } = false;

		/// <summary>
		/// 추가 데이터 (Python에서 전달)
		/// </summary>
		public Dictionary<string, object> Data { get; set; } = new();

		public override string ToString()
		{
			return $"PredictedEvent[{Type}] at +{TriggerMinutes}min, interrupts={InterruptsTime}, units=[{string.Join(",", InvolvedUnitIds)}]";
		}
	}

	/// <summary>
	/// 이동 경로 경유지
	/// </summary>
	public struct RouteWaypoint
	{
		/// <summary>위치</summary>
		public LocationRef Location { get; set; }
		/// <summary>도착 시간 (시뮬레이션 시작으로부터 경과 분)</summary>
		public int ArrivalTime { get; set; }
		/// <summary>체류 시간 (분). 0이면 경유지 통과</summary>
		public int StayDuration { get; set; }
		/// <summary>이 위치에 있는 시간 범위의 끝 (ArrivalTime + StayDuration)</summary>
		public int DepartureTime => ArrivalTime + StayDuration;
		/// <summary>최종 목적지 여부 (도착 후 머무름)</summary>
		public bool IsFinalDestination { get; set; }
	}
}
