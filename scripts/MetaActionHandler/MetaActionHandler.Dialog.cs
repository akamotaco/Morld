#define DEBUG_LOG

using Godot;
using SE;
using Morld;
using SharpPy;

/// <summary>
/// MetaActionHandler - Dialog 핸들러
/// @ret, @proc, @finish, @next, @prev 처리
/// </summary>
public partial class MetaActionHandler
{
	/// <summary>
	/// @ret:값 처리 - 다이얼로그 종료, yield에 값 반환
	/// pendingGenerator가 있으면 generator 재개, 없으면 pendingAction 처리 (yes/no)
	/// 멀티페이지인 경우 다음 페이지로 이동하거나, 마지막 페이지면 ReturnValue로 재개
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
		// _pendingGenerator 또는 TextUISystem의 PendingDialogGenerator 확인 (Animlog에서 전환된 경우)
		var activeGenerator = _pendingGenerator ?? _textUISystem?.PendingDialogGenerator;
		var activeDialogRequest = _pendingDialogRequest ?? _textUISystem?.PendingDialogRequest;

		if (activeGenerator != null)
		{
			// 멀티페이지 처리: 다음 페이지가 있으면 이동
			if (activeDialogRequest != null && activeDialogRequest.HasNextPage)
			{
				activeDialogRequest.MoveToNextPage();
				var nextPageText = activeDialogRequest.Text;
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] Multi-page dialog: moving to page {activeDialogRequest.CurrentPageIndex + 1}/{activeDialogRequest.Pages.Count}");
#endif
				_textUISystem?.UpdateDialogText(nextPageText);
				return;  // generator는 재개하지 않음, 다이얼로그 유지
			}

			// 마지막 페이지 완료: ReturnValue가 있으면 그 값으로, 없으면 클릭한 값으로 재개
			var generator = activeGenerator;
			_pendingGenerator = null;
			_pendingDialogRequest = null;
			_textUISystem?.ClearPendingDialog();  // TextUISystem 쪽도 클리어

			// 최종 반환값 결정
			string finalValue = activeDialogRequest?.ReturnValue ?? value;

			// 다이얼로그 Pop
			_textUISystem?.Pop();

			// generator에 값 전달하고 계속 실행
			// processCompletion=true: generator 완료 시 PopIfInvalid 및 이벤트 처리 수행
			var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
			if (scriptSystem != null)
			{
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] Resuming generator with final value: {finalValue}");
#endif
				var nextResult = scriptSystem.ResumeGenerator(generator, finalValue);
				ProcessScriptResult(nextResult, scriptSystem, processCompletion: true);
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

