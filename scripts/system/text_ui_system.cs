using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using ECS;
using Godot;
using Morld;

namespace SE
{
	/// <summary>
	/// 행동 로그 항목
	/// </summary>
	public class ActionLogEntry
	{
		public string Message { get; set; } = "";
		public bool IsRead { get; set; } = false;

		public ActionLogEntry(string message)
		{
			Message = message;
		}
	}

	/// <summary>
	/// 다이얼로그 큐 항목 (연쇄 다이얼로그용)
	/// </summary>
	public class DialogQueueItem
	{
		public string Text { get; set; } = "";
		public int TimeConsumed { get; set; } = 0;

		public DialogQueueItem(string text, int timeConsumed = 0)
		{
			Text = text;
			TimeConsumed = timeConsumed;
		}
	}

	/// <summary>
	/// UI 텍스트 시스템 (Focus 스택 기반)
	/// 스택에는 Focus 정보만 저장하고, 표시 시 항상 최신 데이터로 렌더링
	/// </summary>
	public class TextUISystem : ECS.System
	{
		private readonly RichTextLabel _textUi;
		private readonly FocusStack _stack = new();
		private readonly DescribeSystem _describeSystem;
		private string? _hoveredMeta = null;

		// 행동 로그 시스템
		private readonly List<ActionLogEntry> _actionLogs = new();
		private const int MaxLogLength = 50;   // 최대 로그 보관 개수

		// Lazy update 플래그
		private bool _needsUpdateDisplay = false;

		// 다이얼로그 큐 (연쇄 다이얼로그용)
		private readonly Queue<DialogQueueItem> _dialogQueue = new();

		// 데이터 조회용 참조 (UpdateDisplay에서 사용)
		private PlayerSystem? _playerSystem;
		private InventorySystem? _inventorySystem;
		private ScriptSystem? _scriptSystem;

		public TextUISystem(RichTextLabel textUi, DescribeSystem describeSystem)
		{
			_textUi = textUi;
			_describeSystem = describeSystem;
		}

