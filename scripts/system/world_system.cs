#define DEBUG_LOG

using ECS;
using Godot;
using System;

namespace SE
{
    public class WorldSystem : ECS.System
    {
        /// <summary>
        /// graph terrain 데이터 저장하는 곳
        /// json 파일로 import/export 하는 기능을 제공하며, 다음의 것을 제공함
        /// [morld]
        /// - terrain
        /// - region (+ region edge)
        /// - location (+ edge)
        /// </summary>
        private Morld.Terrain _terrain;
        private Morld.GameTime _currentTime;

        // 시간 업데이트용 누적 시간 (밀리초)
        private int _accumulatedTime = 0;
        private const int TimeUpdateInterval = 1000; // 1초마다 업데이트
        private const int MinutesPerUpdate = 15; // 1초당 15분씩 증가

        // 지난 프레임 이후 흐른 게임 시간 (분 단위)
        private int _deltaGameMinutes = 0;

        public WorldSystem(string TerrainName)
        {
            _terrain = new Morld.Terrain(TerrainName);
            _currentTime = new Morld.GameTime();
        }

        public Morld.Terrain GetTerrain()
        {
            return this._terrain;
        }

        internal Morld.GameTime GetTime()
        {
            return this._currentTime;
        }

        /// <summary>
        /// 지난 프레임 이후 흐른 게임 시간(분) 반환
        /// </summary>
        public int GetDeltaGameMinutes()
        {
            return _deltaGameMinutes;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            // 시간 누적
            _accumulatedTime += step;

            // 매 프레임 초기화
            _deltaGameMinutes = 0;

            // 1초(1000ms)마다 게임 시간 15분씩 증가
            if (_accumulatedTime >= TimeUpdateInterval)
            {
                _accumulatedTime -= TimeUpdateInterval;
                _deltaGameMinutes = MinutesPerUpdate;
                _currentTime.AddMinutes(MinutesPerUpdate);

#if DEBUG_LOG
                GD.Print($"[WorldSystem] Current Time: {_currentTime}");
#endif
            }
        }
    }
}