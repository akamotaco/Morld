namespace Morld;

using System.Text.Json.Serialization;

/// <summary>
/// GameTime JSON 루트 데이터
/// </summary>
internal class GameTimeJsonData
{
    [JsonPropertyName("calendar")]
    public CalendarConfig Calendar { get; set; } = new();

    [JsonPropertyName("currentTime")]
    public CurrentTimeData CurrentTime { get; set; } = new();

    [JsonPropertyName("holidays")]
    public HolidayData[] Holidays { get; set; } = [];
}

/// <summary>
/// 달력 설정
/// </summary>
internal class CalendarConfig
{
    [JsonPropertyName("daysPerMonth")]
    public int[] DaysPerMonth { get; set; } = [];

    [JsonPropertyName("weekdayNames")]
    public string[] WeekdayNames { get; set; } = [];
}

/// <summary>
/// 현재 시간 데이터
/// </summary>
internal class CurrentTimeData
{
    [JsonPropertyName("year")]
    public int Year { get; set; }

    [JsonPropertyName("month")]
    public int Month { get; set; }

    [JsonPropertyName("day")]
    public int Day { get; set; }

    [JsonPropertyName("hour")]
    public int Hour { get; set; }

    [JsonPropertyName("minute")]
    public int Minute { get; set; }
}

/// <summary>
/// 기념일 데이터
/// </summary>
internal class HolidayData
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("month")]
    public int Month { get; set; }

    [JsonPropertyName("startDay")]
    public int StartDay { get; set; }

    [JsonPropertyName("endDay")]
    public int EndDay { get; set; }
}
