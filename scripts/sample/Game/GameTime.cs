namespace PathFinding.Game;

using System;

/// <summary>
/// 요일
/// </summary>
public enum DayOfWeek
{
    Monday = 0,
    Tuesday = 1,
    Wednesday = 2,
    Thursday = 3,
    Friday = 4,
    Saturday = 5,
    Sunday = 6
}

/// <summary>
/// 게임 시간 시스템
/// - 1달 = 4주 = 28일
/// - 1주 = 7일 (월~일)
/// - 1일 = 24시간
/// - 1시간 = 60분
/// </summary>
public class GameTime : IComparable<GameTime>, IEquatable<GameTime>
{
    public const int MinutesPerHour = 60;
    public const int HoursPerDay = 24;
    public const int DaysPerWeek = 7;
    public const int WeeksPerMonth = 4;
    public const int DaysPerMonth = DaysPerWeek * WeeksPerMonth; // 28일
    public const int MinutesPerDay = MinutesPerHour * HoursPerDay; // 1440분

    private int _totalMinutes;

    /// <summary>
    /// 월 (1부터 시작)
    /// </summary>
    public int Month => (_totalMinutes / MinutesPerDay / DaysPerMonth) + 1;

    /// <summary>
    /// 월 내 일자 (1~28)
    /// </summary>
    public int Day => ((_totalMinutes / MinutesPerDay) % DaysPerMonth) + 1;

    /// <summary>
    /// 주차 (1~4)
    /// </summary>
    public int Week => ((Day - 1) / DaysPerWeek) + 1;

    /// <summary>
    /// 요일
    /// </summary>
    public DayOfWeek DayOfWeek => (DayOfWeek)(((_totalMinutes / MinutesPerDay) % DaysPerWeek));

    /// <summary>
    /// 시간 (0~23)
    /// </summary>
    public int Hour => (_totalMinutes / MinutesPerHour) % HoursPerDay;

    /// <summary>
    /// 분 (0~59)
    /// </summary>
    public int Minute => _totalMinutes % MinutesPerHour;

    /// <summary>
    /// 하루 중 경과 분 (0~1439)
    /// </summary>
    public int MinuteOfDay => Hour * MinutesPerHour + Minute;

    /// <summary>
    /// 전체 경과 분
    /// </summary>
    public int TotalMinutes => _totalMinutes;

    /// <summary>
    /// 전체 경과 일
    /// </summary>
    public int TotalDays => _totalMinutes / MinutesPerDay;

    /// <summary>
    /// 기본 생성자 (1월 1일 00:00)
    /// </summary>
    public GameTime()
    {
        _totalMinutes = 0;
    }

    /// <summary>
    /// 시간 지정 생성자
    /// </summary>
    public GameTime(int month, int day, int hour, int minute)
    {
        SetTime(month, day, hour, minute);
    }

    /// <summary>
    /// 총 분으로 생성
    /// </summary>
    public GameTime(int totalMinutes)
    {
        _totalMinutes = Math.Max(0, totalMinutes);
    }

    /// <summary>
    /// 시간 설정
    /// </summary>
    public void SetTime(int month, int day, int hour, int minute)
    {
        if (month < 1) throw new ArgumentException("Month must be >= 1");
        if (day < 1 || day > DaysPerMonth) throw new ArgumentException($"Day must be 1-{DaysPerMonth}");
        if (hour < 0 || hour > 23) throw new ArgumentException("Hour must be 0-23");
        if (minute < 0 || minute > 59) throw new ArgumentException("Minute must be 0-59");

        int totalDays = (month - 1) * DaysPerMonth + (day - 1);
        _totalMinutes = totalDays * MinutesPerDay + hour * MinutesPerHour + minute;
    }

    /// <summary>
    /// 분 추가
    /// </summary>
    public void AddMinutes(int minutes)
    {
        _totalMinutes = Math.Max(0, _totalMinutes + minutes);
    }

    /// <summary>
    /// 시간 추가
    /// </summary>
    public void AddHours(int hours)
    {
        AddMinutes(hours * MinutesPerHour);
    }

