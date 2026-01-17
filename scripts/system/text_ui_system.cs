using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using ECS;
using Godot;
using Morld;

namespace SE
{
	/// <summary>
	/// UI 텍스트 시스템 (Focus 스택 기반)
	/// 스택에는 Focus 정보만 저장하고, 표시 시 항상 최신 데이터로 렌더링
	/// </summary>
	public class TextUISystem : ECS.System
	{
		private readonly RichTextLabel _textUi;
		private readonly FocusStack _stack = new();
		private readonly DescribeSystem _describeSystem;
		private ActionLogSystem _actionLogSystem;
		private string? _hoveredMeta = null;

		// Lazy update 플래그
		private bool _needsUpdateDisplay = false;

		public TextUISystem(RichTextLabel textUi, DescribeSystem describeSystem)
		{
			_textUi = textUi;
			_describeSystem = describeSystem;
		}

		/// <summary>
		/// ActionLogSystem 참조 설정 (시스템 등록 후 호출)
		/// </summary>
		public void SetActionLogSystem(ActionLogSystem actionLogSystem)
		{
			_actionLogSystem = actionLogSystem;
			_actionLogSystem.OnLogAdded = RequestUpdateDisplay;
		}

		/// <summary>
		/// 현재 hover 중인 메타 설정 (null = hover 없음)
		/// </summary>
		public void SetHoveredMeta(string? meta)
		{
			if (_hoveredMeta == meta) return;
			_hoveredMeta = meta;
			RequestUpdateDisplay();
		}

		/// <summary>
		/// UI 업데이트 요청 (lazy update)
		/// 실제 렌더링은 FlushDisplay()에서 수행
		/// </summary>
		public void RequestUpdateDisplay()
		{
			_needsUpdateDisplay = true;
		}

		/// <summary>
		/// 스택이 비어있는지 확인
		/// </summary>
		public bool IsStackEmpty() => _stack.Count == 0;

		/// <summary>
		/// 대기 중인 UI 업데이트 수행 (lazy update 적용)
		/// </summary>
		public void FlushDisplay()
		{
			if (!_needsUpdateDisplay) return;
			_needsUpdateDisplay = false;

			Godot.GD.Print($"[TextUISystem] FlushDisplay: stack={_stack.Current?.Type}, hoveredMeta={_hoveredMeta ?? "null"}");

			if (_stack.Current == null)
			{
				Godot.GD.Print("[TextUISystem] FlushDisplay: stack is empty, clearing text");
				_textUi.Text = "";
				return;
			}

			var text = RenderFocus(_stack.Current);

			_textUi.Text = ToggleRenderer.Render(
				text,
				_stack.Current.ExpandedToggles,
				_hoveredMeta
			);

			Godot.GD.Print($"[TextUISystem] FlushDisplay: rendered {_stack.Current.Type}, textLen={_textUi.Text.Length}");

			// 읽음 처리는 FlushDisplay에서 하지 않음
			// OnPlayerAction()에서 플레이어 액션 시점에 처리
		}

		/// <summary>
		/// 화면 콘텐츠가 변경될 때 호출 (플레이어 액션 시)
		/// 새로운 화면으로 전환되기 전에 현재 상태를 정리하는 역할
		///
		/// 포함 기능:
		/// - 현재 표시된 로그 읽음 처리 (markLogsAsRead=true일 때만)
		/// - (향후) 기타 정리 작업 추가 가능
		/// </summary>
		/// <param name="markLogsAsRead">true면 로그 읽음 처리, false면 건너뜀 (토글 등 UI 상태만 변경 시)</param>
		public void OnContentChange(bool markLogsAsRead = true)
		{
			// 1. 로그 읽음 처리 (Situation, Unit 화면에서만, markLogsAsRead=true일 때)
			if (markLogsAsRead &&
				(_stack.Current.Type == FocusType.Situation || _stack.Current.Type == FocusType.Unit))
			{
				MarkPrintedLogsAsRead();
			}

			// 2. (향후 추가 기능을 여기에)
		}

		/// <summary>
		/// 현재 Focus를 기반으로 텍스트 생성 및 표시 (즉시 실행)
		/// </summary>
		public void UpdateDisplay()
		{
			RequestUpdateDisplay();
			FlushDisplay();
		}

