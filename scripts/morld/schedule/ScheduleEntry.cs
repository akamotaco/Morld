namespace Morld;

using System;

/// <summary>
/// 스케줄 항목
/// </summary>
public class ScheduleEntry
{
	/// <summary>
	/// 스케줄 이름
	/// </summary>
	public string Name { get; set; }

	/// <summary>
	/// 목적지 Location
	/// </summary>
	public LocationRef Location { get; set; }

	/// <summary>
	/// 시간 범위
	/// </summary>
	public TimeRange TimeRange { get; set; }

	/// <summary>
	/// 활동 상태 (예: "수면", "영업", "휴식", "식사" 등)
	/// </summary>
	public string Activity { get; set; }

	/// <summary>
	/// 추가 데이터
	/// </summary>
	public object? Tag { get; set; }

	public ScheduleEntry(string name, LocationRef location, TimeRange timeRange, string activity = "")
	{
		Name = name ?? throw new ArgumentNullException(nameof(name));
		Location = location;
		TimeRange = timeRange;
		Activity = activity;
	}

	public ScheduleEntry(string name, int regionId, int locationId, int startMinute, int endMinute, string activity = "")
		: this(name, new LocationRef(regionId, locationId), new TimeRange(startMinute, endMinute), activity)
	{
	}

	/// <summary>
	/// 현재 시간이 이 스케줄 범위 내인지 확인
	/// </summary>
	public bool IsActive(GameTime time) => TimeRange.Contains(time);

	/// <summary>
	/// 스케줄 시작 시간인지 확인
	/// </summary>
	public bool IsStartTime(GameTime time) => TimeRange.IsStartTime(time);

	public override string ToString()
	{
		return $"{Name} @ {Location} ({TimeRange})";
	}
}
