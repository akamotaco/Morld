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
	/// MovementSystem - 스케줄 스택 기반 유닛 이동 처리
	/// - 스케줄 레이어에서 목표 위치 추출
	/// - 경로 계산 및 이동 처리
	/// - 충돌 감지 (디버그 출력)
	/// </summary>
	public class MovementSystem : ECS.System
	{
		public MovementSystem()
		{
		}

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
			var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.FindSystem("inventorySystem") as InventorySystem;

			if (worldSystem == null || unitSystem == null || playerSystem == null)
				return;

			var terrain = worldSystem.GetTerrain();
			var time = worldSystem.GetTime();
			var duration = playerSystem.NextStepDuration;

			// 시간 진행이 없으면 스킵
			if (duration <= 0)
				return;

#if DEBUG_LOG
			// 모든 유닛의 이동 경로 계산 (충돌 감지용)
			var movements = new Dictionary<int, MovementPlan>();
			foreach (var unit in unitSystem.Units.Values)
			{
				// 오브젝트는 이동하지 않음
				if (unit.IsObject) continue;

				var plan = CalculateMovementPlan(unit, duration, terrain, time);
				if (plan != null)
					movements[unit.Id] = plan;
			}

			// 충돌 감지 (디버그 출력)
			DetectCollisions(movements, unitSystem, terrain);
#endif

			// 이동 처리
			foreach (var unit in unitSystem.Units.Values)
			{
				// 오브젝트는 이동하지 않음
				if (unit.IsObject) continue;

				ProcessMovement(unit, duration, terrain, time, itemSystem, inventorySystem);
			}

			// 스케줄 Lifetime 감소 (시간 경과에 따른 스케줄 수명 처리)
			foreach (var unit in unitSystem.Units.Values)
			{
				if (unit.IsObject) continue;

				var layer = unit.CurrentScheduleLayer;
				if (layer != null && layer.RemainingLifetime > 0)
				{
					layer.RemainingLifetime -= duration;
					if (layer.RemainingLifetime < 0)
						layer.RemainingLifetime = 0;
#if DEBUG_LOG
					GD.Print($"[MovementSystem] {unit.Name} schedule '{layer.Name}' lifetime: {layer.RemainingLifetime}분 remaining");
#endif
				}
			}

			// GameTime 업데이트
			time.AddMinutes(duration);

#if DEBUG_LOG
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"[MovementSystem] Time advanced: {duration}분 → {time}");
			PrintUnitStates(unitSystem, terrain);
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
		}

		/// <summary>
		/// 유닛의 이동 계획 계산 (충돌 감지용)
		/// </summary>
		private MovementPlan? CalculateMovementPlan(Unit unit, int duration, Terrain terrain, GameTime time)
		{
			var layer = unit.CurrentScheduleLayer;
			if (layer == null) return null;

			LocationRef? goalLocation = GetGoalLocation(unit, layer, time);
			if (!goalLocation.HasValue || unit.CurrentLocation == goalLocation.Value)
				return null;

			// 경로 계산
			var pathResult = terrain.FindPath(unit.CurrentLocation, goalLocation.Value, unit);
			if (!pathResult.Found || pathResult.Path.Count < 2)
				return null;

			// 도착 시간 계산
			var plan = new MovementPlan
			{
				UnitId = unit.Id,
				Path = pathResult.Path,
				StartTime = 0
			};

			int arrivalTime = 0;
			for (int i = 0; i < pathResult.Path.Count; i++)
			{
				plan.ArrivalTimes[pathResult.Path[i]] = arrivalTime;
				if (i < pathResult.Path.Count - 1)
				{
					var from = new LocationRef(pathResult.Path[i]);
					var to = new LocationRef(pathResult.Path[i + 1]);
					arrivalTime += GetTravelTime(from, to, terrain);
				}
			}

			return plan;
		}