		/// <summary>
		/// 출력된 로그를 읽음 처리
		/// </summary>
		private void MarkPrintedLogsAsRead()
		{
			_actionLogSystem?.MarkPrintedLogsAsRead();
		}

		/// <summary>
		/// Focus 정보를 기반으로 텍스트 생성
		/// </summary>
		private string RenderFocus(Focus focus)
		{
			return focus.Type switch
			{
				FocusType.Situation => RenderSituation(),
				FocusType.Unit => RenderUnit(focus.TargetUnitId ?? 0),
				FocusType.Inventory => RenderInventory(),
				FocusType.Equipment => RenderEquipment(),
				FocusType.Item => RenderItem(focus.ItemId ?? 0, focus.Context ?? "inventory", focus.TargetUnitId),
				FocusType.Result => RenderResult(focus.Message ?? ""),
				FocusType.Dialog => RenderDialog(focus),
				_ => ""
			};
		}

		/// <summary>
		/// 다이얼로그 렌더링 (morld.dialog() API)
		/// BBCode URL을 그대로 표시 (@ret:값, @proc:값 패턴은 MetaActionHandler에서 처리)
		/// </summary>
		private string RenderDialog(Focus focus)
		{
			var lines = new List<string>();

			// Header: 구분선
			lines.Add("[color=gray]────────────────────[/color]");

			// Body: 다이얼로그 텍스트
			var body = focus.DialogText ?? "";
			lines.Add(body);

			// Footer: 구분선
			lines.Add("[color=gray]────────────────────[/color]");

			return string.Join("\n", lines);
		}

		private string RenderSituation()
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

			var lookResult = _playerSystem.Look();
			var time = (_hub.GetSystem("worldSystem") as WorldSystem).GetTime();

			var lines = new List<string>();

			// Header: 시간/날씨 (Python get_header())
			var header = GetHeaderFromPython();
			if (!string.IsNullOrEmpty(header))
			{
				lines.Add(header);
				lines.Add("[color=gray]────────────────────[/color]");
			}

			// Body: 묘사 텍스트
			var describeText = _describeSystem.GetSituationText(lookResult, time);
			Godot.GD.Print($"[RenderSituation] describeText.Length={describeText?.Length ?? 0}");
			lines.Add(describeText);

			// 행동 텍스트 (Python 훅 또는 C# 폴백)
			var actionText = GetActionTextFromPython();
			Godot.GD.Print($"[RenderSituation] actionText from Python: {actionText?.Length ?? 0} chars");
			if (string.IsNullOrEmpty(actionText))
			{
				// Python 훅 실패 시 C# 폴백
				actionText = _describeSystem.GetActionText(lookResult);
				Godot.GD.Print($"[RenderSituation] actionText from C# fallback: {actionText?.Length ?? 0} chars");
			}
			lines.Add(actionText);

			// Footer: 상태바
			var footer = GetFooterFromPython();
			if (!string.IsNullOrEmpty(footer))
			{
				lines.Add(footer);
			}

			var result = string.Join("\n", lines);
			Godot.GD.Print($"[RenderSituation] total={result.Length} chars");
			return result;
		}

		/// <summary>
		/// Python ui.get_action_text() 훅 호출
		/// </summary>
		private string? GetActionTextFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				// ui 모듈의 get_action_text() 호출
				var result = _scriptSystem.CallModuleFunction("ui", "get_action_text");
				if (result != null && result is not SharpPy.PyNone)
				{
					var text = result.AsString();
					if (!string.IsNullOrEmpty(text))
					{
						// 구분선 추가
						return "[color=gray]────────────────────[/color]\n" + text;
					}
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python get_action_text() error: {ex.Message}");
			}

