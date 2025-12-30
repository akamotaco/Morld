namespace Morld;

using System.Collections.Generic;
using System.Text.Json.Serialization;

/// <summary>
/// Character JSON 데이터
/// </summary>
internal class CharacterJsonData
{
	[JsonPropertyName("id")]
	public string Id { get; set; } = string.Empty;

	[JsonPropertyName("name")]
	public string Name { get; set; } = string.Empty;

	[JsonPropertyName("regionId")]
	public int RegionId { get; set; }

	[JsonPropertyName("locationId")]
	public int LocationId { get; set; }

	[JsonPropertyName("tags")]
	public Dictionary<string, int>? Tags { get; set; }

	[JsonPropertyName("schedule")]
	public ScheduleEntryJsonData[] Schedule { get; set; } = [];
}

/// <summary>
/// Schedule Entry JSON 데이터
/// </summary>
internal class ScheduleEntryJsonData
{
	[JsonPropertyName("name")]
	public string Name { get; set; } = string.Empty;

	[JsonPropertyName("regionId")]
	public int RegionId { get; set; }

	[JsonPropertyName("locationId")]
	public int LocationId { get; set; }

	[JsonPropertyName("start")]
	public int Start { get; set; }

	[JsonPropertyName("end")]
	public int End { get; set; }
}
