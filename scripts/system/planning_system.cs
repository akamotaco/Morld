#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;

namespace SE
{
	/// <summary>
	/// 캐릭터의 스케줄을 기반으로 행동 Queue를 생성하는 시스템
	/// </summary>
	public class PlanningSystem : ECS.System
	{
		private PathFinder? _pathFinder;

		/// <summary>
		/// 다음 Step에서 진행할 시간 (분)
		/// MovementSystem이 이 값을 읽어서 시간 진행
		/// </summary>
		public int NextStepDuration { get; private set; } = 0;

		/// <summary>
		/// 캐릭터별 행동 Queue (런타임만, 저장 안 함)
		/// </summary>
		private Dictionary<string, List<ActionLog>> _actionQueues = new();

		/// <summary>
		/// 캐릭터별 현재 Action 인덱스 (런타임만, 저장 안 함)
		/// </summary>
		private Dictionary<string, int> _currentActionIndices = new();

		public PlanningSystem()
		{
		}

		/// <summary>
		/// Queue 접근 메서드 - 캐릭터의 ActionQueue 가져오기
		/// </summary>
		public List<ActionLog>? GetActionQueue(string characterId) =>
			_actionQueues.TryGetValue(characterId, out var queue) ? queue : null;

		/// <summary>
		/// Queue 접근 메서드 - 현재 Action 인덱스 가져오기
		/// </summary>
		public int GetCurrentActionIndex(string characterId) =>
			_currentActionIndices.TryGetValue(characterId, out var idx) ? idx : 0;

		/// <summary>
		/// Queue 접근 메서드 - 현재 Action 인덱스 설정
		/// </summary>
		public void SetCurrentActionIndex(string characterId, int index) =>
			_currentActionIndices[characterId] = index;

		/// <summary>
		/// 현재 자정까지 남은 시간 (ActionQueue의 최대 길이)
		/// </summary>
		public int MinutesToMidnight { get; private set; } = GameTime.MinutesPerDay;

		/// <summary>
		/// NextStepDuration 설정 (PlayerSystem에서 사용)
		/// 자정을 넘지 않도록 자동 제한됨
		/// </summary>
		public void SetNextStepDuration(int duration) =>
			NextStepDuration = Math.Min(duration, MinutesToMidnight);

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

			// 자정까지 남은 시간 계산 (planDuration 제한)
			MinutesToMidnight = GameTime.MinutesPerDay - time.MinuteOfDay;
			if (MinutesToMidnight <= 0) MinutesToMidnight = GameTime.MinutesPerDay;

			// 매 Step마다 Queue 초기화 (새로 생성)
			_actionQueues.Clear();
			_currentActionIndices.Clear();

			// 모든 캐릭터에 대해 ActionQueue 생성 (자정까지만)
			foreach (var character in characterSystem.Characters.Values)
			{
				BuildActionQueue(character, time, terrain, MinutesToMidnight);
			}

			// 기본값: 자정까지 남은 시간 (PlayerSystem에서 덮어쓸 수 있음)
			NextStepDuration = MinutesToMidnight;
		}

