#define DEBUG_LOG

using Godot;
using SE;
using Morld;
using SharpPy;

/// <summary>
/// MetaActionHandler - Script 핸들러
/// call 액션, ProcessScriptResult, unit action 처리
/// </summary>
public partial class MetaActionHandler
{
	/// <summary>
	/// 유닛 행동 처리: action:actionType:unitId
	/// 현재는 call: 패턴으로 위임만 수행
	/// </summary>
	private void HandleUnitAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid action format. Expected: action:actionType:unitId");
			return;
		}

		var actionType = parts[1];

		// call 액션인 경우 HandleCallAction으로 위임
		// action:call:methodName:displayName:unitId → call:methodName:unitId
		if (actionType == "call")
		{
			// parts[0]="action", parts[1]="call", parts[2]=methodName, parts[3]=displayName, parts[4]=unitId
			if (parts.Length >= 5)
			{
				// unitId가 명시된 경우 (아이템 인벤토리 등)
				var callParts = new string[] { "call", parts[2], parts[4] };
				HandleCallAction(callParts);
			}
			else
			{
				// unitId가 없는 경우 (Focus.TargetUnitId 사용)
				var callParts = new string[] { "call", parts[2] };
				HandleCallAction(callParts);
			}
			return;
		}

		// 미지원 액션 타입
		GD.PrintErr($"[MetaActionHandler] Unknown action type: {actionType}. Use call: pattern instead.");
	}

	/// <summary>
	/// Python 인스턴스 메서드 호출: call:methodName[:arg]
	/// 현재 Focus의 UnitId 또는 ItemId의 Asset 인스턴스 메서드를 호출
	/// </summary>
	private void HandleCallAction(string[] parts)
	{
		if (parts.Length < 2)
		{
			GD.PrintErr("[MetaActionHandler] Invalid call format. Expected: call:methodName");
			return;
		}

		var methodName = parts[1];
		var currentFocus = _textUISystem?.CurrentFocus;
		int? instanceId = null;
		string[] methodArgs = null;

		// container 컨텍스트에서 URL에 인자가 있는 경우:
		// call:method:arg → 오브젝트(TargetUnitId)의 method(arg) 호출
		// 예: call:take_item:100 → 오브젝트의 take_item(100) 호출
		if (currentFocus?.Context == "container" && parts.Length >= 3)
		{
			instanceId = currentFocus.TargetUnitId;
			methodArgs = parts[2..]; // C# 8.0 range operator
		}
		// 일반적인 경우: instance ID 결정 우선순위
		// 1. parts[2]에 명시된 경우 (URL에서 전달)
		// 2. Focus.ItemId (아이템 메뉴에서 호출)
		// 3. Focus.TargetUnitId (오브젝트/유닛에서 호출)
		else
		{
			if (parts.Length >= 3 && int.TryParse(parts[2], out int explicitId))
			{
				instanceId = explicitId;
			}
			else if (currentFocus?.ItemId.HasValue == true)
			{
				instanceId = currentFocus.ItemId;
			}
			else if (currentFocus?.TargetUnitId.HasValue == true)
			{
				instanceId = currentFocus.TargetUnitId;
			}
		}

		if (!instanceId.HasValue)
		{
			GD.PrintErr("[MetaActionHandler] call: requires a target (Focus.ItemId or TargetUnitId)");
			_textUISystem?.ShowResult("대상을 찾을 수 없습니다.");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[MetaActionHandler] Call action: {methodName} on instance {instanceId.Value}" +
			(methodArgs != null ? $" with args [{string.Join(", ", methodArgs)}]" : ""));
#endif

		// 다이얼로그 내에서 call: 호출은 금지 - pending generator가 있으면 에러
		if (_pendingGenerator != null)
		{
			GD.PrintErr($"[MetaActionHandler] call: called while dialog is pending - use @proc: pattern instead! method={methodName}");
			_textUISystem?.ShowResult("다이얼로그 중에는 call: 호출이 금지됩니다.\n@proc: 패턴을 사용하세요.");
			return;
		}

		var scriptSystem = _world.GetSystem("scriptSystem") as ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] ScriptSystem not found");
			return;
		}

		// Python의 assets.call_instance_method(instance_id, method_name, *args) 호출
		var result = scriptSystem.CallInstanceMethod(instanceId.Value, methodName, methodArgs);

		// 결과 타입에 따른 처리
		if (result == null)
		{
			// 스크립트가 반환값 없이 완료됨 - invalid focus 처리 및 화면 갱신
			_textUISystem?.PopIfInvalid();
			_textUISystem?.UpdateDisplay();
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
					_pendingDialogRequest = dialogResult.DialogRequest;  // 멀티페이지 처리용

					// proc('init') 호출 - Dialog 초기화 시 텍스트 갱신 기회 제공
					var displayText = dialogResult.DialogText;
					if (dialogResult.DialogRequest?.ProcCallback != null)
					{
						var (initText, _) = scriptSystem.CallProcCallback(dialogResult.DialogRequest.ProcCallback, "init");
						if (initText != null)
						{
							displayText = initText;
							dialogResult.DialogRequest.UpdateCurrentPageText(initText);
#if DEBUG_LOG
							GD.Print($"[MetaActionHandler] proc('init') returned text, using: {initText.Substring(0, System.Math.Min(50, initText.Length))}...");
#endif
						}
					}

					// Win32 DialogBox 스타일: Push → Update → Pop
					// 현재 다이얼로그가 열려있으면 텍스트만 갱신, 없으면 새로 Push
					if (_textUISystem?.CurrentFocus?.Type == FocusType.Dialog)
					{
						_textUISystem.UpdateDialogText(displayText);
#if DEBUG_LOG
						var pageInfo = dialogResult.DialogRequest?.Pages.Count > 1
							? $" (page {dialogResult.DialogRequest.CurrentPageIndex + 1}/{dialogResult.DialogRequest.Pages.Count})"
							: "";
						GD.Print($"[MetaActionHandler] Dialog update{pageInfo}: {displayText.Substring(0, System.Math.Min(50, displayText.Length))}...");
#endif
					}
					else
					{
						_textUISystem?.PushDialog(displayText);
#if DEBUG_LOG
						var pageInfo = dialogResult.DialogRequest?.Pages.Count > 1
							? $" (page {dialogResult.DialogRequest.CurrentPageIndex + 1}/{dialogResult.DialogRequest.Pages.Count})"
							: "";
						GD.Print($"[MetaActionHandler] Dialog push{pageInfo}: {displayText.Substring(0, System.Math.Min(50, displayText.Length))}...");
#endif
					}
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
