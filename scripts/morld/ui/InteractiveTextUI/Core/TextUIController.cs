using System;
using System.Collections.Generic;

namespace Morld.TextUI;

/// <summary>
/// 파싱, 상태 관리, 이벤트 라우팅을 담당하는 플랫폼 무관 컨트롤러.
/// Godot/WinForms 호스트 모두 이것을 내부에 두고 위임한다.
/// </summary>
public class TextUIController
{
	public WidgetStateStore State { get; } = new();
	public TextUIThemeBase Theme { get; set; } = new();

	private List<AstNode> _ast = new();
	private readonly ITextUIRenderer _renderer;
	private string _hoveredMeta;

	// ── 이벤트 ──
	public event Action<string, bool>   TodoChanged;
	public event Action<string, bool>   ButtonChanged;
	public event Action<string, bool>   ToggleChanged;
	public event Action<string, string> RadioChanged;
	public event Action<string, string> ChoiceSelected;

	public TextUIController(ITextUIRenderer renderer)
	{
		_renderer = renderer;
		_renderer.WidgetClicked += HandleWidgetClick;
	}

	/// <summary>마크업 설정 → 파싱 → 상태 초기화 → 렌더링</summary>
	public void SetMarkup(string markup)
	{
		_ast = TextUIParser.Parse(markup);
		State.InitFromAst(_ast);
		Render();
	}

	/// <summary>현재 hover 메타 설정 → 재렌더링</summary>
	public void SetHoveredMeta(string meta)
	{
		if (_hoveredMeta == meta) return;
		_hoveredMeta = meta;
		Render();
	}

	/// <summary>상태 변경 후 재렌더링 트리거</summary>
	public void Render()
	{
		_renderer.Render(_ast, State, Theme, _hoveredMeta);
	}

	/// <summary>렌더링 결과 BBCode 문자열 (Godot용)</summary>
	public string RenderedText => _renderer.RenderedText;

	/// <summary>AST 반환 (외부에서 직접 사용 시)</summary>
	public List<AstNode> Ast => _ast;

	/// <summary>모든 상태 초기화</summary>
	public void Clear()
	{
		_ast.Clear();
		State.Clear();
		_renderer.Clear();
	}

	// ── 위젯 클릭 핸들링 ──

	private void HandleWidgetClick(string widgetId)
	{
		if (string.IsNullOrEmpty(widgetId)) return;

		if (widgetId.StartsWith("todo:"))
		{
			string key = widgetId["todo:".Length..];
			State.ToggleTodo(key);
			TodoChanged?.Invoke(key, State.GetTodo(key));
			Render();
		}
		else if (widgetId.StartsWith("button:"))
		{
			string key = widgetId["button:".Length..];
			State.ToggleButton(key);
			ButtonChanged?.Invoke(key, State.GetButton(key));
			Render();
		}
		else if (widgetId.StartsWith("toggle:"))
		{
			string key = widgetId["toggle:".Length..];
			State.ToggleToggle(key);
			ToggleChanged?.Invoke(key, State.GetToggle(key));
			Render();
		}
		else if (widgetId.StartsWith("radio:"))
		{
			string rest = widgetId["radio:".Length..];
			int sep = rest.IndexOf(':');
			if (sep > 0)
			{
				string group = rest[..sep];
				string value = rest[(sep + 1)..];
				State.SetRadio(group, value);
				RadioChanged?.Invoke(group, value);
				Render();
			}
		}
		else if (widgetId.StartsWith("choice:"))
		{
			string rest = widgetId["choice:".Length..];
			int sep = rest.IndexOf(':');
			if (sep > 0)
			{
				string key = rest[..sep];
				string value = rest[(sep + 1)..];
				if (State.TrySetChoice(key, value))
				{
					ChoiceSelected?.Invoke(key, value);
					Render();
				}
			}
		}
	}
}
