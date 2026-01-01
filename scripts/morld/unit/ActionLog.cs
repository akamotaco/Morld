namespace Morld;

/// <summary>
/// 유닛의 단일 행동 기록 (Edge 단위로 분리)
/// </summary>
public class ActionLog
{
	/// <summary>
	/// 행동 시작 시간 (상대 분 - 현재 Step 시작 기준 0분부터)
	/// </summary>
	public int StartTime { get; set; }

	/// <summary>
	/// 행동 종료 시간 (상대 분)
	/// </summary>
	public int EndTime { get; set; }

	/// <summary>
	/// 이동 중 여부 (true면 이동 처리, Activity 값은 무시하고 보관만)
	/// </summary>
	public bool IsMoving { get; set; }

	/// <summary>
	/// 위치 (IsMoving=false면 현재 위치, IsMoving=true면 출발지)
	/// LocationRef는 readonly struct이므로 자동 값 복사
	/// </summary>
	public LocationRef Location { get; set; }

	/// <summary>
	/// 도착 위치 (IsMoving=true일 때만 유효, 단일 Edge의 도착지)
	/// LocationRef는 readonly struct이므로 자동 값 복사
	/// </summary>
	public LocationRef? Destination { get; set; }

	/// <summary>
	/// 활동명 (스케줄에서 그대로 복사, null이면 Idle)
	/// IsMoving=true일 때도 값 유지 (이동 목적 표시용)
	/// </summary>
	public string? Activity { get; set; }

	/// <summary>
	/// 행동 소요 시간 (분)
	/// </summary>
	public int Duration => EndTime - StartTime;

	public override string ToString()
	{
		if (IsMoving)
		{
			return $"[{StartTime}~{EndTime}분] Moving: {Location} → {Destination} ({Activity ?? "이동"})";
		}
		else
		{
			return $"[{StartTime}~{EndTime}분] {Activity ?? "Idle"} @ {Location}";
		}
	}
}

/// <summary>
/// Edge 위에서의 진행 상태 (이동 중단 시 현재 위치 정보 보존용)
/// </summary>
public class EdgeProgress
{
	/// <summary>
	/// 출발 Location (LocationRef는 readonly struct이므로 자동 값 복사)
	/// </summary>
	public LocationRef From { get; set; }

	/// <summary>
	/// 도착 Location (LocationRef는 readonly struct이므로 자동 값 복사)
	/// </summary>
	public LocationRef To { get; set; }

	/// <summary>
	/// 총 이동 시간 (분)
	/// </summary>
	public int TotalTime { get; set; }

	/// <summary>
	/// 경과 시간 (분)
	/// </summary>
	public int ElapsedTime { get; set; }

	/// <summary>
	/// 남은 시간 (분) - 다음 Planning에서 사용
	/// </summary>
	public int RemainingTime => TotalTime - ElapsedTime;

	/// <summary>
	/// 진행률 (0.0 ~ 1.0)
	/// </summary>
	public float Progress => TotalTime > 0 ? (float)ElapsedTime / TotalTime : 1.0f;

	public override string ToString()
	{
		return $"Edge: {From} → {To} ({ElapsedTime}/{TotalTime}분, {Progress:P0})";
	}
}
