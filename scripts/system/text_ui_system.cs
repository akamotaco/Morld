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

		// 데이터 조회용 참조 (UpdateDisplay에서 사용)
		private PlayerSystem? _playerSystem;
		private InventorySystem? _inventorySystem;

		public TextUISystem(RichTextLabel textUi, DescribeSystem describeSystem)
		{
			_textUi = textUi;
			_describeSystem = describeSystem;
		}

		/// <summary>
		/// 시스템 참조 설정 (GameEngine에서 호출)
		/// </summary>
		public void SetSystemReferences(PlayerSystem playerSystem, InventorySystem inventorySystem)
		{
			_playerSystem = playerSystem;
			_inventorySystem = inventorySystem;
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
			GD.Print($"[TextUISystem] Stack depth: {_stack.Count}");

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
				else if (context == "ground" && _playerSystem != null)
				{
					var lookResult = _playerSystem.Look();
					lookResult.GroundItems.TryGetValue(itemId, out count);
				}
			}

			return _describeSystem.GetItemMenuText(context, itemId, count, unitId);
		}

		private string RenderResult(string message)
		{
			return $"[b]{message}[/b]\n\n[url=back]뒤로[/url]";
		}

		// === 화면 전환 API (Focus Push) ===

		/// <summary>
		/// 상황 화면 표시 (스택 초기화 후 Push)
		/// </summary>
		public void ShowSituation()
		{
			Clear();
			_stack.Push(Focus.Situation());
			UpdateDisplay();
		}

		/// <summary>
		/// 유닛 상세 화면 표시 (Push)
		/// </summary>
		public void ShowUnitLook(int unitId)
		{
			_stack.Push(Focus.Unit(unitId));
			UpdateDisplay();
		}

		/// <summary>
		/// 인벤토리 화면 표시 (Push)
		/// </summary>
		public void ShowInventory()
		{
			_stack.Push(Focus.Inventory());
			UpdateDisplay();
		}

		/// <summary>
		/// 아이템 메뉴 표시 (Push)
		/// </summary>
		public void ShowItemMenu(int itemId, string context, int? unitId = null)
		{
			_stack.Push(Focus.Item(itemId, context, unitId));
			UpdateDisplay();
		}

		/// <summary>
		/// 결과 메시지 표시 (Push)
		/// </summary>
		public void ShowResult(string message)
		{
			_stack.Push(Focus.Result(message));
			UpdateDisplay();
		}

		// === 스택 조작 API ===

		/// <summary>
		/// 최상위 레이어 Pop (자동으로 상위 화면 갱신)
		/// </summary>
		public void Pop()
		{
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
			else if (context == "ground" && _playerSystem != null)
			{
				var lookResult = _playerSystem.Look();
				lookResult.GroundItems.TryGetValue(itemId, out int count);
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
