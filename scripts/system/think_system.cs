#define DEBUG_LOG

using System;
using ECS;
using Godot;

namespace SE
{
    /// <summary>
    /// ThinkSystem - NPC AI 경로 계획
    ///
    /// 역할:
    /// - Python think.think_all() 함수 호출
    /// - 각 NPC Agent가 경로를 계획 (PlannedRoute 설정)
    /// - MovementSystem이 계획된 경로를 실행
    ///
    /// 실행 순서: ThinkSystem → MovementSystem → BehaviorSystem
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
            // 시간 진행이 없으면 스킵
            if (_playerSystem == null || _playerSystem.NextStepDuration <= 0)
                return;

            // ScriptSystem이 없으면 스킵
            if (_scriptSystem == null)
                return;

            // think 모듈 존재 여부 한 번만 체크
            if (!_checkedModule)
            {
                _checkedModule = true;
                _thinkModuleAvailable = _scriptSystem.IsThinkModuleAvailable();
#if DEBUG_LOG
                if (_thinkModuleAvailable)
                    GD.Print("[ThinkSystem] think module available");
                else
                    GD.Print("[ThinkSystem] think module not available, using schedule-based movement");
#endif
            }

            // think 모듈이 없으면 스킵 (스케줄 기반 이동으로 폴백)
            if (!_thinkModuleAvailable) return;

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
