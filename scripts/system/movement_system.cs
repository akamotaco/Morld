using System;
using ECS;
using Morld;
using Vec2 = Godot.Vector2;

namespace SE
{
    /// <summary>
    /// MovementSystem - 속도 → 위치 갱신
    ///
    /// Velocity를 Position에 반영한다.
    /// 이전 위치를 보존하여 Swept 충돌 검사에 활용한다.
    /// Ring geometry에서는 X축 wrap-around(NormalizeX)를 적용한다.
    ///
    /// 실행 위치: GravitySystem 뒤, CollisionSystem 앞
    /// </summary>
    public class MovementSystem : ECS.System
    {
        private UnitSystem _unitSystem;
        private WorldSystem _worldSystem;
        private bool _initialized;

        /// <summary>
        /// 시스템 활성화 여부 (시나리오 02/03: false — 기존 이동 유지)
        /// </summary>
        public bool Enabled { get; set; } = false;

        private void EnsureInitialized()
        {
            if (_initialized) return;
            _unitSystem = this._hub?.GetSystem("unitSystem") as UnitSystem;
            _worldSystem = this._hub?.GetSystem("worldSystem") as WorldSystem;
            _initialized = _unitSystem != null && _worldSystem != null;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            if (!Enabled) return;

            EnsureInitialized();
            if (!_initialized) return;

            float dt = step / 1000f;  // ms → 초
            var terrain = _worldSystem.GetTerrain();
            if (terrain == null) return;

            foreach (var unit in _unitSystem.Units.Values)
            {
                if (!unit.CollisionEnabled) continue;

                // 이전 위치 보존 (Swept 검사용)
                unit.PrevPosition = unit.Position;

                // 속도 → 위치 갱신
                var pos = unit.Position;
                pos.X += unit.VelocityX * dt;
                pos.Y += unit.VelocityY * dt;

                // Ring wrap-around
                var location = terrain.GetLocation(unit.CurrentLocation);
                if (location != null && location.Geometry == LocationGeometry.Ring)
                {
                    float maxX = location.MaxX;
                    if (maxX > 0f)
                    {
                        while (pos.X < 0f) pos.X += maxX;
                        while (pos.X >= maxX) pos.X -= maxX;
                    }
                }
                // Line clamp
                else if (location != null)
                {
                    pos.X = MathF.Max(0f, MathF.Min(pos.X, location.MaxX));
                }

                unit.Position = pos;
            }
        }
    }
}
