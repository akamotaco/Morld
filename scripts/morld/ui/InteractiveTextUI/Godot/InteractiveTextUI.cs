using System;
using System.Collections.Generic;

namespace Morld.TextUI;

/// <summary>
/// InteractiveTextUI 파사드.
/// TextUISystem에서 RichTextLabel에 연결하여 사용.
/// 마크업 → 파싱 → 상태 관리 → BBCode 렌더링 파이프라인을 캡슐화.
///
/// 사용법:
///   var itui = new InteractiveTextUI();
///   itui.ToggleChanged += (key, open) => { ... };
///   string bbcode = itui.RenderMarkup(rawMarkup, hoveredMeta);
///   richTextLabel.Text = bbcode;
/// </summary>
public class InteractiveTextUI
{
	private readonly TextUIController _controller;
	private readonly GodotRenderer _renderer;

	// ── 시그널/이벤트 ──
	public event Action<string, bool>   TodoChanged;
	public event Action<string, bool>   ButtonChanged;
	public event Action<string, bool>   ToggleChanged;
	public event Action<string, string> RadioChanged;
	public event Action<string, string> ChoiceSelected;

	public InteractiveTextUI()
	{
		_renderer = new GodotRenderer();
		_controller = new TextUIController(_renderer);

		// 컨트롤러 이벤트 → 외부 전달
		_controller.TodoChanged   += (k, v) => TodoChanged?.Invoke(k, v);
		_controller.ButtonChanged += (k, v) => ButtonChanged?.Invoke(k, v);
		_controller.ToggleChanged += (k, v) => ToggleChanged?.Invoke(k, v);
		_controller.RadioChanged  += (g, v) => RadioChanged?.Invoke(g, v);
		_controller.ChoiceSelected += (k, v) => ChoiceSelected?.Invoke(k, v);
	}

	/// <summary>테마 접근</summary>
	public TextUIThemeBase Theme
	{
		get => _controller.Theme;
		set => _controller.Theme = value;
	}

	/// <summary>상태 저장소 직접 접근</summary>
	public WidgetStateStore State => _controller.State;

	/// <summary>
	/// 마크업을 파싱하고 BBCode로 렌더링하여 반환.
	/// TextUISystem.FlushDisplay()에서 호출.
	/// </summary>
	/// <param name="markup">원본 마크업 (BBCode + 위젯 태그 혼합)</param>
	/// <param name="hoveredMeta">현재 hover 중인 메타 (null = 없음)</param>
	/// <returns>렌더링된 BBCode 문자열</returns>
	public string RenderMarkup(string markup, string hoveredMeta = null)
	{
		_controller.SetMarkup(markup);
		_controller.SetHoveredMeta(hoveredMeta);
		return _renderer.RenderedText;
	}

	/// <summary>
	/// 이전과 동일한 마크업에서 hover만 변경 시 (재파싱 없이 렌더링만)
	/// </summary>
	public string RenderWithHover(string hoveredMeta)
	{
		_controller.SetHoveredMeta(hoveredMeta);
		return _renderer.RenderedText;
	}

	/// <summary>
	/// MetaClicked 이벤트 처리.
	/// RichTextLabel.MetaClicked에서 이 메서드로 전달하면
	/// 위젯 클릭은 내부 처리하고, 일반 URL은 false를 반환.
	/// </summary>
	/// <returns>true = 위젯이 처리함, false = 일반 URL (외부에서 처리 필요)</returns>
	public bool HandleMetaClicked(string meta)
	{
		if (string.IsNullOrEmpty(meta)) return false;

		// 위젯 프리픽스 확인
		if (meta.StartsWith("todo:") || meta.StartsWith("button:") ||
			meta.StartsWith("toggle:") || meta.StartsWith("radio:") ||
			meta.StartsWith("choice:"))
		{
			_renderer.OnMetaClicked(meta);
			return true;
		}

		return false; // 일반 URL → 외부에서 처리
	}

	/// <summary>렌더링 결과 BBCode 문자열</summary>
	public string RenderedText => _renderer.RenderedText;

	/// <summary>토글 상태 직접 조회 (Focus.ExpandedToggles 호환용)</summary>
	public bool GetToggleState(string key) => _controller.State.GetToggle(key);

	/// <summary>토글 상태 직접 설정</summary>
	public void SetToggleState(string key, bool value)
	{
		_controller.State.SetToggle(key, value);
	}

	/// <summary>상태 초기화</summary>
	public void Clear() => _controller.Clear();

	/// <summary>상태 직렬화 (세이브)</summary>
	public string SerializeState() => _controller.State.Serialize();

	/// <summary>상태 복원 (로드)</summary>
	public void DeserializeState(string json) => _controller.State.Deserialize(json);
}
