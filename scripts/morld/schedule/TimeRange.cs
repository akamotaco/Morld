namespace Morld;

/// <summary>
/// 하루 중 시간 범위 (스케줄용) - 분 단위
/// </summary>
public readonly struct TimeRange
{
    /// <summary>
    /// 시작 시간 (분, 0~1439)
    /// </summary>
    public int StartMinute { get; }

    /// <summary>
    /// 종료 시간 (분, 0~1439)
    /// </summary>
    public int EndMinute { get; }

    /// <summary>
    /// 자정을 넘는 범위인지
    /// </summary>
    public bool SpansMidnight => StartMinute > EndMinute;

    /// <summary>
    /// 시작 시간 (시)
    /// </summary>
    public int StartHour => StartMinute / GameTime.MinutesPerHour;

    /// <summary>
    /// 시작 시간 (분 부분)
    /// </summary>
    public int StartMinutePart => StartMinute % GameTime.MinutesPerHour;

    /// <summary>
    /// 종료 시간 (시)
    /// </summary>
    public int EndHour => EndMinute / GameTime.MinutesPerHour;

    /// <summary>
    /// 종료 시간 (분 부분)
    /// </summary>
    public int EndMinutePart => EndMinute % GameTime.MinutesPerHour;

    /// <summary>
    /// 분 단위로 생성
    /// </summary>
    public TimeRange(int startMinute, int endMinute)
    {
        StartMinute = startMinute;
        EndMinute = endMinute;
    }

    /// <summary>
    /// 시:분으로 생성
    /// </summary>
    public static TimeRange FromHourMinute(int startHour, int startMinute, int endHour, int endMinute)
    {
        return new TimeRange(
            startHour * GameTime.MinutesPerHour + startMinute,
            endHour * GameTime.MinutesPerHour + endMinute);
    }

    /// <summary>
    /// 시간만으로 생성 (분은 0)
    /// </summary>
    public static TimeRange FromHours(int startHour, int endHour)
    {
        return new TimeRange(
            startHour * GameTime.MinutesPerHour,
            endHour * GameTime.MinutesPerHour);
    }

    /// <summary>
    /// 현재 시간이 범위 내인지 확인
    /// </summary>
    public bool Contains(GameTime time)
    {
        return Contains(time.MinuteOfDay);
    }

    /// <summary>
    /// 현재 시간(분)이 범위 내인지 확인
    /// </summary>
    public bool Contains(int minuteOfDay)
    {
        if (SpansMidnight)
        {
            // 자정 넘는 경우: 시작 시간 이후이거나, 자정 이후~종료 전
            return minuteOfDay >= StartMinute || minuteOfDay < EndMinute;
        }
        else
        {
            return minuteOfDay >= StartMinute && minuteOfDay < EndMinute;
        }
    }

    /// <summary>
    /// 현재 시간이 시작 시간인지 확인
    /// </summary>
    public bool IsStartTime(GameTime time)
    {
        return time.MinuteOfDay == StartMinute;
    }

    /// <summary>
    /// 현재 시간이 시작 시간 이후인지 확인 (같은 날 기준)
    /// </summary>
    public bool HasStarted(GameTime time)
    {
        int currentMinute = time.MinuteOfDay;

        if (SpansMidnight)
        {
            return currentMinute >= StartMinute || currentMinute < EndMinute;
        }
        else
        {
            return currentMinute >= StartMinute;
        }
    }

    /// <summary>
    /// 범위가 지났는지 확인 (같은 날 기준)
    /// </summary>
    public bool HasEnded(GameTime time)
    {
        int currentMinute = time.MinuteOfDay;

        if (SpansMidnight)
        {
            return currentMinute >= EndMinute && currentMinute < StartMinute;
        }
        else
        {
            return currentMinute >= EndMinute;
        }
    }

    public override string ToString()
    {
        return $"{StartHour:D2}:{StartMinutePart:D2} ~ {EndHour:D2}:{EndMinutePart:D2}";
    }
}
