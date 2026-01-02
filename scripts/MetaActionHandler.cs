#define DEBUG_LOG

using Godot;
using SE;
using Morld;
using System.Collections.Generic;

/// <summary>
/// BBCode 메타 액션 핸들러
/// URL 클릭 시 발생하는 모든 액션을 처리
/// TextUISystem을 통해 화면 관리
/// </summary>
public class MetaActionHandler
{
	private readonly SE.World _world;
	private readonly PlayerSystem _playerSystem;
	private readonly TextUISystem _textUISystem;

	/// <summary>
	/// UI 텍스트 업데이트 요청 델리게이트
	/// </summary>
	public delegate void UpdateSituationHandler();
	public event UpdateSituationHandler OnUpdateSituation;

	public MetaActionHandler(SE.World world, PlayerSystem playerSystem, TextUISystem textUISystem)
	{
		_world = world;
		_playerSystem = playerSystem;
		_textUISystem = textUISystem;
	}

	/// <summary>
	/// 메타 액션 처리 진입점
	/// </summary>
	public void HandleAction(string metaString)
	{
		if (string.IsNullOrEmpty(metaString))
			return;

		var parts = metaString.Split(':');
		var action = parts[0];

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Meta clicked: {metaString}");
#endif

		switch (action)
		{
			case "move":
				HandleMoveAction(parts);
				break;
			case "idle":
				HandleIdleAction(parts);
				break;
			case "back":
			case "confirm":
			case "done":
				HandleBackAction();
				break;
			case "toggle":
				HandleToggleAction(parts);
				break;
			case "inventory":
				HandleInventoryAction();
				break;
			case "drop":
				HandleDropAction(parts);
				break;
			case "look_unit":
				HandleLookUnitAction(parts);
				break;
			case "take":
				HandleTakeAction(parts);
				break;
			case "put":
				HandlePutAction(parts);
				break;
			case "action":
				HandleUnitAction(parts);
				break;
			case "item_ground_menu":
				HandleItemGroundMenuAction(parts);
				break;
			case "item_inv_menu":
				HandleItemInvMenuAction(parts);
				break;
			case "back_inventory":
				HandleInventoryAction();
				break;
			case "item_use":
				HandleItemUseAction(parts);
				break;
			case "item_combine":
				HandleItemCombineAction(parts);
				break;
			case "item_unit_menu":
				HandleItemUnitMenuAction(parts);
				break;
			case "back_unit":
				HandleBackUnitAction(parts);
				break;
			default:
				GD.PrintErr($"[MetaActionHandler] Unknown action: {action}");
				break;
		}
	}

	/// <summary>
	/// 상황 텍스트 업데이트 요청
	/// </summary>
	private void RequestUpdateSituation()
	{
		OnUpdateSituation?.Invoke();
	}

