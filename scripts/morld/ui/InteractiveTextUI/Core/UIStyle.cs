namespace Morld.TextUI;

/// <summary>
/// UI 스타일 상수 — C# 코드에서 사용.
/// Python의 ui_style.py와 동일한 역할.
/// 콘텐츠(대사/묘사)는 자유롭게 [color=...] 사용 가능.
/// UI 요소만 이 상수를 참조.
/// </summary>
public static class UIStyle
{
	// ── 색상 값 ──
	public const string Muted     = "gray";
	public const string Highlight = "yellow";
	public const string Info      = "cyan";
	public const string Danger    = "red";
	public const string Success   = "lime";
	public const string Warning   = "orange";
	public const string Accent    = "white";

	// ── 상태 임계 색상 ──
	public const string StatNormal  = "white";
	public const string StatCaution = "yellow";
	public const string StatDanger  = "red";

	// ── 헬퍼 메서드 ──

	/// <summary>[color=X]text[/color]</summary>
	public static string C(string color, string text) => $"[color={color}]{text}[/color]";

	/// <summary>비활성/부차 정보</summary>
	public static string StyleMuted(string text) => $"[color={Muted}]{text}[/color]";

	/// <summary>강조/현재</summary>
	public static string StyleHighlight(string text) => $"[color={Highlight}]{text}[/color]";

	/// <summary>시스템 정보</summary>
	public static string StyleInfo(string text) => $"[color={Info}]{text}[/color]";

	/// <summary>위험</summary>
	public static string StyleDanger(string text) => $"[color={Danger}]{text}[/color]";

	/// <summary>긍정/존재</summary>
	public static string StyleSuccess(string text) => $"[color={Success}]{text}[/color]";

	/// <summary>주의</summary>
	public static string StyleWarning(string text) => $"[color={Warning}]{text}[/color]";

	/// <summary>섹션 헤더</summary>
	public static string StyleSection(string text) => $"[color={Muted}]── {text} ──[/color]";
}
