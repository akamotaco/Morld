using ECS;
using SharpPy;

namespace SE
{
    /// <summary>
    /// WeatherSystem - 모든 Region의 Python update_weather() 호출
    ///
    /// 역할:
    /// - 매 Step마다 Python entities.proc_all("BaseRegion", "update_weather", game_time) 호출
    /// - 각 Region이 시간에 따라 날씨를 변경하도록 함
    ///
    /// 실행 순서:
    /// MovementSystem → EventSystem → WeatherSystem → ThinkSystem → BehaviorSystem
    /// </summary>
    public class WeatherSystem : ECS.System
    {
        private WorldSystem _worldSystem;
        private ScriptSystem _scriptSystem;

        /// <summary>
        /// 시스템 참조 설정
        /// </summary>
        public void SetSystemReferences(
            WorldSystem worldSystem,
            ScriptSystem scriptSystem)
        {
            _worldSystem = worldSystem;
            _scriptSystem = scriptSystem;
        }

        /// <summary>
        /// 매 Step마다 호출
        /// </summary>
        public void Proc(int step)
        {
            if (_worldSystem == null || _scriptSystem == null)
            {
                Godot.GD.PrintErr("[WeatherSystem] System references not set");
                return;
            }

            // 현재 게임 시간 (분 단위)
            int gameTime = _worldSystem.GetTime().MinuteOfDay;

            // Python proc_all 호출
            try
            {
                // entities.proc_all("BaseRegion", "update_weather", game_time) 호출
                var code = $"entities.proc_all('BaseRegion', 'update_weather', {gameTime})";
                _scriptSystem.Eval(code);

                // update_weather는 morld.set_region_weather()를 직접 호출하므로
                // 별도의 결과 처리 불필요
            }
            catch (System.Exception ex)
            {
                // entities 모듈이 아직 로드되지 않은 경우 무시
                // (기존 JSON 모드에서는 entities 모듈이 없음)
                if (!ex.Message.Contains("entities"))
                {
                    Godot.GD.PrintErr($"[WeatherSystem] Error: {ex.Message}");
                }
            }
        }
    }
}