		/// <summary>
		/// 캐릭터의 ActionQueue 생성
		/// </summary>
		/// <param name="planDuration">계획할 시간 (분) - 자정까지 남은 시간으로 제한</param>
		private void BuildActionQueue(Character character, GameTime time, Terrain terrain, int planDuration)
		{
			var queue = new List<ActionLog>();
			int currentTime = 0; // 상대 시간 (Step 시작 기준 0분)

			// 1. CurrentEdge 처리 - 이동 중이었으면 남은 이동을 첫 Action으로 추가
			if (character.CurrentEdge != null)
			{
				var edge = character.CurrentEdge;
				var remainingTime = edge.RemainingTime;

				if (remainingTime > 0)
				{
					queue.Add(new ActionLog
					{
						StartTime = currentTime,
						EndTime = currentTime + remainingTime,
						IsMoving = true,
						Location = edge.From,
						Destination = edge.To,
						Activity = character.CurrentSchedule?.Activity
					});
					currentTime += remainingTime;
				}

				// CurrentEdge는 ActionQueue로 변환되었으므로 null로 설정
				// (실제 null 처리는 MovementSystem에서 이동 완료 시)
			}

			// 2. 현재 위치 결정 (이동 중이면 도착지, 아니면 현재 위치)
			var startLocation = character.CurrentEdge != null
				? character.CurrentEdge.To
				: character.CurrentLocation;

			// 3. 스케줄 기반 행동 계획
			while (currentTime < planDuration)
			{
				// 현재 게임 시간 + 상대 시간으로 활성 스케줄 확인
				var gameMinuteOfDay = (time.MinuteOfDay + currentTime) % 1440;
				var currentEntry = character.Schedule.GetEntryAt(gameMinuteOfDay);

				if (currentEntry == null)
				{
					// 스케줄 없음 - Idle
					var idleEndTime = Math.Min(currentTime + (planDuration - currentTime), planDuration);
					queue.Add(new ActionLog
					{
						StartTime = currentTime,
						EndTime = idleEndTime,
						IsMoving = false,
						Location = startLocation,
						Destination = null,
						Activity = null
					});
					currentTime = idleEndTime;
					continue;
				}

				// 목적지가 현재 위치와 같으면 해당 활동 수행
				if (startLocation == currentEntry.Location)
				{
					// 스케줄 종료 시간까지 또는 계획 시간까지
					var scheduleEndMinute = currentEntry.TimeRange.EndMinute;
					var minutesUntilEnd = scheduleEndMinute > gameMinuteOfDay
						? scheduleEndMinute - gameMinuteOfDay
						: (1440 - gameMinuteOfDay) + scheduleEndMinute;

					var activityEndTime = Math.Min(currentTime + minutesUntilEnd, planDuration);

					queue.Add(new ActionLog
					{
						StartTime = currentTime,
						EndTime = activityEndTime,
						IsMoving = false,
						Location = startLocation,
						Destination = null,
						Activity = currentEntry.Activity
					});

					character.SetCurrentSchedule(currentEntry);
					currentTime = activityEndTime;
					continue;
				}

				// 이동 필요 - 경로 탐색
				if (_pathFinder == null)
				{
					currentTime = planDuration;
					continue;
				}

				var pathResult = _pathFinder.FindPath(
					startLocation,
					currentEntry.Location,
					character.TraversalContext
				);

				if (!pathResult.Found || pathResult.Path.Count < 2)
				{
					// 경로 없음 - 현재 위치에서 Idle
					queue.Add(new ActionLog
					{
						StartTime = currentTime,
						EndTime = planDuration,
						IsMoving = false,
						Location = startLocation,
						Destination = null,
						Activity = null
					});
					currentTime = planDuration;
					continue;
				}

				// Edge 단위로 이동 Action 생성
				for (int i = 0; i < pathResult.Path.Count - 1 && currentTime < planDuration; i++)
				{
					var fromLocation = pathResult.Path[i];
					var toLocation = pathResult.Path[i + 1];
					var from = new LocationRef(fromLocation);
					var to = new LocationRef(toLocation);
					var travelTime = GetTravelTime(from, to, terrain);

					var moveEndTime = Math.Min(currentTime + travelTime, planDuration);

					queue.Add(new ActionLog
					{
						StartTime = currentTime,
						EndTime = moveEndTime,
						IsMoving = true,
						Location = from,
						Destination = to,
						Activity = currentEntry.Activity
					});

					currentTime = moveEndTime;
					startLocation = to; // 다음 출발지 업데이트
				}

				// 도착 후 활동 시간이 남으면 추가
				if (currentTime < planDuration && startLocation == currentEntry.Location)
				{
					character.SetCurrentSchedule(currentEntry);

					queue.Add(new ActionLog
					{
						StartTime = currentTime,
						EndTime = planDuration,
						IsMoving = false,
						Location = startLocation,
						Destination = null,
						Activity = currentEntry.Activity
					});
					currentTime = planDuration;
				}
			}

			_actionQueues[character.Id] = queue;
			_currentActionIndices[character.Id] = 0;
		}

		/// <summary>
		/// 두 Location 간 이동 시간 계산
		/// </summary>
		private int GetTravelTime(LocationRef from, LocationRef to, Terrain terrain)
		{
			// 같은 Region 내 이동
			if (from.RegionId == to.RegionId)
			{
				var region = terrain.GetRegion(from.RegionId);
				var edge = region?.GetEdgeBetween(from.LocalId, to.LocalId);

				if (edge != null)
				{
					// Edge의 A→B 방향 확인 (from.LocalId가 LocationA.LocalId와 같으면 A→B)
					var travelTime = edge.LocationA.LocalId == from.LocalId
						? edge.TravelTimeAtoB
						: edge.TravelTimeBtoA;
					return travelTime >= 0 ? travelTime : 1;
				}
			}
			else
			{
				// Region 간 이동 - RegionEdge 찾기
				foreach (var regionEdge in terrain.RegionEdges)
				{
					var locA = regionEdge.LocationA;
					var locB = regionEdge.LocationB;

					if (locA.RegionId == from.RegionId && locA.LocalId == from.LocalId &&
						locB.RegionId == to.RegionId && locB.LocalId == to.LocalId)
					{
						return regionEdge.TravelTimeAtoB >= 0 ? regionEdge.TravelTimeAtoB : 1;
					}
					else if (locB.RegionId == from.RegionId && locB.LocalId == from.LocalId &&
							 locA.RegionId == to.RegionId && locA.LocalId == to.LocalId)
					{
						return regionEdge.TravelTimeBtoA >= 0 ? regionEdge.TravelTimeBtoA : 1;
					}
				}
			}

			// 기본값
			return 1;
		}

	}
}
