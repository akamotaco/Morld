using System;
using System.Collections.Generic;

namespace Morld.TextUI;

/// <summary>
/// 마크업 → AST 변환 파서 (재귀 하강).
///
/// 위젯 태그:
///   [todo key=X]...[/todo]
///   [button key=X on=... off=...]...[/button]
///   [toggle key=X]헤더[content]...[/toggle]
///   [radio group=G value=V]...[/radio]
///   [choice key=X mode=hide|fade|keep] [option value=V]...[/option] [/choice]
///
/// 구조화 태그 (Link, Style):
///   [url=meta]...[/url]           → Link 노드 (렌더러가 테마 기반 색상 적용)
///   [b]...[/b]                    → Style 노드 (bold)
///   [i]...[/i]                    → Style 노드 (italic)
///   [s]...[/s]                    → Style 노드 (strikethrough)
///   [color=X]...[/color]          → Style 노드 (color)
///   [font_size=X]...[/font_size]  → Style 노드 (font_size)
///   [center]...[/center]          → Style 노드 (center)
///   [indent]...[/indent]          → Style 노드 (indent)
///
/// 알 수 없는 [태그]는 Text 노드로 통과.
/// </summary>
public static class TextUIParser
{
	// ─── 위젯 태그 ───
	private static readonly (string name, NodeType type)[] WidgetTags =
	{
		("toggle", NodeType.Toggle),
		("button", NodeType.Button),
		("todo",   NodeType.Todo),
		("radio",  NodeType.Radio),
		("choice", NodeType.Choice),
		("option", NodeType.Option),
	};

	// ─── BBCode 스타일 태그 (재귀 파싱 — 내부에 위젯/링크 포함 가능) ───
	private static readonly string[] StyleTags =
		{ "b", "i", "s", "u", "color", "font_size", "center", "indent" };

	/// <summary>
	/// 마크업 전체를 파싱하여 AST 반환
	/// </summary>
	public static List<AstNode> Parse(string markup)
	{
		if (string.IsNullOrEmpty(markup))
			return new List<AstNode>();
		return Parse(markup, 0, out _, null);
	}

	// ─── 재귀 파서 본체 ───

	private static List<AstNode> Parse(string markup, int startPos, out int endPos, string stopTag)
	{
		var nodes = new List<AstNode>();
		int pos = startPos;
		int textStart = pos;

		while (pos < markup.Length)
		{
			int bk = markup.IndexOf('[', pos);
			if (bk < 0)
			{
				FlushText(nodes, markup, textStart, markup.Length);
				pos = markup.Length;
				break;
			}

			// ── stopTag 닫는 태그 도달 → 반환 ──
			if (stopTag != null && MatchClose(markup, bk, stopTag))
			{
				FlushText(nodes, markup, textStart, bk);
				endPos = bk + 2 + stopTag.Length + 1; // [/ + tag + ]
				return nodes;
			}

			// 다른 닫는 태그 → 텍스트로 취급
			if (bk + 1 < markup.Length && markup[bk + 1] == '/')
			{ pos = bk + 1; continue; }

			// ── [url=...] 링크 ──
			if (TryParseLink(markup, bk, nodes, ref pos, ref textStart, stopTag))
				continue;

			// ── BBCode 스타일 태그 ──
			if (TryParseStyle(markup, bk, nodes, ref pos, ref textStart, stopTag))
				continue;

			// ── 위젯 태그 매칭 시도 ──
			var (tagName, nodeType) = TryMatchWidgetTag(markup, bk);

			if (nodeType == null)
			{ pos = bk + 1; continue; }

			int tagBodyEnd = markup.IndexOf(']', bk);
			if (tagBodyEnd < 0) { pos = bk + 1; continue; }

			string attrStr = markup[(bk + 1 + tagName.Length)..tagBodyEnd].Trim();
			var attrs = ParseAttrs(attrStr);
			int innerStart = tagBodyEnd + 1;

			// ── Toggle → 재귀 파싱 ──
			if (nodeType == NodeType.Toggle)
			{
				int contentPos = FindContentMarker(markup, innerStart, tagName);

				string label;
				List<AstNode> children;
				int afterClose;

				if (contentPos >= 0)
				{
					label = markup[innerStart..contentPos];
					int childStart = contentPos + "[content]".Length;
					children = Parse(markup, childStart, out afterClose, tagName);
				}
				else
				{
					int closePos = FindMatchingClose(markup, innerStart, tagName);
					if (closePos < 0) { pos = innerStart; continue; }
					label = markup[innerStart..closePos];
					children = new List<AstNode>();
					afterClose = closePos + $"[/{tagName}]".Length;
				}

				FlushText(nodes, markup, textStart, bk);
				nodes.Add(new AstNode
				{
					Type = NodeType.Toggle,
					Key = attrs.GetValueOrDefault("key", ""),
					Label = label,
					DefaultState = attrs.ContainsKey("open"),
					Children = children,
				});

				pos = afterClose;
				textStart = pos;
			}
			// ── Choice → option 자식 재귀 파싱 ──
			else if (nodeType == NodeType.Choice)
			{
				var children = Parse(markup, innerStart, out int afterClose, tagName);

				FlushText(nodes, markup, textStart, bk);
				nodes.Add(new AstNode
				{
					Type = NodeType.Choice,
					Key = attrs.GetValueOrDefault("key", ""),
					Mode = attrs.GetValueOrDefault("mode", "hide"),
					Children = children,
				});

				pos = afterClose;
				textStart = pos;
			}
			// ── Todo, Button, Radio, Option → 단순 파싱 ──
			else
			{
				string closeTag = $"[/{tagName}]";
				int closeIdx = IndexOfCI(markup, closeTag, innerStart);
				if (closeIdx < 0) { pos = innerStart; continue; }

				FlushText(nodes, markup, textStart, bk);

				string key = attrs.GetValueOrDefault("key", "");
				string group = attrs.GetValueOrDefault("group", "");

				nodes.Add(new AstNode
				{
					Type = nodeType.Value,
					Key = nodeType == NodeType.Radio ? group : key,
					Value = attrs.GetValueOrDefault("value", ""),
					Label = markup[innerStart..closeIdx],
					OnText = attrs.GetValueOrDefault("on", ""),
					OffText = attrs.GetValueOrDefault("off", ""),
					DefaultState = nodeType.Value switch
					{
						NodeType.Todo   => attrs.ContainsKey("checked"),
						NodeType.Button => attrs.ContainsKey("checked"),
						NodeType.Radio  => attrs.ContainsKey("selected"),
						NodeType.Option => false,
						_ => false
					},
					Disabled = attrs.ContainsKey("disabled"),
				});

				pos = closeIdx + closeTag.Length;
				textStart = pos;
			}
		}

		endPos = pos;
		return nodes;
	}

