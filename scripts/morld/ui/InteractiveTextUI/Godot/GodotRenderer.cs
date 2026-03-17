using System;
using System.Collections.Generic;
using System.Text;

namespace Morld.TextUI;

/// <summary>
/// Godot RichTextLabel용 BBCode 렌더러.
/// AST + 상태 → BBCode 문자열 + 즉시 구간 맵 생성.
///
/// 모든 텍스트 스타일링은 여기서 테마 기반으로 적용.
/// 즉시 구간 맵은 타이핑 연출 시스템(text_ui_system.cs)이 소비.
/// </summary>
public class GodotRenderer : ITextUIRenderer
{
	public event Action<string> WidgetClicked;

	public string RenderedText { get; private set; } = "";

	/// <summary>
	/// 즉시 표시 구간 맵 (visible char 기준 start, length).
	/// [!]...[/!] 노드와 [url=...] Link 노드가 등록됨.
	/// 타이핑 연출 시 이 구간은 한 번에 표시됨.
	/// </summary>
	public List<(int start, int length)> InstantSegments { get; private set; } = new();

	// ── 렌더링 컨텍스트 (AST 순회 중 상태 추적) ──
	private class RenderCtx
	{
		public readonly StringBuilder Sb = new();
		public readonly WidgetStateStore State;
		public readonly TextUIThemeBase Theme;
		public readonly string HoveredMeta;
		public readonly List<(int start, int length)> Segments = new();

		/// <summary>현재까지의 visible char 수 (BBCode 태그 제외)</summary>
		public int VisibleCharCount;

		/// <summary>Instant 노드 진입 시의 visible char 위치 (null = 밖)</summary>
		public int? InstantStart;

		/// <summary>Instant 중첩 깊이 (중첩 [!] 내부에서 외부만 기록)</summary>
		public int InstantDepth;

		public RenderCtx(WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
		{
			State = state;
			Theme = theme;
			HoveredMeta = hoveredMeta;
		}
	}

	public void Render(List<AstNode> ast, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta = null)
	{
		var ctx = new RenderCtx(state, theme, hoveredMeta);
		RenderNodes(ctx, ast, 0);
		RenderedText = ctx.Sb.ToString();
		InstantSegments = ctx.Segments;
	}

	public void Clear()
	{
		RenderedText = "";
		InstantSegments = new();
	}

	/// <summary>외부에서 MetaClicked 이벤트를 전달할 때 호출</summary>
	public void OnMetaClicked(string meta)
	{
		WidgetClicked?.Invoke(meta);
	}

	// ── BBCode 출력 + visible char 카운팅 ──

	/// <summary>BBCode 태그 출력 (visible char 카운트 안 함)</summary>
	private static void AppendTag(RenderCtx ctx, string tag)
	{
		ctx.Sb.Append(tag);
	}

	/// <summary>보이는 텍스트 출력 (visible char 카운트 증가)</summary>
	private static void AppendVisible(RenderCtx ctx, string text)
	{
		ctx.Sb.Append(text);
		// BBCode가 아닌 문자만 카운트
		bool inTag = false;
		foreach (char c in text)
		{
			if (c == '[') { inTag = true; continue; }
			if (c == ']') { inTag = false; continue; }
			if (!inTag) ctx.VisibleCharCount++;
		}
	}

	/// <summary>raw 텍스트 출력 (BBCode 포함 가능 — visible char만 카운트)</summary>
	private static void AppendRaw(RenderCtx ctx, string rawText)
	{
		ctx.Sb.Append(rawText);
		bool inTag = false;
		foreach (char c in rawText)
		{
			if (c == '[') { inTag = true; continue; }
			if (c == ']') { inTag = false; continue; }
			if (!inTag) ctx.VisibleCharCount++;
		}
	}

	// ── 재귀 렌더링 ──

	private void RenderNodes(RenderCtx ctx, List<AstNode> nodes, int depth)
	{
		foreach (var n in nodes)
		{
			switch (n.Type)
			{
				case NodeType.Text:
					AppendRaw(ctx, n.RawText);
					break;
				case NodeType.Instant:
					RenderInstant(ctx, n, depth);
					break;
				case NodeType.Link:
					RenderLink(ctx, n, depth);
					break;
				case NodeType.Style:
					RenderStyle(ctx, n, depth);
					break;
				case NodeType.Todo:
					AppendVisible(ctx, RenderTodo(n, ctx.State, ctx.Theme, ctx.HoveredMeta));
					break;
				case NodeType.Button:
					AppendVisible(ctx, RenderButton(n, ctx.State, ctx.Theme, ctx.HoveredMeta));
					break;
				case NodeType.Toggle:
					RenderToggle(ctx, n, depth);
					break;
				case NodeType.Radio:
					AppendVisible(ctx, RenderRadio(n, ctx.State, ctx.Theme, ctx.HoveredMeta));
					break;
				case NodeType.Choice:
					RenderChoice(ctx, n, depth);
					break;
			}
		}
	}

	// ── Instant 렌더링 ──

	private void RenderInstant(RenderCtx ctx, AstNode n, int depth)
	{
		// 중첩 [!] 처리: 외부 [!]만 구간 기록
		bool isOutermost = ctx.InstantDepth == 0;
		if (isOutermost)
			ctx.InstantStart = ctx.VisibleCharCount;

		ctx.InstantDepth++;

		// children 렌더링 ([!] 태그 자체는 출력하지 않음)
		RenderNodes(ctx, n.Children, depth);

		ctx.InstantDepth--;

		if (isOutermost && ctx.InstantStart.HasValue)
		{
			int length = ctx.VisibleCharCount - ctx.InstantStart.Value;
			if (length > 0)
				ctx.Segments.Add((ctx.InstantStart.Value, length));
			ctx.InstantStart = null;
		}
	}

