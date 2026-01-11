#define DEBUG_LOG

using Godot;
using SE;

/// <summary>
/// MetaActionHandler - Item 핸들러
/// 아이템 관련 액션 처리 (메뉴, 사용, 조합, 버리기 등)
/// </summary>
public partial class MetaActionHandler
{
	/// <summary>
	/// 아이템 버리기 처리 (레거시 - 현재 사용 안함)
	/// 바닥에 버리기는 put:바닥unitId:itemId 로 처리됨
	/// </summary>
	private void HandleDropAction(string[] parts)
	{
		GD.PrintErr("[MetaActionHandler] drop action is deprecated. Use put:unitId:itemId instead.");
	}

	/// <summary>
	/// 바닥 아이템 메뉴 표시: item_ground_menu:itemId
	/// </summary>
	private void HandleItemGroundMenuAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_ground_menu format. Expected: item_ground_menu:itemId");
			return;
		}

		_textUISystem?.ShowItemMenu(itemId, "ground");
	}

	/// <summary>
	/// 인벤토리 아이템 메뉴 표시: item_inv_menu:itemId
	/// </summary>
	private void HandleItemInvMenuAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_inv_menu format. Expected: item_inv_menu:itemId");
			return;
		}

		// 현재 Focus의 TargetUnitId를 전달 (넣기 버튼 생성용)
		var targetUnitId = _textUISystem?.CurrentFocus?.TargetUnitId;
		_textUISystem?.ShowItemMenu(itemId, "inventory", targetUnitId);
	}

	/// <summary>
	/// 아이템 사용: item_use:itemId
	/// </summary>
	private void HandleItemUseAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_use format. Expected: item_use:itemId");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] 아이템 사용: itemId={itemId}");
#endif

		// TODO: 실제 사용 처리
		_textUISystem?.ShowResult("사용 기능은 아직 구현되지 않았습니다.");
	}

	/// <summary>
	/// 아이템 조합: item_combine:itemId
	/// </summary>
	private void HandleItemCombineAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_combine format. Expected: item_combine:itemId");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] 아이템 조합: itemId={itemId}");
#endif

		// TODO: 실제 조합 처리
		_textUISystem?.ShowResult("조합 기능은 아직 구현되지 않았습니다.");
	}

	/// <summary>
	/// 오브젝트 인벤토리 아이템 메뉴 표시: item_unit_menu:unitId:itemId
	/// </summary>
	private void HandleItemUnitMenuAction(string[] parts)
	{
		if (parts.Length < 3 ||
			!int.TryParse(parts[1], out int unitId) ||
			!int.TryParse(parts[2], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_unit_menu format. Expected: item_unit_menu:unitId:itemId");
			return;
		}

		_textUISystem?.ShowItemMenu(itemId, "container", unitId);
	}

	/// <summary>
	/// 인벤토리 화면으로 돌아가기: back_inventory
	/// 뒤로 → Pop
	/// </summary>
	private void HandleBackInventoryAction()
	{
		_textUISystem?.Pop();
	}

	/// <summary>
	/// 유닛 화면으로 돌아가기: back_unit:unitId
	/// 뒤로 → Pop
	/// </summary>
	private void HandleBackUnitAction()
	{
		_textUISystem?.Pop();
	}

	/// <summary>
	/// 넣기 대상 선택 (인벤토리 표시): put_select:unitId
	/// Unit에서 '넣기' 클릭 → Inventory Focus로 전환
	/// </summary>
	private void HandlePutSelectAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int unitId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid put_select format. Expected: put_select:unitId");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] 넣기 대상 선택: unitId={unitId}");
#endif

		// 인벤토리 화면으로 전환 (현재 Unit Focus 위에 Push - 스택에서 targetUnitId 탐색)
		_textUISystem?.ShowInventory();
	}

	/// <summary>
	/// 아이템 장착: equip:itemId
	/// 같은 슬롯 키("장착:X")를 가진 아이템이 있으면 자동 해제 후 장착
	/// </summary>
	private void HandleEquipAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid equip format. Expected: equip:itemId");
			return;
		}

		var player = _playerSystem?.FindPlayerUnit();
		if (player == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleEquipAction: Player not found");
			return;
		}

		var itemSystem = _world.GetSystem("itemSystem") as ItemSystem;
		var inventorySystem = _world.GetSystem("inventorySystem") as InventorySystem;

		if (itemSystem == null || inventorySystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleEquipAction: Systems not found");
			return;
		}

		var item = itemSystem.FindItem(itemId);
		if (item == null)
		{
			GD.PrintErr($"[MetaActionHandler] HandleEquipAction: Item not found: {itemId}");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] 아이템 장착: itemId={itemId}, playerId={player.Id}");
