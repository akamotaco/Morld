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
				HandleBackInventoryAction();
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
				HandleBackUnitAction();
				break;
			case "put_select":
				HandlePutSelectAction(parts);
				break;
			case "script":
				HandleScriptAction(parts);
				break;
			case "monologue_next":
				HandleMonologueNextAction();
				break;
			case "monologue_done":
				HandleMonologueDoneAction(parts);
				break;
			case "monologue_yes":
				HandleMonologueYesAction();
				break;
			case "monologue_no":
				HandleMonologueNoAction();
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
	/// 아이템 버리기 처리 (레거시 - 현재 사용 안함)
	/// 바닥에 버리기는 put:바닥unitId:itemId 로 처리됨
	/// </summary>
	private void HandleDropAction(string[] parts)
	{
		GD.PrintErr("[MetaActionHandler] drop action is deprecated. Use put:unitId:itemId instead.");
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

		_textUISystem?.ShowUnitLook(unitId);
	}

	/// <summary>
	/// 아이템 가져오기 처리: take:unitId:itemId
	/// 데이터 변경 → PopIfInvalid (아이템 0개면 Pop, 아니면 UpdateDisplay)
	/// </summary>
	private void HandleTakeAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int unitId) || !int.TryParse(parts[2], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid take format");
			return;
		}

		_playerSystem?.TakeFromUnit(unitId, itemId);
		// 로그는 InventorySystem.OnInventoryChanged 콜백에서 자동 생성

		_textUISystem?.PopIfInvalid();
	}

	/// <summary>
	/// 유닛에 아이템 넣기 처리: put:unitId:itemId
	/// 데이터 변경 → PopIfInvalid (아이템 메뉴에서 아이템 0개면 Pop)
	/// </summary>
	private void HandlePutAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int unitId) || !int.TryParse(parts[2], out int itemId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid put format");
			return;
		}

		_playerSystem?.PutToUnit(unitId, itemId);
		// 로그는 InventorySystem.OnInventoryChanged 콜백에서 자동 생성

		_textUISystem?.PopIfInvalid();
	}

	/// <summary>
	/// 유닛 행동 처리: action:actionType:unitId
	/// script 액션인 경우: action:script:functionName:displayName[:args...]
	/// </summary>
	private void HandleUnitAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid action format. Expected: action:actionType:unitId");
			return;
		}

		var actionType = parts[1];

		// script 액션인 경우 HandleScriptAction으로 위임
		// action:script:functionName:displayName[:args...] → script:functionName[:args...]
		if (actionType == "script")
		{
			// parts[0]="action", parts[1]="script", parts[2]=functionName, parts[3]=displayName, parts[4...]=args
			// displayName은 표시용이므로 스킵하고 functionName과 args만 전달
			var scriptParts = new string[parts.Length - 2];  // "script", functionName, args...
			scriptParts[0] = "script";
			scriptParts[1] = parts[2];  // functionName
			// displayName(parts[3]) 스킵하고 나머지 args 복사
			for (int i = 4; i < parts.Length; i++)
			{
				scriptParts[i - 2] = parts[i];
			}
			HandleScriptAction(scriptParts);
			return;
		}

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

		_textUISystem?.ShowItemMenu(itemId, "inventory");
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

		// 인벤토리 화면으로 전환 (현재 Unit Focus 위에 Push)
		_textUISystem?.ShowInventory();
	}

	/// <summary>
	/// Python 스크립트 함수 호출: script:functionName:arg1:arg2:...
	/// 현재 Focus의 UnitId를 context로 자동 전달
	/// </summary>
	private void HandleScriptAction(string[] parts)
	{
		if (parts.Length < 2)
		{
			GD.PrintErr("[MetaActionHandler] Invalid script format. Expected: script:functionName[:arg1:arg2:...]");
			return;
		}

		var functionName = parts[1];
		var args = parts.Length > 2
			? parts[2..]  // C# 8.0 range operator
			: System.Array.Empty<string>();

		// 현재 Focus에서 context 정보 추출
		var currentFocus = _textUISystem?.CurrentFocus;
		int? contextUnitId = currentFocus?.UnitId;

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Script call: {functionName}({string.Join(", ", args)}) [context unitId={contextUnitId?.ToString() ?? "null"}]");
#endif

		var scriptSystem = _world.FindSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] ScriptSystem not found");
			return;
		}

		var result = scriptSystem.CallFunctionEx(functionName, args, contextUnitId);

		// 결과 타입에 따른 처리
		if (result == null)
		{
			return;
		}

		switch (result.Type)
		{
			case "monologue":
				if (result is SE.MonologueScriptResult monoResult)
				{
					// 모놀로그 표시 (스택에 Push - 거절 시 이전 화면으로 돌아갈 수 있도록)
					_textUISystem?.ShowMonologue(monoResult.Pages, monoResult.TimeConsumed, monoResult.ButtonType, monoResult.YesCallback, monoResult.NoCallback);
#if DEBUG_LOG
					GD.Print($"[MetaActionHandler] Script result: monologue ({monoResult.Pages.Count} pages, button={monoResult.ButtonType}, yes={monoResult.YesCallback}, no={monoResult.NoCallback})");
#endif
				}
				break;

			case "update":
				// 현재 모놀로그 내용만 교체 (Push 없이 in-place 갱신)
				if (result is SE.MonologueScriptResult updateResult)
				{
					_textUISystem?.UpdateMonologueContent(updateResult.Pages, updateResult.ButtonType);
#if DEBUG_LOG
					GD.Print($"[MetaActionHandler] Script result: update ({updateResult.Pages.Count} pages, button={updateResult.ButtonType})");
#endif
				}
				break;

			case "message":
				if (!string.IsNullOrEmpty(result.Message))
				{
					_textUISystem?.ShowResult(result.Message);
				}
				break;

			case "error":
				GD.PrintErr($"[MetaActionHandler] Script error: {result.Message}");
				_textUISystem?.ShowResult($"스크립트 오류: {result.Message}");
				break;

			default:
				if (!string.IsNullOrEmpty(result.Message))
				{
					_textUISystem?.ShowResult(result.Message);
				}
				break;
		}
	}

	/// <summary>
	/// 모놀로그 다음 페이지: monologue_next
	/// </summary>
	private void HandleMonologueNextAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] Monologue next page");
