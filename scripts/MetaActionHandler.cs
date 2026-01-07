#define DEBUG_LOG

using Godot;
using SE;
using Morld;
using SharpPy;
using System.Collections.Generic;
using System.Linq;

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
	/// YesNo 다이얼로그에서 Yes 클릭 시 실행할 pending 작업
	/// 다이얼로그 표시 시 설정, Yes 클릭 시 실행 후 null로 초기화
	/// </summary>
	private Action _pendingAction;

	/// <summary>
	/// MessageBox 다이얼로그 대기 중인 제너레이터
	/// 다이얼로그 결과를 generator.Send()로 전달하여 스크립트 재개
	/// </summary>
	private PyGenerator _pendingGenerator;

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
	/// 외부에서 Generator 설정 (EventSystem에서 호출)
	/// </summary>
	public void SetPendingGenerator(PyGenerator generator)
	{
		_pendingGenerator = generator;
	}

	/// <summary>
	/// 메타 액션 처리 진입점
	/// </summary>
	public void HandleAction(string metaString)
	{
		if (string.IsNullOrEmpty(metaString))
			return;

		// @ret:값 - 다이얼로그 종료, yield에 값 반환
		if (metaString.StartsWith("@ret:"))
		{
			HandleRetAction(metaString.Substring(5));  // "@ret:yes" → "yes"
			return;
		}

		// @proc:값 - generator에 값 전달, 다이얼로그 유지
		if (metaString.StartsWith("@proc:"))
		{
			HandleProcAction(metaString.Substring(6));  // "@proc:next" → "next"
			return;
		}

		var parts = metaString.Split(':');
		var action = parts[0];

		// 콘텐츠 변경 전 정리 작업
		// - 토글은 UI 상태만 변경하므로 로그 읽음 처리 제외
		// - script 계열은 대화 중이므로 로그 읽음 처리 제외
		bool markLogsAsRead = action != "toggle"
			&& action != "script";
		_textUISystem?.OnContentChange(markLogsAsRead);

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Meta clicked: {metaString}");
#endif

		switch (action)
		{
			case "move":
				HandleMoveAction(parts, _moveConfirmThreshold);
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
			case "sit":
				HandleSitAction(parts);
				break;
			case "stand_up":
				HandleStandUpAction();
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
	/// 이동 확인 다이얼로그 threshold (분)
	/// 이 시간 이상 이동 시 확인 다이얼로그 표시
	/// int.MaxValue면 다이얼로그 없이 항상 즉시 이동
	/// </summary>
	private int _moveConfirmThreshold = 60;

	/// <summary>
	/// 이동 액션 처리: move:regionId:localId 또는 confirm_move:regionId:localId
	/// </summary>
	/// <param name="parts">move:regionId:localId 또는 confirm_move:regionId:localId</param>
	/// <param name="thresholdMinutes">이 시간(분) 이상이면 확인 다이얼로그, 0이면 즉시 이동</param>
	private void HandleMoveAction(string[] parts, int thresholdMinutes)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid move format. Expected: move:regionId:localId");
			return;
		}

		if (!int.TryParse(parts[1], out int regionId) || !int.TryParse(parts[2], out int localId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid regionId or localId");
			return;
		}

		// threshold가 0이면 무한대로 처리 (다이얼로그 없이 즉시 이동)
		int effectiveThreshold = thresholdMinutes == 0 ? int.MaxValue : thresholdMinutes;
		ExecuteMoveWithConfirm(regionId, localId, effectiveThreshold);
	}

	/// <summary>
	/// 통합 이동 함수 - threshold 기반 확인 다이얼로그
	/// </summary>
	/// <param name="regionId">목적지 Region ID</param>
	/// <param name="localId">목적지 Location ID</param>
	/// <param name="thresholdMinutes">이 시간(분) 이상이면 확인 다이얼로그 표시</param>
	private void ExecuteMoveWithConfirm(int regionId, int localId, int thresholdMinutes)
	{
		// 이동 시간 계산
		int travelTime = _playerSystem?.CalculateTravelTime(regionId, localId) ?? -1;
		if (travelTime < 0)
		{
			_textUISystem?.ShowResult("이동할 수 없습니다.");
			return;
		}

		// threshold 이상이면 확인 다이얼로그
		if (travelTime >= thresholdMinutes)
		{
			// Python에서 메시지 가져오기 시도
			string message = GetMoveConfirmMessage(travelTime);
			if (string.IsNullOrEmpty(message))
			{
				// 기본 메시지 (Python 실패 시 fallback)
				message = FormatTravelTimeMessage(travelTime);
			}

			// Yes 클릭 시 실행할 작업 저장
			_pendingAction = () => _playerSystem?.RequestCommand($"이동:{regionId}:{localId}");

			// Dialog 형식으로 YesNo 표시
			var dialogText = $"{message}\n\n[url=@ret:yes]예[/url]  [url=@ret:no]아니오[/url]";
			_textUISystem?.PushDialog(dialogText, 0);
			return;
		}

		// threshold 미만이면 즉시 이동
		_playerSystem?.RequestCommand($"이동:{regionId}:{localId}");
	}

	/// <summary>
	/// Python에서 이동 확인 메시지 가져오기
	/// </summary>
	private string? GetMoveConfirmMessage(int travelTimeMinutes)
	{
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem == null) return null;

		try
		{
			var result = scriptSystem.CallFunctionEx(
				"ui_get_move_confirm_message",
				new string[] { travelTimeMinutes.ToString() },
				null
			);
			return result?.Message;
		}
		catch
		{
			return null;
		}
	}

	/// <summary>
	/// 이동 시간 포맷팅 (기본 fallback)
	/// </summary>
	private string FormatTravelTimeMessage(int travelTimeMinutes)
	{
		int hours = travelTimeMinutes / 60;
		int minutes = travelTimeMinutes % 60;
		string timeText = minutes > 0 ? $"{hours}시간 {minutes}분" : $"{hours}시간";
		return $"이동하는 데 {timeText}이 걸립니다. 이동하시겠습니까?";
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

		// sit@seatName 액션인 경우 HandleSitAction으로 위임
		// action:sit@seatName:unitId → sit:unitId:seatName
		if (actionType.StartsWith("sit@"))
		{
			var seatName = actionType.Substring(4);  // "sit@" 이후 부분
			var sitParts = new string[] { "sit", parts[2], seatName };
			HandleSitAction(sitParts);
			return;
		}

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

		var actionSystem = _world.GetSystem("actionSystem") as ActionSystem;
		var unitSystem = _world.GetSystem("unitSystem") as UnitSystem;

		if (actionSystem != null && unitSystem != null && _playerSystem != null)
		{
			var player = _playerSystem.GetPlayerUnit();
			var target = unitSystem.FindUnit(unitId);

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
	/// 앉기 액션 처리: sit:objectId:seatName
	/// 오브젝트의 특정 좌석에 앉기
	/// </summary>
	private void HandleSitAction(string[] parts)
	{
		if (parts.Length < 3 ||
			!int.TryParse(parts[1], out int objectId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid sit format. Expected: sit:objectId:seatName");
			return;
		}

		var seatName = parts[2];

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Sit action: objectId={objectId}, seatName={seatName}");
#endif

		var unitSystem = _world.GetSystem("unitSystem") as UnitSystem;
		if (unitSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] UnitSystem not found");
			return;
		}

		var player = _playerSystem?.GetPlayerUnit();
		if (player == null)
		{
			GD.PrintErr("[MetaActionHandler] Player not found");
			return;
		}

		var obj = unitSystem.FindUnit(objectId);
		if (obj == null)
		{
			_textUISystem?.ShowResult("앉을 수 없습니다: 오브젝트를 찾을 수 없습니다.");
			return;
		}

		// 1. 이미 앉아있는지 확인
		var seatedOn = player.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
		if (seatedOn.Prop.IsValid)
		{
			_textUISystem?.ShowResult("앉을 수 없습니다: 이미 앉아있습니다.");
			return;
		}

		// 2. 좌석이 비어있는지 확인
		var seatPropName = $"seated_by:{seatName}";
		int seatOccupant = obj.TraversalContext.Props.Get(seatPropName);
		if (seatOccupant != -1)
		{
			_textUISystem?.ShowResult("앉을 수 없습니다: 좌석이 이미 차있습니다.");
			return;
		}

		// 3. 양방향 Prop 설정
		player.TraversalContext.Props.Set($"seated_on:{objectId}", seatName.GetHashCode());
		obj.TraversalContext.Props.Set(seatPropName, player.Id);

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Sit success: player={player.Id} sat on object={objectId}, seat={seatName}");
#endif

		// 앉기 성공 - 화면 갱신
		_textUISystem?.Pop();  // Focus 닫기
		RequestUpdateSituation();
	}

	/// <summary>
	/// 일어나기 액션 처리: stand_up
	/// 현재 앉아있는 상태에서 일어나기
	/// </summary>
	private void HandleStandUpAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] Stand up action");
#endif

		var unitSystem = _world.GetSystem("unitSystem") as UnitSystem;
		if (unitSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] UnitSystem not found");
			return;
		}

		var player = _playerSystem?.GetPlayerUnit();
		if (player == null)
		{
			GD.PrintErr("[MetaActionHandler] Player not found");
			return;
		}

		// 1. seated_on prop 확인
		var seatedOn = player.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
		if (!seatedOn.Prop.IsValid)
		{
			_textUISystem?.ShowResult("일어날 수 없습니다: 앉아있지 않습니다.");
			return;
		}

		// 2. seated_on:{objectId}에서 objectId 추출
		var propName = seatedOn.Prop.Name;  // "seated_on:123"
		var colonIdx = propName.IndexOf(':');
		if (colonIdx < 0 || !int.TryParse(propName.Substring(colonIdx + 1), out int objectId))
		{
			GD.PrintErr($"[MetaActionHandler] Invalid seated_on prop format: {propName}");
			return;
		}

		// 3. 오브젝트의 seated_by prop 해제
		var obj = unitSystem.FindUnit(objectId);
		if (obj != null)
		{
			// seated_by에서 이 플레이어를 찾아서 해제
			var seatedByProps = obj.TraversalContext.Props.GetByType("seated_by");
			foreach (var sbProp in seatedByProps)
			{
				if (sbProp.Value == player.Id)
				{
					obj.TraversalContext.Props.Set(sbProp.Prop.Name, -1);
					break;
				}
			}
		}

		// 4. 플레이어의 seated_on prop 제거
		player.TraversalContext.Props.Remove(seatedOn.Prop);

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Stand up success: player={player.Id}");
#endif

		// 일어나기 성공 - 화면 갱신
		RequestUpdateSituation();
	}

	/// <summary>
	/// @ret:값 처리 - 다이얼로그 종료, yield에 값 반환
	/// pendingGenerator가 있으면 generator 재개, 없으면 pendingAction 처리 (yes/no)
	/// </summary>
	private void HandleRetAction(string value)
	{
#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] @ret: action with value: {value}");
#endif

		// 다이얼로그가 열려있는지 확인
		if (_textUISystem?.CurrentFocus?.Type != FocusType.Dialog)
		{
			GD.PrintErr("[MetaActionHandler] @ret: called but no dialog is open - this is a bug!");
			return;
		}

		// Case 1: pendingGenerator가 있으면 generator 재개
		if (_pendingGenerator != null)
		{
			var generator = _pendingGenerator;
			_pendingGenerator = null;

			// 다이얼로그 Pop
			_textUISystem?.Pop();

			// generator에 값 전달하고 계속 실행
			var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
			if (scriptSystem != null)
			{
				var nextResult = scriptSystem.ResumeGenerator(generator, value);
				ProcessScriptResult(nextResult, scriptSystem);
			}

			// generator가 완료되면 상황 업데이트
			if (_pendingGenerator == null)
			{
				RequestUpdateSituation();
			}
			return;
		}

		// Case 2: pendingAction이 있으면 yes/no 처리 (이동 확인 등)
		if (_pendingAction != null)
		{
			var action = _pendingAction;
			_pendingAction = null;

			// 다이얼로그 Pop
			_textUISystem?.Pop();

			// yes면 액션 실행, no면 취소
			if (value == "yes")
			{
				action.Invoke();
			}

			RequestUpdateSituation();
			return;
		}

		// Case 3: 둘 다 없으면 단순 다이얼로그 종료
		_textUISystem?.Pop();
		RequestUpdateSituation();
	}

	/// <summary>
	/// @proc:값 처리 - generator에 값 전달, 다이얼로그 유지
	/// </summary>
	private void HandleProcAction(string value)
	{
#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] @proc: action with value: {value}");
#endif

		// pendingGenerator가 없으면 에러
		if (_pendingGenerator == null)
		{
			GD.PrintErr("[MetaActionHandler] @proc: called without pending generator - this is a bug!");
			return;
		}

		// 다이얼로그가 열려있는지 확인
		if (_textUISystem?.CurrentFocus?.Type != FocusType.Dialog)
		{
			GD.PrintErr("[MetaActionHandler] @proc: called but no dialog is open - this is a bug!");
			return;
		}

		var generator = _pendingGenerator;
		_pendingGenerator = null;  // 일시적으로 null (ResumeGenerator에서 다시 설정됨)

		// generator에 값 전달하고 계속 실행 (Pop 안함 - 다이얼로그 유지)
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem != null)
		{
			var nextResult = scriptSystem.ResumeGenerator(generator, value);
			ProcessScriptResult(nextResult, scriptSystem);
		}
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

		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
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

		ProcessScriptResult(result, scriptSystem);
	}

	/// <summary>
	/// ScriptResult 처리 (HandleScriptAction과 ResumeGenerator에서 공통 사용)
	/// </summary>
	private void ProcessScriptResult(SE.ScriptResult result, ScriptSystem scriptSystem)
	{
		if (result == null)
		{
			return;
		}

		switch (result.Type)
		{
			case "generator_dialog":
				// 제너레이터가 Dialog를 yield한 경우 (새 통합 API)
				if (result is SE.GeneratorScriptResult dialogResult)
				{
					_pendingGenerator = dialogResult.Generator;

					// Win32 DialogBox 스타일: Push → Update → Pop
					// 현재 다이얼로그가 열려있으면 텍스트만 갱신, 없으면 새로 Push
					if (_textUISystem?.CurrentFocus?.Type == FocusType.Dialog)
					{
						_textUISystem.UpdateDialogText(dialogResult.DialogText);
#if DEBUG_LOG
						GD.Print($"[MetaActionHandler] Dialog update: {dialogResult.DialogText.Substring(0, System.Math.Min(50, dialogResult.DialogText.Length))}...");
#endif
					}
					else
					{
						_textUISystem?.PushDialog(dialogResult.DialogText);
#if DEBUG_LOG
						GD.Print($"[MetaActionHandler] Dialog push: {dialogResult.DialogText.Substring(0, System.Math.Min(50, dialogResult.DialogText.Length))}...");
#endif
					}
				}
				break;

			case "monologue":
				// 레거시 monologue 타입 → Dialog로 변환
				if (result is SE.MonologueScriptResult monoResult)
				{
					// 페이지들을 하나의 Dialog 텍스트로 결합 (첫 페이지만 표시, 나머지는 큐)
					for (int i = 0; i < monoResult.Pages.Count; i++)
					{
						var page = monoResult.Pages[i];
						var isLast = i == monoResult.Pages.Count - 1;
						var timeForPage = isLast ? monoResult.TimeConsumed : 0;

						// 마지막 페이지가 아니면 [다음] 버튼, 마지막이면 버튼 타입에 따라
						string dialogText;
						if (!isLast)
						{
							dialogText = page + "\n\n[url=@ret:next]다음[/url]";
						}
						else
						{
							// 마지막 페이지 - button_type에 따른 버튼
							// none_on_last인 경우 버튼 없음 (script URL 사용)
							if (monoResult.ButtonType == "none_on_last" || monoResult.ButtonType == "none")
							{
								dialogText = page;
							}
							else if (monoResult.ButtonType == "yesno")
							{
								dialogText = page + "\n\n[url=@ret:yes]예[/url]  [url=@ret:no]아니오[/url]";
							}
							else
							{
								dialogText = page + "\n\n[url=@ret:ok]확인[/url]";
							}
						}

						if (i == 0)
						{
							_textUISystem?.PushDialog(dialogText, timeForPage);
						}
						else
						{
							// 큐에 추가 (PushDialog가 내부적으로 처리)
							_textUISystem?.PushDialog(dialogText, timeForPage);
						}
					}
#if DEBUG_LOG
					GD.Print($"[MetaActionHandler] Script result: monologue → dialog ({monoResult.Pages.Count} pages queued)");
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
	/// 대기 중인 제너레이터에 결과를 전달하고 계속 실행
	/// </summary>
	private void ResumeGeneratorWithResult(PyGenerator generator, string result)
	{
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] ScriptSystem not found for generator resume");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Resuming generator with result: {result}");
#endif

		var nextResult = scriptSystem.ResumeGenerator(generator, result);
		ProcessScriptResult(nextResult, scriptSystem);
	}
}
