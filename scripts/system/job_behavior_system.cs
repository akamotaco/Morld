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

			// Duration=0: 즉시 행동 처리 (frozen 이동 또는 Gate 인접 이동)
			// HasPendingInstantAction일 때만 처리 (PlayerSystem이 NextStepDuration 미설정 시 오진입 방지)
			if (duration <= 0)
			{
				if (!_playerSystem.HasPendingInstantAction)
					return; // PlayerSystem이 아직 NextStepDuration을 설정하지 않음 → 스킵

				var player = _playerSystem.FindPlayerUnit();
				if (player != null && player.CurrentJob != null)
				{
					ProcessJobMovement(player, 0, terrain, time);
					player.JobList.Clear();
				}
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
			time.AddMillis(duration);

			// 5. 시간 경과 이벤트 발생 (EventSystem으로 전달)
			var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
			if (_eventSystem != null)
			{
				_eventSystem.Enqueue(GameEvent.OnTimeElapsed(duration));
			}

#if DEBUG_LOG
			int durationMin = duration / GameTime.MillisPerMinute;
			GD.Print($"[JobBehaviorSystem] Time: {time}, duration={durationMin}분 ({duration}ms), units={_unitSystem.Units.Count}");
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
					// 목표 위치로 이동 (Pi-World: TargetX까지 이동)
					var goalLoc = currentJob.GetLocationRef();
#if DEBUG_LOG
					if (!unit.IsObject && unit.Id > 0)
						GD.Print($"[JobBehaviorSystem] Unit {unit.Id} move: current={unit.CurrentLocation} -> goal={goalLoc} (targetX={currentJob.TargetX})");
#endif
					ProcessMoveAction(unit, goalLoc, currentJob.TargetX, duration, terrain);
					break;

				case "follow":
					// 대상 따라가기 (Pi-World: 대상의 X 좌표까지 이동)
					if (currentJob.TargetId.HasValue && _unitSystem != null)
					{
						var target = _unitSystem.FindUnit(currentJob.TargetId.Value);
						if (target != null)
						{
							ProcessMoveAction(unit, target.CurrentLocation, target.PositionX, duration, terrain);
						}
					}
					break;

				case "flee":
					// TODO: 대상 피하기
					break;
			}
		}

		/// <summary>
		/// 목표 위치로 이동 처리 (Pi-World Gate 기반)
		/// </summary>
		/// <param name="unit">이동할 유닛</param>
		/// <param name="goalLocation">목표 Location</param>
		/// <param name="targetX">목표 X 좌표 (0이면 Gate의 ArrivalX 사용)</param>
		/// <param name="duration">이동 가능 시간 (밀리초)</param>
		/// <param name="terrain">지형 정보</param>
		private void ProcessMoveAction(Unit unit, LocationRef goalLocation, float targetX, int duration, Terrain terrain)
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

			// 이미 목표 Location에 도착한 경우: targetX로 이동
			if (unit.CurrentLocation == goalLocation)
			{
				// targetX가 지정되어 있고, 현재 위치와 다르면 이동
				if (targetX > 0f && MathF.Abs(unit.PositionX - targetX) > 0.1f)
				{
					ProcessMoveWithinLocation(unit, targetX, duration, terrain);
				}
				return;
			}

			// Pi-World: Gate 기반 이동
			ProcessMoveAction2D(unit, goalLocation, targetX, duration, terrain);
		}

		/// <summary>
		/// Location 내에서 targetX로 이동 (Gate 없이)
		/// 이미 목표 Location에 도착한 상태에서 특정 X 좌표로 이동할 때 사용
		/// </summary>
		/// <param name="unit">이동할 유닛</param>
		/// <param name="targetX">목표 X 좌표</param>
		/// <param name="duration">이동 가능 시간 (밀리초)</param>
		/// <param name="terrain">지형 정보</param>
		private void ProcessMoveWithinLocation(Unit unit, float targetX, int duration, Terrain terrain)
		{
			var location = terrain.GetLocation(unit.CurrentLocation);
			if (location == null)
				return;

			var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
			var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
			var inventory = _inventorySystem?.GetUnitInventory(unit.Id);
			var equippedItems = _inventorySystem?.GetUnitEquippedItems(unit.Id);

			int remainingTime = duration;

			while (remainingTime > 0)
			{
				// 이동 중이면 진행
				if (unit.CurrentMovement != null)
				{
					var movement = unit.CurrentMovement;
					int timeUsed = movement.Advance(remainingTime);
					remainingTime -= timeUsed;

					if (movement.IsComplete)
					{
						unit.PositionX = location.NormalizeX(movement.TargetX);
						unit.CurrentMovement = null;
					}
					continue;
				}

				// 목표 도착 확인
				float toX = location.NormalizeX(targetX);
				if (MathF.Abs(unit.PositionX - toX) <= 0.1f)
					break;

				// 이동 시작
				float fromX = unit.PositionX;
				float distance = location.CalculateDistance(fromX, toX);

				if (distance <= 0.1f)
					break;

				int movementSpeedPercent = unit.GetMovementSpeed(_itemSystem, inventory, equippedItems);
				float speed = location.BaseSpeed * movementSpeedPercent / 100f;
				if (speed <= 0f) speed = 1f;

				unit.CurrentMovement = new MovementProgress
				{
					StartX = fromX,
					TargetX = toX,
					TargetGateId = null,  // Gate 통과 아님
					TotalDistance = distance,
					TraveledDistance = 0f,
					Speed = speed,
					ElapsedTime = 0
				};

#if DEBUG_LOG
				GD.Print($"[JobBehaviorSystem] {unit.Name} move within location: X={fromX:F1} -> X={toX:F1}");
#endif
			}
		}

		/// <summary>
		/// Pi-World 2D 이동 처리 (Gate 기반)
		/// - Location 내에서는 좌표 기반 이동 (MovementProgress)
		/// - Location 간에는 Gate 통과 (즉시 전환)
		/// - 목적지 도착 후 targetX까지 추가 이동
		/// </summary>
		/// <param name="unit">이동할 유닛</param>
		/// <param name="goalLocation">목표 Location</param>
		/// <param name="targetX">목표 X 좌표 (0이면 Gate의 ArrivalX 사용)</param>
		/// <param name="duration">이동 가능 시간 (밀리초)</param>
		/// <param name="terrain">지형 정보</param>
		private void ProcessMoveAction2D(Unit unit, LocationRef goalLocation, float targetX, int duration, Terrain terrain)
		{
			var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
			var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

			var inventory = _inventorySystem?.GetUnitInventory(unit.Id);
			var equippedItems = _inventorySystem?.GetUnitEquippedItems(unit.Id);
			var actualProps = unit.GetActualProps(_itemSystem, inventory, equippedItems);

			// Duration=0: 즉시 이동 (frozen 또는 Gate 인접)
			if (duration == 0)
			{
				// 진행 중인 이동 취소
				unit.CurrentMovement = null;
				unit.RemainingStayTime = 0;

				// 출발지에서 목적지로 연결된 Gate 찾기 → ArrivalX 사용
				var sourceRegion = terrain.GetRegion(unit.CurrentLocation.RegionId);
				if (sourceRegion != null)
				{
					var sourceGates = sourceRegion.GetGates(unit.CurrentLocation.LocalId);
					foreach (var srcGate in sourceGates)
					{
						if (srcGate.ConnectedLocation == goalLocation &&
							srcGate.CanTraverseForward(actualProps))
						{
							unit.SetLocation2D(goalLocation, srcGate.ArrivalX, srcGate.ArrivalY);
#if DEBUG_LOG
							GD.Print($"[JobBehaviorSystem] {unit.Name} instant move via Gate: {unit.CurrentLocation} -> {goalLocation} (X={srcGate.ArrivalX})");
#endif
							return;
						}
					}
				}

				// Gate 연결 없으면 직접 텔레포트 (targetX 또는 기본 위치)
				unit.SetCurrentLocation(goalLocation);
				var destLocation = terrain.GetLocation(goalLocation);
				if (destLocation != null && targetX > 0f)
					unit.PositionX = destLocation.NormalizeX(targetX);
				else
					unit.PositionX = 0f;

#if DEBUG_LOG
				GD.Print($"[JobBehaviorSystem] {unit.Name} instant move (no gate): -> {goalLocation}");
#endif
				return;
			}

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
								// Gate 통과 시간 차감
								if (gate.TravelTime > 0)
									remainingTime -= gate.TravelTime;

								// Gate를 통해 다른 Location으로 이동
								unit.SetCurrentLocation(gate.ConnectedLocation);
								unit.PositionX = gate.ArrivalX;
								unit.PositionY = gate.ArrivalY;
#if DEBUG_LOG
								GD.Print($"[JobBehaviorSystem] {unit.Name} passed gate: {gate.OwnerLocation} -> {gate.ConnectedLocation} (X={gate.ArrivalX}, travelTime={gate.TravelTime})");
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
				{
					// targetX가 지정되어 있으면 해당 위치로 추가 이동
					if (targetX > 0f && MathF.Abs(unit.PositionX - targetX) > 0.1f)
					{
						float targetFromX = unit.PositionX;
						float targetToX = location.NormalizeX(targetX);
						float targetDistance = location.CalculateDistance(targetFromX, targetToX);

						if (targetDistance > 0.1f)
						{
							int targetSpeedPercent = unit.GetMovementSpeed(_itemSystem, inventory, equippedItems);
							float targetSpeed = location.BaseSpeed * targetSpeedPercent / 100f;
							if (targetSpeed <= 0f) targetSpeed = 1f;

							unit.CurrentMovement = new MovementProgress
							{
								StartX = targetFromX,
								TargetX = targetToX,
								TargetGateId = null,  // Gate 통과 아님
								TotalDistance = targetDistance,
								TraveledDistance = 0f,
								Speed = targetSpeed,
								ElapsedTime = 0
							};
#if DEBUG_LOG
							GD.Print($"[JobBehaviorSystem] {unit.Name} arrived at goal, moving to targetX: X={targetFromX:F1} -> X={targetToX:F1}");
#endif
							continue;  // 이동 시작 후 루프 계속
						}
					}
					break;  // 도착 완료
				}

				// 4. 다음 Gate 찾기
				var targetGate = FindNextGate2D(unit, goalLocation, terrain, actualProps);

				if (targetGate == null)
				{
					// Gate가 없으면 경로 없음
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
