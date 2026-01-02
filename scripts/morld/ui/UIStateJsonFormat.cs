using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Morld;

/// <summary>
/// 화면 레이어 JSON 직렬화 포맷
/// </summary>
public class ScreenLayerJsonData
{
	[JsonPropertyName("text")]
	public string Text { get; set; } = "";

	[JsonPropertyName("expandedToggles")]
	public List<string> ExpandedToggles { get; set; } = new();

	/// <summary>
	/// ScreenLayer로 변환
	/// </summary>
	public ScreenLayer ToScreenLayer()
	{
		return new ScreenLayer
		{
			Text = Text,
			ExpandedToggles = new HashSet<string>(ExpandedToggles)
		};
	}

	/// <summary>
	/// ScreenLayer에서 생성
	/// </summary>
	public static ScreenLayerJsonData FromScreenLayer(ScreenLayer layer)
	{
		return new ScreenLayerJsonData
		{
			Text = layer.Text,
			ExpandedToggles = new List<string>(layer.ExpandedToggles)
		};
	}
}

/// <summary>
/// UI 상태 JSON 직렬화 포맷
/// </summary>
public class UIStateJsonData
{
	[JsonPropertyName("screenStack")]
	public List<ScreenLayerJsonData> ScreenStack { get; set; } = new();
}
