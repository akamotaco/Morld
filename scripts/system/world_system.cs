using ECS;
using Godot;
using System;

namespace SE
{
    public class WorldSystem : ECS.System
    {
        /// <summary>
        /// graph world 데이터 저장하는 곳
        /// json 파일로 import/export 하는 기능을 제공하며, 다음의 것을 제공함
        /// [morld]
        /// - world
        /// - region (+ region edge)
        /// - location (+ edge)
        /// </summary>
        private Morld.World _world;
        private Morld.GameTime _currentTime;

        public WorldSystem(string WorldName)
        {
            _world = new Morld.World(WorldName);
            _currentTime = new Morld.GameTime();
        }

        public Morld.World GetWorld()
        {
            return this._world;
        }

        internal Morld.GameTime GetTime()
        {
            return this._currentTime;
        }
    }
}