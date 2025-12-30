using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using World = Morld.World;

namespace SE
{
	/// <summary>
	/// 캐릭터의 스케줄을 기반으로 이동 계획을 수립하는 시스템
	/// </summary>
	public class PlanningSystem : ECS.System
	{
		private PathFinder? _pathFinder;

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

			var world = worldSystem.GetWorld();
			var time = worldSystem.GetTime();

			// PathFinder 초기화 (첫 실행 시)
			if (_pathFinder == null)
			{
				_pathFinder = new PathFinder(world);
			}

			// 모든 캐릭터 처리
			foreach (var character in characterSystem.Characters.Values)
			{
				ProcessCharacter(character, time, world);
			}
		}

		/// <summary>
		/// 개별 캐릭터 처리
		/// </summary>
		private void ProcessCharacter(Character character, GameTime time, Morld.World world)
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
				if (TryPlanMovement(character, currentEntry.Location, world))
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
						if (TryPlanMovement(character, startingEntry.Location, world))
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
		private bool TryPlanMovement(Character character, LocationRef destination, Morld.World world)
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
				SetupNextSegment(character, world);
				return true;
			}

			return false;
		}

		/// <summary>
		/// 캐릭터의 다음 이동 구간 설정
		/// </summary>
		private void SetupNextSegment(Character character, Morld.World world)
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
				var region = world.GetRegion(current.RegionId);
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
				foreach (var regionEdge in world.RegionEdges)
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
