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
	/// 이동 확인 다이얼로그 threshold (분)
	/// 이 시간 이상 이동 시 확인 다이얼로그 표시
	/// int.MaxValue면 다이얼로그 없이 항상 즉시 이동
	/// </summary>
	private int _moveConfirmThreshold = 60;

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
			case "call":
				HandleCallAction(parts);
				break;
			// TODO: sit, stand_up을 call: 패턴으로 전환 필요
			// case "sit":
			// case "stand_up":
			default:
				GD.PrintErr($"[MetaActionHandler] Unknown action: {action}");
				break;
		}
	}

	/// <summary>
	/// 대기 중인 이벤트 및 ExcessTime 처리
	/// 다이얼로그가 표시되었거나 ExcessTime으로 인해 시간이 흘렀으면 true 반환
	/// </summary>
	/// <returns>이벤트/시간 처리됨 (UI 업데이트 불필요)</returns>
	private bool ProcessPendingEvents()
	{
		// 남은 이벤트 처리 (다이얼로그 완료 후 다음 이벤트 실행)
		var eventSystem = _world.GetSystem("eventSystem") as EventSystem;
		if (eventSystem != null && eventSystem.FlushEvents())
		{
			// 다이얼로그가 표시됨
#if DEBUG_LOG
			GD.Print("[MetaActionHandler] ProcessPendingEvents: Next event triggered dialog");
#endif
			return true;
		}

		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;

		// ExcessTime 체크 (Python meet 이벤트 큐 처리 전에 확인)
		// 다이얼로그에서 시간이 경과했으면 남은 meet 이벤트를 스킵해야 함
		if (eventSystem != null)
		{
			eventSystem.FinalizeDialogTime();

			var excessTime = eventSystem.ConsumeExcessTime();
			if (excessTime > 0)
			{
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] ExcessTime={excessTime}, clearing pending meet events");
#endif
				_playerSystem?.AddExcessTime(excessTime);

				// ExcessTime > 0이면 대기 중인 meet 이벤트 모두 제거
				// (시간이 흘렀으므로 남은 만남 이벤트는 스킵)
				ClearPendingMeetEvents(scriptSystem);

				// ExcessTime이 있으면 _Process에서 시간 진행 후 UI 업데이트됨
				return true;
			}
		}

		// ExcessTime == 0일 때만 Python meet 이벤트 큐 확인
		if (scriptSystem != null && HasPendingMeetEvents(scriptSystem))
		{
			// Python 큐에 대기 중인 meet 이벤트가 있으면 다음 이벤트 처리
			if (ProcessNextMeetEvent(scriptSystem))
			{
#if DEBUG_LOG
				GD.Print("[MetaActionHandler] ProcessPendingEvents: Python meet event triggered dialog");
#endif
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
	/// </summary>
	private void ProcessEventsAndUpdateDisplay()
	{
		if (!ProcessPendingEvents())
		{
			// 처리할 이벤트가 없으면 현재 화면 갱신 (스택 유지)
			_textUISystem?.UpdateDisplay();
		}
	}

	/// <summary>
	/// Python에 대기 중인 meet 이벤트가 있는지 확인
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
	/// Python 큐에서 다음 meet 이벤트 처리
	/// </summary>
	/// <returns>다이얼로그가 표시되었으면 true</returns>
	private bool ProcessNextMeetEvent(ScriptSystem scriptSystem)
	{
		try
		{
			// 더미 on_meet 이벤트로 Python 호출 - 큐에서 다음 이벤트 반환
			// _pending_meet_events가 비어있지 않으면 큐에서 pop
			var playerId = _playerSystem?.PlayerId ?? 0;
			var result = scriptSystem.Eval($"on_single_event(['on_meet', {playerId}])");

			if (result is SharpPy.PyNone || result == null)
			{
				return false;
			}

			// Generator인 경우 Dialog 처리
			if (result is SharpPy.PyGenerator generator)
			{
#if DEBUG_LOG
				GD.Print("[MetaActionHandler] ProcessNextMeetEvent: Generator returned, processing...");
#endif
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
	/// 스크립트 결과를 이벤트로 처리 (EventSystem.ProcessEventResult와 유사)
	/// </summary>
	private void ProcessEventResultFromScript(SE.ScriptResult result)
	{
		if (result == null) return;

		if (result.Type == "generator_dialog" && result is SE.GeneratorScriptResult genResult)
		{
			// MetaActionHandler에 Generator와 DialogRequest 설정
			SetPendingGenerator(genResult.Generator, genResult.DialogRequest);

			// 다이얼로그 아래에 Situation이 있어야 Pop 후 정상 동작
			if (_textUISystem != null && _textUISystem.IsStackEmpty())
			{
				_textUISystem.ShowSituation();
			}

			// Dialog 표시
			_textUISystem?.PushDialog(genResult.DialogText);
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] ProcessEventResultFromScript: Dialog pushed");
#endif
		}
	}

	/// <summary>
	/// Python의 대기 중인 meet 이벤트 모두 제거
	/// </summary>
	private void ClearPendingMeetEvents(ScriptSystem scriptSystem)
	{
		if (scriptSystem == null) return;

		try
		{
			scriptSystem.Eval("clear_pending_meet_events()");
#if DEBUG_LOG
			GD.Print("[MetaActionHandler] Cleared pending meet events (ExcessTime > 0)");
#endif
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] clear_pending_meet_events error: {ex.Message}");
		}
	}
}
