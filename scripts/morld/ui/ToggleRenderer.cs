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
	private const string CollapsedIcon = "▶";
	private const string ExpandedIcon = "▼";

	/// <summary>
	/// 토글 마크업 렌더링
	/// </summary>
	/// <param name="text">원본 BBCode 텍스트</param>
	/// <param name="expanded">펼쳐진 토글 ID 목록</param>
	/// <returns>렌더링된 BBCode 텍스트</returns>
	public static string Render(string text, HashSet<string> expanded)
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
		return ReplaceToggleIcons(result.ToString(), expanded);
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
}
