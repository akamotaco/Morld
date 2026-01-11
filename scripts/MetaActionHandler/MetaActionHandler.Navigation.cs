#define DEBUG_LOG

using Godot;

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
		// TODO: 조건부 이동 체크 (locked 조건)
		// var (canMove, blockMessage) = CheckMoveConditions(regionId, localId);
		// if (!canMove)
		// {
		//     // 조건 미달 → 메시지 다이얼로그 + [확인] 버튼
		//     var dialogText = $"{blockMessage}\n\n[url=back]확인[/url]";
		//     _textUISystem?.PushDialog(dialogText, 0);
		//     return;
		// }

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
			// 이동 확인 메시지 생성
			string message = FormatTravelTimeMessage(travelTime);

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
	/// 이동 시간 포맷팅
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
	/// 장비 목록 확인 처리
	/// </summary>
	private void HandleEquipmentAction()
	{
		_textUISystem?.ShowEquipment();
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

	#region TODO: 조건부 이동 시스템

	// === 이동 조건 체계 설계 ===
	//
	// | 상태                    | UI 표시    | 클릭 시                        |
	// |------------------------|------------|-------------------------------|
	// | 연결 없음               | 표시 안됨   | -                             |
	// | 조건 미달 (hidden)      | 표시 안됨   | -                             |
	// | 조건 미달 (locked)      | 정상 표시   | 메시지 다이얼로그 + [확인]      |
	// | 조건 충족 (단거리)       | 정상 표시   | 즉시 이동                      |
	// | 조건 충족 (장거리)       | 정상 표시   | 확인 다이얼로그 + [예/아니오]   |
	//
	// === Edge/RegionEdge 조건 타입 ===
	//
	// - hidden: 조건 미달 시 목록에서 숨김 (예: 관찰력 부족으로 숨겨진 문 못찾음)
	// - locked: 조건 미달 시 표시는 되나 이동 시 메시지 (예: 잠긴 문)
	//
	// === Python Edge 정의 예시 ===
	//
	// EDGES = [
	//     (0, 1, 1),  # 기본 연결
	//     (1, 10, 1, {"hidden": {"관찰력": 5}}),  # 숨겨진 문
	//     (1, 11, 1, {"locked": {"has:열쇠": 1}, "message": "문이 잠겨 있다."}),  # 잠긴 문
	// ]
	//
	// === C# 구현 TODO ===
	//
	// private (bool canMove, string? blockMessage) CheckMoveConditions(int regionId, int localId)
	// {
	//     // 1. Edge/RegionEdge에서 locked 조건 가져오기
	//     // 2. 플레이어 props와 비교
	//     // 3. 미달 시 (false, message) 반환
	//     // 4. 충족 시 (true, null) 반환
	// }

	#endregion
}