	// ─── Link 파싱: [url=meta]...[/url] ───

	private static bool TryParseLink(string markup, int bk, List<AstNode> nodes,
		ref int pos, ref int textStart, string stopTag)
	{
		const string urlPrefix = "[url=";
		if (!MatchAt(markup, bk, urlPrefix))
			return false;

		int metaStart = bk + urlPrefix.Length;
		int metaEnd = markup.IndexOf(']', metaStart);
		if (metaEnd < 0) return false;

		string meta = markup[metaStart..metaEnd];
		int innerStart = metaEnd + 1;

		// [/url] 찾기
		const string urlClose = "[/url]";
		int closeIdx = markup.IndexOf(urlClose, innerStart, StringComparison.Ordinal);
		if (closeIdx < 0) return false;

		FlushText(nodes, markup, textStart, bk);

		// 링크 내부를 재귀 파싱 (내부에 [color=...] 등 스타일 가능)
		var children = Parse(markup, innerStart, out _, "url");
		// Parse가 [/url]을 stopTag로 소비했으면 그 위치 사용
		// 아니면 수동으로 closeIdx 사용
		int afterClose = closeIdx + urlClose.Length;

		// 자식이 단순 텍스트 1개면 Label로 축약
		string label = "";
		if (children.Count == 1 && children[0].Type == NodeType.Text)
		{
			label = children[0].RawText;
			children = new List<AstNode>();
		}

		nodes.Add(new AstNode
		{
			Type = NodeType.Link,
			Meta = meta,
			Label = label,
			Children = children,
		});

		pos = afterClose;
		textStart = pos;
		return true;
	}

	// ─── Style 파싱: [b]...[/b], [color=X]...[/color] 등 ───

	private static bool TryParseStyle(string markup, int bk, List<AstNode> nodes,
		ref int pos, ref int textStart, string stopTag)
	{
		foreach (var tag in StyleTags)
		{
			// [tag] 또는 [tag=value] 매칭
			if (!MatchAt(markup, bk, $"[{tag}]") && !MatchAt(markup, bk, $"[{tag}="))
				continue;

			int tagBodyEnd = markup.IndexOf(']', bk);
			if (tagBodyEnd < 0) continue;

			// 전체 열기 태그 문자열 (예: "color=#ff0000", "b", "font_size=20")
			string fullTag = markup[(bk + 1)..tagBodyEnd];
			int innerStart = tagBodyEnd + 1;

			// 닫기 태그: [/tag]
			string closeTag = $"[/{tag}]";

			FlushText(nodes, markup, textStart, bk);

			// 내부를 재귀 파싱 (스타일 안에 링크, 위젯 등 포함 가능)
			var children = Parse(markup, innerStart, out int afterClose, tag);

			nodes.Add(new AstNode
			{
				Type = NodeType.Style,
				StyleTag = fullTag,
				Children = children,
			});

			pos = afterClose;
			textStart = pos;
			return true;
		}

		return false;
	}

