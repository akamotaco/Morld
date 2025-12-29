using ECS;
using Godot;
using System;

namespace SE
{
    public class WorldSystem : ECS.System
    {
        /// <summary>
        /// 로그 출력 시스템. 일단은 eneity를 개수하기 위해 임시로 구현
        /// 향후 텍스트 로그 출력 시스템으로 개조할 예정 있음
        /// </summary>
        private Morld.World _world;

        public WorldSystem(string WorldName)
        {
            _world = new Morld.World(WorldName);
        }

        public Morld.World GetWorld()
        {
            return this._world;
        }
    }
}