using System;
using ECS;
using Morld;
using Vec2 = Godot.Vector2;

namespace SE
{
    /// <summary>
    /// ResolveSystem - 충돌 응답 처리
    ///
    /// CollisionSystem이 감지한 충돌 결과를 소비하여
    /// 착지, 벽 정지, 천장 반전 등을 처리한다.
    ///
    /// 실행 위치: CollisionSystem 뒤
    /// </summary>
    public class ResolveSystem : ECS.System
    {
        private CollisionSystem _collisionSystem;
        private bool _initialized;

        /// <summary>
        /// 시스템 활성화 여부 (시나리오 02/03: false)
        /// </summary>
        public bool Enabled { get; set; } = false;

        private void EnsureInitialized()
        {
            if (_initialized) return;
            _collisionSystem = this._hub?.GetSystem("collisionSystem") as CollisionSystem;
            _initialized = _collisionSystem != null;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            if (!Enabled) return;

            EnsureInitialized();
            if (!_initialized) return;

            // TODO: Platform Line 충돌 결과 처리
            // - 바닥 충돌 → 착지 (VelocityY=0, Position.Y=바닥, IsGrounded=true)
            // - 벽 충돌 → 정지 (VelocityX=0, Position.X=벽)
            // - 천장 충돌 → 반전 (VelocityY=0)

            // TODO: AABB 유닛↔유닛 충돌 결과 처리
            // - 밀어내기 (push-back)
        }
    }
}
