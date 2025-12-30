using ECS;
using Godot;
using Morld;
using System;

namespace SE
{
	/// <summary>
	/// 캐릭터의 실제 이동을 처리하는 시스템
	/// </summary>
	public class MovementSystem : ECS.System
	{
		public MovementSystem()
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
			var deltaMinutes = worldSystem.GetDeltaGameMinutes();

			// 게임 시간이 흐르지 않았으면 스킵
			if (deltaMinutes <= 0)
				return;

			// 모든 캐릭터 처리
			foreach (var character in characterSystem.Characters.Values)
			{
				ProcessCharacter(character, deltaMinutes, terrain);
			}
		}

		/// <summary>
		/// 개별 캐릭터 처리
		/// </summary>
		private void ProcessCharacter(Character character, int deltaMinutes, Morld.Terrain terrain)
		{
			// 이동 중인 캐릭터만 처리
			if (character.State != CharacterState.Moving)
				return;

			if (character.Movement == null)
			{
				character.ArriveAtDestination();
				return;
			}

			// 이동 시간 경과 (WorldSystem에서 전달받은 게임 시간)
			character.AddTravelTime(deltaMinutes);

			// 현재 구간 완료 확인
			if (character.Movement.IsSegmentComplete)
			{
				if (character.Movement.IsPathComplete)
				{
					// 최종 목적지 도착
#if DEBUG_LOG
					GD.Print($"[MovementSystem] {character.Name} arrived at {character.Movement.FinalDestination}");
#endif
					character.ArriveAtDestination();
				}
				else
				{
					// 다음 구간으로
					if (character.MoveToNextSegment())
					{
						// 다음 구간 이동 시간 계산
						SetupNextSegment(character, terrain);
					}
				}
			}
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
