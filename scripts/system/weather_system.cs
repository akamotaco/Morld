using System;
using ECS;
using Morld;

namespace SE
{
    /// <summary>
    /// WeatherSystem - 매일 자정에 랜덤으로 날씨 변경
    ///
    /// 역할:
    /// - 자정(00:00)에 모든 Region의 날씨를 랜덤으로 변경
    /// - Region.WeatherTypes 배열에서 랜덤 선택
    ///
    /// 실행 순서:
    /// JobBehaviorSystem → EventSystem → WeatherSystem → ThinkSystem
    /// </summary>
    public class WeatherSystem : ECS.System
    {
        private WorldSystem _worldSystem;
        private Random _random = new Random();

        /// <summary>
        /// 마지막으로 날씨를 변경한 날짜 (중복 변경 방지)
        /// </summary>
        private int _lastWeatherChangeDay = -1;

        /// <summary>
        /// 시스템 참조 설정
        /// </summary>
        public void SetSystemReferences(WorldSystem worldSystem)
        {
            _worldSystem = worldSystem;
        }

        /// <summary>
        /// 매 Step마다 호출 - 자정에 날씨 변경
        /// </summary>
        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            if (_worldSystem == null)
                return;

            var time = _worldSystem.GetTime();
            var currentDay = time.Day;

            // 이미 오늘 날씨를 변경했으면 스킵
            if (currentDay == _lastWeatherChangeDay)
                return;

            // 자정(00:00~00:59) 또는 첫 실행 시 날씨 변경
            if (time.Hour == 0 || _lastWeatherChangeDay == -1)
            {
                ChangeAllRegionsWeather();
                _lastWeatherChangeDay = currentDay;
            }
        }

        /// <summary>
        /// 모든 Region의 날씨를 랜덤으로 변경
        /// </summary>
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
