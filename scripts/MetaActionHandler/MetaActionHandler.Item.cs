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
}