#endif

		// 슬롯 충돌 확인 및 기존 장비 해제
		// 새 아이템의 슬롯 키("장착:X" 또는 "착용:X")와 같은 키를 가진 장착 아이템 해제
		var slotKeys = new List<string>();

		// 장비 슬롯 (장착:손 등) - 단일 슬롯
		var equipSlotKey = item.GetEquipPropKey("장착:");
		if (equipSlotKey != null)
			slotKeys.Add(equipSlotKey);

		// 의류 슬롯 (착용:상의, 착용:하의 등) - 복수 슬롯 가능
		var wearSlotKeys = item.GetAllEquipPropKeys("착용:");
		slotKeys.AddRange(wearSlotKeys);

		if (slotKeys.Count > 0)
		{
			var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);
			var itemsToUnequip = new List<int>();

			foreach (var equippedId in equippedItems)
			{
				var equippedItem = itemSystem.FindItem(equippedId);
				if (equippedItem?.EquipProps == null) continue;

				// 슬롯 키 중 하나라도 충돌하면 해제 대상
				foreach (var slotKey in slotKeys)
				{
					if (equippedItem.EquipProps.ContainsKey(slotKey))
					{
#if DEBUG_LOG
						GD.Print($"[MetaActionHandler] 슬롯 충돌 - 기존 장비 해제: {equippedId} (슬롯 키: {slotKey})");
#endif
						if (!itemsToUnequip.Contains(equippedId))
							itemsToUnequip.Add(equippedId);
						break;
					}
				}
			}

			// 충돌하는 모든 아이템 해제 (Python equipment.unequip_item 호출)
			var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
			foreach (var unequipId in itemsToUnequip)
			{
				try
				{
					scriptSystem.Eval($"import equipment; equipment.unequip_item({player.Id}, {unequipId})");
				}
				catch (Exception ex)
				{
					GD.PrintErr($"[MetaActionHandler] unequip error: {ex.Message}");
					inventorySystem.UnequipItemFromUnit(player.Id, unequipId);
				}
			}
		}

		// 새 아이템 장착 - Python equipment.equip_item() 호출
		var scriptSys = _world.GetSystem("scriptSystem") as ScriptSystem;
		try
		{
			scriptSys.Eval($"import equipment; equipment.equip_item({player.Id}, {itemId})");
		}
		catch (Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] equip error: {ex.Message}");
			inventorySystem.EquipItemOnUnit(player.Id, itemId);
		}

		// UI 갱신 (아이템 메뉴 닫고 인벤토리로 돌아가기)
		_textUISystem?.Pop();
	}

	/// <summary>
	/// 아이템 장착 해제: unequip:itemId
	/// </summary>
	private void HandleUnequipAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid unequip format. Expected: unequip:itemId");
			return;
		}

		var player = _playerSystem?.FindPlayerUnit();
		if (player == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleUnequipAction: Player not found");
			return;
		}

		var inventorySystem = _world.GetSystem("inventorySystem") as InventorySystem;
		if (inventorySystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleUnequipAction: InventorySystem not found");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] 아이템 장착 해제: itemId={itemId}, playerId={player.Id}");
#endif

		// Python equipment.unequip_item() 호출 (put ActionProp 재활성화)
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		try
		{
			scriptSystem.Eval($"import equipment; equipment.unequip_item({player.Id}, {itemId})");
		}
		catch (Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] unequip error: {ex.Message}");
			inventorySystem.UnequipItemFromUnit(player.Id, itemId);
		}

		// UI 갱신 (아이템 메뉴 닫고 인벤토리로 돌아가기)
		_textUISystem?.Pop();
	}

}
