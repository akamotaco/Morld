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
		private string? _hoveredMeta = null;
		private string? _lastActionMessage = null;  // 휘발성 행동 결과 메시지

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
			UpdateDisplay();
		}

		/// <summary>
		/// 현재 Focus를 기반으로 텍스트 생성 및 표시
		/// </summary>
		public void UpdateDisplay()
		{

			if (_stack.Current == null)
			{
				_textUi.Text = "";
				return;
			}

			var text = RenderFocus(_stack.Current);

			// 행동 결과 메시지 추가 (있으면)
			if (!string.IsNullOrEmpty(_lastActionMessage))
			{
				text += $"\n\n[color=yellow]*{_lastActionMessage}[/color]";
			}

			_textUi.Text = ToggleRenderer.Render(
				text,
				_stack.Current.ExpandedToggles,
				_hoveredMeta
			);
		}

		/// <summary>
		/// 행동 결과 메시지 설정 (휘발성, 화면 전환 시 초기화)
		/// </summary>
		public void SetActionMessage(string message)
		{
			_lastActionMessage = message;
		}

		/// <summary>
		/// 행동 결과 메시지 초기화
		/// </summary>
		private void ClearActionMessage()
		{
			_lastActionMessage = null;
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
			return _describeSystem.GetSituationText(lookResult, time);
		}

		private string RenderUnit(int unitId)
		{
			if (_playerSystem == null) return "";
			var unitLook = _playerSystem.LookUnit(unitId);
			if (unitLook == null) return "[color=gray]유닛을 찾을 수 없습니다.[/color]\n\n[url=back]뒤로[/url]";
			return _describeSystem.GetUnitLookText(unitLook);
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
		/// </summary>
		public void ShowSituation()
		{
			ClearActionMessage();
			Clear();
			_stack.Push(Focus.Situation());
			UpdateDisplay();
		}

		/// <summary>
		/// 유닛 상세 화면 표시 (Push)
		/// </summary>
		public void ShowUnitLook(int unitId)
		{
			ClearActionMessage();
			_stack.Push(Focus.Unit(unitId));
			UpdateDisplay();
		}

		/// <summary>
		/// 인벤토리 화면 표시 (Push)
		/// </summary>
		public void ShowInventory()
		{
			ClearActionMessage();
			_stack.Push(Focus.Inventory());
			UpdateDisplay();
		}

		/// <summary>
		/// 아이템 메뉴 표시 (Push)
		/// </summary>
		public void ShowItemMenu(int itemId, string context, int? unitId = null)
		{
			ClearActionMessage();
			_stack.Push(Focus.Item(itemId, context, unitId));
			UpdateDisplay();
		}

		/// <summary>
		/// 결과 메시지 표시 (Push)
		/// </summary>
		public void ShowResult(string message)
		{
			ClearActionMessage();
			_stack.Push(Focus.Result(message));
			UpdateDisplay();
		}

		/// <summary>
		/// 모놀로그 표시 (Push) - 페이지 데이터 직접 전달
		/// </summary>
		public void ShowMonologue(List<string> pages, int timeConsumed, MonologueButtonType buttonType = MonologueButtonType.Ok, string yesCallback = null, string noCallback = null)
		{
			ClearActionMessage();
			_stack.Push(Focus.Monologue(pages, timeConsumed, buttonType, yesCallback, noCallback));
			UpdateDisplay();
		}

		/// <summary>
		/// 모놀로그 다음 페이지로 이동
		/// </summary>
		public void MonologueNextPage()
		{
			if (_stack.Current?.Type != FocusType.Monologue) return;

			_stack.Current.CurrentPage++;
			UpdateDisplay();
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
			ClearActionMessage();
			_stack.Pop();
			UpdateDisplay();
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

			UpdateDisplay();
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
			ClearActionMessage();
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

			UpdateDisplay();
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
