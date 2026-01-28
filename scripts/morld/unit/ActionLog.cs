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
/// Location 내 2D 이동 진행 상태 (Pi-World)
/// Gate 기반 2D 좌표 이동 추적
/// </summary>
public class MovementProgress
{
	/// <summary>
	/// 출발 X 좌표
	/// </summary>
	public float StartX { get; set; }

	/// <summary>
	/// 출발 Y 좌표 (확장용)
	/// </summary>
	public float StartY { get; set; } = 0f;

	/// <summary>
	/// 목표 X 좌표
	/// </summary>
	public float TargetX { get; set; }

	/// <summary>
	/// 목표 Y 좌표 (확장용)
	/// </summary>
	public float TargetY { get; set; } = 0f;

	/// <summary>
	/// 목표 Gate ID (Gate 통과 이동 시)
	/// null이면 Location 내 단순 이동
	/// </summary>
	public int? TargetGateId { get; set; }

	/// <summary>
	/// 총 이동 거리 (단위)
	/// </summary>
	public float TotalDistance { get; set; }

	/// <summary>
	/// 이동한 거리 (단위)
	/// </summary>
	public float TraveledDistance { get; set; }

	/// <summary>
	/// 이동 속도 (단위/분)
	/// </summary>
	public float Speed { get; set; }

	/// <summary>
	/// 경과 시간 (분)
	/// </summary>
	public int ElapsedTime { get; set; }

	/// <summary>
	/// 총 이동 시간 (분, 계산됨)
	/// </summary>
	public int TotalTime => Speed > 0 ? (int)MathF.Ceiling(TotalDistance / Speed) : int.MaxValue;

	/// <summary>
	/// 남은 시간 (분)
	/// </summary>
	public int RemainingTime => TotalTime - ElapsedTime;

	/// <summary>
	/// 진행률 (0.0 ~ 1.0)
	/// </summary>
	public float Progress => TotalDistance > 0 ? TraveledDistance / TotalDistance : 1f;

	/// <summary>
	/// 현재 X 좌표 (선형 보간)
	/// </summary>
	public float CurrentX => StartX + (TargetX - StartX) * Progress;

	/// <summary>
	/// 현재 Y 좌표 (선형 보간, 확장용)
	/// </summary>
	public float CurrentY => StartY + (TargetY - StartY) * Progress;

	/// <summary>
	/// 이동 완료 여부
	/// </summary>
	public bool IsComplete => TraveledDistance >= TotalDistance;

	/// <summary>
	/// Gate 통과 이동인지 여부
	/// </summary>
	public bool IsGateMovement => TargetGateId.HasValue;

	/// <summary>
	/// 시간 경과 처리
	/// </summary>
	/// <param name="minutes">경과 시간 (분)</param>
	/// <returns>실제 소모된 시간 (분)</returns>
	public int Advance(int minutes)
	{
		if (IsComplete) return 0;

		float distanceToTravel = minutes * Speed;
		float remainingDistance = TotalDistance - TraveledDistance;

		if (distanceToTravel >= remainingDistance)
		{
			// 도착
			TraveledDistance = TotalDistance;
			int timeUsed = (int)MathF.Ceiling(remainingDistance / Speed);
			ElapsedTime += timeUsed;
			return timeUsed;
		}
		else
		{
			// 진행 중
			TraveledDistance += distanceToTravel;
			ElapsedTime += minutes;
			return minutes;
		}
	}

	public override string ToString()
	{
		var gateInfo = TargetGateId.HasValue ? $" → Gate{TargetGateId}" : "";
		return $"Movement: ({StartX:F1},{StartY:F1}) → ({TargetX:F1},{TargetY:F1}){gateInfo} ({Progress:P0}, {RemainingTime}분 남음)";
	}
}
