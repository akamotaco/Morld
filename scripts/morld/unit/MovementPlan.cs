namespace Morld;

using System.Collections.Generic;

/// <summary>
/// 유닛의 이동 계획 (충돌 감지용)
/// </summary>
public class MovementPlan
{
	/// <summary>
	/// 유닛 ID
	/// </summary>
	public int UnitId { get; set; }

	/// <summary>
	/// 이동 경로 (Location 리스트)
	/// </summary>
	public List<Location> Path { get; set; } = new();

	/// <summary>
	/// 시작 시간 (상대 분)
	/// </summary>
	public int StartTime { get; set; }

	/// <summary>
	/// 각 Location별 도착 시간 (상대 분)
	/// </summary>
	public Dictionary<Location, int> ArrivalTimes { get; set; } = new();

	/// <summary>
	/// 특정 Location의 도착 시간 조회
	/// </summary>
	public int GetArrivalTime(Location loc) =>
		ArrivalTimes.TryGetValue(loc, out var t) ? t : -1;

	public override string ToString()
	{
		return $"MovementPlan[{UnitId}] {Path.Count}개 위치, 시작={StartTime}분";
	}
}