#if DEBUG_LOG
		/// <summary>
		/// 충돌 감지 (디버그 출력)
		/// </summary>
		private void DetectCollisions(Dictionary<int, MovementPlan> movements, UnitSystem unitSystem, Terrain terrain)
		{
			// 모든 쌍 비교
			var ids = movements.Keys.ToList();
			for (int i = 0; i < ids.Count; i++)
			{
				for (int j = i + 1; j < ids.Count; j++)
				{
					var planA = movements[ids[i]];
					var planB = movements[ids[j]];

					// 경로가 겹치는 위치 찾기
					var commonLocations = planA.Path.Intersect(planB.Path);
					foreach (var loc in commonLocations)
					{
						var timeA = planA.GetArrivalTime(loc);
						var timeB = planB.GetArrivalTime(loc);

						// 시간이 겹치면 충돌 (5분 이내)
						if (Math.Abs(timeA - timeB) < 5)
						{
							var unitA = unitSystem.GetUnit(ids[i]);
							var unitB = unitSystem.GetUnit(ids[j]);
							GD.Print($"[Collision] {unitA?.Name} & {unitB?.Name} @ {loc.Name} (t={timeA}~{timeB})");
						}
					}
				}
			}
		}

		/// <summary>
		/// 모든 유닛의 현재 상태 출력 (디버그용)
		/// </summary>
		private void PrintUnitStates(UnitSystem unitSystem, Terrain terrain)
		{
			foreach (var unit in unitSystem.Units.Values)
			{
				// 오브젝트는 스킵
				if (unit.IsObject) continue;

				var location = terrain.GetLocation(unit.CurrentLocation);
				var locationName = location?.Name ?? "Unknown";
				var region = location != null ? terrain.GetRegion(location.RegionId) : null;
				var regionName = region?.Name ?? "Unknown";
				var stateStr = unit.IsMoving ? "Moving" : "Idle";

				// 현재 활동 정보
				var currentSchedule = unit.CurrentSchedule;
				var activityStr = currentSchedule != null && !string.IsNullOrEmpty(currentSchedule.Activity)
					? $" - {currentSchedule.Activity}"
					: "";

				// 현재 스케줄 레이어 정보
				var layerName = unit.CurrentScheduleLayer?.Name ?? "없음";

				GD.Print($"  • {unit.Name}: {regionName}/{locationName} [{stateStr}]{activityStr} (레이어: {layerName})");

				// 이동 중이면 목적지 정보도 출력
				if (unit.IsMoving && unit.CurrentEdge != null)
				{
					var destination = terrain.GetLocation(unit.CurrentEdge.To);
					var destName = destination?.Name ?? "Unknown";
					var destRegion = destination != null ? terrain.GetRegion(destination.RegionId) : null;
					var destRegionName = destRegion?.Name ?? "Unknown";
					GD.Print($"    → Destination: {destRegionName}/{destName}");
				}
			}
		}
