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
		if (_pendingGenerator != null)
		{
			// 멀티페이지 처리: 다음 페이지가 있으면 이동
			if (_pendingDialogRequest != null && _pendingDialogRequest.HasNextPage)
			{
				_pendingDialogRequest.MoveToNextPage();
				var nextPageText = _pendingDialogRequest.Text;
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] Multi-page dialog: moving to page {_pendingDialogRequest.CurrentPageIndex + 1}/{_pendingDialogRequest.Pages.Count}");
#endif
				_textUISystem?.UpdateDialogText(nextPageText);
				return;  // generator는 재개하지 않음, 다이얼로그 유지
			}

			// 마지막 페이지 완료: ReturnValue가 있으면 그 값으로, 없으면 클릭한 값으로 재개
			var generator = _pendingGenerator;
			_pendingGenerator = null;
			var dialogRequest = _pendingDialogRequest;
			_pendingDialogRequest = null;

			// 최종 반환값 결정
			string finalValue = dialogRequest?.ReturnValue ?? value;

			// 다이얼로그 Pop
			_textUISystem?.Pop();

			// generator에 값 전달하고 계속 실행
			var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
			if (scriptSystem != null)
			{
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] Resuming generator with final value: {finalValue}");
#endif
				var nextResult = scriptSystem.ResumeGenerator(generator, finalValue);
				ProcessScriptResult(nextResult, scriptSystem);
			}

			// generator가 완료되면 현재 화면 갱신
			// 다이얼로그는 이미 Pop되었으므로 이전 focus(Unit 등)가 유지됨
			// 주의: OnContentChange()는 로그를 읽음 처리하므로 여기서 호출하면 안됨
			if (_pendingGenerator == null)
			{
				_textUISystem?.UpdateDisplay();
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

		// proc 콜백이 있으면 호출
		if (_pendingDialogRequest?.ProcCallback != null)
		{
			var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
			if (scriptSystem != null)
			{
				var (newText, shouldFinish) = scriptSystem.CallProcCallback(_pendingDialogRequest.ProcCallback, value);

				// proc 콜백이 True를 반환하면 다이얼로그 종료
				if (shouldFinish)
				{
#if DEBUG_LOG
					GD.Print("[MetaActionHandler] proc callback returned True, finishing dialog");
#endif
					// @finish와 동일한 처리
					var generator = _pendingGenerator;
					_pendingGenerator = null;
					var dialogRequest = _pendingDialogRequest;
					_pendingDialogRequest = null;

					_textUISystem?.Pop();

					PyObject resultValue = dialogRequest?.ResultObject ?? PyNone.Instance;
					var nextResult = scriptSystem.ResumeGeneratorWithPyObject(generator, resultValue);
					ProcessScriptResult(nextResult, scriptSystem);

					if (_pendingGenerator == null)
					{
						RequestUpdateSituation();
					}
					return;
				}

				// 반환값이 문자열이면 화면 업데이트
				if (newText != null)
				{
					_pendingDialogRequest.UpdateCurrentPageText(newText);
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
		var generatorFallback = _pendingGenerator;
		_pendingGenerator = null;  // 일시적으로 null (ResumeGenerator에서 다시 설정됨)

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

		if (_pendingGenerator == null)
		{
			// generator 없으면 단순 다이얼로그 종료
			_textUISystem?.Pop();
			RequestUpdateSituation();
			return;
		}

		var generator = _pendingGenerator;
		_pendingGenerator = null;
		var dialogRequest = _pendingDialogRequest;
		_pendingDialogRequest = null;

		// 다이얼로그 Pop
		_textUISystem?.Pop();

		// generator에 ResultObject 전달하고 계속 실행
		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem != null)
		{
			// ResultObject가 있으면 그것을, 없으면 None 반환
			PyObject resultValue = dialogRequest?.ResultObject ?? PyNone.Instance;
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] @finish: resuming generator with result={resultValue.GetTypeName()}");
#endif
			var nextResult = scriptSystem.ResumeGeneratorWithPyObject(generator, resultValue);
			ProcessScriptResult(nextResult, scriptSystem);
		}

		// generator가 완료되면 상황 업데이트
		if (_pendingGenerator == null)
		{
			RequestUpdateSituation();
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

		if (_pendingDialogRequest == null)
		{
			GD.PrintErr("[MetaActionHandler] @next: called without pending dialog request - this is a bug!");
			return;
		}

		if (_pendingDialogRequest.MoveToNextPage())
		{
			// 다음 페이지 텍스트로 업데이트 (autofill 버튼 포함)
			var nextPageText = _pendingDialogRequest.Text;
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] @next: moved to page {_pendingDialogRequest.CurrentPageIndex + 1}/{_pendingDialogRequest.Pages.Count}");
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

		if (_pendingDialogRequest == null)
		{
			GD.PrintErr("[MetaActionHandler] @prev: called without pending dialog request - this is a bug!");
			return;
		}

		if (_pendingDialogRequest.MoveToPrevPage())
		{
			// 이전 페이지 텍스트로 업데이트 (autofill 버튼 포함)
			var prevPageText = _pendingDialogRequest.Text;
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] @prev: moved to page {_pendingDialogRequest.CurrentPageIndex + 1}/{_pendingDialogRequest.Pages.Count}");
#endif
			_textUISystem?.UpdateDialogText(prevPageText);
		}
		else
		{
			GD.PrintErr("[MetaActionHandler] @prev: no previous page available - this is a bug!");
		}
	}
}
