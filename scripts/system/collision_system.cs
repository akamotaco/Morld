using System;
using System.Collections.Generic;
using ECS;
using Morld;
using Vec2 = Godot.Vector2;

namespace SE
{
    /// <summary>
    /// CollisionSystem - AABB 충돌 판정
    ///
    /// 같은 Location 내 유닛 간 AABB 충돌을 감지한다.
    /// Ring geometry에서는 X축 wrap-around를 고려한다.
    ///
    /// 모드:
    ///   - log_only: 충돌 감지 시 로그만 출력 (시나리오 02/03)
    ///   - full: 충돌 응답 처리 (시나리오 04, 향후)
    ///
    /// 실행 위치: EventSystem 앞
    /// </summary>
    public class CollisionSystem : ECS.System
    {
        private WorldSystem _worldSystem;
        private UnitSystem _unitSystem;
        private bool _initialized;

        /// <summary>
        /// 충돌 모드
        /// </summary>
        public enum CollisionMode
        {
            Disabled,  // 충돌 판정 안 함
            LogOnly,   // 감지만 + 로그
            Full       // 감지 + 응답 (향후)
        }

        public CollisionMode Mode { get; set; } = CollisionMode.Disabled;

        /// <summary>
        /// 이번 Step에서 감지된 충돌 쌍 (외부에서 조회 가능)
        /// </summary>
        public List<CollisionPair> CurrentCollisions { get; } = new();

        private void EnsureInitialized()
        {
            if (_initialized) return;
            _worldSystem = this._hub?.GetSystem("worldSystem") as WorldSystem;
            _unitSystem = this._hub?.GetSystem("unitSystem") as UnitSystem;
            _initialized = _worldSystem != null && _unitSystem != null;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            if (Mode == CollisionMode.Disabled) return;

            EnsureInitialized();
            if (!_initialized) return;

            CurrentCollisions.Clear();

            var terrain = _worldSystem.GetTerrain();
            if (terrain == null) return;

            // Location별로 유닛을 그룹화하여 충돌 판정
            var unitsByLocation = GroupUnitsByLocation();

            foreach (var (locationRef, units) in unitsByLocation)
            {
                if (units.Count < 2) continue;

                var location = terrain.GetLocation(locationRef);
                if (location == null) continue;

                bool isRing = location.Geometry == LocationGeometry.Ring;
                float wrapX = isRing ? location.MaxX : 0f;

                // O(n^2) 브루트포스 — Location 내 유닛 수가 적으므로 OK
                for (int i = 0; i < units.Count; i++)
                {
                    var a = units[i];
                    if (!a.CollisionEnabled) continue;

                    for (int j = i + 1; j < units.Count; j++)
                    {
                        var b = units[j];
                        if (!b.CollisionEnabled) continue;

                        if (CheckAABB(a, b, isRing, wrapX))
                        {
                            var pair = new CollisionPair(a, b, locationRef);
                            CurrentCollisions.Add(pair);

                            if (Mode == CollisionMode.LogOnly)
                            {
#if DEBUG_LOG
                                Godot.GD.Print(
                                    $"[Collision] {a.Name}(id={a.Id}) ↔ {b.Name}(id={b.Id}) " +
                                    $"at R{locationRef.RegionId}L{locationRef.LocalId} " +
                                    $"(A={a.PositionX:F0}, B={b.PositionX:F0})");
#endif
                            }
                        }
                    }
                }
            }
        }

        /// <summary>
        /// 같은 Location에 있는 유닛끼리 그룹화
        /// </summary>
        private Dictionary<LocationRef, List<Unit>> GroupUnitsByLocation()
        {
            var result = new Dictionary<LocationRef, List<Unit>>();
            foreach (var unit in _unitSystem.Units.Values)
            {
                if (!unit.CollisionEnabled) continue;
                var loc = unit.CurrentLocation;
                if (!result.TryGetValue(loc, out var list))
                {
                    list = new List<Unit>();
                    result[loc] = list;
                }
                list.Add(unit);
            }
            return result;
        }

        /// <summary>
        /// AABB 충돌 판정 (2D)
        /// Ring geometry에서는 X축 wrap-around를 고려한다.
        /// </summary>
        private static bool CheckAABB(Unit a, Unit b, bool isRing, float wrapX)
        {
            // Y축 판정
            float aMinY = a.PositionY - a.CollisionSize.Y * 0.5f;
            float aMaxY = a.PositionY + a.CollisionSize.Y * 0.5f;
            float bMinY = b.PositionY - b.CollisionSize.Y * 0.5f;
            float bMaxY = b.PositionY + b.CollisionSize.Y * 0.5f;

            if (aMaxY <= bMinY || bMaxY <= aMinY)
                return false;  // Y축 분리

            // X축 판정
            float aHalfW = a.CollisionSize.X * 0.5f;
            float bHalfW = b.CollisionSize.X * 0.5f;

            float dx = MathF.Abs(a.PositionX - b.PositionX);

            // Ring wrap-around: 직선 거리와 wrap 거리 중 짧은 쪽
            if (isRing && wrapX > 0f)
                dx = MathF.Min(dx, wrapX - dx);

            return dx < (aHalfW + bHalfW);
        }
    }

    /// <summary>
    /// 충돌 쌍 데이터
    /// </summary>
    public readonly struct CollisionPair
    {
        public Unit A { get; }
        public Unit B { get; }
        public LocationRef Location { get; }

        public CollisionPair(Unit a, Unit b, LocationRef location)
        {
            A = a;
            B = b;
            Location = location;
        }

        public override string ToString() =>
            $"{A.Name} ↔ {B.Name} at {Location}";
    }
}
