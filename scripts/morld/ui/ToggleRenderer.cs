using System.Collections.Generic;
using System.Text;

namespace Morld;

/// <summary>
/// 토글 마크업 렌더러
/// [hidden=X]...[/hidden=X] 구문을 파싱하여 펼침/접힘 처리
/// </summary>
public static class ToggleRenderer
{
	private const string HiddenOpenPrefix = "[hidden=";
	private const string HiddenClosePrefix = "[/hidden=";
	private const char TagEnd = ']';
	private const string ToggleUrlPrefix = "[url=toggle:";
	private const string UrlPrefix = "[url=";
	private const string UrlClose = "[/url]";
	private const string CollapsedIcon = "▶";
	private const string ExpandedIcon = "▼";
	private const string HoverColor = "#ffff00"; // 노란색

	/// <summary>
	/// 토글 마크업 렌더링
	/// </summary>
	/// <param name="text">원본 BBCode 텍스트</param>
	/// <param name="expanded">펼쳐진 토글 ID 목록</param>
	/// <param name="hoveredMeta">현재 hover 중인 메타 (null = 없음)</param>
	/// <returns>렌더링된 BBCode 텍스트</returns>
	public static string Render(string text, HashSet<string> expanded, string? hoveredMeta = null)
	{
		if (string.IsNullOrEmpty(text))
			return "";

		var result = new StringBuilder();
		var hiddenStack = new Stack<string>();
		int i = 0;

		while (i < text.Length)
		{
			// [hidden=X] 시작 태그 찾기
			if (TryParseOpenTag(text, i, out var openId, out var openEnd))
			{
				if (!expanded.Contains(openId))
				{
					hiddenStack.Push(openId);
				}
				i = openEnd;
				continue;
			}

			// [/hidden=X] 닫는 태그 찾기
			if (TryParseCloseTag(text, i, out var closeId, out var closeEnd))
			{
				if (hiddenStack.Count > 0 && hiddenStack.Peek() == closeId)
				{
					hiddenStack.Pop();
				}
				i = closeEnd;
				continue;
			}

			// 현재 숨김 상태가 아니면 출력
			if (hiddenStack.Count == 0)
			{
				result.Append(text[i]);
			}
			i++;
		}

		// ▶/▼ 아이콘 교체
		var withIcons = ReplaceToggleIcons(result.ToString(), expanded);

		// hover 링크 색상 적용
		return ApplyHoverColor(withIcons, hoveredMeta);
	}

	/// <summary>
	/// [hidden=X] 열기 태그 파싱
	/// </summary>
	private static bool TryParseOpenTag(string text, int pos, out string id, out int endPos)
	{
		id = "";
		endPos = pos;

		if (pos + HiddenOpenPrefix.Length >= text.Length)
			return false;

		// [hidden= 로 시작하는지 확인
		if (!text.Substring(pos).StartsWith(HiddenOpenPrefix))
			return false;

		// ID 추출
		int idStart = pos + HiddenOpenPrefix.Length;
		int idEnd = text.IndexOf(TagEnd, idStart);
		if (idEnd < 0)
			return false;

		id = text.Substring(idStart, idEnd - idStart);
		endPos = idEnd + 1;
		return true;
	}

	/// <summary>
	/// [/hidden=X] 닫기 태그 파싱
	/// </summary>
	private static bool TryParseCloseTag(string text, int pos, out string id, out int endPos)
	{
		id = "";
		endPos = pos;

		if (pos + HiddenClosePrefix.Length >= text.Length)
			return false;

		// [/hidden= 로 시작하는지 확인
		if (!text.Substring(pos).StartsWith(HiddenClosePrefix))
			return false;

		// ID 추출
		int idStart = pos + HiddenClosePrefix.Length;
		int idEnd = text.IndexOf(TagEnd, idStart);
		if (idEnd < 0)
			return false;

		id = text.Substring(idStart, idEnd - idStart);
		endPos = idEnd + 1;
		return true;
	}

	/// <summary>
	/// 토글 아이콘 교체 (▶ → ▼ for expanded)
	/// </summary>
	private static string ReplaceToggleIcons(string text, HashSet<string> expanded)
	{
		var result = new StringBuilder();
		int i = 0;

		while (i < text.Length)
		{
			// [url=toggle:X] 패턴 찾기
			if (text.Substring(i).StartsWith(ToggleUrlPrefix))
			{
				int idStart = i + ToggleUrlPrefix.Length;
				int idEnd = text.IndexOf(TagEnd, idStart);

				if (idEnd > idStart)
				{
					string toggleId = text.Substring(idStart, idEnd - idStart);
					bool isExpanded = expanded.Contains(toggleId);

					// 태그 전체 복사
					result.Append(text.Substring(i, idEnd + 1 - i));
					i = idEnd + 1;

					// ▶ 또는 ▼ 아이콘 교체
					if (i < text.Length && text[i] == CollapsedIcon[0])
					{
						result.Append(isExpanded ? ExpandedIcon : CollapsedIcon);
						i += CollapsedIcon.Length;
					}
					else if (i < text.Length && text[i] == ExpandedIcon[0])
					{
						result.Append(isExpanded ? ExpandedIcon : CollapsedIcon);
						i += ExpandedIcon.Length;
					}
					continue;
				}
			}

			result.Append(text[i]);
			i++;
		}

		return result.ToString();
	}

	/// <summary>
	/// hover 중인 링크에 색상 적용
	/// </summary>
	private static string ApplyHoverColor(string text, string? hoveredMeta)
	{
		if (string.IsNullOrEmpty(hoveredMeta))
			return text;

		var result = new StringBuilder();
		int i = 0;

		while (i < text.Length)
		{
			// [url=X] 패턴 찾기
			if (i + UrlPrefix.Length < text.Length && text.Substring(i).StartsWith(UrlPrefix))
			{
				int metaStart = i + UrlPrefix.Length;
				int metaEnd = text.IndexOf(TagEnd, metaStart);

				if (metaEnd > metaStart)
				{
					string meta = text.Substring(metaStart, metaEnd - metaStart);

					// hover 중인 링크인지 확인
					if (meta == hoveredMeta)
					{
						// [url=X] 복사
						result.Append(text.Substring(i, metaEnd + 1 - i));
						i = metaEnd + 1;

						// [/url] 찾기
						int closePos = text.IndexOf(UrlClose, i);
						if (closePos > i)
						{
							// 링크 텍스트를 색상 태그로 감싸기
							string linkText = text.Substring(i, closePos - i);
							result.Append($"[color={HoverColor}]{linkText}[/color]");
							result.Append(UrlClose);
							i = closePos + UrlClose.Length;
							continue;
						}
					}
				}
			}

			result.Append(text[i]);
			i++;
		}

		return result.ToString();
	}
}
