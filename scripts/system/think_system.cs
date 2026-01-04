using System;
using ECS;
using Godot;

namespace SE
{
    /// <summary>
    /// ThinkSystem - Python Agent 전용 AI 시스템
    ///
    /// 역할:
    /// - Python think.think_all() 함수 호출
    /// - 각 NPC Agent가 JobList에 Job을 삽입
    /// - JobBehaviorSystem이 Job을 실행
    ///
    /// 실행 순서: ThinkSystem → JobBehaviorSystem → EventSystem
    /// (ThinkSystem이 먼저 JobList를 채우고, JobBehaviorSystem이 실행)
    /// </summary>
    public class ThinkSystem : ECS.System
    {
        private ScriptSystem? _scriptSystem;
        private PlayerSystem? _playerSystem;
        private UnitSystem? _unitSystem;
        private bool _thinkModuleAvailable = false;
        private bool _checkedModule = false;

        /// <summary>
        /// 시스템 참조 설정
        /// </summary>
        public void SetSystemReferences(
            ScriptSystem? scriptSystem,
            PlayerSystem? playerSystem,
            UnitSystem? unitSystem)
        {
            _scriptSystem = scriptSystem;
            _playerSystem = playerSystem;
            _unitSystem = unitSystem;
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

            // think 모듈 존재 여부 한 번만 체크
            if (!_checkedModule)
            {
                _checkedModule = true;
                _thinkModuleAvailable = _scriptSystem.IsThinkModuleAvailable();
            }

            // think 모듈이 없으면 스킵
            if (!_thinkModuleAvailable)
                return;

            // Python think_all() 호출
            try
            {
                _scriptSystem.CallThinkAll();
            }
            catch (Exception ex)
            {
                GD.PrintErr($"[ThinkSystem] Error calling think_all(): {ex.Message}");
            }
        }
    }
}
