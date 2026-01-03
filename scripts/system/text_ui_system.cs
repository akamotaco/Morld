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
				(_stack.Current?.Type == FocusType.Situation || _stack.Current?.Type == FocusType.Unit))
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
				FocusType.Unit => RenderUnit(focus.UnitId ?? 0),
				FocusType.Inventory => RenderInventory(),
				FocusType.Item => RenderItem(focus.ItemId ?? 0, focus.Context ?? "inventory", focus.UnitId),
				FocusType.Result => RenderResult(focus.Message ?? ""),
				FocusType.Monologue => RenderMonologue(focus),
				_ => ""
			};
		}

		private string RenderSituation()
		{
			if (_playerSystem == null) return "";
			var lookResult = _playerSystem.Look();
			var time = (_hub?.FindSystem("worldSystem") as WorldSystem)?.GetTime();
			return _describeSystem.GetSituationText(lookResult, time, GetPrintableLogs());
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

		private string RenderItem(int itemId, string context, int? unitId)
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
				else if (context == "container" && unitId.HasValue)
				{
					var inv = _inventorySystem.GetUnitInventory(unitId.Value);
					inv.TryGetValue(itemId, out count);
				}
			}

			// 인벤토리 컨텍스트에서 상위 컨테이너(Unit 또는 Situation) 찾기
			Focus? parentContainer = null;
			if (context == "inventory")
			{
				parentContainer = FindParentContainer();
			}

			return _describeSystem.GetItemMenuText(context, itemId, count, unitId, parentContainer);
		}

		private string RenderResult(string message)
		{
			return $"[b]{message}[/b]\n\n[url=back]뒤로[/url]";
		}

		private string RenderMonologue(Focus focus)
		{
			var pages = focus.MonologuePages;
			if (pages == null || pages.Count == 0)
			{
				return "[color=gray]모놀로그를 불러올 수 없습니다.[/color]\n\n[url=monologue_done]확인[/url]";
			}

			var currentPage = focus.CurrentPage;
			if (currentPage < 0 || currentPage >= pages.Count)
			{
				return "[color=gray]모놀로그 페이지를 찾을 수 없습니다.[/color]\n\n[url=monologue_done]확인[/url]";
			}

			var pageText = pages[currentPage];
			var isLastPage = currentPage >= pages.Count - 1;
			var buttonType = focus.MonologueButtonType;

			// 페이지에 script: 링크가 있으면 선택형 페이지 - None 타입으로 자동 전환
			bool hasScriptLink = pageText.Contains("[url=script:");
			if (hasScriptLink)
			{
				buttonType = MonologueButtonType.None;
			}

			var lines = new List<string>();
			lines.Add(pageText);

			// 버튼 타입에 따라 다른 버튼 렌더링
			switch (buttonType)
			{
				case MonologueButtonType.Ok:
					lines.Add("");
					if (isLastPage)
					{
						lines.Add("[url=monologue_done]확인[/url]");
					}
					else
					{
						lines.Add("[url=monologue_next]계속[/url]");
					}
					break;

				case MonologueButtonType.None:
					// 버튼 없음 (선택지가 페이지 내에 포함된 경우)
					break;

				case MonologueButtonType.YesNo:
					lines.Add("");
					lines.Add("[url=monologue_yes]승낙[/url]  [url=monologue_no]거절[/url]");
					break;
			}

			return string.Join("\n", lines);
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
		/// 모놀로그 표시 (Push) - 페이지 데이터 직접 전달
		/// </summary>
		public void ShowMonologue(List<string> pages, int timeConsumed, MonologueButtonType buttonType = MonologueButtonType.Ok, string doneCallback = null, string cancelCallback = null)
		{
			_stack.Push(Focus.Monologue(pages, timeConsumed, buttonType, doneCallback, cancelCallback));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 모놀로그 다음 페이지로 이동
		/// </summary>
		public void MonologueNextPage()
		{
			if (_stack.Current?.Type != FocusType.Monologue) return;

			_stack.Current.CurrentPage++;
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 현재 모놀로그 내용 교체 (Push 없이 in-place 갱신)
		/// 비밀번호 입력 등 상태 변경 시 사용
		/// </summary>
		public void UpdateMonologueContent(List<string> pages, MonologueButtonType buttonType = MonologueButtonType.None)
		{
			if (_stack.Current?.Type != FocusType.Monologue) return;

			_stack.Current.MonologuePages = pages;
			_stack.Current.CurrentPage = 0;
			_stack.Current.MonologueButtonType = buttonType;
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 모놀로그 완료 처리 (Pop + 시간 소요)
		/// </summary>
		/// <returns>소요 시간 (분)</returns>
		public int MonologueDone()
		{
			int timeConsumed = 0;

			// Focus에 저장된 시간 사용
			if (_stack.Current?.Type == FocusType.Monologue)
			{
				timeConsumed = _stack.Current.MonologueTimeConsumed;
			}

			Pop();
			return timeConsumed;
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
				var unitId = _stack.Current.UnitId;

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
		/// 스택에서 최상위 컨테이너(Unit 또는 Situation) 찾기
		/// </summary>
		/// <returns>Unit이면 unitId, Situation이면 null, 없으면 예외</returns>
		public Focus? FindParentContainer()
		{
			return _stack.FindParentContainer();
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