	// ─── 파싱 헬퍼 ───

	private static int FindContentMarker(string markup, int from, string tagName)
	{
		int depth = 0;
		int pos = from;
		string openPfx = $"[{tagName}";
		string closePfx = $"[/{tagName}]";
		const string marker = "[content]";

		while (pos < markup.Length)
		{
			int nextBk = markup.IndexOf('[', pos);
			if (nextBk < 0) return -1;

			if (depth == 0 && MatchAt(markup, nextBk, marker))
				return nextBk;

			if (MatchAt(markup, nextBk, closePfx))
			{
				if (depth > 0) depth--;
				else return -1;
				pos = nextBk + closePfx.Length;
				continue;
			}

			if (MatchOpenTagAt(markup, nextBk, tagName))
			{
				depth++;
				pos = nextBk + openPfx.Length;
				continue;
			}

			pos = nextBk + 1;
		}
		return -1;
	}

	private static int FindMatchingClose(string markup, int from, string tagName)
	{
		int depth = 1;
		int pos = from;
		string closePfx = $"[/{tagName}]";

		while (pos < markup.Length && depth > 0)
		{
			int nextBk = markup.IndexOf('[', pos);
			if (nextBk < 0) return -1;

			if (MatchAt(markup, nextBk, closePfx))
			{
				depth--;
				if (depth == 0) return nextBk;
				pos = nextBk + closePfx.Length;
				continue;
			}

			if (MatchOpenTagAt(markup, nextBk, tagName))
			{
				depth++;
				pos = nextBk + 1 + tagName.Length;
				continue;
			}

			pos = nextBk + 1;
		}
		return -1;
	}

	private static bool MatchAt(string s, int pos, string sub)
	{
		if (pos + sub.Length > s.Length) return false;
		for (int i = 0; i < sub.Length; i++)
			if (char.ToLowerInvariant(s[pos + i]) != char.ToLowerInvariant(sub[i])) return false;
		return true;
	}

	private static bool MatchOpenTagAt(string markup, int bracketPos, string tagName)
	{
		if (bracketPos + 1 + tagName.Length > markup.Length) return false;
		if (markup[bracketPos] != '[') return false;
		if (bracketPos + 1 < markup.Length && markup[bracketPos + 1] == '/') return false;

		for (int i = 0; i < tagName.Length; i++)
			if (char.ToLowerInvariant(markup[bracketPos + 1 + i]) != tagName[i]) return false;

		int after = bracketPos + 1 + tagName.Length;
		return after >= markup.Length || markup[after] == ' ' || markup[after] == ']';
	}

	private static bool MatchClose(string markup, int pos, string tagName)
	{
		string pat = $"[/{tagName}]";
		return MatchAt(markup, pos, pat);
	}

	private static (string name, NodeType? type) TryMatchWidgetTag(string markup, int bk)
	{
		foreach (var (name, t) in WidgetTags)
		{
			if (MatchOpenTagAt(markup, bk, name))
				return (name, t);
		}
		return ("", null);
	}

	private static void FlushText(List<AstNode> nodes, string markup, int from, int to)
	{
		if (from >= to) return;
		nodes.Add(new AstNode { Type = NodeType.Text, RawText = markup[from..to] });
	}

	private static int IndexOfCI(string s, string sub, int from)
		=> s.IndexOf(sub, from, StringComparison.OrdinalIgnoreCase);

	private static Dictionary<string, string> ParseAttrs(string input)
	{
		var d = new Dictionary<string, string>();
		int i = 0;
		while (i < input.Length)
		{
			while (i < input.Length && input[i] == ' ') i++;
			if (i >= input.Length) break;
			int ks = i;
			while (i < input.Length && input[i] != '=' && input[i] != ' ') i++;
			string k = input[ks..i].Trim();
			if (i < input.Length && input[i] == '=')
			{
				i++;
				int vs = i;
				while (i < input.Length && input[i] != ' ') i++;
				d[k] = input[vs..i].Trim();
			}
			else if (!string.IsNullOrEmpty(k))
				d[k] = "";
		}
		return d;
	}
}
