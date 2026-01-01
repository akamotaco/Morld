namespace Morld;

using System.Collections.Generic;
using System.Text.Json.Serialization;

/// <summary>
/// Character JSON 데이터
/// </summary>
internal class CharacterJsonData
{
	[JsonPropertyName("id")]
	public int Id { get; set; }

	[JsonPropertyName("name")]
	public string Name { get; set; } = string.Empty;

	[JsonPropertyName("comment")]
	public string? Comment { get; set; }

	[JsonPropertyName("regionId")]
	public int RegionId { get; set; }

	[JsonPropertyName("locationId")]
	public int LocationId { get; set; }

	[JsonPropertyName("tags")]
	public Dictionary<string, int>? Tags { get; set; }

	[JsonPropertyName("inventory")]
	public Dictionary<int, int>? Inventory { get; set; }

	[JsonPropertyName("equippedItems")]
	public List<int>? EquippedItems { get; set; }

	[JsonPropertyName("scheduleStack")]
	public ScheduleLayerJsonData[] ScheduleStack { get; set; } = [];

	[JsonPropertyName("currentEdge")]
	public EdgeProgressJsonData? CurrentEdge { get; set; }
}

/// <summary>
/// ScheduleLayer JSON 데이터
/// </summary>
internal class ScheduleLayerJsonData
{
	[JsonPropertyName("name")]
	public string Name { get; set; } = string.Empty;

	[JsonPropertyName("schedule")]
	public ScheduleEntryJsonData[]? Schedule { get; set; }

	[JsonPropertyName("endConditionType")]
	public string? EndConditionType { get; set; }

	[JsonPropertyName("endConditionParam")]
	public string? EndConditionParam { get; set; }
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

	[JsonPropertyName("activity")]
	public string? Activity { get; set; }
}

/// <summary>
/// EdgeProgress JSON 데이터
/// </summary>
internal class EdgeProgressJsonData
{
	[JsonPropertyName("fromRegionId")]
	public int FromRegionId { get; set; }

	[JsonPropertyName("fromLocalId")]
	public int FromLocalId { get; set; }

	[JsonPropertyName("toRegionId")]
	public int ToRegionId { get; set; }

	[JsonPropertyName("toLocalId")]
	public int ToLocalId { get; set; }

	[JsonPropertyName("totalTime")]
	public int TotalTime { get; set; }

	[JsonPropertyName("elapsedTime")]
	public int ElapsedTime { get; set; }
}