		/// <summary>
		/// 시스템 참조 설정 (GameEngine에서 호출)
		/// </summary>
		public void SetSystemReferences(PlayerSystem playerSystem, InventorySystem inventorySystem, ScriptSystem? scriptSystem = null)
		{
			_playerSystem = playerSystem;
			_inventorySystem = inventorySystem;
			_scriptSystem = scriptSystem;
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

			if (_stack.Current == null)
			{
				_textUi.Text = "";
				return;
			}

			var text = RenderFocus(_stack.Current);

			_textUi.Text = ToggleRenderer.Render(
				text,
				_stack.Current.ExpandedToggles,
				_hoveredMeta
			);

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
		/// 행동 로그 추가 (appearance 다음, 액션 전에 표시)
		/// 자동으로 UI 업데이트 요청
		/// </summary>
		public void AddActionLog(string message)
		{
			_actionLogs.Add(new ActionLogEntry(message));

			// MaxLogLength 초과 시 오래된 로그 삭제
			while (_actionLogs.Count > MaxLogLength)
			{
				_actionLogs.RemoveAt(0);
			}

			// UI 업데이트 요청 (lazy)
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 출력용 로그 엔트리 반환 (읽지 않은 것만)
		/// </summary>
		public IReadOnlyList<ActionLogEntry> GetPrintableLogs()
		{
			// 읽지 않은 로그만 반환
			return _actionLogs
				.Where(e => !e.IsRead)
				.ToList();
		}

		/// <summary>
		/// 모든 로그를 읽음 처리
		/// </summary>
		public void MarkAllLogsAsRead()
		{
			foreach (var log in _actionLogs)
			{
				log.IsRead = true;
			}
		}

		/// <summary>
		/// 출력된 로그를 읽음 처리 (읽지 않은 것만)
		/// </summary>
		private void MarkPrintedLogsAsRead()
		{
			foreach (var log in _actionLogs.Where(e => !e.IsRead))
			{
				log.IsRead = true;
			}
		}

		/// <summary>
		/// 읽지 않은 로그 개수
		/// </summary>
		public int UnreadLogCount => _actionLogs.Count(e => !e.IsRead);

		/// <summary>
		/// 디버그용: 전체 로그 상태 출력
		/// </summary>
		public void DebugPrintLogs()
		{
#if DEBUG_LOG
			GD.Print($"[ActionLogs] Total: {_actionLogs.Count}, Unread: {UnreadLogCount}");
			foreach (var log in _actionLogs)
			{
				var readMark = log.IsRead ? "[R]" : "[U]";
				GD.Print($"  {readMark} {log.Message}");
			}
#endif
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
			return focus.DialogText ?? "";
		}

		private string RenderSituation()
		{
			if (_playerSystem == null) return "";
			var lookResult = _playerSystem.Look();
			var time = (_hub.GetSystem("worldSystem") as WorldSystem).GetTime();

			// 1. 묘사 텍스트 (행동 옵션 제외)
			var describeText = _describeSystem.GetDescribeText(lookResult, time, GetPrintableLogs());

			// 2. 행동 텍스트 (Python 훅 또는 C# 폴백)
			var actionText = GetActionTextFromPython();
			if (string.IsNullOrEmpty(actionText))
			{
				// Python 훅 실패 시 C# 폴백
				actionText = _describeSystem.GetActionText(lookResult);
			}

			return describeText + "\n" + actionText;
		}

		/// <summary>
		/// Python ui.get_action_text() 훅 호출
		/// </summary>
		private string? GetActionTextFromPython()
		{
			if (_scriptSystem == null) return null;

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

		private string RenderUnit(int unitId)
		{
			if (_playerSystem == null) return "";
			var unitLook = _playerSystem.LookUnit(unitId);
			if (unitLook == null) return "[color=gray]유닛을 찾을 수 없습니다.[/color]\n\n[url=back]뒤로[/url]";
			return _describeSystem.GetUnitLookText(unitLook, GetPrintableLogs());
		}

		private string RenderInventory()
		{
			return _describeSystem.GetInventoryText();
		}

		private string RenderItem(int itemId, string context, int? targetUnitId)
		{
			// 아이템 개수 조회
			int count = 0;
			if (_inventorySystem != null)
			{
				if (context == "inventory" && _playerSystem != null)
				{
					var player = _playerSystem.GetPlayerUnit();
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

			// inventory 컨텍스트에서 targetUnitId가 없으면 스택에서 찾기
			var effectiveTargetUnitId = targetUnitId ?? (context == "inventory" ? FindTargetUnitId() : null);

			return _describeSystem.GetItemMenuText(context, itemId, count, effectiveTargetUnitId);
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
		/// 이미 다이얼로그가 열려있으면 큐에 추가 (연쇄 다이얼로그)
		/// </summary>
		public void PushDialog(string text, int timeConsumed = 0)
		{
			// 이미 다이얼로그가 열려있으면 큐에 추가
			if (_stack.Current.Type == FocusType.Dialog)
			{
				_dialogQueue.Enqueue(new DialogQueueItem(text, timeConsumed));
#if DEBUG_LOG
				GD.Print($"[TextUISystem] Dialog queued (queue size: {_dialogQueue.Count})");
#endif
				return;
			}

			_stack.Push(Focus.Dialog(text, timeConsumed));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 다이얼로그 텍스트 갱신 (@proc: 후 다음 yield 호출 시)
		/// 즉시 RichTextLabel 텍스트 갱신 (lazy 아님)
		/// </summary>
		public void UpdateDialogText(string text)
		{
			if (_stack.Current.Type != FocusType.Dialog)
			{
				Godot.GD.PrintErr("[TextUISystem] UpdateDialogText called but no dialog is open - this is a bug!");
				return;
			}

			_stack.Current.DialogText = text;
			// 즉시 RichTextLabel 텍스트 갱신 (lazy 아님)
			_textUi.Text = text;
		}

		/// <summary>
		/// 다이얼로그 완료 처리 (Pop + 시간 소요 + 큐에서 다음 다이얼로그 표시)
		/// </summary>
		/// <returns>소요 시간 (분)</returns>
		public int DialogDone()
		{
			int timeConsumed = 0;

			// Focus에 저장된 시간 사용
			if (_stack.Current.Type == FocusType.Dialog)
			{
				timeConsumed = _stack.Current.TimeConsumed;
			}

			Pop();

			// 큐에 다음 다이얼로그가 있으면 표시
			if (_dialogQueue.Count > 0)
			{
				var next = _dialogQueue.Dequeue();
#if DEBUG_LOG
				GD.Print($"[TextUISystem] Showing next dialog from queue (remaining: {_dialogQueue.Count})");
#endif
				_stack.Push(Focus.Dialog(next.Text, next.TimeConsumed));
				RequestUpdateDisplay();
			}

			return timeConsumed;
		}

		/// <summary>
		/// 다이얼로그 큐에 대기 중인 항목이 있는지 확인
		/// </summary>
		public bool HasQueuedDialogs => _dialogQueue.Count > 0;

		/// <summary>
		/// 다이얼로그 큐 비우기
		/// </summary>
		public void ClearDialogQueue()
		{
			_dialogQueue.Clear();
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
			if (_inventorySystem == null) return 0;

			if (context == "inventory" && _playerSystem != null)
			{
				var player = _playerSystem.GetPlayerUnit();
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
		/// 스택에서 가장 가까운 Unit의 TargetUnitId 찾기
		/// 넣기/가져오기 대상 유닛 ID를 찾는 데 사용
		/// </summary>
		public int? FindTargetUnitId()
		{
			return _stack.FindTargetUnitId();
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