#endif
		_textUISystem?.MonologueNextPage();
	}

	/// <summary>
	/// 모놀로그 완료: monologue_done
	/// </summary>
	private void HandleMonologueDoneAction(string[] parts)
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] Monologue done");
#endif

		var timeConsumed = _textUISystem?.MonologueDone() ?? 0;

		if (timeConsumed > 0)
		{
			_playerSystem?.RequestTimeAdvance(timeConsumed, "모놀로그");
		}

		// 모놀로그가 끝나면 상황 업데이트
		RequestUpdateSituation();
	}

	/// <summary>
	/// 모놀로그 승낙: monologue_yes
	/// Focus에 저장된 YesCallback 스크립트 호출
	/// </summary>
	private void HandleMonologueYesAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] Monologue yes");
#endif

		var currentFocus = _textUISystem?.CurrentFocus;
		if (currentFocus?.YesCallback == null)
		{
			// 콜백이 없으면 단순 Pop
			_textUISystem?.Pop();
			RequestUpdateSituation();
			return;
		}

		// 승낙 시: 현재 YesNo 다이얼로그 Pop 후 콜백 실행
		// (콜백 결과가 새 모놀로그면 그 위에 Push됨)
		_textUISystem?.Pop();

		// 콜백 파싱: "함수명:인자1:인자2" 형식 → "script:함수명:인자1:인자2" 형식으로 변환
		var callbackParts = currentFocus.YesCallback.Split(':');
		var parts = new string[callbackParts.Length + 1];
		parts[0] = "script";
		callbackParts.CopyTo(parts, 1);
		HandleScriptAction(parts);
	}

	/// <summary>
	/// 모놀로그 거절: monologue_no
	/// Focus에 저장된 NoCallback 스크립트 호출 또는 단순 Pop
	/// </summary>
	private void HandleMonologueNoAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] Monologue no");
#endif

		var currentFocus = _textUISystem?.CurrentFocus;
		if (currentFocus?.NoCallback == null)
		{
			// 콜백이 없으면 현재 YesNo 다이얼로그만 Pop (이전 선택 화면으로)
			_textUISystem?.Pop();
			return;
		}

		// 거절 시: 현재 YesNo 다이얼로그 Pop 후 콜백 실행
		_textUISystem?.Pop();

		// 콜백 파싱: "함수명:인자1:인자2" 형식 → "script:함수명:인자1:인자2" 형식으로 변환
		var callbackParts = currentFocus.NoCallback.Split(':');
		var parts = new string[callbackParts.Length + 1];
		parts[0] = "script";
		callbackParts.CopyTo(parts, 1);
		HandleScriptAction(parts);
	}
}
