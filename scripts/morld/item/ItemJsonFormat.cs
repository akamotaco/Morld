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

	[JsonPropertyName("passiveTags")]
	public Dictionary<string, int>? PassiveTags { get; set; }

	[JsonPropertyName("equipTags")]
	public Dictionary<string, int>? EquipTags { get; set; }

	[JsonPropertyName("value")]
	public int Value { get; set; } = 0;
}
