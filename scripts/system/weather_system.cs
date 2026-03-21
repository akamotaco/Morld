using System;
using ECS;
using Morld;

namespace SE
{
    /// <summary>
    /// WeatherSystem - 자정 전환 시 랜덤으로 날씨 변경
    ///
    /// 시간이 자정(00시)으로 넘어가는 순간 모든 Region의 날씨를 변경.
    /// 시간이 흐르지 않으면 날씨도 바뀌지 않음.
    /// </summary>
    public class WeatherSystem : ECS.System
    {
        private WorldSystem _worldSystem;
        private Random _random = new Random();

        /// <summary>
        /// 이전 Step의 시각 (자정 전환 감지용)
        /// </summary>
        private int _prevHour = -1;

        public void SetSystemReferences(WorldSystem worldSystem)
        {
            _worldSystem = worldSystem;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            if (_worldSystem == null)
                return;

            var time = _worldSystem.GetTime();
            var hour = time.Hour;

            // 자정 전환 감지: 이전 시각이 0이 아닌데 현재 0이면 → 날짜가 바뀜
            if (hour == 0 && _prevHour != 0 && _prevHour != -1)
            {
                ChangeAllRegionsWeather();
            }

            _prevHour = hour;
        }

        private void ChangeAllRegionsWeather()
        {
            var terrain = _worldSystem.GetTerrain();
            if (terrain == null)
                return;

            foreach (var region in terrain.Regions)
            {
                var weatherTypes = Region.WeatherTypes;
                var newWeather = weatherTypes[_random.Next(weatherTypes.Length)];
                region.CurrentWeather = newWeather;

#if DEBUG_LOG
                Godot.GD.Print($"[WeatherSystem] Region '{region.Name}' 날씨 변경: {newWeather}");
#endif
            }
        }
    }
}
