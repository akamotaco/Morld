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
	/// MovementSystem - 스케줄 스택 기반 캐릭터 이동 처리
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
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;

			if (worldSystem == null || characterSystem == null || playerSystem == null)
				return;

			var terrain = worldSystem.GetTerrain();
			var time = worldSystem.GetTime();
			var duration = playerSystem.NextStepDuration;

			// 시간 진행이 없으면 스킵
			if (duration <= 0)
				return;

#if DEBUG_LOG
			// 모든 캐릭터의 이동 경로 계산 (충돌 감지용)
			var movements = new Dictionary<int, MovementPlan>();
			foreach (var character in characterSystem.Characters.Values)
			{
				var plan = CalculateMovementPlan(character, duration, terrain, time);
				if (plan != null)
					movements[character.Id] = plan;
			}

			// 충돌 감지 (디버그 출력)
			DetectCollisions(movements, characterSystem, terrain);
#endif

			// 이동 처리
			foreach (var character in characterSystem.Characters.Values)
			{
				ProcessMovement(character, duration, terrain, time);
			}

			// GameTime 업데이트
			time.AddMinutes(duration);

#if DEBUG_LOG
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"[MovementSystem] Time advanced: {duration}분 → {time}");
			PrintCharacterStates(characterSystem, terrain);
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
		}

		/// <summary>
		/// 캐릭터의 이동 계획 계산 (충돌 감지용)
		/// </summary>
		private MovementPlan? CalculateMovementPlan(Character character, int duration, Terrain terrain, GameTime time)
		{
			var layer = character.CurrentScheduleLayer;
			if (layer == null) return null;

			LocationRef? goalLocation = GetGoalLocation(character, layer, time);
			if (!goalLocation.HasValue || character.CurrentLocation == goalLocation.Value)
				return null;

			// 경로 계산
			var pathResult = terrain.FindPath(character.CurrentLocation, goalLocation.Value, character);
			if (!pathResult.Found || pathResult.Path.Count < 2)
				return null;

			// 도착 시간 계산
			var plan = new MovementPlan
			{
				CharacterId = character.Id,
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
		private void DetectCollisions(Dictionary<int, MovementPlan> movements, CharacterSystem characterSystem, Terrain terrain)
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
							var charA = characterSystem.GetCharacter(ids[i]);
							var charB = characterSystem.GetCharacter(ids[j]);
							GD.Print($"[Collision] {charA?.Name} & {charB?.Name} @ {loc.Name} (t={timeA}~{timeB})");
						}
					}
				}
			}
		}

		/// <summary>
		/// 모든 캐릭터의 현재 상태 출력 (디버그용)
		/// </summary>
		private void PrintCharacterStates(CharacterSystem characterSystem, Terrain terrain)
		{
			foreach (var character in characterSystem.Characters.Values)
			{
				var location = terrain.GetLocation(character.CurrentLocation);
				var locationName = location?.Name ?? "Unknown";
				var region = location != null ? terrain.GetRegion(location.RegionId) : null;
				var regionName = region?.Name ?? "Unknown";
				var stateStr = character.IsMoving ? "Moving" : "Idle";

				// 현재 활동 정보
				var currentSchedule = character.CurrentSchedule;
				var activityStr = currentSchedule != null && !string.IsNullOrEmpty(currentSchedule.Activity)
					? $" - {currentSchedule.Activity}"
					: "";

				// 현재 스케줄 레이어 정보
				var layerName = character.CurrentScheduleLayer?.Name ?? "없음";

				GD.Print($"  • {character.Name}: {regionName}/{locationName} [{stateStr}]{activityStr} (레이어: {layerName})");

				// 이동 중이면 목적지 정보도 출력
				if (character.IsMoving && character.CurrentEdge != null)
				{
					var destination = terrain.GetLocation(character.CurrentEdge.To);
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
		private void ProcessMovement(Character character, int duration, Terrain terrain, GameTime time)
		{
			int remainingTime = duration;

			while (remainingTime > 0)
			{
				// 이동 중이면 계속 진행
				if (character.CurrentEdge != null)
				{
					var edge = character.CurrentEdge;
					var timeToComplete = edge.TotalTime - edge.ElapsedTime;

					if (remainingTime >= timeToComplete)
					{
						// 도착
						character.SetCurrentLocation(edge.To);
						character.CurrentEdge = null;
						remainingTime -= timeToComplete;
#if DEBUG_LOG
						var destLocation = terrain.GetLocation(edge.To);
						GD.Print($"[MovementSystem] {character.Name} arrived at {destLocation?.Name ?? "Unknown"}");
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
				var layer = character.CurrentScheduleLayer;
				if (layer == null)
				{
					break;
				}

				LocationRef? goalLocation = GetGoalLocation(character, layer, time);
				if (!goalLocation.HasValue || character.CurrentLocation == goalLocation.Value)
				{
					// 목표 없거나 이미 도착 - 스케줄 엔트리 업데이트만
					UpdateCurrentScheduleEntry(character, layer, time);
					break;
				}

				var pathResult = terrain.FindPath(character.CurrentLocation, goalLocation.Value, character);
				if (!pathResult.Found || pathResult.Path.Count < 2)
				{
					break;
				}

				// 첫 Edge로 이동 시작
				var from = character.CurrentLocation;
				var to = new LocationRef(pathResult.Path[1]);
				var travelTime = GetTravelTime(from, to, terrain);

				character.CurrentEdge = new EdgeProgress
				{
					From = from,
					To = to,
					TotalTime = travelTime,
					ElapsedTime = 0
				};

				// 스케줄 엔트리 업데이트
				UpdateCurrentScheduleEntry(character, layer, time);
			}
		}

		/// <summary>
		/// 현재 스케줄 엔트리 업데이트
		/// </summary>
		private void UpdateCurrentScheduleEntry(Character character, ScheduleLayer layer, GameTime time)
		{
			if (layer.Schedule != null && layer.Schedule.Entries.Count > 0)
			{
				var entry = layer.Schedule.GetEntryAt(time.MinuteOfDay);
				character.SetCurrentSchedule(entry);
			}
			else
			{
				character.SetCurrentSchedule(null);
			}
		}

		/// <summary>
		/// 스케줄 레이어에서 목표 위치 추출
		/// </summary>
		private LocationRef? GetGoalLocation(Character character, ScheduleLayer layer, GameTime time)
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
				// 다른 캐릭터 따라가기
				if (int.TryParse(layer.EndConditionParam, out int targetId))
				{
					var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
					var target = characterSystem?.GetCharacter(targetId);
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
