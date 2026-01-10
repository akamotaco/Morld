#define DEBUG_LOG

using Godot;
using SE;

/// <summary>
/// MetaActionHandler - Navigation 핸들러
/// move, back, toggle, idle, inventory, look_unit 처리
/// </summary>
public partial class MetaActionHandler
{
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
}
