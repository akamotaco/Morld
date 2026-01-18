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

			// 이벤트 예측 (만남, 도착)
			_predictedEvents.Clear();
			PredictMeetings(pendingDuration);
			PredictArrivals(pendingDuration);

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

			// 현재 이동 중이 아니면 스킵
			if (player.CurrentEdge == null) return;

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
		/// 1. 현재 Edge 완료 시점
		/// 2. 경유지 체류 시간 적용
		/// 3. 다음 Edge 계산 (Job 목적지 기준)
		/// 4. duration 내에서 반복
		/// </summary>
		private List<RouteWaypoint>? GetMovementRoute(Unit unit, int duration, Terrain terrain)
		{
			var route = new List<RouteWaypoint>();

			// 현재 위치 추가 (ArrivalTime=0)
			route.Add(new RouteWaypoint
			{
				Location = unit.CurrentLocation,
				ArrivalTime = 0
			});

			// Job에서 최종 목적지 가져오기
			var currentJob = unit.CurrentJob;
			if (currentJob == null || currentJob.Action != "move")
			{
				// move Job이 없으면 현재 Edge 목적지만 반환 (있는 경우)
				if (unit.CurrentEdge != null)
				{
					int remainingTime = unit.CurrentEdge.RemainingTime;
					if (remainingTime > 0 && remainingTime <= duration)
					{
						route.Add(new RouteWaypoint
						{
							Location = unit.CurrentEdge.To,
							ArrivalTime = remainingTime
						});
					}
				}
				return route;
			}

			var goalLocation = currentJob.GetLocationRef();

			// 이미 목적지에 있으면 현재 위치만 반환
			if (unit.CurrentLocation == goalLocation)
				return route;

			// 시뮬레이션 변수
			var currentLocation = unit.CurrentLocation;
			var currentEdge = unit.CurrentEdge;
			int elapsedTime = 0;
			int remainingStayTime = unit.RemainingStayTime;

			// 무한 루프 방지
			int maxIterations = 50;
			int iterations = 0;

			while (elapsedTime < duration && iterations < maxIterations)
			{
				iterations++;

				// Edge 위에 있으면 완료까지 진행
				if (currentEdge != null)
				{
					int timeToComplete = currentEdge.TotalTime - currentEdge.ElapsedTime;
					int arrivalTime = elapsedTime + timeToComplete;

					if (arrivalTime <= duration)
					{
						// 도착
						currentLocation = currentEdge.To;
						elapsedTime = arrivalTime;
						currentEdge = null;

						route.Add(new RouteWaypoint
						{
							Location = currentLocation,
							ArrivalTime = arrivalTime
						});

						// 목적지 도착하면 종료
						if (currentLocation == goalLocation)
							break;

						// 경유지 체류 시간 설정
						var arrivedLocation = terrain.GetLocation(currentLocation);
						if (arrivedLocation != null && arrivedLocation.StayDuration > 0)
						{
							remainingStayTime = arrivedLocation.StayDuration;
						}
					}
					else
					{
						// duration 내에 도착 불가
						break;
					}
					continue;
				}

				// 체류 중이면 대기
				if (remainingStayTime > 0)
				{
					int stayTime = Math.Min(duration - elapsedTime, remainingStayTime);
					elapsedTime += stayTime;
					remainingStayTime -= stayTime;
					continue;
				}

				// 이미 목적지면 종료
				if (currentLocation == goalLocation)
					break;

				// 다음 Edge 계산
				var pathResult = terrain.FindPath(currentLocation, goalLocation, unit.TraversalContext);
				if (!pathResult.Found || pathResult.Path.Count < 2)
					break;

				var nextLocation = pathResult.Path[1];
				var nextLocationRef = new LocationRef(nextLocation);
				int travelTime = terrain.GetTravelTimeBetween(currentLocation, nextLocationRef);
				if (travelTime < 0) travelTime = 10;

				currentEdge = new EdgeProgress
				{
					From = currentLocation,
					To = nextLocationRef,
					TotalTime = travelTime,
					ElapsedTime = 0
				};
			}

			return route;
		}

		/// <summary>
		/// 두 경로가 만나는 시점 계산
		///
		/// 만남 판정 기준:
		/// 1. 둘 다 ArrivalTime == 0: 이미 같은 위치 → 스킵 (DetectMeetings에서 처리)
		/// 2. 한쪽만 ArrivalTime == 0: 한쪽이 이미 있고 다른 쪽이 도착 → 만남
		/// 3. 둘 다 이동 중: 도착 시간 차이 5분 이내 → 만남
		/// </summary>
		private int? FindMeetingTime(List<RouteWaypoint> playerRoute, List<RouteWaypoint> npcRoute, int duration)
		{
			foreach (var playerWp in playerRoute)
			{
				foreach (var npcWp in npcRoute)
				{
					// 같은 위치인지 확인
					if (playerWp.Location.RegionId != npcWp.Location.RegionId) continue;
					if (playerWp.Location.LocalId != npcWp.Location.LocalId) continue;

					// 케이스 1: 둘 다 이미 같은 위치에 있음 → 스킵
					// 실제 on_meet 이벤트는 EventSystem.DetectMeetings()에서 별도로 감지됨
					if (playerWp.ArrivalTime == 0 && npcWp.ArrivalTime == 0)
						continue;

					// 케이스 2: 한쪽이 이미 그 위치에 있음 (정지 상태)
					// → 다른 쪽이 도착하는 시점에 만남 발생
					// 예: 플레이어가 현관에서 멍때리기, NPC가 현관을 경유지로 통과
					if (playerWp.ArrivalTime == 0 || npcWp.ArrivalTime == 0)
					{
						return Math.Max(playerWp.ArrivalTime, npcWp.ArrivalTime);
					}

					// 케이스 3: 둘 다 이동 중 → 도착 시간 차이가 작으면 만남 (5분 이내)
					int timeDiff = Math.Abs(playerWp.ArrivalTime - npcWp.ArrivalTime);
					if (timeDiff <= 5)
					{
						return Math.Max(playerWp.ArrivalTime, npcWp.ArrivalTime);
					}
				}
			}

			return null;
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
		public LocationRef Location { get; set; }
		public int ArrivalTime { get; set; }
	}
}