    /// <summary>
    /// 일 추가
    /// </summary>
    public void AddDays(int days)
    {
        AddMinutes(days * MinutesPerDay);
    }

    /// <summary>
    /// 복사본 생성
    /// </summary>
    public GameTime Clone()
    {
        return new GameTime(_totalMinutes);
    }

    /// <summary>
    /// 시간 차이 (분)
    /// </summary>
    public int DifferenceInMinutes(GameTime other)
    {
        return _totalMinutes - other._totalMinutes;
    }

    /// <summary>
    /// 특정 시간이 지났는지 확인
    /// </summary>
    public bool IsAfter(GameTime other)
    {
        return _totalMinutes > other._totalMinutes;
    }

    /// <summary>
    /// 특정 시간 이전인지 확인
    /// </summary>
    public bool IsBefore(GameTime other)
    {
        return _totalMinutes < other._totalMinutes;
    }

    /// <summary>
    /// 같은 날인지 확인
    /// </summary>
    public bool IsSameDay(GameTime other)
    {
        return TotalDays == other.TotalDays;
    }

    /// <summary>
    /// 하루 중 특정 시간(시:분)인지 확인
    /// </summary>
    public bool IsTimeOfDay(int hour, int minute)
    {
        return Hour == hour && Minute == minute;
    }

    /// <summary>
    /// 하루 중 특정 시간 범위 내인지 확인 (자정 넘김 지원)
    /// </summary>
    public bool IsInTimeRange(int startHour, int startMinute, int endHour, int endMinute)
    {
        int currentMinute = MinuteOfDay;
        int startMinuteOfDay = startHour * MinutesPerHour + startMinute;
        int endMinuteOfDay = endHour * MinutesPerHour + endMinute;

        if (startMinuteOfDay <= endMinuteOfDay)
        {
            // 같은 날 내 범위 (예: 08:00 ~ 18:00)
            return currentMinute >= startMinuteOfDay && currentMinute < endMinuteOfDay;
        }
        else
        {
            // 자정을 넘는 범위 (예: 22:00 ~ 06:00)
            return currentMinute >= startMinuteOfDay || currentMinute < endMinuteOfDay;
        }
    }

    public int CompareTo(GameTime? other)
    {
        if (other == null) return 1;
        return _totalMinutes.CompareTo(other._totalMinutes);
    }

    public bool Equals(GameTime? other)
    {
        if (other == null) return false;
        return _totalMinutes == other._totalMinutes;
    }

    public override bool Equals(object? obj) => Equals(obj as GameTime);
    public override int GetHashCode() => _totalMinutes.GetHashCode();

    public static bool operator ==(GameTime? a, GameTime? b)
    {
        if (a is null && b is null) return true;
        if (a is null || b is null) return false;
        return a._totalMinutes == b._totalMinutes;
    }

    public static bool operator !=(GameTime? a, GameTime? b) => !(a == b);
    public static bool operator <(GameTime a, GameTime b) => a._totalMinutes < b._totalMinutes;
    public static bool operator >(GameTime a, GameTime b) => a._totalMinutes > b._totalMinutes;
    public static bool operator <=(GameTime a, GameTime b) => a._totalMinutes <= b._totalMinutes;
    public static bool operator >=(GameTime a, GameTime b) => a._totalMinutes >= b._totalMinutes;

    public override string ToString()
    {
        return $"{Month}월 {Day}일 ({DayOfWeek}) {Hour:D2}:{Minute:D2}";
    }

    /// <summary>
    /// 시간만 표시
    /// </summary>
    public string ToTimeString()
    {
        return $"{Hour:D2}:{Minute:D2}";
    }

    /// <summary>
    /// 날짜만 표시
    /// </summary>
    public string ToDateString()
    {
        return $"{Month}월 {Day}일 ({DayOfWeek})";
    }
}

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
        int currentMinute = time.MinuteOfDay;

        if (SpansMidnight)
        {
            // 자정 넘는 경우: 시작 시간 이후이거나, 자정 이후~종료 전
            return currentMinute >= StartMinute || currentMinute < EndMinute;
        }
        else
        {
            return currentMinute >= StartMinute && currentMinute < EndMinute;
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