#endif

		/// <summary>
		/// 실제 이동 처리
		/// </summary>
		private void ProcessMovement(Unit unit, int duration, Terrain terrain, GameTime time, ItemSystem? itemSystem, InventorySystem? inventorySystem)
		{
			int remainingTime = duration;

			while (remainingTime > 0)
			{
				// 지체 시간 처리 (경유지 통과 중)
				if (unit.RemainingStayTime > 0)
				{
					if (remainingTime >= unit.RemainingStayTime)
					{
						remainingTime -= unit.RemainingStayTime;
						unit.RemainingStayTime = 0;
						// 지체 완료, 다음 이동 진행
					}
					else
					{
						// 지체 중
						unit.RemainingStayTime -= remainingTime;
						remainingTime = 0;
					}
					continue;
				}

				// 이동 중이면 계속 진행
				if (unit.CurrentEdge != null)
				{
					var edge = unit.CurrentEdge;
					var timeToComplete = edge.TotalTime - edge.ElapsedTime;

					if (remainingTime >= timeToComplete)
					{
						// 도착
						unit.SetCurrentLocation(edge.To);
						unit.CurrentEdge = null;
						remainingTime -= timeToComplete;

						// 경유지 지체 시간 설정 (목적지가 아닌 경우만)
						var arrivedLocation = terrain.GetLocation(edge.To);
						if (arrivedLocation != null && arrivedLocation.StayDuration > 0)
						{
							// 목적지인지 확인
							var scheduleLayer = unit.CurrentScheduleLayer;
							var finalGoal = scheduleLayer != null ? GetGoalLocation(unit, scheduleLayer, time) : null;
							if (!finalGoal.HasValue || edge.To != finalGoal.Value)
							{
								// 경유지이므로 지체 시간 적용
								unit.RemainingStayTime = arrivedLocation.StayDuration;
#if DEBUG_LOG
								GD.Print($"[MovementSystem] {unit.Name} delayed at {arrivedLocation.Name} for {arrivedLocation.StayDuration}분");
#endif
							}
						}
#if DEBUG_LOG
						GD.Print($"[MovementSystem] {unit.Name} arrived at {arrivedLocation?.Name ?? "Unknown"}");
#endif
					}
					else
					{
						// 이동 진행 중
						edge.ElapsedTime += remainingTime;
						remainingTime = 0;
					}
					continue;
				}

				// 새 이동 시작
				var currentLayer = unit.CurrentScheduleLayer;
				if (currentLayer == null)
				{
					break;
				}

				LocationRef? goalLocation = GetGoalLocation(unit, currentLayer, time);
				if (!goalLocation.HasValue || unit.CurrentLocation == goalLocation.Value)
				{
					// 목표 없거나 이미 도착 - 스케줄 엔트리 업데이트만
					UpdateCurrentScheduleEntry(unit, currentLayer, time);
					break;
				}

				// 아이템 효과가 반영된 태그로 경로 탐색
				var inventory = inventorySystem?.GetUnitInventory(unit.Id);
				var equippedItems = inventorySystem?.GetUnitEquippedItems(unit.Id);
				var actualTags = unit.GetActualTags(itemSystem, inventory, equippedItems);
				var pathResult = terrain.FindPath(unit.CurrentLocation, goalLocation.Value, actualTags);
				if (!pathResult.Found || pathResult.Path.Count < 2)
				{
					break;
				}

				// 첫 Edge로 이동 시작
				var from = unit.CurrentLocation;
				var to = new LocationRef(pathResult.Path[1]);
				var travelTime = GetTravelTime(from, to, terrain);

				unit.CurrentEdge = new EdgeProgress
				{
					From = from,
					To = to,
					TotalTime = travelTime,
					ElapsedTime = 0
				};

				// 스케줄 엔트리 업데이트
				UpdateCurrentScheduleEntry(unit, currentLayer, time);
			}
		}

		/// <summary>
		/// 현재 스케줄 엔트리 업데이트
		/// </summary>
		private void UpdateCurrentScheduleEntry(Unit unit, ScheduleLayer layer, GameTime time)
		{
			if (layer.Schedule != null && layer.Schedule.Entries.Count > 0)
			{
				var entry = layer.Schedule.GetEntryAt(time.MinuteOfDay);
				unit.SetCurrentSchedule(entry);
			}
			else
			{
				unit.SetCurrentSchedule(null);
			}
		}

		/// <summary>
		/// 스케줄 레이어에서 목표 위치 추출
		/// </summary>
		private LocationRef? GetGoalLocation(Unit unit, ScheduleLayer layer, GameTime time)
		{
			if (layer.Schedule != null && layer.Schedule.Entries.Count > 0)
			{
				// 시간 기반 스케줄
				var entry = layer.Schedule.GetEntryAt(time.MinuteOfDay);
				if (entry != null)
					return entry.Location;
			}
			else if (layer.EndConditionType == "이동")
			{
				// 단일 목표 이동
				return ScheduleLayer.ParseLocationRef(layer.EndConditionParam);
			}
			else if (layer.EndConditionType == "따라가기")
			{
				// 다른 유닛 따라가기
				if (int.TryParse(layer.EndConditionParam, out int targetId))
				{
					var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
					var target = unitSystem?.GetUnit(targetId);
					if (target != null)
						return target.CurrentLocation;
				}
			}
			return null;
		}

		/// <summary>
		/// 두 Location 간 이동 시간 계산
		/// </summary>
		private int GetTravelTime(LocationRef from, LocationRef to, Terrain terrain)
		{
			if (from.RegionId == to.RegionId)
			{
				var region = terrain.GetRegion(from.RegionId);
				var edge = region?.GetEdgeBetween(from.LocalId, to.LocalId);
				if (edge != null)
				{
					return edge.LocationA.LocalId == from.LocalId
						? edge.TravelTimeAtoB : edge.TravelTimeBtoA;
				}
			}
			else
			{
				foreach (var regionEdge in terrain.RegionEdges)
				{
					var locA = regionEdge.LocationA;
					var locB = regionEdge.LocationB;
					if (locA == from && locB == to) return regionEdge.TravelTimeAtoB;
					if (locB == from && locA == to) return regionEdge.TravelTimeBtoA;
				}
			}
			return 1; // 기본값
		}
	}
}
