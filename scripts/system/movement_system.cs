#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;

namespace SE
{
	/// <summary>
	/// PlanningSystem의 ActionQueue를 소비하여 캐릭터 이동을 처리하는 시스템
	/// Step 실행 순서: MovementSystem → PlanningSystem
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
			var planningSystem = _hub.FindSystem("planningSystem") as PlanningSystem;

			if (worldSystem == null || characterSystem == null || planningSystem == null)
				return;

			var terrain = worldSystem.GetTerrain();
			var time = worldSystem.GetTime();

			// PlanningSystem에서 진행할 시간 가져오기
			var duration = planningSystem.NextStepDuration;

			// 첫 Step에서는 Queue가 비어있으므로 스킵
			if (duration <= 0)
				return;

			// 모든 캐릭터 처리
			foreach (var character in characterSystem.Characters.Values)
			{
				ProcessCharacter(character, duration, planningSystem, terrain);
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

#if DEBUG_LOG
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

				GD.Print($"  • {character.Name}: {regionName}/{locationName} [{stateStr}]{activityStr}");

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
		/// 개별 캐릭터 처리 - ActionQueue 소비
		/// </summary>
		private void ProcessCharacter(
			Character character,
			int duration,
			PlanningSystem planningSystem,
			Terrain terrain)
		{
			var queue = planningSystem.GetActionQueue(character.Id);
			if (queue == null || queue.Count == 0)
				return;

			var currentIndex = planningSystem.GetCurrentActionIndex(character.Id);
			int elapsedTime = 0;

			// duration 분량만큼 Action 소비
			while (currentIndex < queue.Count && elapsedTime < duration)
			{
				var action = queue[currentIndex];

				// 현재 Action의 남은 시간 계산
				var actionRemaining = action.EndTime - Math.Max(action.StartTime, elapsedTime);

				if (actionRemaining <= 0)
				{
					// 이미 완료된 Action - 다음으로
					currentIndex++;
					continue;
				}

				// 이번 Step에서 소비할 시간
				var timeToConsume = Math.Min(actionRemaining, duration - elapsedTime);

				if (action.IsMoving)
				{
					// 이동 Action 처리
					ProcessMovingAction(character, action, elapsedTime, timeToConsume, duration);
				}
				else
				{
					// 활동/대기 Action 처리
					ProcessIdleAction(character, action);
				}

				elapsedTime += timeToConsume;

				// Action 완료 여부 확인
				if (elapsedTime >= action.EndTime)
				{
					// 이동 완료 시 위치 업데이트
					if (action.IsMoving && action.Destination.HasValue)
					{
						character.SetCurrentLocation(action.Destination.Value);
						character.CurrentEdge = null;

#if DEBUG_LOG
						var destLocation = terrain.GetLocation(action.Destination.Value);
						GD.Print($"[MovementSystem] {character.Name} arrived at {destLocation?.Name ?? "Unknown"}");
#endif
					}

					currentIndex++;
				}
				else if (action.IsMoving)
				{
					// 이동 중 Step 종료 - CurrentEdge에 진행 상태 저장
					var totalTime = action.EndTime - action.StartTime;
					var elapsed = elapsedTime - action.StartTime;

					character.CurrentEdge = new EdgeProgress
					{
						From = action.Location,
						To = action.Destination!.Value,
						TotalTime = totalTime,
						ElapsedTime = elapsed
					};
				}
			}

			// 현재 Action 인덱스 업데이트
			planningSystem.SetCurrentActionIndex(character.Id, currentIndex);
		}

		/// <summary>
		/// 이동 Action 처리
		/// </summary>
		private void ProcessMovingAction(
			Character character,
			ActionLog action,
			int elapsedTime,
			int timeToConsume,
			int duration)
		{
			// 이동 시작 시 출발지 확인
			if (elapsedTime <= action.StartTime)
			{
				// 이동 시작 - CurrentLocation은 출발지여야 함
				if (character.CurrentLocation != action.Location)
				{
					character.SetCurrentLocation(action.Location);
				}
			}
		}

		/// <summary>
		/// 활동/대기 Action 처리
		/// </summary>
		private void ProcessIdleAction(Character character, ActionLog action)
		{
			// 해당 위치에서 활동 중
			if (character.CurrentLocation != action.Location)
			{
				character.SetCurrentLocation(action.Location);
			}

			// CurrentEdge는 null이어야 함 (이동 중이 아님)
			character.CurrentEdge = null;
		}
	}
}
