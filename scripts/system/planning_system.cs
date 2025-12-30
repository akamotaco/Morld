#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;

namespace SE
{
	/// <summary>
	/// 캐릭터의 스케줄을 기반으로 이동 계획을 수립하는 시스템
	/// </summary>
	public class PlanningSystem : ECS.System
	{
		private PathFinder? _pathFinder;

		// 디버그 출력용 누적 시간 (밀리초)
		private int _accumulatedTime = 0;
		private const int DebugPrintInterval = 1000; // 1초마다 출력

		public PlanningSystem()
		{
		}

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 필요한 시스템 가져오기
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;

			if (worldSystem == null || characterSystem == null)
				return;

			var terrain = worldSystem.GetTerrain();
			var time = worldSystem.GetTime();

			// PathFinder 초기화 (첫 실행 시)
			if (_pathFinder == null)
			{
				_pathFinder = new PathFinder(terrain);
			}

			// 모든 캐릭터 처리
			foreach (var character in characterSystem.Characters.Values)
			{
				ProcessCharacter(character, time, terrain);
			}

#if DEBUG_LOG
			// 시간 누적
			_accumulatedTime += step;

			// 1초(1000ms)마다 캐릭터 상태 출력
			if (_accumulatedTime >= DebugPrintInterval)
			{
				_accumulatedTime -= DebugPrintInterval;
				PrintCharacterStates(characterSystem, terrain);
			}
#endif
		}

		/// <summary>
		/// 모든 캐릭터의 현재 상태 출력 (디버그용)
		/// </summary>
		private void PrintCharacterStates(CharacterSystem characterSystem, Terrain terrain)
		{
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print("[PlanningSystem] Character Status:");

			foreach (var character in characterSystem.Characters.Values)
			{
				var location = terrain.GetLocation(character.CurrentLocation);
				var locationName = location?.Name ?? "Unknown";
				var region = location != null ? terrain.GetRegion(location.RegionId) : null;
				var regionName = region?.Name ?? "Unknown";
				var stateStr = character.State == CharacterState.Moving ? "Moving" : "Idle";

				// 현재 활동 정보
				var currentSchedule = character.CurrentSchedule;
				var activityStr = currentSchedule != null && !string.IsNullOrEmpty(currentSchedule.Activity)
					? $" - {currentSchedule.Activity}"
					: "";

				GD.Print($"  • {character.Name}: {regionName}/{locationName} [{stateStr}]{activityStr}");

				// 이동 중이면 목적지 정보도 출력
				if (character.State == CharacterState.Moving && character.Movement != null)
				{
					var destination = terrain.GetLocation(character.Movement.FinalDestination);
					var destName = destination?.Name ?? "Unknown";
					var destRegion = destination != null ? terrain.GetRegion(destination.RegionId) : null;
					var destRegionName = destRegion?.Name ?? "Unknown";
					GD.Print($"    → Destination: {destRegionName}/{destName}");
				}
			}

			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}

		/// <summary>
		/// 개별 캐릭터 처리
		/// </summary>
		private void ProcessCharacter(Character character, GameTime time, Morld.Terrain terrain)
		{
			// 이미 이동 중이면 스킵
			if (character.State == CharacterState.Moving)
				return;

			// 현재 활성 스케줄 확인
			var currentEntry = character.Schedule.GetCurrentEntry(time);

			if (currentEntry != null)
			{
				// 이미 목적지에 있는 경우
				if (character.CurrentLocation == currentEntry.Location)
				{
					character.SetCurrentSchedule(currentEntry);
					return;
				}

				// 목적지로 이동 필요
				if (TryPlanMovement(character, currentEntry.Location, terrain))
				{
					character.SetCurrentSchedule(currentEntry);
				}
			}
			else
			{
				// 다음 스케줄의 시작 시간인지 확인
				var startingEntry = character.Schedule.GetStartingEntry(time);

				if (startingEntry != null)
				{
					// 스케줄 시작 시간 - 목적지로 이동
					if (character.CurrentLocation != startingEntry.Location)
					{
						if (TryPlanMovement(character, startingEntry.Location, terrain))
						{
							character.SetCurrentSchedule(startingEntry);
						}
					}
					else
					{
						character.SetCurrentSchedule(startingEntry);
					}
				}
				else
				{
					character.SetCurrentSchedule(null);
				}
			}
		}

		/// <summary>
		/// 이동 경로 계획 시도
		/// </summary>
		private bool TryPlanMovement(Character character, LocationRef destination, Morld.Terrain terrain)
		{
			if (_pathFinder == null)
				return false;

			// 이미 목적지에 있으면 불필요
			if (character.CurrentLocation == destination)
				return false;

			// 경로 탐색
			var pathResult = _pathFinder.FindPath(
				character.CurrentLocation,
				destination,
				character.TraversalContext
			);

			if (!pathResult.Found || pathResult.Path.Count < 2)
				return false;

			// 이동 시작
			if (character.StartMovement(pathResult.Path, destination))
			{
				// 첫 구간 이동 시간 설정
				SetupNextSegment(character, terrain);
				return true;
			}

			return false;
		}

		/// <summary>
		/// 캐릭터의 다음 이동 구간 설정
		/// </summary>
		private void SetupNextSegment(Character character, Morld.Terrain terrain)
		{
			if (character.Movement == null)
				return;

			var path = character.Movement.FullPath;
			var idx = character.Movement.CurrentPathIndex;

			if (idx >= path.Count - 1)
				return;

			var current = path[idx];
			var next = path[idx + 1];

			// 같은 Region 내 이동인지 확인
			if (current.RegionId == next.RegionId)
			{
				var region = terrain.GetRegion(current.RegionId);
				var edge = region?.GetEdgeBetween(current.LocalId, next.LocalId);

				if (edge != null)
				{
					var travelTime = edge.GetTravelTime(current);
					character.SetSegmentTravelTime(travelTime >= 0 ? travelTime : 1);
					return;
				}
			}
			else
			{
				// Region 간 이동 - RegionEdge 찾기
				foreach (var regionEdge in terrain.RegionEdges)
				{
					var locA = regionEdge.LocationA;
					var locB = regionEdge.LocationB;

					if ((locA.RegionId == current.RegionId && locA.LocalId == current.LocalId &&
						 locB.RegionId == next.RegionId && locB.LocalId == next.LocalId))
					{
						var travelTime = regionEdge.TravelTimeAtoB >= 0 ? regionEdge.TravelTimeAtoB : 1;
						character.SetSegmentTravelTime(travelTime);
						return;
					}
					else if ((locB.RegionId == current.RegionId && locB.LocalId == current.LocalId &&
							  locA.RegionId == next.RegionId && locA.LocalId == next.LocalId))
					{
						var travelTime = regionEdge.TravelTimeBtoA >= 0 ? regionEdge.TravelTimeBtoA : 1;
						character.SetSegmentTravelTime(travelTime);
						return;
					}
				}
			}

			// 기본값
			character.SetSegmentTravelTime(1);
		}
	}
}
