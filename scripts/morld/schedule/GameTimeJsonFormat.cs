namespace Morld;

using System.Text.Json.Serialization;

/// <summary>
/// GameTime JSON 데이터
/// </summary>
internal class GameTimeJsonData
{
    [JsonPropertyName("month")]
    public int Month { get; set; }

    [JsonPropertyName("day")]
    public int Day { get; set; }

    [JsonPropertyName("hour")]
    public int Hour { get; set; }

    [JsonPropertyName("minute")]
    public int Minute { get; set; }
}