			// yes면 액션 실행 후 이벤트 처리 및 상황 화면으로 전환 (시간이 흐름)
			// no면 취소이므로 현재 화면만 갱신 (스택 유지)
			if (value == "yes")
			{
				action.Invoke();
				ProcessEventsAndShowSituation();
			}
			else
			{
				_textUISystem?.UpdateDisplay();
			}
			return;
		}

		// Case 3: 둘 다 없으면 단순 다이얼로그 종료 (스택 유지)
		// meet 이벤트 핸들러일 수 있으므로 남은 이벤트 처리
		_textUISystem?.Pop();
		ProcessEventsAndUpdateDisplay();
	}

	/// <summary>
	/// @proc:값 처리 - proc 콜백 호출
	/// proc 콜백 반환값:
	///   - str: 텍스트 업데이트, 다이얼로그 유지
	///   - True: 다이얼로그 종료 (result 반환)
	///   - None/False: 변경 없음, 다이얼로그 유지
	/// </summary>
	private void HandleProcAction(string value)
	{
#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] @proc: action with value: {value}");
#endif

		// _pendingGenerator 또는 TextUISystem의 PendingDialogGenerator 확인 (Animlog에서 전환된 경우)
		var activeGenerator = _pendingGenerator ?? _textUISystem?.PendingDialogGenerator;
		var activeDialogRequest = _pendingDialogRequest ?? _textUISystem?.PendingDialogRequest;

		// pendingGenerator가 없으면 에러
		if (activeGenerator == null)
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

		// proc 콜백이 있으면 호출
		if (activeDialogRequest?.ProcCallback != null)
		{
			var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
			if (scriptSystem != null)
			{
				var (newText, shouldFinish) = scriptSystem.CallProcCallback(activeDialogRequest.ProcCallback, value);

				// proc 콜백이 True를 반환하면 다이얼로그 종료
				if (shouldFinish)
				{
#if DEBUG_LOG
					GD.Print("[MetaActionHandler] proc callback returned True, finishing dialog");
#endif
					// @finish와 동일한 처리
					var generator = activeGenerator;
					_pendingGenerator = null;
					_pendingDialogRequest = null;
					_textUISystem?.ClearPendingDialog();  // TextUISystem 쪽도 클리어

					_textUISystem?.Pop();

					// ResultObject가 있으면 그것을, 없으면 None 반환
					// 주의: activeDialogRequest?.ResultObject가 null일 수 있으므로 별도 처리 필요
					PyObject resultValue = activeDialogRequest?.ResultObject ?? PyNone.Instance;
					if (resultValue == null) resultValue = PyNone.Instance;
					var nextResult = scriptSystem.ResumeGeneratorWithPyObject(generator, resultValue);
					ProcessScriptResult(nextResult, scriptSystem, processCompletion: true);
					return;
				}

				// 반환값이 문자열이면 화면 업데이트
				if (newText != null)
				{
					activeDialogRequest.UpdateCurrentPageText(newText);
					_textUISystem?.UpdateDialogText(newText);
#if DEBUG_LOG
					GD.Print($"[MetaActionHandler] proc callback returned text, updating dialog: {newText.Substring(0, System.Math.Min(50, newText.Length))}...");
#endif
				}
#if DEBUG_LOG
				else
				{
					GD.Print("[MetaActionHandler] proc callback returned None/False, no change");
				}
#endif
			}
			return;  // proc 콜백 사용 시 generator는 재개하지 않음
		}

		// proc 콜백이 없으면 기존 동작: generator에 값 전달
		var generatorFallback = activeGenerator;
		_pendingGenerator = null;
		_textUISystem?.ClearPendingDialog();  // TextUISystem 쪽도 클리어

		// generator에 값 전달하고 계속 실행 (Pop 안함 - 다이얼로그 유지)
		var scriptSystemFallback = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystemFallback != null)
		{
			var nextResult = scriptSystemFallback.ResumeGenerator(generatorFallback, value);
			ProcessScriptResult(nextResult, scriptSystemFallback);
		}
	}

	/// <summary>
	/// @finish 처리 - 다이얼로그 종료, result 파라미터 값 반환
	/// </summary>
	private void HandleFinishAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] @finish action");
#endif

		// 다이얼로그가 열려있는지 확인
		if (_textUISystem?.CurrentFocus?.Type != FocusType.Dialog)
		{
			GD.PrintErr("[MetaActionHandler] @finish: called but no dialog is open - this is a bug!");
			return;
		}

		// _pendingGenerator 또는 TextUISystem의 PendingDialogGenerator 확인 (Animlog에서 전환된 경우)
		var activeGenerator = _pendingGenerator ?? _textUISystem?.PendingDialogGenerator;
		var activeDialogRequest = _pendingDialogRequest ?? _textUISystem?.PendingDialogRequest;

		if (activeGenerator == null)
		{
			// generator 없으면 단순 다이얼로그 종료 (스택 유지)
			// meet 이벤트 핸들러일 수 있으므로 남은 이벤트 처리
			_textUISystem?.Pop();
			ProcessEventsAndUpdateDisplay();
			return;
		}

		var generator = activeGenerator;
		_pendingGenerator = null;
		_pendingDialogRequest = null;
		_textUISystem?.ClearPendingDialog();  // TextUISystem 쪽도 클리어

		// 다이얼로그 Pop
		_textUISystem?.Pop();

		// generator에 ResultObject 전달하고 계속 실행
		// processCompletion=true: generator 완료 시 PopIfInvalid 및 이벤트 처리 수행
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem != null)
		{
			// ResultObject가 있으면 그것을, 없으면 None 반환
			// 주의: activeDialogRequest?.ResultObject가 null일 수 있으므로 별도 처리 필요
			PyObject resultValue = activeDialogRequest?.ResultObject ?? PyNone.Instance;
			if (resultValue == null) resultValue = PyNone.Instance;
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] @finish: resuming generator with result={resultValue.GetTypeName()}");
#endif
			var nextResult = scriptSystem.ResumeGeneratorWithPyObject(generator, resultValue);
			ProcessScriptResult(nextResult, scriptSystem, processCompletion: true);
		}
	}

	/// <summary>
	/// @next 처리 - 다음 페이지로 이동 (autofill 전용)
	/// </summary>
	private void HandleNextPageAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] @next action");
