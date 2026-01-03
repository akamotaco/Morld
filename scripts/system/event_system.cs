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
	/// EventSystem - 게임 이벤트 수집 및 Python 전달
	/// - 위치 변경 감지 (OnReach)
	/// - 유닛 만남 감지 (OnMeet)
	/// - 이벤트 배치 처리 후 Python on_event_list() 호출
	/// </summary>
	public class EventSystem : ECS.System
	{
		// 이번 Step에서 발생한 이벤트 큐
		private readonly List<GameEvent> _pendingEvents = new();

		// 시스템 참조
		private ScriptSystem? _scriptSystem;
		private TextUISystem? _textUISystem;
		private UnitSystem? _unitSystem;
		private PlayerSystem? _playerSystem;

		// 이전 상태 추적 (OnReach 감지용)
		private readonly Dictionary<int, LocationRef> _lastLocations = new();

		// OnMeet 중복 방지
		private readonly HashSet<string> _lastMeetings = new();
		// 역방향 인덱스: 유닛 ID → 해당 유닛이 포함된 만남 키 집합
		private readonly Dictionary<int, HashSet<string>> _unitToMeetings = new();

		// 초기화 완료 여부 (첫 Step에서 위치 초기화용)
		private bool _initialized = false;

		public EventSystem()
		{
		}

		/// <summary>
		/// 시스템 참조 설정
		/// </summary>
		public void SetSystemReferences(
			ScriptSystem? scriptSystem,
			TextUISystem? textUISystem,
			UnitSystem? unitSystem,
			PlayerSystem? playerSystem)
		{
			_scriptSystem = scriptSystem;
			_textUISystem = textUISystem;
			_unitSystem = unitSystem;
			_playerSystem = playerSystem;
		}

		/// <summary>
		/// 이벤트 등록 (외부에서 호출)
		/// </summary>
		public void Enqueue(GameEvent evt)
		{
			_pendingEvents.Add(evt);
#if DEBUG_LOG
			GD.Print($"[EventSystem] Enqueued: {evt}");
#endif
		}

		/// <summary>
		/// 위치 초기화 (게임 시작 시 호출)
		/// 현재 모든 유닛의 위치를 기록하여 첫 Step에서 OnReach 발생 방지
		/// </summary>
		public void InitializeLocations()
		{
			if (_unitSystem == null) return;

			_lastLocations.Clear();
			foreach (var unit in _unitSystem.Units.Values)
			{
				if (unit.GeneratesEvents)
				{
					_lastLocations[unit.Id] = unit.CurrentLocation;
				}
			}
			_initialized = true;

#if DEBUG_LOG
			GD.Print($"[EventSystem] Initialized locations for {_lastLocations.Count} units");
#endif
		}

		/// <summary>
		/// 위치 변경 감지 및 OnReach 이벤트 생성
		/// </summary>
		public void DetectLocationChanges()
		{
			if (_unitSystem == null) return;

			// 초기화 안 됐으면 먼저 초기화
			if (!_initialized)
			{
				InitializeLocations();
				return;
			}

			foreach (var unit in _unitSystem.Units.Values)
			{
				// 이벤트 비활성 유닛은 스킵
				if (!unit.GeneratesEvents) continue;

				var currentLoc = unit.CurrentLocation;

				if (_lastLocations.TryGetValue(unit.Id, out var lastLoc))
				{
					if (currentLoc != lastLoc)
					{
						// 위치가 변경됨 → OnReach 이벤트 생성
						Enqueue(GameEvent.OnReach(unit.Id, currentLoc.RegionId, currentLoc.LocalId));

						// 해당 유닛의 만남 상태 리셋
						ClearMeetingsForUnit(unit.Id);
					}
				}

				_lastLocations[unit.Id] = currentLoc;
			}
		}

		/// <summary>
		/// 같은 위치에 있는 유닛들의 OnMeet 이벤트 생성
		/// </summary>
		public void DetectMeetings()
		{
			if (_unitSystem == null || _playerSystem == null) return;

			var playerId = _playerSystem.PlayerId;
			var player = _unitSystem.GetUnit(playerId);
			if (player == null) return;

			// 플레이어와 같은 위치에 있는 이벤트 활성 유닛 수집
			var unitsAtSameLocation = _unitSystem.Units.Values
				.Where(u => u.Id != playerId
						 && u.CurrentLocation == player.CurrentLocation
						 && u.GeneratesEvents)
				.Select(u => u.Id)
				.OrderBy(id => id)  // 정렬하여 키 정규화
				.ToList();

			if (unitsAtSameLocation.Count == 0) return;

			// 만남 키 생성 (플레이어 + 다른 유닛들, 정렬됨)
			var allIds = new List<int> { playerId };
			allIds.AddRange(unitsAtSameLocation);
			allIds.Sort();
			var meetingKey = string.Join(",", allIds);

			// 이미 발생한 만남인지 확인
			if (_lastMeetings.Contains(meetingKey)) return;

			// 새로운 만남 기록 및 이벤트 생성
			AddMeetingKey(meetingKey, allIds.ToArray());
			Enqueue(GameEvent.OnMeet(allIds.ToArray()));
		}

		/// <summary>
		/// 이벤트 큐 플러시 및 Python 호출
		/// </summary>
		/// <returns>처리 결과 (모놀로그 표시 시 true)</returns>
		public bool FlushEvents()
		{
			if (_pendingEvents.Count == 0) return false;

#if DEBUG_LOG
			GD.Print($"[EventSystem] Flushing {_pendingEvents.Count} events");
#endif

			// Python에 이벤트 리스트 전달
			var result = _scriptSystem?.CallEventHandler(_pendingEvents);
			_pendingEvents.Clear();

			// 결과 처리 (모놀로그 등)
			return ProcessEventResult(result);
		}

		/// <summary>
		/// 이벤트 결과 처리
		/// </summary>
		private bool ProcessEventResult(ScriptResult? result)
		{
			if (result == null) return false;

			switch (result.Type)
			{
				case "monologue":
					if (result is MonologueScriptResult monoResult)
					{
						// 모놀로그 아래에 Situation이 있어야 Pop 후 정상 동작
						// 스택이 비어있으면 먼저 Situation Push
						if (_textUISystem != null && _textUISystem.IsStackEmpty())
						{
							_textUISystem.ShowSituation();
						}

						_textUISystem?.ShowMonologue(
							monoResult.Pages,
							monoResult.TimeConsumed,
							monoResult.ButtonType,
							monoResult.DoneCallback,
							monoResult.CancelCallback);
#if DEBUG_LOG
						GD.Print($"[EventSystem] Showing monologue ({monoResult.Pages.Count} pages)");
#endif
						return true;
					}
					break;
			}

			return false;
		}

		/// <summary>
		/// 만남 키 등록 (역방향 인덱스도 갱신)
		/// </summary>
		private void AddMeetingKey(string meetingKey, int[] unitIds)
		{
			_lastMeetings.Add(meetingKey);
			foreach (var id in unitIds)
			{
				if (!_unitToMeetings.ContainsKey(id))
					_unitToMeetings[id] = new HashSet<string>();
				_unitToMeetings[id].Add(meetingKey);
			}
		}

		/// <summary>
		/// 특정 유닛의 만남 상태 제거 (역방향 인덱스 활용)
		/// </summary>
		private void ClearMeetingsForUnit(int unitId)
		{
			if (_unitToMeetings.TryGetValue(unitId, out var keys))
			{
				foreach (var key in keys)
					_lastMeetings.Remove(key);
				_unitToMeetings.Remove(unitId);
			}
		}

		/// <summary>
		/// Proc은 빈 구현 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
