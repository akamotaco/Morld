namespace Morld;

/// <summary>
/// 유닛이 수행할 작업 단위
/// - 시간 기반으로 duration이 감소하며 소진되면 다음 Job으로 이동
/// - Name: 표시용 이름 ("사냥", "아침식사", "파티")
/// - Action: 실제 동작 (C#에서 구현된 stay, move, follow, flee)
/// </summary>
public class Job
{
	/// <summary>
	/// 표시용 이름 ("사냥", "상점 정리", "아침식사", "파티" 등)
	/// </summary>
	public string Name { get; set; } = string.Empty;

	/// <summary>
	/// 실제 동작 (C#에서 구현)
	/// - "stay": 현재 위치 유지 (이동 없음)
	/// - "move": 지정 위치로 이동
	/// - "follow": 대상 따라가기
	/// - "flee": 대상 피하기
	/// </summary>
	public string Action { get; set; } = "stay";

	/// <summary>
	/// 목표 지역 ID (move, stay에서 사용)
	/// </summary>
	public int RegionId { get; set; }

	/// <summary>
	/// 목표 장소 ID (move, stay에서 사용)
	/// </summary>
	public int LocationId { get; set; }

	/// <summary>
	/// 시작 시간 (JobList 내에서의 상대 시간, 분)
	/// - 0이면 즉시 시작 (현재 시점)
	/// - 양수면 그만큼 뒤에 시작 (Merge용)
	/// </summary>
	public int StartOffset { get; set; } = 0;

	/// <summary>
	/// 남은 시간 (분 단위, 시간 경과 시 감소)
	/// </summary>
	public int Duration { get; set; }

	/// <summary>
	/// 대상 ID (follow, flee에서 사용)
	/// - follow: 따라갈 유닛 ID
	/// - flee: 피할 유닛 ID
	/// </summary>
	public int? TargetId { get; set; }

	/// <summary>
	/// 목표 위치를 LocationRef로 반환
	/// </summary>
	public LocationRef GetLocationRef() => new LocationRef(RegionId, LocationId);

	/// <summary>
	/// 복제본 생성 (잘라내기 시 사용)
	/// </summary>
	public Job Clone()
	{
		return new Job
		{
			Name = Name,
			Action = Action,
			RegionId = RegionId,
			LocationId = LocationId,
			StartOffset = StartOffset,
			Duration = Duration,
			TargetId = TargetId
		};
	}

	public override string ToString()
	{
		var target = TargetId.HasValue ? $", target={TargetId}" : "";
		var location = Action == "stay" || Action == "move" ? $" @{RegionId}:{LocationId}" : "";
		return $"Job[{Name}:{Action}]{location} ({Duration}분{target})";
	}
}
