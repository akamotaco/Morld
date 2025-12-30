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
	/// 스케줄 항목 추가 (편의 메서드)
	/// </summary>
	public DailySchedule AddEntry(string name, int regionId, int locationId, int startMinute, int endMinute)
	{
		_entries.Add(new ScheduleEntry(name, regionId, locationId, startMinute, endMinute));
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
	/// 현재 시간에 시작하는 스케줄 항목 찾기
	/// </summary>
	public ScheduleEntry? GetStartingEntry(GameTime time)
	{
		return _entries.FirstOrDefault(e => e.IsStartTime(time));
	}

	/// <summary>
	/// 특정 시간 범위 내의 모든 스케줄 항목 찾기
	/// </summary>
	public List<ScheduleEntry> GetEntriesInRange(int startMinute, int endMinute)
	{
		return _entries.Where(e =>
			e.TimeRange.StartMinute < endMinute &&
			e.TimeRange.EndMinute > startMinute
		).ToList();
	}

	public override string ToString()
	{
		return $"DailySchedule ({_entries.Count} entries)";
	}
}
