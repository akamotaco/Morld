using System;
using ECS;
using Morld;
using Vec2 = Godot.Vector2;

namespace SE
{
    /// <summary>
    /// GravitySystem - 중력 가속도 적용
    ///
    /// 유닛의 VelocityY에 중력을 가산한다.
    /// 최대 낙하 속도를 캡하여 터널링을 방지한다.
    ///
    /// 실행 위치: MovementSystem 앞
    /// </summary>
    public class GravitySystem : ECS.System
    {
        private UnitSystem _unitSystem;
        private bool _initialized;

        /// <summary>
        /// 시스템 활성화 여부 (시나리오 02/03: false)
        /// </summary>
        public bool Enabled { get; set; } = false;

        // 물리 상수 (튜닝 가능)
        public float Gravity { get; set; } = 800f;       // 픽셀/초²
        public float MaxFallSpeed { get; set; } = 400f;   // 픽셀/초 (캡)

        private void EnsureInitialized()
        {
            if (_initialized) return;
            _unitSystem = this._hub?.GetSystem("unitSystem") as UnitSystem;
            _initialized = _unitSystem != null;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            if (!Enabled) return;

            EnsureInitialized();
            if (!_initialized) return;

            float dt = step / 1000f;  // ms → 초

            foreach (var unit in _unitSystem.Units.Values)
            {
                if (!unit.CollisionEnabled) continue;
                if (unit.IsGrounded) continue;  // 지면이면 중력 불필요

                unit.VelocityY += Gravity * dt;
                if (unit.VelocityY > MaxFallSpeed)
                    unit.VelocityY = MaxFallSpeed;
            }
        }
    }
}
