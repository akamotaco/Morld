#define DEBUG_LOG

using System;
using System.Collections.Generic;
using System.Linq;
using ECS;
using Godot;
using Morld;

namespace SE
{
	/// <summary>
	/// EventPredictionSystem - 이벤트 예측 및 시간 조정 시스템
	///
	/// 역할:
	/// 1. Python의 predict_events() 호출하여 예측 이벤트 수집
	/// 2. 시간 중단 이벤트 중 가장 빠른 것 찾기
	/// 3. PlayerSystem.NextStepDuration 조정
	///
	/// 실행 순서: ThinkSystem → EventPredictionSystem → JobBehaviorSystem → EventSystem
	/// </summary>
	public class EventPredictionSystem : ECS.System
	{
		private ScriptSystem? _scriptSystem;
		private PlayerSystem? _playerSystem;
		private UnitSystem? _unitSystem;
		private WorldSystem? _worldSystem;

		private bool _predictModuleAvailable = false;
		private bool _checkedModule = false;

		/// <summary>
		/// 예측된 이벤트 목록 (Python에서 받아옴)
		/// </summary>
		private List<PredictedEvent> _predictedEvents = new();

		/// <summary>
		/// 마지막으로 조정된 시간 (디버그용)
		/// </summary>
		public int LastAdjustedDuration { get; private set; } = 0;

		/// <summary>
		/// 시스템 참조 설정
		/// </summary>
		public void SetSystemReferences(
			ScriptSystem? scriptSystem,
			PlayerSystem? playerSystem,
			UnitSystem? unitSystem,
			WorldSystem? worldSystem)
		{
			_scriptSystem = scriptSystem;
			_playerSystem = playerSystem;
			_unitSystem = unitSystem;
			_worldSystem = worldSystem;
		}

		/// <summary>
		/// 매 Step마다 호출
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 시간 진행 대기 중이 아니면 스킵
			if (_playerSystem == null || !_playerSystem.HasPendingTime)
				return;

			// ScriptSystem이 없으면 스킵
			if (_scriptSystem == null)
				return;

			// predict 모듈 존재 여부 한 번만 체크
			if (!_checkedModule)
			{
				_checkedModule = true;
				_predictModuleAvailable = _scriptSystem.IsPredictModuleAvailable();
			}

			// predict 모듈이 없으면 스킵
			if (!_predictModuleAvailable)
				return;

			int pendingDuration = _playerSystem.NextStepDuration;
			if (pendingDuration <= 0)
				return;

			// Python predict_events() 호출
			try
			{
				_predictedEvents = _scriptSystem.CallPredictEvents(pendingDuration);
			}
			catch (Exception ex)
			{
				GD.PrintErr($"[EventPredictionSystem] Error calling predict_events(): {ex.Message}");
				return;
			}

			// 시간 중단 이벤트 중 가장 빠른 것 찾기
			var earliestInterrupt = FindEarliestInterrupt();
			if (earliestInterrupt != null && earliestInterrupt.TriggerMinutes < pendingDuration)
			{
				// 시간 조정
				int adjustedDuration = earliestInterrupt.TriggerMinutes;
				if (adjustedDuration < 1) adjustedDuration = 1;

				_playerSystem.AdjustNextStepDuration(adjustedDuration);
				LastAdjustedDuration = adjustedDuration;

#if DEBUG_LOG
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
				GD.Print($"[EventPredictionSystem] 시간 조정!");
				GD.Print($"  원래 시간: {pendingDuration}분");
				GD.Print($"  조정된 시간: {adjustedDuration}분");
				GD.Print($"  이벤트 타입: {earliestInterrupt.Type}");
				GD.Print($"  관련 유닛: {string.Join(", ", earliestInterrupt.InvolvedUnitIds)}");
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
			}
			else
			{
				LastAdjustedDuration = 0;
			}
		}

		/// <summary>
		/// 시간 중단 이벤트 중 가장 빠른 것 찾기
		/// </summary>
		private PredictedEvent? FindEarliestInterrupt()
		{
			PredictedEvent? earliest = null;

			foreach (var evt in _predictedEvents)
			{
				if (!evt.InterruptsTime)
					continue;

				if (earliest == null || evt.TriggerMinutes < earliest.TriggerMinutes)
				{
					earliest = evt;
				}
			}

			return earliest;
		}

		/// <summary>
		/// 예측된 이벤트 목록 반환 (디버그/UI용)
		/// </summary>
		public IReadOnlyList<PredictedEvent> GetPredictedEvents() => _predictedEvents;

		/// <summary>
		/// 예측된 이벤트 초기화 (테스트용)
		/// </summary>
		public void ClearPredictedEvents()
		{
			_predictedEvents.Clear();
		}
	}

	/// <summary>
	/// 예측된 이벤트
	/// </summary>
	public class PredictedEvent
	{
		/// <summary>
		/// 이벤트 타입 (on_meet, on_reach, on_action, on_collision 등)
		/// </summary>
		public string Type { get; set; } = "";

		/// <summary>
		/// 트리거 시간 (현재로부터 경과 분)
		/// </summary>
		public int TriggerMinutes { get; set; } = 0;

		/// <summary>
		/// 관련된 유닛 ID들
		/// </summary>
		public List<int> InvolvedUnitIds { get; set; } = new();

		/// <summary>
		/// 시간 중단 여부
		/// </summary>
		public bool InterruptsTime { get; set; } = false;

		/// <summary>
		/// 추가 데이터 (Python에서 전달)
		/// </summary>
		public Dictionary<string, object> Data { get; set; } = new();

		public override string ToString()
		{
			return $"PredictedEvent[{Type}] at +{TriggerMinutes}min, interrupts={InterruptsTime}, units=[{string.Join(",", InvolvedUnitIds)}]";
		}
	}
}
