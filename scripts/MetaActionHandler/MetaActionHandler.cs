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
///
/// Partial class 구조:
/// - MetaActionHandler.cs: 필드, 생성자, HandleAction 진입점
/// - MetaActionHandler.Dialog.cs: @ret, @proc, @finish, @next, @prev 핸들러
/// - MetaActionHandler.Navigation.cs: move, back, toggle, idle 핸들러
/// - MetaActionHandler.Item.cs: 아이템 관련 핸들러
/// - MetaActionHandler.Script.cs: call, ProcessScriptResult, 이벤트 처리
/// </summary>
public partial class MetaActionHandler
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
	/// 멀티페이지 다이얼로그 요청 (페이지 진행용)
	/// </summary>
	private PyDialogRequest _pendingDialogRequest;


	/// <summary>
	/// 이동 확인 다이얼로그 threshold (밀리초)
	/// 이 시간 이상 이동 시 확인 다이얼로그 표시
	/// int.MaxValue면 다이얼로그 없이 항상 즉시 이동
	/// </summary>
	private int _moveConfirmThresholdMillis = 60 * GameTime.MillisPerMinute;

	public MetaActionHandler(SE.World world, PlayerSystem playerSystem, TextUISystem textUISystem)
	{
		_world = world;
		_playerSystem = playerSystem;
		_textUISystem = textUISystem;
	}

	/// <summary>
	/// 외부에서 Generator와 DialogRequest 설정 (EventSystem에서 호출)
	/// </summary>
	public void SetPendingGenerator(PyGenerator generator, PyDialogRequest dialogRequest = null)
	{
		_pendingGenerator = generator;
		_pendingDialogRequest = dialogRequest;
	}

	/// <summary>
	/// 메타 액션 처리 진입점
	/// </summary>
	public void HandleAction(string metaString)
	{
		if (string.IsNullOrEmpty(metaString))
			return;

		// Animation Focus일 때 Mode 체크
		if (_textUISystem?.IsAnimationFocus == true)
		{
			var mode = _textUISystem.GetAnimlogMode();
			if (mode == Morld.AnimlogMode.Lock || mode == Morld.AnimlogMode.Block)
			{
				// Lock/Block 모드: 스킵만 허용, 다른 액션 무시
				_textUISystem.SkipAnimation();
				return;
			}
			// Normal 모드: 스킵 후 일반 액션도 처리
			_textUISystem.SkipAnimation();
			// 아래 일반 액션 처리 계속...
		}

		// @ret:값 - 다이얼로그 종료, yield에 값 반환 (레거시 호환)
		if (metaString.StartsWith("@ret:"))
		{
			HandleRetAction(metaString.Substring(5));  // "@ret:yes" → "yes"
			return;
		}

		// @finish - 다이얼로그 종료, result 파라미터 값 반환
		if (metaString == "@finish")
		{
			HandleFinishAction();
			return;
		}

		// @next - 다음 페이지로 이동 (autofill 전용)
		if (metaString == "@next")
		{
			HandleNextPageAction();
			return;
		}

		// @prev - 이전 페이지로 이동 (book 전용)
		if (metaString == "@prev")
		{
			HandlePrevPageAction();
			return;
		}

		// @proc:값 - proc 콜백 호출, 다이얼로그 유지
		if (metaString.StartsWith("@proc:"))
		{
			HandleProcAction(metaString.Substring(6));  // "@proc:next" → "next"
			return;
		}

		// MetaFlags suffix (%, #) 제거 — 렌더러용 플래그이므로 액션 처리에서는 불필요
		var cleanMeta = metaString.TrimEnd('%', '#');
		var parts = cleanMeta.Split(':');
		var action = parts[0];

		// 콘텐츠 변경 전 정리 작업
		// - 토글은 UI 상태만 변경하므로 로그 읽음 처리 제외
		// - script 계열은 대화 중이므로 로그 읽음 처리 제외
		// - look_unit은 조회 행위이며 이벤트(first_meet 등)가 끼어들 수 있으므로 제외
		bool markLogsAsRead = action != "toggle"
			&& action != "script"
			&& action != "look_unit"
			&& action != "tab";
		_textUISystem?.OnContentChange(markLogsAsRead);

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Meta clicked: {metaString}");
#endif

		switch (action)
		{
			case "move":
				// 앉은 상태에서는 이동 불가 (UI에서 grey out이지만 안전장치)
				var movePlayer = _playerSystem?.FindPlayerUnit();
				if (movePlayer != null && movePlayer.TraversalContext.Props.GetByType("seated_on").FirstOrDefault().Prop.IsValid)
					break;
				HandleMoveAction(parts, _moveConfirmThresholdMillis);
				break;
			case "idle":
				HandleIdleAction(parts);
				break;
			case "dungeon":
				HandleDungeonAction(parts);
				break;
			case "recruit":
				HandleRecruitAction(parts);
				break;
			case "wait":
				HandleWaitAction(parts);
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
			case "quest":
				HandleQuestAction();
				break;
			case "settings":
				HandleSettingsAction();
				break;
			case "drop":
				HandleDropAction(parts);
				break;
			case "drop_floor":
				HandleDropFloorAction(parts);
				break;
			case "look_unit":
				HandleLookUnitAction(parts);
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
			case "equip":
				HandleEquipAction(parts);
				break;
			case "unequip":
				HandleUnequipAction(parts);
				break;
			case "call":
				HandleCallAction(parts);
				break;
			case "map":
				HandleMapAction(parts);
				break;
			case "posture":
				HandlePostureAction(parts);
				break;
			case "stance":
				HandleStanceAction(parts);
				break;
			case "move_x":
				HandleMoveXAction(parts);
				break;
			case "tab":
				HandleTabAction(parts);
				break;
			default:
				GD.PrintErr($"[MetaActionHandler] Unknown action: {action}");
				break;
		}
	}

	/// <summary>
	/// 플레이어 이동 취소
	/// NPC 주도 이벤트 발동 시 호출하여 기존 위치 유지
	/// </summary>
	private void CancelPlayerMovement()
	{
		// 시간 진행 중단
		_playerSystem?.ClearPendingTime();

		// 플레이어 Job/이동 초기화 (Pi-World)
		var player = _playerSystem?.FindPlayerUnit();
		if (player != null)
		{
			player.JobList.Clear();
			player.CurrentMovement = null;
#if DEBUG_LOG
			GD.Print("[MetaActionHandler] CancelPlayerMovement: Player movement cancelled");
#endif
		}
	}

	/// <summary>
	/// 대기 중인 이벤트 및 ExcessTime 처리
	/// 다이얼로그가 표시되었거나 ExcessTime으로 인해 시간이 흘렀으면 true 반환
	/// </summary>
	/// <returns>이벤트/시간 처리됨 (UI 업데이트 불필요)</returns>
	private bool ProcessPendingEvents()
	{
		var eventSystem = _world.GetSystem("eventSystem") as EventSystem;
		if (eventSystem == null) return false;

		// ExcessTime 체크 (핸들러 처리 전에 확인)
		// 다이얼로그에서 시간이 경과했으면 남은 핸들러를 스킵해야 함
		var dialogTimeConsumed = eventSystem.FinalizeDialogTime();
		var excessTime = eventSystem.ConsumeExcessTime();

		if (excessTime > 0)
		{
			_playerSystem?.AddExcessTime(excessTime);
		}

		// 다이얼로그에서 시간이 소모되었으면:
		// 1. 대기 중인 핸들러 모두 제거 (C# 큐)
		// 2. 플레이어의 남은 행동(idle/이동) 취소
		if (dialogTimeConsumed > 0)
		{
			eventSystem.ClearPendingHandlers();
			_playerSystem?.CancelRemainingDuration();
			return true;
		}

		// GameEvent 처리 + C# 핸들러 큐 처리
		if (eventSystem.FlushEvents())
		{
			// 다이얼로그가 표시됨
			return true;
		}

		// C# 핸들러 큐에 남은 이벤트가 있으면 처리
		if (eventSystem.HasPendingHandlers())
		{
			if (eventSystem.ProcessNextHandler())
			{
				return true;
			}
		}

		return false;
	}

	/// <summary>
	/// 이벤트 처리 후 상황 화면으로 전환
	/// 시간이 흐르는 액션(이동, 휴식 등) 완료 후 호출
	/// </summary>
	private void ProcessEventsAndShowSituation()
	{
		if (!ProcessPendingEvents())
		{
			// 처리할 이벤트가 없으면 상황 화면 표시
			_textUISystem?.ShowSituation();
		}
	}

	/// <summary>
	/// 이벤트 처리 후 현재 화면 갱신 (스택 유지)
	/// Generator 기반 다이얼로그 완료 후 호출
	/// 남은 meet 이벤트가 있으면 처리하고, 없으면 현재 화면만 갱신
	/// 플레이어가 이동 중이었으면 이동 재개
	/// </summary>
	private void ProcessEventsAndUpdateDisplay()
	{
		if (!ProcessPendingEvents())
		{
			// 플레이어가 이동 중이면 이동 재개
			// 이동 재개 시 UI 업데이트 스킵 (도착 후 자동 업데이트됨)
			if (ResumePlayerMovementIfNeeded())
			{
				return;
			}

			// 처리할 이벤트가 없으면 현재 화면 갱신 (스택 유지)
			_textUISystem?.UpdateDisplay();
		}
	}

	/// <summary>
	/// 플레이어가 이동 중단된 상태면 이동 재개 (Pi-World)
	/// 다이얼로그 완료 후 호출
	/// </summary>
	/// <returns>이동 재개됨 여부 (true면 UI 업데이트 불필요)</returns>
	private bool ResumePlayerMovementIfNeeded()
	{
		var player = _playerSystem?.FindPlayerUnit();
		if (player == null) return false;

		// Pi-World: 이동 중이고 Job이 남아있으면 이동 재개
		if (player.CurrentMovement != null && player.CurrentJob != null)
		{
			// 남은 이동 시간 계산
			int remainingTime = player.CurrentMovement.RemainingTime;

			// Job의 남은 Duration도 고려 (여러 Gate를 거치는 경우)
			var job = player.CurrentJob;
			if (job.Duration > remainingTime)
			{
				remainingTime = job.Duration;
			}

			if (remainingTime > 0)
			{
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] Resuming player movement: {remainingTime}ms 남음");
#endif
				_playerSystem.RequestTimeAdvance(remainingTime, "이동 재개");
				return true;
			}
		}
		return false;
	}

	#region Legacy Python Queue Methods (향후 제거 예정)
	// 새로운 C# EventSystem._pendingHandlers 큐로 대체됨
	// Python _pending_meet_events 제거 후 이 메서드들도 제거

	/// <summary>
	/// [레거시] Python에 대기 중인 meet 이벤트가 있는지 확인
	/// </summary>
	private bool HasPendingMeetEvents(ScriptSystem scriptSystem)
	{
		try
		{
			var result = scriptSystem.Eval("has_pending_meet_events()");
			return result is SharpPy.PyBool pyBool && pyBool.Value;
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] has_pending_meet_events error: {ex.Message}");
			return false;
		}
	}

	/// <summary>
	/// [레거시] Python 큐에서 다음 meet 이벤트 처리
	/// </summary>
	private bool ProcessNextMeetEvent(ScriptSystem scriptSystem)
	{
		try
		{
			var playerId = _playerSystem?.PlayerId;
			if (playerId == null)
			{
				GD.PrintErr("[MetaActionHandler] ProcessNextMeetEvent: Player not found");
				return false;
			}
			var result = scriptSystem.Eval($"on_single_event(['on_meet', {playerId}])");

			if (result is SharpPy.PyNone || result == null)
			{
				return false;
			}

			if (result is SharpPy.PyGenerator generator)
			{
				var genResult = scriptSystem.ProcessGenerator(generator);
				if (genResult != null)
				{
					ProcessEventResultFromScript(genResult);
					return genResult.Type == "generator_dialog";
				}
			}

			return false;
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] ProcessNextMeetEvent error: {ex.Message}");
			return false;
		}
	}

	/// <summary>
	/// [레거시] 스크립트 결과를 이벤트로 처리
	/// </summary>
	private void ProcessEventResultFromScript(SE.ScriptResult result)
	{
		if (result == null) return;

		if (result.Type == "generator_dialog" && result is SE.GeneratorScriptResult genResult)
		{
			SetPendingGenerator(genResult.Generator, genResult.DialogRequest);

			if (_textUISystem != null && _textUISystem.IsStackEmpty())
			{
				_textUISystem.ShowSituation();
			}

			bool timeFlows = genResult.DialogRequest?.TimeFlows ?? false;
			_textUISystem?.PushDialog(genResult.DialogText, timeConsumed: 0, timeFlows: timeFlows);
		}
	}

	/// <summary>
	/// [레거시] Python의 대기 중인 meet 이벤트 모두 제거
	/// </summary>
	private void ClearPendingMeetEvents(ScriptSystem scriptSystem)
	{
		if (scriptSystem == null) return;

		try
		{
			scriptSystem.Eval("clear_pending_meet_events()");
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] clear_pending_meet_events error: {ex.Message}");
		}
	}

	#endregion
}
