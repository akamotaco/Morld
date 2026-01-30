namespace Morld;

/// <summary>
/// 하루 중 시간 범위 (스케줄용) - 밀리초 단위
/// </summary>
public readonly struct TimeRange
{
    /// <summary>
    /// 시작 시간 (밀리초, 0~86,399,999)
    /// </summary>
    public int StartMillis { get; }

    /// <summary>
    /// 종료 시간 (밀리초, 0~86,399,999)
    /// </summary>
    public int EndMillis { get; }

    /// <summary>
    /// 자정을 넘는 범위인지
    /// </summary>
    public bool SpansMidnight => StartMillis > EndMillis;

    /// <summary>
    /// 시작 시간 (시)
    /// </summary>
    public int StartHour => StartMillis / GameTime.MillisPerHour;

    /// <summary>
    /// 시작 시간 (분 부분)
    /// </summary>
    public int StartMinutePart => (StartMillis % GameTime.MillisPerHour) / GameTime.MillisPerMinute;

    /// <summary>
    /// 종료 시간 (시)
    /// </summary>
    public int EndHour => EndMillis / GameTime.MillisPerHour;

    /// <summary>
    /// 종료 시간 (분 부분)
    /// </summary>
    public int EndMinutePart => (EndMillis % GameTime.MillisPerHour) / GameTime.MillisPerMinute;

    /// <summary>
    /// 밀리초 단위로 생성
    /// </summary>
    public TimeRange(int startMillis, int endMillis)
    {
        StartMillis = startMillis;
        EndMillis = endMillis;
    }

    /// <summary>
    /// 시:분으로 생성
    /// </summary>
    public static TimeRange FromHourMinute(int startHour, int startMinute, int endHour, int endMinute)
    {
        return new TimeRange(
            startHour * GameTime.MillisPerHour + startMinute * GameTime.MillisPerMinute,
            endHour * GameTime.MillisPerHour + endMinute * GameTime.MillisPerMinute);
    }

    /// <summary>
    /// 시간만으로 생성 (분은 0)
    /// </summary>
    public static TimeRange FromHours(int startHour, int endHour)
    {
        return new TimeRange(
            startHour * GameTime.MillisPerHour,
            endHour * GameTime.MillisPerHour);
    }

    /// <summary>
    /// 현재 시간이 범위 내인지 확인
    /// </summary>
    public bool Contains(GameTime time)
    {
        return ContainsMillis(time.MillisOfDay);
    }

    /// <summary>
    /// 현재 시간(밀리초)이 범위 내인지 확인
    /// </summary>
    public bool ContainsMillis(int millisOfDay)
    {
        if (SpansMidnight)
        {
            // 자정 넘는 경우: 시작 시간 이후이거나, 자정 이후~종료 전
            return millisOfDay >= StartMillis || millisOfDay < EndMillis;
        }
        else
        {
            return millisOfDay >= StartMillis && millisOfDay < EndMillis;
        }
    }

    /// <summary>
    /// 현재 시간이 시작 시간인지 확인 (같은 분에 해당하면 true)
    /// </summary>
    public bool IsStartTime(GameTime time)
    {
        int startMinuteMillis = (StartMillis / GameTime.MillisPerMinute) * GameTime.MillisPerMinute;
        int timeMinuteMillis = (time.MillisOfDay / GameTime.MillisPerMinute) * GameTime.MillisPerMinute;
        return timeMinuteMillis == startMinuteMillis;
    }

    /// <summary>
    /// 현재 시간이 시작 시간 이후인지 확인 (같은 날 기준)
    /// </summary>
    public bool HasStarted(GameTime time)
    {
        int currentMillis = time.MillisOfDay;

        if (SpansMidnight)
        {
            return currentMillis >= StartMillis || currentMillis < EndMillis;
        }
        else
        {
            return currentMillis >= StartMillis;
        }
    }

    /// <summary>
    /// 범위가 지났는지 확인 (같은 날 기준)
    /// </summary>
    public bool HasEnded(GameTime time)
    {
        int currentMillis = time.MillisOfDay;

        if (SpansMidnight)
        {
            return currentMillis >= EndMillis && currentMillis < StartMillis;
        }
        else
        {
            return currentMillis >= EndMillis;
        }
    }

    public override string ToString()
    {
        return $"{StartHour:D2}:{StartMinutePart:D2} ~ {EndHour:D2}:{EndMinutePart:D2}";
    }
}