#endif

		// 다이얼로그가 열려있는지 확인
		if (_textUISystem?.CurrentFocus?.Type != FocusType.Dialog)
		{
			GD.PrintErr("[MetaActionHandler] @next: called but no dialog is open - this is a bug!");
			return;
		}

		// _pendingDialogRequest 또는 TextUISystem의 PendingDialogRequest 확인 (Animlog에서 전환된 경우)
		var activeDialogRequest = _pendingDialogRequest ?? _textUISystem?.PendingDialogRequest;

		if (activeDialogRequest == null)
		{
			// 비정상 상태: Dialog가 열려있지만 DialogRequest가 없음
			// 이는 버그이므로 에러를 발생시켜 원인 파악 필요
			throw new System.InvalidOperationException(
				"[MetaActionHandler] @next: called without pending dialog request. " +
				"This indicates a bug in Generator/Dialog state management.");
		}

		if (activeDialogRequest.MoveToNextPage())
		{
			// 다음 페이지 텍스트로 업데이트 (autofill 버튼 포함)
			var nextPageText = activeDialogRequest.Text;
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] @next: moved to page {activeDialogRequest.CurrentPageIndex + 1}/{activeDialogRequest.Pages.Count}");
#endif
			_textUISystem?.UpdateDialogText(nextPageText);
		}
		else
		{
			GD.PrintErr("[MetaActionHandler] @next: no next page available - this is a bug!");
		}
	}

	/// <summary>
	/// @prev 처리 - 이전 페이지로 이동 (book 전용)
	/// </summary>
	private void HandlePrevPageAction()
	{
#if DEBUG_LOG
		GD.Print("[MetaActionHandler] @prev action");
#endif

		// 다이얼로그가 열려있는지 확인
		if (_textUISystem?.CurrentFocus?.Type != FocusType.Dialog)
		{
			GD.PrintErr("[MetaActionHandler] @prev: called but no dialog is open - this is a bug!");
			return;
		}

		// _pendingDialogRequest 또는 TextUISystem의 PendingDialogRequest 확인 (Animlog에서 전환된 경우)
		var activeDialogRequest = _pendingDialogRequest ?? _textUISystem?.PendingDialogRequest;

		if (activeDialogRequest == null)
		{
			GD.PrintErr("[MetaActionHandler] @prev: called without pending dialog request - this is a bug!");
			return;
		}

		if (activeDialogRequest.MoveToPrevPage())
		{
			// 이전 페이지 텍스트로 업데이트 (autofill 버튼 포함)
			var prevPageText = activeDialogRequest.Text;
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] @prev: moved to page {activeDialogRequest.CurrentPageIndex + 1}/{activeDialogRequest.Pages.Count}");
#endif
			_textUISystem?.UpdateDialogText(prevPageText);
		}
		else
		{
			GD.PrintErr("[MetaActionHandler] @prev: no previous page available - this is a bug!");
		}
	}

	/// <summary>
	/// 자동 시간 흐름에 의한 다이얼로그 갱신 (tick)
	/// TimeFlows=true인 Dialog가 열려있고 proc 콜백이 있으면 proc("tick") 호출
	/// 지도 UI 등 시간 흐름에 따라 갱신이 필요한 다이얼로그용
	/// </summary>
	/// <returns>tick 처리가 수행되었으면 true</returns>
	public bool TriggerDialogTick()
	{
		// 1. Dialog Focus가 열려있는지 확인
		if (_textUISystem?.CurrentFocus?.Type != FocusType.Dialog)
			return false;

		// 2. TimeFlows=true인지 확인
		if (_textUISystem.CurrentFocus.TimeFlows != true)
			return false;

		// 3. pendingDialogRequest와 proc 콜백이 있는지 확인 (Animlog에서 전환된 경우도 포함)
		var activeDialogRequest = _pendingDialogRequest ?? _textUISystem?.PendingDialogRequest;
		if (activeDialogRequest?.ProcCallback == null)
			return false;

		// 4. proc("tick") 호출
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem == null)
			return false;

		var (newText, shouldFinish) = scriptSystem.CallProcCallback(activeDialogRequest.ProcCallback, "tick");

		// 5. 반환값 처리
		if (shouldFinish)
		{
			// True 반환: 다이얼로그 종료 (예상치 못한 상황)
#if DEBUG_LOG
			GD.Print("[MetaActionHandler] tick: proc returned True, finishing dialog");
#endif
			HandleFinishAction();
			return true;
		}

		if (newText != null)
		{
			// 새 텍스트로 업데이트
			activeDialogRequest.UpdateCurrentPageText(newText);
			_textUISystem?.UpdateDialogText(newText);
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] tick: dialog updated");
#endif
		}

		return true;
	}
}