	// ── Link 렌더링 (즉시 구간으로도 등록) ──

	private void RenderLink(RenderCtx ctx, AstNode n, int depth)
	{
		bool hovered = IsHovered(ctx.HoveredMeta, n.Meta);
		string color = TextUIThemeBase.ToHex(
			hovered ? ctx.Theme.LinkHoverColor : ctx.Theme.LinkColor);

		// Link는 즉시 구간으로 등록 (Instant 내부가 아닐 때만 — 중복 방지)
		bool registerAsInstant = ctx.InstantDepth == 0;
		int linkStart = ctx.VisibleCharCount;

		AppendTag(ctx, $"[url={n.Meta}][color={color}]");

		if (n.Children.Count > 0)
			RenderNodes(ctx, n.Children, depth);
		else
			AppendVisible(ctx, n.Label);

		AppendTag(ctx, "[/color][/url]");

		if (registerAsInstant)
		{
			int length = ctx.VisibleCharCount - linkStart;
			if (length > 0)
				ctx.Segments.Add((linkStart, length));
		}
	}

	// ── Style 렌더링 ──

	private void RenderStyle(RenderCtx ctx, AstNode n, int depth)
	{
		AppendTag(ctx, $"[{n.StyleTag}]");

		if (n.Children.Count > 0)
			RenderNodes(ctx, n.Children, depth);

		string closeTag = n.StyleTag;
		int eqIdx = closeTag.IndexOf('=');
		if (eqIdx >= 0) closeTag = closeTag[..eqIdx];
		AppendTag(ctx, $"[/{closeTag}]");
	}

	// ── 위젯 렌더링 ──

	private static string RenderTodo(AstNode n, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
	{
		bool on = state.GetTodo(n.Key);
		string icon = on ? theme.TodoCheckedIcon : theme.TodoUncheckedIcon;
		string color = GetWidgetColor(n.Disabled, on, theme, hoveredMeta, $"todo:{n.Key}");
		string label = on ? $"[s]{n.Label}[/s]" : n.Label;
		return n.Disabled
			? $"[color={color}]{icon} {label}[/color]"
			: $"[url=todo:{n.Key}][color={color}]{icon} {label}[/color][/url]";
	}

	private static string RenderButton(AstNode n, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
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

	private void RenderToggle(RenderCtx ctx, AstNode n, int depth)
	{
		bool open = ctx.State.GetToggle(n.Key);
		string arrow = open ? ctx.Theme.ToggleOpenIcon : ctx.Theme.ToggleClosedIcon;
		string meta = $"toggle:{n.Key}";
		string hColor = IsHovered(ctx.HoveredMeta, meta)
			? TextUIThemeBase.ToHex(ctx.Theme.HoverColor)
			: TextUIThemeBase.ToHex(open ? ctx.Theme.ActiveColor : ctx.Theme.InactiveColor);

		AppendVisible(ctx, $"[url={meta}][color={hColor}]{arrow}{n.Label}[/color][/url]");

		if (open && n.Children.Count > 0)
		{
			AppendTag(ctx, "\n[indent]");
			RenderNodes(ctx, n.Children, depth + 1);
			AppendTag(ctx, "[/indent]");
		}
	}

	private static string RenderRadio(AstNode n, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta)
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

	private void RenderChoice(RenderCtx ctx, AstNode n, int depth)
	{
		string choiceVal = ctx.State.GetChoice(n.Key);
		bool chosen = !string.IsNullOrEmpty(choiceVal);

		foreach (var opt in n.Children)
		{
			if (opt.Type != NodeType.Option) continue;

			if (!chosen)
			{
				string meta = $"choice:{n.Key}:{opt.Value}";
				if (opt.Disabled)
				{
					string dColor = TextUIThemeBase.ToHex(ctx.Theme.DisabledColor);
					AppendVisible(ctx, $"[color={dColor}]{ctx.Theme.ChoiceIcon} {opt.Label}[/color]\n");
				}
				else
				{
					string cColor = IsHovered(ctx.HoveredMeta, meta)
						? TextUIThemeBase.ToHex(ctx.Theme.HoverColor)
						: TextUIThemeBase.ToHex(ctx.Theme.ChoiceColor);
					AppendVisible(ctx, $"[url={meta}][color={cColor}]{ctx.Theme.ChoiceIcon} {opt.Label}[/color][/url]\n");
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
							string aColor = TextUIThemeBase.ToHex(ctx.Theme.ActiveColor);
							AppendVisible(ctx, $"[color={aColor}]{ctx.Theme.ChoiceSelectedIcon} {opt.Label}[/color]\n");
						}
						break;
					case "fade":
						if (isThis)
						{
							string aColor = TextUIThemeBase.ToHex(ctx.Theme.ActiveColor);
							AppendVisible(ctx, $"[color={aColor}]{ctx.Theme.ChoiceSelectedIcon} {opt.Label}[/color]\n");
						}
						else
						{
							string fColor = TextUIThemeBase.ToHex(ctx.Theme.ChoiceFadeColor);
							AppendVisible(ctx, $"[color={fColor}][s]{ctx.Theme.ChoiceIcon} {opt.Label}[/s][/color]\n");
						}
						break;
					case "keep":
						if (isThis)
						{
							string aColor = TextUIThemeBase.ToHex(ctx.Theme.ActiveColor);
							AppendVisible(ctx, $"[color={aColor}][b]{ctx.Theme.ChoiceIcon} {opt.Label}[/b][/color]\n");
						}
						else
						{
							string iColor = TextUIThemeBase.ToHex(ctx.Theme.InactiveColor);
							AppendVisible(ctx, $"[color={iColor}]{ctx.Theme.ChoiceIcon} {opt.Label}[/color]\n");
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
