namespace Morld;

using System.Collections.Generic;

/// <summary>
/// 액션 실행 결과
/// </summary>
public class ActionResult
{
	/// <summary>
	/// 성공 여부
	/// </summary>
	public bool Success { get; set; }

	/// <summary>
	/// 결과 메시지 (UI 표시용)
	/// </summary>
	public string Message { get; set; } = "";

	/// <summary>
	/// 소요 시간 (분, 0이면 즉시)
	/// </summary>
	public int TimeConsumed { get; set; } = 0;

	/// <summary>
	/// 추가 데이터 (액션별 커스텀)
	/// </summary>
	public Dictionary<string, object>? Data { get; set; }

	/// <summary>
	/// 후속 액션 (연쇄 이벤트)
	/// </summary>
	public string? FollowUpAction { get; set; }

	/// <summary>
	/// 성공 결과 생성
	/// </summary>
	public static ActionResult Ok(string message, int timeConsumed = 0)
	{
		return new ActionResult
		{
			Success = true,
			Message = message,
			TimeConsumed = timeConsumed
		};
	}

	/// <summary>
	/// 실패 결과 생성
	/// </summary>
	public static ActionResult Fail(string message)
	{
		return new ActionResult
		{
			Success = false,
			Message = message
		};
	}
}