	/// <summary>
	/// 이동 액션 처리: move:regionId:localId
	/// </summary>
	private void HandleMoveAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid move format. Expected: move:regionId:localId");
			return;
		}

		_playerSystem?.RequestCommand($"이동:{parts[1]}:{parts[2]}");
	}

	/// <summary>
	/// 휴식 액션 처리: idle:minutes
	/// </summary>
	private void HandleIdleAction(string[] parts)
	{
		if (parts.Length >= 2)
		{
			_playerSystem?.RequestCommand($"휴식:{parts[1]}");
		}
		else
		{
			GD.PrintErr("[MetaActionHandler] Invalid idle format. Expected: idle:minutes");
		}
	}

	/// <summary>
	/// 뒤로 가기 처리 (back, confirm, done)
	/// </summary>
	private void HandleBackAction()
	{
		_textUISystem?.Pop();
	}

	/// <summary>
	/// 토글 처리: toggle:toggleId
	/// </summary>
	private void HandleToggleAction(string[] parts)
	{
		if (parts.Length < 2)
		{
			GD.PrintErr("[MetaActionHandler] Invalid toggle format. Expected: toggle:toggleId");
			return;
		}

		_textUISystem?.ToggleExpand(parts[1]);
	}

	/// <summary>
	/// 인벤토리 확인 처리
	/// </summary>
	private void HandleInventoryAction()
	{
		_textUISystem?.ShowInventory();
	}

	/// <summary>
	/// 아이템 놓기 처리: drop:itemId
	/// </summary>
	private void HandleDropAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid drop format. Expected: drop:itemId");
			return;
		}

		_playerSystem?.DropItem(itemId);
		RequestUpdateSituation();
	}

	/// <summary>
	/// 유닛 살펴보기 처리: look_unit:unitId
	/// </summary>
	private void HandleLookUnitAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int unitId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid look_unit format. Expected: look_unit:unitId");
			return;
		}

		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _textUISystem != null)
		{
			_textUISystem.ShowUnitLook(unitLook);
		}
	}

	/// <summary>
	/// 아이템 가져오기 처리: take:ground:itemId 또는 take:unitId:itemId
	/// </summary>
	private void HandleTakeAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid take format. Expected: take:ground:itemId or take:unitId:itemId");
			return;
		}

		// 바닥에서 줍기: take:ground:itemId
		if (parts[1] == "ground")
		{
			if (!int.TryParse(parts[2], out int itemId))
			{
				GD.PrintErr("[MetaActionHandler] Invalid take:ground format. Expected: take:ground:itemId");
				return;
			}
			_playerSystem?.PickupItem(itemId);
			RequestUpdateSituation();
			return;
		}

		// 유닛에서 가져오기: take:unitId:itemId
		if (!int.TryParse(parts[1], out int unitId) || !int.TryParse(parts[2], out int itemId2))
		{
			GD.PrintErr("[MetaActionHandler] Invalid take format. Expected: take:unitId:itemId");
			return;
		}

		_playerSystem?.TakeFromUnit(unitId, itemId2);

		// 유닛 살펴보기 화면 새로고침
		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _textUISystem != null)
		{
			_textUISystem.ShowUnitLook(unitLook);
		}
	}

	/// <summary>
	/// 유닛에 아이템 넣기 처리: put:unitId:itemId
	/// </summary>
	private void HandlePutAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int unitId) || !int.TryParse(parts[2], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid put format. Expected: put:unitId:itemId");
			return;
		}

		_playerSystem?.PutToUnit(unitId, itemId);

		// 유닛 살펴보기 화면 새로고침
		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _textUISystem != null)
		{
			_textUISystem.ShowUnitLook(unitLook);
		}
	}

	/// <summary>
	/// 유닛 행동 처리: action:actionType:unitId
	/// </summary>
	private void HandleUnitAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid action format. Expected: action:actionType:unitId");
			return;
		}

		var actionType = parts[1];

		if (!int.TryParse(parts[2], out int unitId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid unitId in action");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] 유닛 행동: unitId={unitId}, type={actionType}");
#endif

		var actionSystem = _world.FindSystem("actionSystem") as ActionSystem;
		var unitSystem = _world.FindSystem("unitSystem") as UnitSystem;

		if (actionSystem != null && unitSystem != null && _playerSystem != null)
		{
			var player = _playerSystem.GetPlayerUnit();
			var target = unitSystem.GetUnit(unitId);

			if (player != null && target != null)
			{
				var result = actionSystem.ApplyAction(player, actionType, new List<Unit> { target });

				_textUISystem?.ShowResult(result.Message);

				if (result.TimeConsumed > 0)
				{
					_playerSystem.RequestTimeAdvance(result.TimeConsumed, actionType);
				}
			}
		}
	}

	/// <summary>
	/// 바닥 아이템 메뉴 표시: item_ground_menu:itemId:count
	/// </summary>
	private void HandleItemGroundMenuAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int itemId) || !int.TryParse(parts[2], out int count))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_ground_menu format. Expected: item_ground_menu:itemId:count");
			return;
		}

		_textUISystem?.ShowItemMenu(itemId, count, "ground");
	}

	/// <summary>
	/// 인벤토리 아이템 메뉴 표시: item_inv_menu:itemId:count
	/// </summary>
	private void HandleItemInvMenuAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int itemId) || !int.TryParse(parts[2], out int count))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_inv_menu format. Expected: item_inv_menu:itemId:count");
			return;
		}

		_textUISystem?.ShowItemMenu(itemId, count, "inventory");
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
	/// 오브젝트 인벤토리 아이템 메뉴 표시: item_unit_menu:unitId:itemId:count
	/// </summary>
	private void HandleItemUnitMenuAction(string[] parts)
	{
		if (parts.Length < 4 ||
			!int.TryParse(parts[1], out int unitId) ||
			!int.TryParse(parts[2], out int itemId) ||
			!int.TryParse(parts[3], out int count))
		{
			GD.PrintErr("[MetaActionHandler] Invalid item_unit_menu format. Expected: item_unit_menu:unitId:itemId:count");
			return;
		}

		_textUISystem?.ShowItemMenu(itemId, count, "container");
	}

	/// <summary>
	/// 유닛 화면으로 돌아가기: back_unit:unitId
	/// </summary>
	private void HandleBackUnitAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int unitId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid back_unit format. Expected: back_unit:unitId");
			return;
		}

		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _textUISystem != null)
		{
			_textUISystem.ShowUnitLook(unitLook);
		}
	}
}