			return null;
		}

		/// <summary>
		/// Python ui.get_header() 훅 호출
		/// Focus 화면 상단에 시간/날씨 정보 표시
		/// </summary>
		private string? GetHeaderFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				var result = _scriptSystem.CallModuleFunction("ui", "get_header");
				if (result != null && result is not SharpPy.PyNone)
				{
					var text = result.AsString();
					if (!string.IsNullOrEmpty(text))
					{
						return text;
					}
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python get_header() error: {ex.Message}");
			}

			return null;
		}

		/// <summary>
		/// Python ui.get_footer() 훅 호출
		/// Focus 화면 하단에 상태바 정보 표시
		/// </summary>
		private string? GetFooterFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				var result = _scriptSystem.CallModuleFunction("ui", "get_footer");
				if (result != null && result is not SharpPy.PyNone)
				{
					var text = result.AsString();
					if (!string.IsNullOrEmpty(text))
					{
						return text;
					}
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python get_footer() error: {ex.Message}");
			}

			return null;
		}

		private string RenderUnit(int unitId)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

			var unitLook = _playerSystem.LookUnit(unitId);
			if (unitLook == null) return "[color=gray]유닛을 찾을 수 없습니다.[/color]\n\n[url=back]뒤로[/url]";

			var lines = new List<string>();

			// Header: 시간/날씨
			var header = GetHeaderFromPython();
			if (!string.IsNullOrEmpty(header))
			{
				lines.Add(header);
				lines.Add("[color=gray]────────────────────[/color]");
			}

			// Body: 유닛 정보
			var body = _describeSystem.GetUnitLookText(unitLook);
			lines.Add(body);

			// Footer: 인벤토리 + 상태바 (Python ui.get_footer()에서 통합 생성)
			// 주의: Unit Focus에서 인벤토리 열고 장비 변경 시 on_equip_change 이벤트 관련 이슈 있음
			// - 다중 NPC가 있을 때 첫 번째 NPC만 이벤트 처리됨 (events/__init__.py 참고)
			var footer = GetFooterFromPython();
			if (!string.IsNullOrEmpty(footer))
			{
				lines.Add(footer);
			}

			return string.Join("\n", lines);
		}

		private string RenderInventory()
		{
			// 인벤토리는 header/footer 없이 구분선 + body + 구분선
			var lines = new List<string>();
			lines.Add("[color=gray]────────────────────[/color]");
			lines.Add(_describeSystem.GetInventoryText());
			lines.Add("[color=gray]────────────────────[/color]");
			return string.Join("\n", lines);
		}

		private string RenderEquipment()
		{
			var lines = new List<string>();

			// Header: 시간/날씨
			var header = GetHeaderFromPython();
			if (!string.IsNullOrEmpty(header))
			{
				lines.Add(header);
				lines.Add("[color=gray]────────────────────[/color]");
			}

			// Body: 장비
			var body = _describeSystem.GetEquipmentText();
			lines.Add(body);

			// Footer: 상태바
			var footer = GetFooterFromPython();
			if (!string.IsNullOrEmpty(footer))
			{
				lines.Add(footer);
			}

			return string.Join("\n", lines);
		}

		private string RenderItem(int itemId, string context, int? targetUnitId)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;

			// 아이템 개수 조회
			int count = 0;
			if (_inventorySystem != null)
			{
				if (context == "inventory" && _playerSystem != null)
				{
					var player = _playerSystem.FindPlayerUnit();
					if (player != null)
					{
						var inv = _inventorySystem.GetUnitInventory(player.Id);
						inv.TryGetValue(itemId, out count);
					}
				}
				else if (context == "container" && targetUnitId.HasValue)
				{
					var inv = _inventorySystem.GetUnitInventory(targetUnitId.Value);
					inv.TryGetValue(itemId, out count);
				}
			}

			// 아이템은 header/footer 없이 구분선 + body + 구분선
			var lines = new List<string>();
			lines.Add("[color=gray]────────────────────[/color]");

			var body = _describeSystem.GetItemMenuText(context, itemId, count, targetUnitId);
			lines.Add(body);

			lines.Add("[color=gray]────────────────────[/color]");
			return string.Join("\n", lines);
		}

		private string RenderResult(string message)
		{
			return $"[b]{message}[/b]\n\n[url=back]뒤로[/url]";
		}

		// === 화면 전환 API (Focus Push) ===

		/// <summary>
		/// 상황 화면 표시 (스택 초기화 후 Push)
		/// 로그는 유지됨 (MaxLogLength 초과 시에만 자동 삭제)
		/// </summary>
		public void ShowSituation()
		{
			Clear();
			_stack.Push(Focus.Situation());
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 유닛 상세 화면 표시 (Push)
		/// </summary>
		public void ShowUnitLook(int unitId)
		{
			_stack.Push(Focus.Unit(unitId));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 인벤토리 화면 표시 (Push)
		/// </summary>
		public void ShowInventory()
		{
			_stack.Push(Focus.Inventory());
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 장착 아이템 목록 표시 (Push)
		/// </summary>
		public void ShowEquipment()
		{
			_stack.Push(Focus.Equipment());
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 아이템 메뉴 표시 (Push)
		/// </summary>
		public void ShowItemMenu(int itemId, string context, int? unitId = null)
		{
			_stack.Push(Focus.Item(itemId, context, unitId));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 결과 메시지 표시 (Push)
		/// </summary>
		public void ShowResult(string message)
		{
			_stack.Push(Focus.Result(message));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 다이얼로그 Push (첫 yield morld.dialog() 호출 시)
		/// Note: 로그 읽음 처리는 액션 버튼 클릭 시점(HandleAction)에서만 수행
		/// 이벤트 연쇄 처리 시 중간 다이얼로그에서 로그가 유실되지 않도록 함
		/// </summary>
		public void PushDialog(string text, int timeConsumed = 0)
		{
			_stack.Push(Focus.Dialog(text, timeConsumed));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 다이얼로그 텍스트 갱신 (@proc: 후 다음 yield 호출 시)
		/// lazy update로 변경 - FlushDisplay()에서 일괄 렌더링
		/// </summary>
		public void UpdateDialogText(string text)
		{
			if (_stack.Current.Type != FocusType.Dialog)
			{
				Godot.GD.PrintErr("[TextUISystem] UpdateDialogText called but no dialog is open - this is a bug!");
				return;
			}

			_stack.Current.DialogText = text;
			RequestUpdateDisplay();
		}

		// === 스택 조작 API ===

		/// <summary>
		/// 최상위 레이어 Pop (자동으로 상위 화면 갱신)
		/// </summary>
		public void Pop()
		{
			_stack.Pop();
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 현재 포커스가 유효하지 않으면 Pop (아이템 0개 등)
		/// </summary>
		public void PopIfInvalid()
		{
			if (_stack.Current == null) return;

			if (_stack.Current.Type == FocusType.Item)
			{
				var itemId = _stack.Current.ItemId ?? 0;
				var context = _stack.Current.Context ?? "inventory";
				var unitId = _stack.Current.TargetUnitId;

				int count = GetItemCount(itemId, context, unitId);
				if (count <= 0)
				{
					Pop();
					return;
				}
			}

			RequestUpdateDisplay();
		}

		/// <summary>
		/// 아이템 개수 조회
		/// </summary>
		private int GetItemCount(int itemId, string context, int? unitId)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;

			if (context == "inventory")
			{
				var player = _playerSystem.FindPlayerUnit();
				if (player != null)
				{
					var inv = _inventorySystem.GetUnitInventory(player.Id);
					inv.TryGetValue(itemId, out int count);
					return count;
				}
			}
			else if (context == "container" && unitId.HasValue)
			{
				var inv = _inventorySystem.GetUnitInventory(unitId.Value);
				inv.TryGetValue(itemId, out int count);
				return count;
			}

			return 0;
		}

		/// <summary>
		/// 스택 전체 비우기
		/// </summary>
		public void Clear()
		{
			_stack.Clear();
		}

		/// <summary>
		/// 토글 펼침/접힘 전환
		/// </summary>
		public void ToggleExpand(string toggleId)
		{
			if (_stack.Current == null) return;

			var toggles = _stack.Current.ExpandedToggles;
			if (toggles.Contains(toggleId))
				toggles.Remove(toggleId);
			else
				toggles.Add(toggleId);

			RequestUpdateDisplay();
		}

		/// <summary>
		/// 스택이 비어있는지 확인
		/// </summary>
		public bool IsEmpty => _stack.Count == 0;

		/// <summary>
		/// 현재 Focus 정보 반환
		/// </summary>
		public Focus? CurrentFocus => _stack.Current;

		/// <summary>
		/// Proc은 빈 구현 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
