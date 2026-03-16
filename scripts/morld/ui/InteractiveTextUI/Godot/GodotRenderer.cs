using System;
using System.Collections.Generic;
using System.Text;

namespace Morld.TextUI;

/// <summary>
/// Godot RichTextLabel용 BBCode 렌더러.
/// AST + 상태 → BBCode 문자열 생성.
///
/// 모든 텍스트 스타일링은 여기서 테마 기반으로 적용.
/// Python/C#은 의미 마크업만 생성, 색상은 렌더러가 결정.
/// </summary>
public class GodotRenderer : ITextUIRenderer
{
	public event Action<string> WidgetClicked;

	public string RenderedText { get; private set; } = "";

	public void Render(List<AstNode> ast, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta = null)
	{
		var sb = new StringBuilder();
		RenderNodes(sb, ast, state, theme, hoveredMeta, 0);
		RenderedText = sb.ToString();
	}

	public void Clear()
	{
		RenderedText = "";
	}

	/// <summary>외부에서 MetaClicked 이벤트를 전달할 때 호출</summary>
	public void OnMetaClicked(string meta)
	{
		WidgetClicked?.Invoke(meta);
	}

	// ── 재귀 렌더링 ──

	private void RenderNodes(StringBuilder sb, List<AstNode> nodes,
		WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta, int depth)
	{
		foreach (var n in nodes)
		{
			switch (n.Type)
			{
				case NodeType.Text:
					sb.Append(n.RawText);
					break;
				case NodeType.Link:
					RenderLink(sb, n, state, theme, hoveredMeta, depth);
					break;
				case NodeType.Style:
					RenderStyle(sb, n, state, theme, hoveredMeta, depth);
					break;
				case NodeType.Todo:
					sb.Append(RenderTodo(n, state, theme, hoveredMeta));
					break;
				case NodeType.Button:
					sb.Append(RenderButton(n, state, theme, hoveredMeta));
					break;
				case NodeType.Toggle:
					RenderToggle(sb, n, state, theme, hoveredMeta, depth);
					break;
				case NodeType.Radio:
					sb.Append(RenderRadio(n, state, theme, hoveredMeta));
					break;
				case NodeType.Choice:
					RenderChoice(sb, n, state, theme, hoveredMeta, depth);
					break;
			}
		}
	}

	// ── Link 렌더링 ──

	private void RenderLink(StringBuilder sb, AstNode n,
		WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta, int depth)
	{
		bool hovered = IsHovered(hoveredMeta, n.Meta);
		string color = TextUIThemeBase.ToHex(
			hovered ? theme.LinkHoverColor : theme.LinkColor);

		sb.Append($"[url={n.Meta}][color={color}]");

		if (n.Children.Count > 0)
			RenderNodes(sb, n.Children, state, theme, hoveredMeta, depth);
		else
			sb.Append(n.Label);

		sb.Append("[/color][/url]");
	}

	// ── Style 렌더링 ──

	private void RenderStyle(StringBuilder sb, AstNode n,
		WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta, int depth)
	{
		// StyleTag: "b", "i", "s", "color=#ff0000", "font_size=20", etc.
		sb.Append($"[{n.StyleTag}]");

		if (n.Children.Count > 0)
			RenderNodes(sb, n.Children, state, theme, hoveredMeta, depth);

		// 닫기 태그: "color=#ff0000" → "color", "b" → "b"
		string closeTag = n.StyleTag;
		int eqIdx = closeTag.IndexOf('=');
		if (eqIdx >= 0) closeTag = closeTag[..eqIdx];
		sb.Append($"[/{closeTag}]");
	}

	// ── 위젯 렌더링 ──

