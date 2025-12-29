namespace PathFinding.Game;

using System;
using System.Collections.Generic;
using System.Linq;
using Morld;

/// <summary>
/// 개별 스케줄 항목
/// </summary>
public class ScheduleEntry
{
    /// <summary>
    /// 스케줄 이름/설명
    /// </summary>
    public string Name { get; set; }

    /// <summary>
    /// 목적지 Location 참조
    /// </summary>
    public LocationRef Destination { get; set; }

    /// <summary>
    /// 활동 시간 범위
    /// </summary>
    public TimeRange TimeRange { get; set; }

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    public ScheduleEntry(string name, LocationRef destination, TimeRange timeRange)
    {
        Name = name;
        Destination = destination;
        TimeRange = timeRange;
    }

    public ScheduleEntry(string name, int regionId, int localId, int startMinute, int endMinute)
        : this(name, new LocationRef(regionId, localId), new TimeRange(startMinute, endMinute))
    {
    }

    /// <summary>
    /// 현재 시간이 이 스케줄 범위 내인지
    /// </summary>
    public bool IsActiveAt(GameTime time) => TimeRange.Contains(time);

    /// <summary>
    /// 현재 시간에 이 스케줄을 시작해야 하는지
    /// </summary>
    public bool ShouldStartAt(GameTime time) => TimeRange.IsStartTime(time);

    /// <summary>
    /// 스케줄 시간이 지났는지 (스킵해야 하는지)
    /// </summary>
    public bool HasExpired(GameTime time) => TimeRange.HasEnded(time);

    public override string ToString()
    {
        return $"[{TimeRange}] {Name} @ {Destination}";
    }
}

/// <summary>
/// NPC의 하루 스케줄
/// </summary>
public class DailySchedule
{
    private readonly List<ScheduleEntry> _entries = new();

    /// <summary>
    /// 스케줄 항목들 (시간순 정렬)
    /// </summary>
    public IReadOnlyList<ScheduleEntry> Entries => _entries;

    /// <summary>
    /// 스케줄 항목 추가
    /// </summary>
    public DailySchedule AddEntry(ScheduleEntry entry)
    {
        _entries.Add(entry);
        SortEntries();
        return this;
    }

    /// <summary>
    /// 스케줄 항목 추가 (분 단위)
    /// </summary>
    public DailySchedule AddEntry(string name, int regionId, int localId, int startMinute, int endMinute)
    {
        return AddEntry(new ScheduleEntry(name, regionId, localId, startMinute, endMinute));
    }

    /// <summary>
    /// 모든 스케줄 제거
    /// </summary>
    public void Clear()
    {
        _entries.Clear();
    }

    /// <summary>
    /// 현재 시간에 활성화된 스케줄 찾기
    /// </summary>
    public ScheduleEntry? GetActiveSchedule(GameTime time)
    {
        return _entries.FirstOrDefault(e => e.IsActiveAt(time));
    }

    /// <summary>
    /// 현재 시간 이후의 다음 스케줄 찾기
    /// </summary>
    public ScheduleEntry? GetNextSchedule(GameTime time)
    {
        int currentMinute = time.MinuteOfDay;

        // 현재 시간 이후에 시작하는 스케줄 찾기
        var upcoming = _entries
            .Where(e => e.TimeRange.StartMinute > currentMinute && !e.TimeRange.SpansMidnight)
            .OrderBy(e => e.TimeRange.StartMinute)
            .FirstOrDefault();

        if (upcoming != null)
            return upcoming;

        // 없으면 자정 이후 (다음날) 첫 스케줄
        return _entries
            .Where(e => !e.TimeRange.SpansMidnight)
            .OrderBy(e => e.TimeRange.StartMinute)
            .FirstOrDefault();
    }

    /// <summary>
    /// 특정 시간에 수행해야 할 스케줄 결정
    /// - 현재 활성 스케줄이 있으면 반환
    /// - 없으면 다음 스케줄 반환
    /// </summary>
    public ScheduleEntry? DetermineSchedule(GameTime time, LocationRef currentLocation)
    {
        // 1. 현재 활성 스케줄 확인
        var active = GetActiveSchedule(time);
        if (active != null)
        {
            return active;
        }

        // 2. 다음 스케줄 찾기
        return GetNextSchedule(time);
    }

    /// <summary>
    /// 스케줄을 시간순으로 정렬
    /// </summary>
    private void SortEntries()
    {
        // 자정 넘는 스케줄은 뒤로
        _entries.Sort((a, b) =>
        {
            if (a.TimeRange.SpansMidnight && !b.TimeRange.SpansMidnight)
                return 1;
            if (!a.TimeRange.SpansMidnight && b.TimeRange.SpansMidnight)
                return -1;
            return a.TimeRange.StartMinute.CompareTo(b.TimeRange.StartMinute);
        });
    }

    public override string ToString()
    {
        return $"DailySchedule ({_entries.Count} entries)";
    }

    /// <summary>
    /// 상세 스케줄 출력
    /// </summary>
    public string ToDetailString()
    {
        var lines = new List<string> { "Daily Schedule:" };
        foreach (var entry in _entries)
        {
            lines.Add($"  {entry}");
        }
        return string.Join(Environment.NewLine, lines);
    }
}
