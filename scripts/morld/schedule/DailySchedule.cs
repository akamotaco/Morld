namespace Morld;

using System;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// 하루 스케줄
/// </summary>
public class DailySchedule
{
	private readonly List<ScheduleEntry> _entries = new();

	/// <summary>
	/// 모든 스케줄 항목 (읽기 전용)
	/// </summary>
	public IReadOnlyList<ScheduleEntry> Entries => _entries;

	/// <summary>
	/// 스케줄 항목 추가
	/// </summary>
	public DailySchedule AddEntry(ScheduleEntry entry)
	{
		_entries.Add(entry ?? throw new ArgumentNullException(nameof(entry)));
		return this;
	}

	/// <summary>
	/// 스케줄 항목 추가 (편의 메서드, 밀리초 단위)
	/// </summary>
	public DailySchedule AddEntry(string name, int regionId, int locationId, int startMillis, int endMillis, string activity = "")
	{
		_entries.Add(new ScheduleEntry(name, regionId, locationId, startMillis, endMillis, activity));
		return this;
	}

	/// <summary>
	/// 스케줄 항목 제거
	/// </summary>
	public bool RemoveEntry(ScheduleEntry entry)
	{
		return _entries.Remove(entry);
	}

	/// <summary>
	/// 모든 스케줄 항목 제거
	/// </summary>
	public void ClearEntries()
	{
		_entries.Clear();
	}

	/// <summary>
	/// 현재 시간에 활성화된 스케줄 항목 찾기
	/// </summary>
	public ScheduleEntry? GetCurrentEntry(GameTime time)
	{
		return _entries.FirstOrDefault(e => e.IsActive(time));
	}

	/// <summary>
	/// 특정 시간(밀리초)에 활성화된 스케줄 항목 찾기
	/// </summary>
	public ScheduleEntry? GetEntryAt(int millisOfDay)
	{
		return _entries.FirstOrDefault(e => e.TimeRange.ContainsMillis(millisOfDay));
	}

	/// <summary>
	/// 현재 시간에 시작하는 스케줄 항목 찾기
	/// </summary>
	public ScheduleEntry? GetStartingEntry(GameTime time)
	{
		return _entries.FirstOrDefault(e => e.IsStartTime(time));
	}

	/// <summary>
	/// 특정 시간 범위 내의 모든 스케줄 항목 찾기 (밀리초)
	/// </summary>
	public List<ScheduleEntry> GetEntriesInRange(int startMillis, int endMillis)
	{
		return _entries.Where(e =>
			e.TimeRange.StartMillis < endMillis &&
			e.TimeRange.EndMillis > startMillis
		).ToList();
	}

	public override string ToString()
	{
		return $"DailySchedule ({_entries.Count} entries)";
	}
}
