using System.Collections.Generic;

namespace Morld;

/// <summary>
/// 화면 레이어 (스택의 각 요소)
/// </summary>
public class ScreenLayer
{
	/// <summary>
	/// 원본 텍스트 (DescribeSystem이 생성한 BBCode)
	/// </summary>
	public string Text { get; set; } = "";

	/// <summary>
	/// 펼쳐진 토글 ID 목록
	/// </summary>
	public HashSet<string> ExpandedToggles { get; set; } = new();
}
