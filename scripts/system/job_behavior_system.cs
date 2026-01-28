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
		/// Pi-World: 2D 모드에서는 Gate 위치로 이동
		/// </summary>
		private void ProcessFrozenPlayerMove(Unit player, Terrain terrain)
		{
			var currentJob = player.CurrentJob;
			if (currentJob == null || currentJob.Action != "move")
				return;

			var goalLocation = currentJob.GetLocationRef();
			if (player.CurrentLocation == goalLocation)
				return;

			// Pi-World: 2D 이동 상태 초기화
			player.CurrentMovement = null;

			// 즉시 목적지로 이동
			player.CurrentEdge = null;
			player.RemainingStayTime = 0;

			// Pi-World: 목적지 Location의 2D 모드 확인
			var destLocation = terrain.GetLocation(goalLocation);
			if (destLocation != null && !destLocation.IsLegacyMode)
			{
				// 2D 모드: 연결된 Gate 위치에서 시작
				var region = terrain.GetRegion(goalLocation.RegionId);
				if (region != null)
				{
					// 출발지에서 연결된 Gate 찾기
					var sourceRegion = terrain.GetRegion(player.CurrentLocation.RegionId);
					if (sourceRegion != null)
					{
						var sourceGates = sourceRegion.GetGates(player.CurrentLocation.LocalId);
						foreach (var srcGate in sourceGates)
						{
							if (srcGate.ConnectedLocation == goalLocation)
							{
								// 목적지의 도착 위치로 이동
								player.SetLocation2D(goalLocation, srcGate.ArrivalX, srcGate.ArrivalY);
#if DEBUG_LOG
								GD.Print($"[JobBehaviorSystem] Frozen move 2D: Player teleported to {goalLocation} at X={srcGate.ArrivalX}");
#endif
								player.JobList.Clear();
								return;
							}
						}
					}

					// Gate 연결이 없으면 기본 위치 (X=0)
					player.SetLocation2D(goalLocation, 0f, 0f);
				}
				else
				{
					player.SetCurrentLocation(goalLocation);
				}
			}
			else
			{
				// Legacy 모드
				player.SetCurrentLocation(goalLocation);
			}

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
		/// Pi-World: Location이 2D 모드면 Gate 기반 이동, Legacy면 Edge 기반 이동
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

			// Pi-World: 현재 Location이 2D 모드인지 확인
			var currentLocation = terrain.GetLocation(unit.CurrentLocation);
			if (currentLocation != null && !currentLocation.IsLegacyMode)
			{
				// 2D 모드: Gate 기반 이동
				ProcessMoveAction2D(unit, goalLocation, duration, terrain);
				return;
			}

			// Legacy 모드: Edge 기반 이동
			ProcessMoveActionLegacy(unit, goalLocation, duration, terrain);
		}

		/// <summary>
		/// Legacy 이동 처리 (Edge 기반)
		/// </summary>
		private void ProcessMoveActionLegacy(Unit unit, LocationRef goalLocation, int duration, Terrain terrain)
		{
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

		/// <summary>
		/// Pi-World 2D 이동 처리 (Gate 기반)
		/// - Location 내에서는 좌표 기반 이동 (MovementProgress)
		/// - Location 간에는 Gate 통과 (즉시 전환)
		/// </summary>
		private void ProcessMoveAction2D(Unit unit, LocationRef goalLocation, int duration, Terrain terrain)
		{
			var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
			var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

			var inventory = _inventorySystem?.GetUnitInventory(unit.Id);
			var equippedItems = _inventorySystem?.GetUnitEquippedItems(unit.Id);
			var actualProps = unit.GetActualProps(_itemSystem, inventory, equippedItems);

			int remainingTime = duration;

			while (remainingTime > 0)
			{
				var location = terrain.GetLocation(unit.CurrentLocation);
				if (location == null)
					break;

				// 1. 이동 중이면 진행
				if (unit.CurrentMovement != null)
				{
					var movement = unit.CurrentMovement;
					int timeUsed = movement.Advance(remainingTime);
					remainingTime -= timeUsed;

					if (movement.IsComplete)
					{
						// 이동 완료 - 위치 업데이트
						unit.PositionX = location.NormalizeX(movement.TargetX);

						// Gate 통과 처리
						if (movement.TargetGateId.HasValue)
						{
							var region = terrain.GetRegion(unit.CurrentLocation.RegionId);
							var gate = region?.GetGate(unit.CurrentLocation.LocalId, movement.TargetGateId.Value);

							if (gate != null && gate.CanTraverseForward(actualProps))
							{
								// Gate를 통해 다른 Location으로 이동
								unit.SetCurrentLocation(gate.ConnectedLocation);
								unit.PositionX = gate.ArrivalX;
								unit.PositionY = gate.ArrivalY;
#if DEBUG_LOG
								GD.Print($"[JobBehaviorSystem] {unit.Name} passed gate: {gate.OwnerLocation} -> {gate.ConnectedLocation} (X={gate.ArrivalX})");
#endif
							}
						}

						unit.CurrentMovement = null;
						// StayDuration 처리
						var arrivedLocation = terrain.GetLocation(unit.CurrentLocation);
						if (arrivedLocation != null && arrivedLocation.StayDuration > 0)
						{
							if (unit.CurrentLocation != goalLocation)
							{
								unit.RemainingStayTime = arrivedLocation.StayDuration;
							}
						}
					}
					continue;
				}

				// 2. 지체 중이면 대기
				if (unit.RemainingStayTime > 0)
				{
					int stayTime = Math.Min(remainingTime, unit.RemainingStayTime);
					unit.RemainingStayTime -= stayTime;
					remainingTime -= stayTime;
					continue;
				}

				// 3. 목적지 도착 확인
				if (unit.CurrentLocation == goalLocation)
					break;

				// 4. 다음 Gate 찾기 (같은 Location이면 목표 위치로 직접 이동)
				var targetGate = FindNextGate2D(unit, goalLocation, terrain, actualProps);

				if (targetGate == null)
				{
					// Gate가 없으면 경로 없음 (또는 Legacy 모드 필요)
#if DEBUG_LOG
					GD.Print($"[JobBehaviorSystem] {unit.Name} no gate found from {unit.CurrentLocation} to {goalLocation}");
#endif
					break;
				}

				// 5. Gate로 이동 시작
				float fromX = unit.PositionX;
				float toX = targetGate.X;
				float distance = location.CalculateDistance(fromX, toX);

				// 이동 속도 계산: Location.BaseSpeed * Unit.MovementSpeed%
				int movementSpeedPercent = unit.GetMovementSpeed(_itemSystem, inventory, equippedItems);
				float speed = location.BaseSpeed * movementSpeedPercent / 100f;
				if (speed <= 0f) speed = 1f;

				unit.CurrentMovement = new MovementProgress
				{
					StartX = fromX,
					TargetX = toX,
					TargetGateId = targetGate.Id,
					TotalDistance = distance,
					TraveledDistance = 0f,
					Speed = speed,
					ElapsedTime = 0
				};

#if DEBUG_LOG
				GD.Print($"[JobBehaviorSystem] {unit.Name} start 2D move: X={fromX:F1} -> Gate{targetGate.Id}(X={toX:F1}), dist={distance:F1}, speed={speed:F1}");
#endif
			}
		}

		/// <summary>
		/// 다음 이동할 Gate 찾기 (Pi-World)
		/// 현재 Location에서 goalLocation으로 가기 위한 Gate 선택
		/// </summary>
		private Gate? FindNextGate2D(Unit unit, LocationRef goalLocation, Terrain terrain, TraversalContext actualProps)
		{
			var region = terrain.GetRegion(unit.CurrentLocation.RegionId);
			if (region == null)
				return null;

			// 1. 먼저 직접 연결된 Gate 중 목표 Location으로 가는 것 찾기
			var gates = region.GetGates(unit.CurrentLocation.LocalId);
			Gate? bestGate = null;
			float bestDistance = float.MaxValue;

			foreach (var gate in gates)
			{
				if (!gate.CanTraverseForward(actualProps))
					continue;

				// 직접 연결된 경우
				if (gate.ConnectedLocation == goalLocation)
				{
					float dist = terrain.GetLocation(unit.CurrentLocation)?.CalculateDistance(unit.PositionX, gate.X) ?? float.MaxValue;
					if (dist < bestDistance)
					{
						bestDistance = dist;
						bestGate = gate;
					}
				}
			}

			if (bestGate != null)
				return bestGate;

			// 2. 경로 탐색 필요 - 다음 Location으로 가는 Gate 찾기
			var pathResult = terrain.FindPath(unit.CurrentLocation, goalLocation, actualProps);
			if (!pathResult.Found || pathResult.Path.Count < 2)
				return null;

			var nextLocationRef = new LocationRef(pathResult.Path[1]);

			// 3. nextLocation으로 연결된 Gate 찾기
			foreach (var gate in gates)
			{
				if (!gate.CanTraverseForward(actualProps))
					continue;

				if (gate.ConnectedLocation == nextLocationRef)
				{
					float dist = terrain.GetLocation(unit.CurrentLocation)?.CalculateDistance(unit.PositionX, gate.X) ?? float.MaxValue;
					if (dist < bestDistance)
					{
						bestDistance = dist;
						bestGate = gate;
					}
				}
			}

			return bestGate;
		}
	}
}
