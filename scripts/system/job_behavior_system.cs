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
			var isTimeFrozen = _worldSystem.IsTimeFrozen();

			// 시간 진행이 없으면 스킵
			if (duration <= 0)
				return;

			// 시간 정지 상태: 플레이어만 즉시 이동 처리 (시간 소모 없음)
			if (isTimeFrozen)
			{
				var player = _playerSystem.FindPlayerUnit();
				if (player != null)
				{
					// 플레이어 즉시 이동 (목적지에 바로 도착)
					ProcessFrozenPlayerMove(player, terrain);
				}
				// 시간 정지 중이므로 시간/이벤트 처리 스킵
				_playerSystem.ClearPendingTime();
				return;
			}

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

			// 5. 시간 경과 이벤트 발생 (EventSystem으로 전달)
			var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
			if (_eventSystem != null)
			{
				_eventSystem.Enqueue(GameEvent.OnTimeElapsed(duration));
			}

#if DEBUG_LOG
			GD.Print($"[JobBehaviorSystem] Time: {time}, duration={duration}분, units={_unitSystem.Units.Count}");
#endif
		}

		/// <summary>
		/// 시간 정지 상태에서 플레이어 즉시 이동 처리
		/// 이동 시간 없이 목적지에 바로 도착
		/// </summary>
		private void ProcessFrozenPlayerMove(Unit player, Terrain terrain)
		{
			var currentJob = player.CurrentJob;
			if (currentJob == null || currentJob.Action != "move")
				return;

			var goalLocation = currentJob.GetLocationRef();
			if (player.CurrentLocation == goalLocation)
				return;

			// 즉시 목적지로 이동
			player.CurrentEdge = null;
			player.RemainingStayTime = 0;
			player.SetCurrentLocation(goalLocation);
			player.JobList.Clear();  // Job 완료

#if DEBUG_LOG
			GD.Print($"[JobBehaviorSystem] Frozen move: Player teleported to {goalLocation}");
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
				int baseTravelTime = terrain.GetTravelTimeBetween(unit.CurrentLocation, nextLocationRef);
				if (baseTravelTime < 0) baseTravelTime = 10;  // 기본값

				// 이동속도 적용 (100=기본, 200=2배 빠름)
				int movementSpeed = unit.GetMovementSpeed(_itemSystem, inventory, equippedItems);
				int actualTravelTime = (int)Math.Ceiling(baseTravelTime * 100.0 / movementSpeed);
				if (actualTravelTime < 1) actualTravelTime = 1;  // 최소 1분

				unit.CurrentEdge = new EdgeProgress
				{
					From = unit.CurrentLocation,
					To = nextLocationRef,
					BaseTravelTime = baseTravelTime,
					TotalTime = actualTravelTime,
					MovementSpeed = movementSpeed,
					ElapsedTime = 0
				};
			}
		}
	}
}
