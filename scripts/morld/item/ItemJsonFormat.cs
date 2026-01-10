namespace Morld;

using System.Collections.Generic;
using System.Text.Json.Serialization;

/// <summary>
/// Item JSON 데이터
/// </summary>
internal class ItemJsonData
{
	[JsonPropertyName("id")]
	public int Id { get; set; }

	[JsonPropertyName("name")]
	public string Name { get; set; } = string.Empty;

	[JsonPropertyName("comment")]
	public string? Comment { get; set; }

	[JsonPropertyName("passiveProps")]
	public Dictionary<string, int>? PassiveProps { get; set; }

	[JsonPropertyName("equipProps")]
	public Dictionary<string, int>? EquipProps { get; set; }

	[JsonPropertyName("value")]
	public int Value { get; set; } = 0;

	[JsonPropertyName("actions")]
	public List<string>? Actions { get; set; }

	[JsonPropertyName("actionProps")]
	public Dictionary<string, int>? ActionProps { get; set; }
}
