using ECS;
using Godot;

namespace SE
{
    /// <summary>
    /// 자동 시간 흐름 시스템
    ///
    /// 기능:
    /// - 실시간 A초마다 게임 시간 B분을 자동으로 흘러가게 함
    /// - ON/OFF 토글 가능 (Python settings.py와 연동)
    /// - 플레이어 액션 시 타이머 리셋
    ///
    /// 동작 원리:
    /// - Update()가 true 반환 시 GameEngine에서 RequestTimeAdvance() 호출
    /// - 기존 ECS 파이프라인(Step)을 통해 전체 시뮬레이션 수행
    /// - 멍때리기와 동일한 로직으로 세계가 움직임 (이벤트 발생 가능)
    /// </summary>
    public class AutoTimeFlowSystem : ECS.System
    {
        /// <summary>
        /// 자동 시간 흐름 활성화 여부
        /// </summary>
        public bool Enabled { get; private set; } = false;

        /// <summary>
        /// 실시간 간격 (초) - 이 시간마다 게임 시간이 흐름
        /// </summary>
        public float RealTimeIntervalSeconds { get; set; } = 5.0f;

        /// <summary>
        /// 게임 시간 간격 (밀리초) - 한 번에 흐르는 게임 시간
        /// </summary>
        public int GameTimeIntervalMillis { get; set; } = Morld.GameTime.MillisPerMinute;

        /// <summary>
        /// 누적된 실시간 (초)
        /// </summary>
        private float _accumulatedRealTime = 0.0f;

        /// <summary>
        /// 자동 시간 흐름 활성화
        /// </summary>
        public void Enable()
        {
            Enabled = true;
            ResetTimer();
            GD.Print("[AutoTimeFlowSystem] Enabled");
        }

        /// <summary>
        /// 자동 시간 흐름 비활성화
        /// </summary>
        public void Disable()
        {
            Enabled = false;
            ResetTimer();
            GD.Print("[AutoTimeFlowSystem] Disabled");
        }

        /// <summary>
        /// 자동 시간 흐름 토글
        /// </summary>
        public void Toggle()
        {
            if (Enabled)
                Disable();
            else
                Enable();
        }

        /// <summary>
        /// 타이머 리셋 (플레이어 액션 시 호출)
        /// </summary>
        public void ResetTimer()
        {
            _accumulatedRealTime = 0.0f;
        }

        /// <summary>
        /// 실시간 경과 업데이트 (GameEngine._Process에서 호출)
        /// </summary>
        /// <param name="deltaSeconds">경과한 실시간 (초)</param>
        /// <returns>시간 진행이 필요하면 true (GameEngine에서 RequestTimeAdvance 호출)</returns>
        public bool Update(float deltaSeconds)
        {
            if (!Enabled)
                return false;

            // 시간 정지 상태면 자동 시간 흐름도 정지
            var worldSystem = _hub?.GetSystem("worldSystem") as WorldSystem;
            if (worldSystem == null || worldSystem.IsTimeFrozen())
                return false;

            // 플레이어가 이미 시간 진행 중이면 자동 흐름 중지 (타이머도 리셋)
            var playerSystem = _hub?.GetSystem("playerSystem") as PlayerSystem;
            if (playerSystem != null && playerSystem.HasPendingTime)
            {
                ResetTimer();
                return false;
            }

            // 현재 Focus가 시간 흐름을 허용하지 않으면 정지
            // (대화, 인벤토리 등에서는 시간이 흐르지 않음)
            // Focus.TimeFlows가 true인 다이얼로그(지도 보기 등)에서만 계속 흐름
            var textUISystem = _hub?.GetSystem("textUISystem") as TextUISystem;
            if (textUISystem != null && !textUISystem.CanAutoTimeFlow())
            {
                return false;
            }

            _accumulatedRealTime += deltaSeconds;

            if (_accumulatedRealTime >= RealTimeIntervalSeconds)
            {
                _accumulatedRealTime = 0.0f;
                // GameEngine에서 RequestTimeAdvance()를 호출하도록 true 반환
                // 기존 ECS 파이프라인(Step)을 통해 전체 시뮬레이션 수행
                int displaySec = GameTimeIntervalMillis / Morld.GameTime.MillisPerSecond;
                GD.Print($"[AutoTimeFlowSystem] Triggering time advance: +{displaySec} seconds ({GameTimeIntervalMillis}ms)");
                return true;
            }

            return false;
        }

        protected override void Proc(int step, System.Span<Component[]> allComponents)
        {
            // Update()에서 처리하므로 Proc은 비어있음
        }
    }
}
