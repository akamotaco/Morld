using System.Collections.Generic;
using System.Text.Json;

namespace Morld.TextUI;

/// <summary>
/// 위젯 상태 저장소.
/// AST와 독립적으로 상태를 관리하며, 마크업 변경 시에도 기존 상태 유지.
/// </summary>
public class WidgetStateStore
{
	private readonly Dictionary<string, bool>   _todoStates   = new();
	private readonly Dictionary<string, bool>   _buttonStates = new();
	private readonly Dictionary<string, bool>   _toggleStates = new();
	private readonly Dictionary<string, string> _radioStates  = new();
	private readonly Dictionary<string, string> _choiceStates = new();

	// ── 조회 ──

	public bool   GetTodo(string key)     => _todoStates.GetValueOrDefault(key, false);
	public bool   GetButton(string key)   => _buttonStates.GetValueOrDefault(key, false);
	public bool   GetToggle(string key)   => _toggleStates.GetValueOrDefault(key, false);
	public string GetRadio(string group)  => _radioStates.GetValueOrDefault(group, "");
	public string GetChoice(string key)   => _choiceStates.GetValueOrDefault(key, "");

	// ── 설정 ──

	public void SetTodo(string key, bool v)       => _todoStates[key] = v;
	public void SetButton(string key, bool v)     => _buttonStates[key] = v;
	public void SetToggle(string key, bool v)     => _toggleStates[key] = v;
	public void SetRadio(string grp, string v)    => _radioStates[grp] = v;

	/// <summary>Choice 설정. 이미 선택된 경우 무시 (비가역).</summary>
	public bool TrySetChoice(string key, string value)
	{
		if (_choiceStates.TryGetValue(key, out var existing) && !string.IsNullOrEmpty(existing))
			return false; // 이미 선택됨
		_choiceStates[key] = value;
		return true;
	}

	/// <summary>Choice 강제 설정 (세이브/로드용)</summary>
	public void ForceSetChoice(string key, string value) => _choiceStates[key] = value;

	// ── 토글 편의 ──

	public void ToggleTodo(string key)
	{
		_todoStates[key] = !GetTodo(key);
	}

	public void ToggleButton(string key)
	{
		_buttonStates[key] = !GetButton(key);
	}

	public void ToggleToggle(string key)
	{
		_toggleStates[key] = !GetToggle(key);
	}

	// ── 일괄 조회 ──

	public Dictionary<string, bool>   GetAllTodos()   => new(_todoStates);
	public Dictionary<string, bool>   GetAllButtons() => new(_buttonStates);
	public Dictionary<string, bool>   GetAllToggles() => new(_toggleStates);
	public Dictionary<string, string> GetAllRadios()  => new(_radioStates);
	public Dictionary<string, string> GetAllChoices() => new(_choiceStates);

	// ── AST에서 초기값 등록 (TryAdd로 기존 상태 보존) ──

	public void InitFromAst(List<AstNode> nodes)
	{
		foreach (var n in nodes)
		{
			switch (n.Type)
			{
				case NodeType.Todo:
					_todoStates.TryAdd(n.Key, n.DefaultState);
					break;
				case NodeType.Button:
					_buttonStates.TryAdd(n.Key, n.DefaultState);
					break;
				case NodeType.Toggle:
					_toggleStates.TryAdd(n.Key, n.DefaultState);
					InitFromAst(n.Children);
					break;
				case NodeType.Radio:
					if (!_radioStates.ContainsKey(n.Key) && n.DefaultState)
						_radioStates[n.Key] = n.Value;
					break;
				case NodeType.Choice:
					_choiceStates.TryAdd(n.Key, "");
					InitFromAst(n.Children);
					break;
			}
		}
	}

	// ── 초기화 ──

	public void Clear()
	{
		_todoStates.Clear();
		_buttonStates.Clear();
		_toggleStates.Clear();
		_radioStates.Clear();
		_choiceStates.Clear();
	}

	// ── JSON 직렬화 ──

	public string Serialize()
	{
		var data = new Dictionary<string, object>
		{
			["todo"]   = _todoStates,
			["button"] = _buttonStates,
			["toggle"] = _toggleStates,
			["radio"]  = _radioStates,
			["choice"] = _choiceStates,
		};
		return JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true });
	}

	public void Deserialize(string json)
	{
		if (string.IsNullOrEmpty(json)) return;

		using var doc = JsonDocument.Parse(json);
		var root = doc.RootElement;

		if (root.TryGetProperty("todo", out var todos))
			foreach (var kv in todos.EnumerateObject())
				_todoStates[kv.Name] = kv.Value.GetBoolean();

		if (root.TryGetProperty("button", out var buttons))
			foreach (var kv in buttons.EnumerateObject())
				_buttonStates[kv.Name] = kv.Value.GetBoolean();

		if (root.TryGetProperty("toggle", out var toggles))
			foreach (var kv in toggles.EnumerateObject())
				_toggleStates[kv.Name] = kv.Value.GetBoolean();

		if (root.TryGetProperty("radio", out var radios))
			foreach (var kv in radios.EnumerateObject())
				_radioStates[kv.Name] = kv.Value.GetString() ?? "";

		if (root.TryGetProperty("choice", out var choices))
			foreach (var kv in choices.EnumerateObject())
				_choiceStates[kv.Name] = kv.Value.GetString() ?? "";
	}
}
