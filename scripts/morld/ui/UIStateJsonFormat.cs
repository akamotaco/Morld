using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Morld;

/// <summary>
/// Focus JSON 직렬화 포맷
/// </summary>
public class FocusJsonData
{
	[JsonPropertyName("type")]
	public string Type { get; set; } = "Situation";

	[JsonPropertyName("unitId")]
	public int? UnitId { get; set; }

	[JsonPropertyName("itemId")]
	public int? ItemId { get; set; }

	[JsonPropertyName("context")]
	public string? Context { get; set; }

	[JsonPropertyName("message")]
	public string? Message { get; set; }

	[JsonPropertyName("expandedToggles")]
	public List<string> ExpandedToggles { get; set; } = new();

	/// <summary>
	/// Focus로 변환
	/// </summary>
	public Focus ToFocus()
	{
		var focusType = Type switch
		{
			"Situation" => FocusType.Situation,
			"Unit" => FocusType.Unit,
			"Inventory" => FocusType.Inventory,
			"Item" => FocusType.Item,
			"Result" => FocusType.Result,
			_ => FocusType.Situation
		};

		return new Focus
		{
			Type = focusType,
			UnitId = UnitId,
			ItemId = ItemId,
			Context = Context,
			Message = Message,
			ExpandedToggles = new HashSet<string>(ExpandedToggles)
		};
	}

	/// <summary>
	/// Focus에서 생성
	/// </summary>
	public static FocusJsonData FromFocus(Focus focus)
	{
		return new FocusJsonData
		{
			Type = focus.Type.ToString(),
			UnitId = focus.UnitId,
			ItemId = focus.ItemId,
			Context = focus.Context,
			Message = focus.Message,
			ExpandedToggles = new List<string>(focus.ExpandedToggles)
		};
	}
}

/// <summary>
/// UI 상태 JSON 직렬화 포맷
/// </summary>
public class UIStateJsonData
{
	[JsonPropertyName("focusStack")]
	public List<FocusJsonData> FocusStack { get; set; } = new();
}
