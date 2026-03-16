namespace Morld.TextUI;

/// <summary>
/// 플랫폼 독립 테마. 색상은 RGBA float (0~1).
/// 모든 텍스트 스타일링의 단일 소스 — Python/C#에서 색상을 하드코딩하지 않음.
/// </summary>
public class TextUIThemeBase
{
	// ── 아이콘 ──
	public string TodoCheckedIcon     = "☑";
	public string TodoUncheckedIcon   = "☐";
	public string ButtonOnIcon        = "●";
	public string ButtonOffIcon       = "○";
	public string ToggleOpenIcon      = "▼";
	public string ToggleClosedIcon    = "▶";
	public string RadioSelectedIcon   = "◉";
	public string RadioUnselectedIcon = "○";
	public string ChoiceIcon          = "▸";
	public string ChoiceSelectedIcon  = "▸";

	// ── 위젯 색상 ──
	public (float R, float G, float B, float A) ActiveColor     = (0.3f, 0.8f, 0.4f, 1f);
	public (float R, float G, float B, float A) InactiveColor   = (0.6f, 0.6f, 0.6f, 1f);
	public (float R, float G, float B, float A) DisabledColor   = (0.4f, 0.4f, 0.4f, 1f);
	public (float R, float G, float B, float A) ContentColor    = (0.8f, 0.8f, 0.8f, 1f);
	public (float R, float G, float B, float A) HoverColor      = (1.0f, 1.0f, 0.0f, 1f);
	public (float R, float G, float B, float A) ChoiceColor     = (0.4f, 0.6f, 1.0f, 1f);
	public (float R, float G, float B, float A) ChoiceFadeColor = (0.27f, 0.27f, 0.27f, 1f);

	// ── 링크 색상 ──
	/// <summary>기본 링크 색상 (클릭 가능한 [url=...])</summary>
	public (float R, float G, float B, float A) LinkColor         = (0.4f, 0.7f, 1.0f, 1f);
	/// <summary>비활성 링크 색상 (grey-out)</summary>
	public (float R, float G, float B, float A) LinkDisabledColor = (0.5f, 0.5f, 0.5f, 1f);
	/// <summary>hover 중인 링크 색상</summary>
	public (float R, float G, float B, float A) LinkHoverColor    = (1.0f, 1.0f, 0.0f, 1f);

	// ── 텍스트 기본 색상 ──
	/// <summary>일반 텍스트 색상</summary>
	public (float R, float G, float B, float A) TextColor = (0.8f, 0.8f, 0.8f, 1f);

	/// <summary>RGBA → "#rrggbb" 헥스 변환</summary>
	public static string ToHex((float R, float G, float B, float A) c)
		=> $"#{(int)(c.R * 255):x2}{(int)(c.G * 255):x2}{(int)(c.B * 255):x2}";
}
