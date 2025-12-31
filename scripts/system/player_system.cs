#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;

namespace SE
{
	/// <summary>
	/// 플레이어 입력 기반 시간 진행 시스템
	/// - 입력이 없으면 시간 정지 (duration = 0)
	/// - RequestTimeAdvance()로 시간 진행 요청
	/// - 자정 제한 자동 적용, 남은 시간은 다음 Step에서 계속
	///
	/// 시간 처리 흐름:
	/// 1. PlayerSystem이 NextStepDuration 설정 (다음 Step에서 사용될 값)
	/// 2. 다음 Step에서 MovementSystem이 해당 시간만큼 진행
	/// 3. PlayerSystem이 실제 소비된 시간을 _remainingDuration에서 차감
	/// </summary>
	public class PlayerSystem : ECS.System
	{
		/// <summary>
		/// 아직 처리해야 할 남은 시간 (분)
		/// </summary>
		private int _remainingDuration = 0;

		/// <summary>
		/// 이전 Step에서 설정한 시간 (이번 Step에서 실제 소비된 시간)
		/// </summary>
		private int _lastSetDuration = 0;

		/// <summary>
		/// 현재 활성화된 액션 이름 (디버그용)
		/// </summary>
		private string _currentAction = "";

		public PlayerSystem()
		{
		}

		/// <summary>
		/// 시간 진행 요청 (외부에서 호출)
		/// </summary>
		/// <param name="minutes">진행할 시간 (분)</param>
		/// <param name="actionName">액션 이름 (디버그용)</param>
		public void RequestTimeAdvance(int minutes, string actionName = "")
		{
			_remainingDuration += minutes;
			_currentAction = actionName;

#if DEBUG_LOG
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"[PlayerSystem] 시간 진행 요청!");
			GD.Print($"  액션: {actionName}");
			GD.Print($"  요청 시간: {minutes}분");
			GD.Print($"  총 대기 시간: {_remainingDuration}분");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
		}

		/// <summary>
		/// 현재 대기 중인 시간이 있는지
		/// </summary>
		public bool HasPendingTime => _remainingDuration > 0;

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var planningSystem = _hub.FindSystem("planningSystem") as PlanningSystem;
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;

			if (planningSystem == null || worldSystem == null)
				return;

			var time = worldSystem.GetTime();

			// 1. 이전 Step에서 설정한 시간을 차감 (이번 Step에서 실제 소비됨)
			if (_lastSetDuration > 0)
			{
				_remainingDuration -= _lastSetDuration;

#if DEBUG_LOG
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
				GD.Print($"[PlayerSystem] Step 완료");
				GD.Print($"  현재 시간: {time}");
				GD.Print($"  액션: {_currentAction}");
				GD.Print($"  소비된 시간: {_lastSetDuration}분");
				GD.Print($"  남은 시간: {_remainingDuration}분");
				if (_remainingDuration > 0)
				{
					GD.Print($"  ⚠ 다음 Step에서 계속 진행 예정");
				}
				else
				{
					GD.Print($"  ✓ 완료!");
					_currentAction = "";
				}
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
			}

			// 2. 대기 중인 시간이 없으면 시간 정지
			if (_remainingDuration <= 0)
			{
				planningSystem.SetNextStepDuration(0);
				_lastSetDuration = 0;
				return;
			}

			// 3. 다음 Step에서 진행할 시간 설정
			planningSystem.SetNextStepDuration(_remainingDuration);

			// 실제 적용될 시간 (자정 제한 적용됨) - 다음 Step에서 차감
			_lastSetDuration = planningSystem.NextStepDuration;

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] 다음 Step 예약: {_lastSetDuration}분");
#endif
		}
	}
}
