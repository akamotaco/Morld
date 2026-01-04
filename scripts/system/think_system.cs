using ECS;
using SharpPy;

namespace SE
{
    /// <summary>
    /// ThinkSystem - 모든 캐릭터의 Python think() 호출
    ///
    /// 역할:
    /// - 매 Step마다 Python entities.proc_all("BaseCharacter", "think", game_time) 호출
    /// - 각 캐릭터가 다음 행동을 결정하도록 함
    /// - PlayerSystem과 연동하여 플레이어 명령 override
    ///
    /// 실행 순서:
    /// MovementSystem → EventSystem → WeatherSystem → ThinkSystem → BehaviorSystem
    /// </summary>
    public class ThinkSystem : ECS.System
    {
        private WorldSystem _worldSystem;
        private UnitSystem _unitSystem;
        private PlayerSystem _playerSystem;
        private ScriptSystem _scriptSystem;

        /// <summary>
        /// 시스템 참조 설정
        /// </summary>
        public void SetSystemReferences(
            WorldSystem worldSystem,
            UnitSystem unitSystem,
            PlayerSystem playerSystem,
            ScriptSystem scriptSystem)
        {
            _worldSystem = worldSystem;
            _unitSystem = unitSystem;
            _playerSystem = playerSystem;
            _scriptSystem = scriptSystem;
        }

        /// <summary>
        /// 매 Step마다 호출
        /// </summary>
        public void Proc(int step)
        {
            if (_worldSystem == null || _unitSystem == null || _scriptSystem == null)
            {
                Godot.GD.PrintErr("[ThinkSystem] System references not set");
                return;
            }

            // 현재 게임 시간 (분 단위)
            int gameTime = _worldSystem.GetTime().MinuteOfDay;

            // Python proc_all 호출
            try
            {
                // entities.proc_all("BaseCharacter", "think", game_time) 호출
                var code = $"entities.proc_all('BaseCharacter', 'think', {gameTime})";
                var result = _scriptSystem.Eval(code);

                // 결과 처리 (현재는 각 캐릭터가 morld API를 직접 호출하므로 별도 처리 불필요)
                // 향후 명령 수집 및 일괄 적용 방식으로 변경 가능
                if (result is PyDict resultDict)
                {
                    ProcessThinkResults(resultDict);
                }
            }
            catch (System.Exception ex)
            {
                // entities 모듈이 아직 로드되지 않은 경우 무시
                // (기존 JSON 모드에서는 entities 모듈이 없음)
                if (!ex.Message.Contains("entities"))
                {
                    Godot.GD.PrintErr($"[ThinkSystem] Error: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// think() 결과 처리
        /// 각 캐릭터의 명령을 수집하고 적용
        /// </summary>
        private void ProcessThinkResults(PyDict results)
        {
            // 현재 구현에서는 각 캐릭터가 think() 내에서 morld API를 직접 호출
            // 향후 명령 수집 방식:
            // - results: { unit_id: { "action": "move", "target": (0, 1) }, ... }
            // - PlayerSystem override 체크
            // - 각 유닛에 명령 적용

            int playerId = _playerSystem?.PlayerId ?? 0;

            var keys = results.Keys();
            for (int i = 0; i < keys.Length(); i++)
            {
                var key = keys.GetItem(i);
                int unitId = key is PyInt pyInt ? (int)pyInt.Value : 0;
                var command = results.GetItem(key) as PyDict;

                if (command == null) continue;

                // 플레이어인 경우 PlayerSystem에서 override 체크
                if (unitId == playerId && _playerSystem != null)
                {
                    // PlayerSystem에 pending 명령이 있으면 Python 결과 무시
                    // (PlayerSystem이 별도로 처리)
                    continue;
                }

                // NPC는 Python 결과 그대로 적용
                // 현재는 think() 내에서 morld API를 직접 호출하므로 추가 처리 불필요
            }
        }

        /// <summary>
        /// 특정 유닛이 "대기" 스케줄 상태인지 확인
        /// freeze된 유닛은 think() 스킵 대상
        /// </summary>
        public bool IsUnitFrozen(int unitId)
        {
            var unit = _unitSystem?.GetUnit(unitId);
            if (unit == null) return false;

            var layer = unit.CurrentScheduleLayer;
            return layer?.EndConditionType == "대기";
        }
    }
}
