#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;

namespace SE
{
	/// <summary>
	/// JobBehaviorSystem - JobList 기반 통합 행동 시스템
	///
	/// 역할:
	/// 1. JobList 빈 슬롯 채우기 (BaseSchedule 기반)
	/// 2. 현재 Job 기반 이동 처리 (move, follow, flee)
	/// 3. 시간 경과 시 JobList Advance
	/// 4. GameTime 업데이트
	///
	/// MovementSystem + BehaviorSystem 통합
	/// ThinkSystem은 Python Agent 전용으로 별도 유지
	/// </summary>
	public class JobBehaviorSystem : ECS.System
	{
		public JobBehaviorSystem()
		{
		}

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

			var terrain = _worldSystem.GetTerrain();
			var time = _worldSystem.GetTime();
			var duration = _playerSystem.NextStepDuration;

			// 시간 진행이 없으면 스킵
			if (duration <= 0)
				return;

			// 각 유닛 처리
			foreach (var unit in _unitSystem.Units.Values)
			{
				if (unit.IsObject) continue;

				// 1. 현재 Job 기반 이동 처리
				// (JobList는 ThinkSystem의 Python Agent에서 채움)
				ProcessJobMovement(unit, duration, terrain, time);

				// 2. JobList Advance (시간 경과)
				unit.AdvanceJobs(duration);
			}

			// 4. GameTime 업데이트
			time.AddMinutes(duration);

#if DEBUG_LOG
			GD.Print($"[JobBehaviorSystem] Time: {time}, duration={duration}분, units={_unitSystem.Units.Count}");
#endif
		}

		/// <summary>
		/// 현재 Job 기반 이동 처리
		/// </summary>
		private void ProcessJobMovement(Unit unit, int duration, Terrain terrain, GameTime time)
		{
			var currentJob = unit.CurrentJob;
			if (currentJob == null)
			{
#if DEBUG_LOG
				if (!unit.IsObject && unit.Id > 0)
					GD.Print($"[JobBehaviorSystem] Unit {unit.Id} ({unit.Name}) has no current job");
#endif
				return;
			}
#if DEBUG_LOG
			if (!unit.IsObject && unit.Id > 0)
				GD.Print($"[JobBehaviorSystem] Unit {unit.Id} ({unit.Name}): Job={currentJob.Name}, Action={currentJob.Action}, Duration={currentJob.Duration}");
#endif

			var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

			// Action에 따라 처리
			switch (currentJob.Action)
			{
				case "stay":
					// 현재 위치 유지 - 아무것도 안 함
					break;

				case "move":
					// 목표 위치로 이동
					var goalLoc = currentJob.GetLocationRef();
#if DEBUG_LOG
					if (!unit.IsObject && unit.Id > 0)
						GD.Print($"[JobBehaviorSystem] Unit {unit.Id} move: current={unit.CurrentLocation} -> goal={goalLoc}");
#endif
					ProcessMoveAction(unit, goalLoc, duration, terrain);
					break;

				case "follow":
					// 대상 따라가기
					if (currentJob.TargetId.HasValue && _unitSystem != null)
					{
						var target = _unitSystem.FindUnit(currentJob.TargetId.Value);
						if (target != null)
						{
							ProcessMoveAction(unit, target.CurrentLocation, duration, terrain);
						}
					}
					break;

				case "flee":
					// TODO: 대상 피하기
					break;
			}
		}

		/// <summary>
		/// 목표 위치로 이동 처리
		/// </summary>
		private void ProcessMoveAction(Unit unit, LocationRef goalLocation, int duration, Terrain terrain)
		{
			// 앉은 상태에서는 이동 불가
			var seatedOn = unit.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
			if (seatedOn.Prop.IsValid)
			{
#if DEBUG_LOG
				GD.Print($"[JobBehaviorSystem] {unit.Name} is seated, cannot move");
#endif
				return;
			}

			// 이미 목표에 도착
			if (unit.CurrentLocation == goalLocation)
				return;

			int remainingTime = duration;

			while (remainingTime > 0)
			{
				// 이미 Edge 위에 있으면 계속 이동
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

						// 경유지 지체 시간 설정
						var arrivedLocation = terrain.GetLocation(edge.To);
						if (arrivedLocation != null && arrivedLocation.StayDuration > 0)
						{
							if (edge.To != goalLocation)
							{
								unit.RemainingStayTime = arrivedLocation.StayDuration;
							}
						}
					}
					else
					{
						edge.ElapsedTime += remainingTime;
						remainingTime = 0;
					}
					continue;
				}

				// 지체 중이면 대기
				if (unit.RemainingStayTime > 0)
				{
					int stayTime = Math.Min(remainingTime, unit.RemainingStayTime);
					unit.RemainingStayTime -= stayTime;
					remainingTime -= stayTime;
					continue;
				}

				// 이미 도착했으면 종료
				if (unit.CurrentLocation == goalLocation)
					break;

				var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
				var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

				// 새 이동 시작 - 경로 계산
				var inventory = _inventorySystem.GetUnitInventory(unit.Id);
				var equippedItems = _inventorySystem.GetUnitEquippedItems(unit.Id);
				var actualProps = unit.GetActualProps(_itemSystem, inventory, equippedItems);
				var pathResult = terrain.FindPath(unit.CurrentLocation, goalLocation, actualProps);

				if (!pathResult.Found || pathResult.Path.Count < 2)
					break;

				// 다음 위치로 Edge 생성
				var nextLocation = pathResult.Path[1];
				var nextLocationRef = new LocationRef(nextLocation);
				int travelTime = GetTravelTime(unit.CurrentLocation, nextLocationRef, pathResult.Path[0], nextLocation, terrain);

				unit.CurrentEdge = new EdgeProgress
				{
					From = unit.CurrentLocation,
					To = nextLocationRef,
					TotalTime = travelTime,
					ElapsedTime = 0
				};
			}
		}

		/// <summary>
		/// 두 위치 간 이동 시간 계산
		/// </summary>
		/// <param name="from">출발 LocationRef</param>
		/// <param name="to">도착 LocationRef</param>
		/// <param name="fromLocation">출발 Location 객체</param>
		/// <param name="toLocation">도착 Location 객체</param>
		/// <param name="terrain">지형</param>
		private int GetTravelTime(LocationRef from, LocationRef to, Location fromLocation, Location toLocation, Terrain terrain)
		{
			if (from.RegionId == to.RegionId)
			{
				// 같은 Region 내 이동
				var region = terrain.GetRegion(from.RegionId);
				var edge = region.GetEdgeBetween(from.LocalId, to.LocalId);
				if (edge != null)
				{
					return edge.GetTravelTime(fromLocation);
				}
			}
			else
			{
				// Region 간 이동 - RegionEdge 탐색
				foreach (var regionEdge in terrain.GetRegionEdgesFrom(from))
				{
					var otherLoc = regionEdge.GetOtherLocation(from);
					if (otherLoc == to)
					{
						return regionEdge.GetTravelTime(from);
					}
				}
			}
			return 10; // 기본값
		}
	}
}
