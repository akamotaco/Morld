using System;
using System.Collections.Generic;

namespace Morld.TextUI;

/// <summary>
/// 플랫폼 독립 렌더러 인터페이스.
/// AST + 상태를 받아 화면에 표시하고, 위젯 클릭 이벤트를 발생시킨다.
/// </summary>
public interface ITextUIRenderer
{
	/// <summary>AST를 현재 상태에 맞게 렌더링한다.</summary>
	void Render(List<AstNode> ast, WidgetStateStore state, TextUIThemeBase theme, string hoveredMeta = null, int darknessLevel = 0);

	/// <summary>표시 내용을 모두 지운다.</summary>
	void Clear();

	/// <summary>
	/// 위젯 클릭 시 발생. 값은 "todo:key", "toggle:key", "radio:group:value" 등.
	/// </summary>
	event Action<string> WidgetClicked;

	/// <summary>렌더링 결과 문자열 (Godot: BBCode, WinForms: N/A)</summary>
	string RenderedText { get; }
}
