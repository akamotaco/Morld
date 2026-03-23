using System;
using System.Collections.Generic;
using ECS;
using Morld;

namespace SE
{
    /// <summary>
    /// WeatherSystem - 자연스러운 날씨 전이 시스템
    ///
    /// CPython temperature.py의 계절/시간 로직을 C#으로 이식.
    /// 매시간 전이 판정: 맑음 ↔ 흐림 ↔ 비/눈 (온도 기반 분기)
    /// 소나기: 맑음→비 돌발 전환 (1~3시간 후 자동 복귀)
    /// 시간이 흐르지 않으면 날씨도 바뀌지 않음.
    /// </summary>
    public class WeatherSystem : ECS.System
    {
        private WorldSystem _worldSystem;
        private Random _random = new Random();
        private int _prevHour = -1;

        #region Constants (Python temperature.py 이식)

        // 계절별 기본 온도 (°C)
        private static readonly Dictionary<string, int> SeasonBase = new()
        {
            { "봄", 15 }, { "여름", 28 }, { "가을", 12 }, { "겨울", -5 }
        };

        // 날씨 보정값
        private static readonly Dictionary<string, int> WeatherModifier = new()
        {
            { "맑음", 2 }, { "흐림", 0 }, { "비", -3 }, { "눈", -5 }
        };

        // 시간대별 온도 오프셋 (index = hour, 0~23)
        private static readonly int[] HourOffsets =
        {
            -4, -4, -5, -5, -5, -5,   // 00~05
            -3, -2, -1,  0,            // 06~09
            +2, +3, +4, +5, +5,       // 10~14
            +4, +3, +2, +1,  0,       // 15~19
            -1, -2, -3, -3,            // 20~23
        };

        // 전이 확률 테이블 (현재날씨 → {다음날씨: 가중치})
        // 매시간 전이 판정 — 대부분 유지, 가끔 전환
        private static readonly Dictionary<string, (string weather, int weight)[]> TransitionTable = new()
        {
            { "맑음", new[] { ("맑음", 85), ("흐림", 12), ("비", 3) } },      // 소나기 확률 3%
            { "흐림", new[] { ("흐림", 60), ("맑음", 20), ("비", 20) } },     // 흐림은 불안정
            { "비",   new[] { ("비", 70), ("흐림", 25), ("맑음", 5) } },      // 비는 서서히 개임
            { "눈",   new[] { ("눈", 75), ("흐림", 20), ("맑음", 5) } },      // 눈도 서서히 개임
        };

        // 소나기 지속 시간 (시간 단위)
        private const int ShowerMinHours = 1;
        private const int ShowerMaxHours = 3;

        #endregion

        #region Per-Region State

        // Region별 소나기 상태 추적
        private readonly Dictionary<int, int> _showerRemainingHours = new();
        // Region별 소나기 이전 날씨 (복귀용)
        private readonly Dictionary<int, string> _showerPrevWeather = new();

        #endregion

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

            // 시간 변경 감지 (매시간 1회만)
            if (hour == _prevHour || _prevHour == -1)
            {
                _prevHour = hour;
                return;
            }

            _prevHour = hour;

            // 매시간 전이 판정
            UpdateAllRegionsWeather(time);
        }

        private void UpdateAllRegionsWeather(Morld.GameTime time)
        {
            var terrain = _worldSystem.GetTerrain();
            if (terrain == null)
                return;

            var season = GetSeason(time.Month);
            var estimatedTemp = EstimateTemperature(season, "흐림", time.Hour); // 중립 날씨 기준 추정

            foreach (var region in terrain.Regions)
            {
                var currentWeather = region.CurrentWeather;
                var newWeather = DetermineNextWeather(region.Id, currentWeather, season, estimatedTemp);

                if (newWeather != currentWeather)
                {
                    region.CurrentWeather = newWeather;
#if DEBUG_LOG
                    Godot.GD.Print($"[WeatherSystem] Region '{region.Name}': {currentWeather} → {newWeather} (temp≈{estimatedTemp}°C)");
#endif
                }
            }
        }

        private string DetermineNextWeather(int regionId, string currentWeather, string season, float estimatedTemp)
        {
            // 1. 소나기 처리: 남은 시간 감소 → 0이면 이전 날씨로 복귀
            if (_showerRemainingHours.TryGetValue(regionId, out var remaining))
            {
                remaining--;
                if (remaining <= 0)
                {
                    _showerRemainingHours.Remove(regionId);
                    var prev = _showerPrevWeather.GetValueOrDefault(regionId, "흐림");
                    _showerPrevWeather.Remove(regionId);
                    return prev;
                }
                _showerRemainingHours[regionId] = remaining;
                return currentWeather; // 소나기 진행 중 — 변경 없음
            }

            // 2. 전이 테이블에서 다음 날씨 뽑기
            if (!TransitionTable.TryGetValue(currentWeather, out var transitions))
                return currentWeather;

            var totalWeight = 0;
            foreach (var (_, w) in transitions)
                totalWeight += w;

            var roll = _random.Next(totalWeight);
            var nextWeather = currentWeather;
            var cumulative = 0;
            foreach (var (weather, weight) in transitions)
            {
                cumulative += weight;
                if (roll < cumulative)
                {
                    nextWeather = weather;
                    break;
                }
            }

            // 3. 온도 기반 비/눈 분기
            if (nextWeather == "비" && estimatedTemp <= 0)
                nextWeather = "눈";
            else if (nextWeather == "눈" && estimatedTemp > 2)
                nextWeather = "비";

            // 4. 소나기 감지: 맑음 → 비 직접 전환 = 소나기
            if (currentWeather == "맑음" && (nextWeather == "비" || nextWeather == "눈"))
            {
                _showerPrevWeather[regionId] = "흐림"; // 소나기 후 흐림으로 복귀 (맑음으로 바로 안 감)
                _showerRemainingHours[regionId] = ShowerMinHours + _random.Next(ShowerMaxHours - ShowerMinHours + 1);
            }

            return nextWeather;
        }

        #region Temperature Estimation (Python temperature.py 이식)

        private static string GetSeason(int month)
        {
            return month switch
            {
                >= 3 and <= 5 => "봄",
                >= 6 and <= 8 => "여름",
                >= 9 and <= 11 => "가을",
                _ => "겨울"
            };
        }

        private static float EstimateTemperature(string season, string weather, int hour)
        {
            var baseTemp = SeasonBase.GetValueOrDefault(season, 15);
            var weatherMod = WeatherModifier.GetValueOrDefault(weather, 0);
            var hourOffset = (hour >= 0 && hour < 24) ? HourOffsets[hour] : 0;
            return baseTemp + weatherMod + hourOffset;
        }

        #endregion
    }
}