	private string RenderTodo(AstNode n, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
	{
		bool on = state.GetTodo(n.Key);
		string icon = on ? theme.TodoCheckedIcon : theme.TodoUncheckedIcon;
		string color = GetWidgetColor(n.Disabled, on, theme, hoveredMeta, $"todo:{n.Key}");
		string label = on ? $"[s]{n.Label}[/s]" : n.Label;
		return n.Disabled
			? $"[color={color}]{icon} {label}[/color]"
			: $"[url=todo:{n.Key}][color={color}]{icon} {label}[/color][/url]";
	}

	private string RenderButton(AstNode n, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
	{
		bool on = state.GetButton(n.Key);
		string icon = on ? theme.ButtonOnIcon : theme.ButtonOffIcon;
		string color = GetWidgetColor(n.Disabled, on, theme, hoveredMeta, $"button:{n.Key}");
		string text = on
			? (!string.IsNullOrEmpty(n.OnText) ? n.OnText : n.Label)
			: (!string.IsNullOrEmpty(n.OffText) ? n.OffText : n.Label);
		return n.Disabled
			? $"[color={color}]{icon} {text}[/color]"
			: $"[url=button:{n.Key}][color={color}]{icon} {text}[/color][/url]";
	}

	private void RenderToggle(StringBuilder sb, AstNode n, WidgetStateStore state,
		TextUIThemeBase theme, string hoveredMeta, int depth)
	{
		bool open = state.GetToggle(n.Key);
		string arrow = open ? theme.ToggleOpenIcon : theme.ToggleClosedIcon;
		string meta = $"toggle:{n.Key}";
		string hColor = IsHovered(hoveredMeta, meta)
			? TextUIThemeBase.ToHex(theme.HoverColor)
			: TextUIThemeBase.ToHex(open ? theme.ActiveColor : theme.InactiveColor);

		sb.Append($"[url={meta}][color={hColor}]{arrow}{n.Label}[/color][/url]");

		if (open && n.Children.Count > 0)
		{
			sb.Append("\n[indent]");
			RenderNodes(sb, n.Children, state, theme, hoveredMeta, depth + 1);
			sb.Append("[/indent]");
		}
	}

	private string RenderRadio(AstNode n, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
	{
		string sel = state.GetRadio(n.Key);
		bool on = sel == n.Value;
		string icon = on ? theme.RadioSelectedIcon : theme.RadioUnselectedIcon;
		string meta = $"radio:{n.Key}:{n.Value}";
		string color = GetWidgetColor(n.Disabled, on, theme, hoveredMeta, meta);
		return n.Disabled
			? $"[color={color}]{icon} {n.Label}[/color]"
			: $"[url={meta}][color={color}]{icon} {n.Label}[/color][/url]";
	}

	private void RenderChoice(StringBuilder sb, AstNode n, WidgetStateStore state,
		TextUIThemeBase theme, string hoveredMeta, int depth)
	{
		string choiceVal = state.GetChoice(n.Key);
		bool chosen = !string.IsNullOrEmpty(choiceVal);

		foreach (var opt in n.Children)
		{
			if (opt.Type != NodeType.Option) continue;

			if (!chosen)
			{
				string meta = $"choice:{n.Key}:{opt.Value}";
				if (opt.Disabled)
				{
					string dColor = TextUIThemeBase.ToHex(theme.DisabledColor);
					sb.Append($"[color={dColor}]{theme.ChoiceIcon} {opt.Label}[/color]\n");
				}
				else
				{
					string cColor = IsHovered(hoveredMeta, meta)
						? TextUIThemeBase.ToHex(theme.HoverColor)
						: TextUIThemeBase.ToHex(theme.ChoiceColor);
					sb.Append($"[url={meta}][color={cColor}]{theme.ChoiceIcon} {opt.Label}[/color][/url]\n");
				}
			}
			else
			{
				bool isThis = opt.Value == choiceVal;
				switch (n.Mode)
				{
					case "hide":
						if (isThis)
						{
							string aColor = TextUIThemeBase.ToHex(theme.ActiveColor);
							sb.Append($"[color={aColor}]{theme.ChoiceSelectedIcon} {opt.Label}[/color]\n");
						}
						break;
					case "fade":
						if (isThis)
						{
							string aColor = TextUIThemeBase.ToHex(theme.ActiveColor);
							sb.Append($"[color={aColor}]{theme.ChoiceSelectedIcon} {opt.Label}[/color]\n");
						}
						else
						{
							string fColor = TextUIThemeBase.ToHex(theme.ChoiceFadeColor);
							sb.Append($"[color={fColor}][s]{theme.ChoiceIcon} {opt.Label}[/s][/color]\n");
						}
						break;
					case "keep":
						if (isThis)
						{
							string aColor = TextUIThemeBase.ToHex(theme.ActiveColor);
							sb.Append($"[color={aColor}][b]{theme.ChoiceIcon} {opt.Label}[/b][/color]\n");
						}
						else
						{
							string iColor = TextUIThemeBase.ToHex(theme.InactiveColor);
							sb.Append($"[color={iColor}]{theme.ChoiceIcon} {opt.Label}[/color]\n");
						}
						break;
				}
			}
		}
	}

	// ── 헬퍼 ──

	private static bool IsHovered(string hoveredMeta, string widgetMeta)
		=> !string.IsNullOrEmpty(hoveredMeta) && hoveredMeta == widgetMeta;

	private static string GetWidgetColor(bool disabled, bool active, TextUIThemeBase theme,
		string hoveredMeta, string widgetMeta)
	{
		if (disabled)
			return TextUIThemeBase.ToHex(theme.DisabledColor);
		if (IsHovered(hoveredMeta, widgetMeta))
			return TextUIThemeBase.ToHex(theme.HoverColor);
		return TextUIThemeBase.ToHex(active ? theme.ActiveColor : theme.InactiveColor);
	}
}
