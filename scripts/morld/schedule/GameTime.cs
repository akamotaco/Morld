namespace Morld;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Godot;

/// <summary>
/// 게임 시간 시스템 (설정 가능한 달력 지원)
/// - 달력 설정: 월 수, 월별 일 수, 요일 이름
/// - 기념일 시스템
/// - 시간 조작: 년/월/일/시간/분
/// </summary>
public class GameTime : IComparable<GameTime>, IEquatable<GameTime>
{
    public const int MinutesPerHour = 60;
    public const int HoursPerDay = 24;
    public const int MinutesPerDay = MinutesPerHour * HoursPerDay; // 1440분

    // 달력 설정 (정적 - 모든 GameTime 인스턴스가 공유)
    private static int[] _daysPerMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    private static string[] _weekdayNames = ["일", "월", "화", "수", "목", "금", "토"];
    private static List<Holiday> _holidays = new();

    // 현재 시간 상태
    private int _year;
    private int _month;
    private int _day;
    private int _hour;
    private int _minute;

    /// <summary>
    /// 년 (1부터 시작)
    /// </summary>
    public int Year => _year;

    /// <summary>
    /// 월 (1부터 시작)
    /// </summary>
    public int Month => _month;

    /// <summary>
    /// 일 (1부터 시작)
    /// </summary>
    public int Day => _day;

    /// <summary>
    /// 시간 (0~23)
    /// </summary>
    public int Hour => _hour;

    /// <summary>
    /// 분 (0~59)
    /// </summary>
    public int Minute => _minute;

    /// <summary>
    /// 요일 인덱스 (0 = 첫 번째 요일)
    /// </summary>
    public int WeekdayIndex
    {
        get
        {
            // 1년 1월 1일을 기준 요일로 계산
            int totalDays = GetTotalDays(_year, _month, _day);
            return totalDays % _weekdayNames.Length;
        }
    }

    /// <summary>
    /// 요일 이름
    /// </summary>
    public string WeekdayName => _weekdayNames[WeekdayIndex];

    /// <summary>
    /// 하루 중 경과 분 (0~1439)
    /// </summary>
    public int MinuteOfDay => _hour * MinutesPerHour + _minute;

    /// <summary>
    /// 1년의 개월 수
    /// </summary>
    public static int MonthsPerYear => _daysPerMonth.Length;

    /// <summary>
    /// 요일 이름 배열
    /// </summary>
    public static string[] WeekdayNames => _weekdayNames;

    /// <summary>
    /// 기념일 목록
    /// </summary>
    public static IReadOnlyList<Holiday> Holidays => _holidays;

    /// <summary>
    /// 기본 생성자 (1년 1월 1일 00:00)
    /// </summary>
    public GameTime()
    {
        _year = 1;
        _month = 1;
        _day = 1;
        _hour = 0;
        _minute = 0;
    }

    /// <summary>
    /// 시간 지정 생성자
    /// </summary>
    public GameTime(int year, int month, int day, int hour, int minute)
    {
        SetTime(year, month, day, hour, minute);
    }

    /// <summary>
    /// 시간 설정
    /// </summary>
    public void SetTime(int year, int month, int day, int hour, int minute)
    {
        if (year < 1) throw new ArgumentException("Year must be >= 1");
        if (month < 1 || month > MonthsPerYear) throw new ArgumentException($"Month must be 1-{MonthsPerYear}");

        int daysInMonth = GetDaysInMonth(year, month);
        if (day < 1 || day > daysInMonth) throw new ArgumentException($"Day must be 1-{daysInMonth} for month {month}");
        if (hour < 0 || hour > 23) throw new ArgumentException("Hour must be 0-23");
        if (minute < 0 || minute > 59) throw new ArgumentException("Minute must be 0-59");

        _year = year;
        _month = month;
        _day = day;
        _hour = hour;
        _minute = minute;
    }

    /// <summary>
    /// 분 추가
    /// </summary>
    public void AddMinutes(int minutes)
    {
        if (minutes == 0) return;

        _minute += minutes;

        // 시간 정규화
        while (_minute >= MinutesPerHour)
        {
            _minute -= MinutesPerHour;
            _hour++;
        }
        while (_minute < 0)
        {
            _minute += MinutesPerHour;
            _hour--;
        }

        // 날짜 정규화
        while (_hour >= HoursPerDay)
        {
            _hour -= HoursPerDay;
            AddDays(1);
        }
        while (_hour < 0)
        {
            _hour += HoursPerDay;
            AddDays(-1);
        }
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
        if (days == 0) return;

        _day += days;

        // 날짜 정규화
        while (_day > GetDaysInMonth(_year, _month))
        {
            _day -= GetDaysInMonth(_year, _month);
            _month++;
            if (_month > MonthsPerYear)
            {
                _month = 1;
                _year++;
            }
        }
        while (_day < 1)
        {
            _month--;
            if (_month < 1)
            {
                _month = MonthsPerYear;
                _year--;
                if (_year < 1) throw new InvalidOperationException("Year cannot be less than 1");
            }
            _day += GetDaysInMonth(_year, _month);
        }
    }

    /// <summary>
    /// 월 추가
    /// </summary>
    public void AddMonths(int months)
    {
        if (months == 0) return;

        _month += months;

        while (_month > MonthsPerYear)
        {
            _month -= MonthsPerYear;
            _year++;
        }
        while (_month < 1)
        {
            _month += MonthsPerYear;
            _year--;
            if (_year < 1) throw new InvalidOperationException("Year cannot be less than 1");
        }

        // 일자가 새 월의 범위를 벗어나면 조정
        int daysInMonth = GetDaysInMonth(_year, _month);
        if (_day > daysInMonth)
        {
            _day = daysInMonth;
        }
    }

    /// <summary>
    /// 년 추가
    /// </summary>
    public void AddYears(int years)
    {
        if (years == 0) return;

        _year += years;
        if (_year < 1) throw new InvalidOperationException("Year cannot be less than 1");

        // 일자가 새 년의 해당 월 범위를 벗어나면 조정
        int daysInMonth = GetDaysInMonth(_year, _month);
        if (_day > daysInMonth)
        {
            _day = daysInMonth;
        }
    }

    /// <summary>
    /// 복사본 생성
    /// </summary>
    public GameTime Clone()
    {
        return new GameTime(_year, _month, _day, _hour, _minute);
    }

    /// <summary>
    /// 시간 차이 (분) - 근사값
    /// </summary>
    public int DifferenceInMinutes(GameTime other)
    {
        int thisTotalDays = GetTotalDays(_year, _month, _day);
        int otherTotalDays = GetTotalDays(other._year, other._month, other._day);

        int dayDiff = thisTotalDays - otherTotalDays;
        int minuteDiff = MinuteOfDay - other.MinuteOfDay;

        return dayDiff * MinutesPerDay + minuteDiff;
    }

    /// <summary>
    /// 특정 시간이 지났는지 확인
    /// </summary>
    public bool IsAfter(GameTime other)
    {
        if (_year != other._year) return _year > other._year;
        if (_month != other._month) return _month > other._month;
        if (_day != other._day) return _day > other._day;
        if (_hour != other._hour) return _hour > other._hour;
        return _minute > other._minute;
    }

    /// <summary>
    /// 특정 시간 이전인지 확인
    /// </summary>
    public bool IsBefore(GameTime other)
    {
        if (_year != other._year) return _year < other._year;
        if (_month != other._month) return _month < other._month;
        if (_day != other._day) return _day < other._day;
        if (_hour != other._hour) return _hour < other._hour;
        return _minute < other._minute;
    }

    /// <summary>
    /// 같은 날인지 확인
    /// </summary>
    public bool IsSameDay(GameTime other)
    {
        return _year == other._year && _month == other._month && _day == other._day;
    }

    /// <summary>
    /// 하루 중 특정 시간(시:분)인지 확인
    /// </summary>
    public bool IsTimeOfDay(int hour, int minute)
    {
        return _hour == hour && _minute == minute;
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

    /// <summary>
    /// 현재 날짜가 기념일인지 확인
    /// </summary>
    public List<Holiday> GetHolidays()
    {
        return _holidays.Where(h => h.IsInRange(_month, _day)).ToList();
    }

    /// <summary>
    /// 현재 날짜가 기념일인지 확인
    /// </summary>
    public bool IsHoliday()
    {
        return _holidays.Any(h => h.IsInRange(_month, _day));
    }

    public int CompareTo(GameTime? other)
    {
        if (other == null) return 1;

        if (_year != other._year) return _year.CompareTo(other._year);
        if (_month != other._month) return _month.CompareTo(other._month);
        if (_day != other._day) return _day.CompareTo(other._day);
        if (_hour != other._hour) return _hour.CompareTo(other._hour);
        return _minute.CompareTo(other._minute);
    }

    public bool Equals(GameTime? other)
    {
        if (other == null) return false;
        return _year == other._year && _month == other._month && _day == other._day &&
               _hour == other._hour && _minute == other._minute;
    }

    public override bool Equals(object? obj) => Equals(obj as GameTime);

    public override int GetHashCode()
    {
        return HashCode.Combine(_year, _month, _day, _hour, _minute);
    }

    public static bool operator ==(GameTime? a, GameTime? b)
    {
        if (a is null && b is null) return true;
        if (a is null || b is null) return false;
        return a.Equals(b);
    }

    public static bool operator !=(GameTime? a, GameTime? b) => !(a == b);
    public static bool operator <(GameTime a, GameTime b) => a.CompareTo(b) < 0;
    public static bool operator >(GameTime a, GameTime b) => a.CompareTo(b) > 0;
    public static bool operator <=(GameTime a, GameTime b) => a.CompareTo(b) <= 0;
    public static bool operator >=(GameTime a, GameTime b) => a.CompareTo(b) >= 0;

    public override string ToString()
    {
        return $"{_year}년 {_month}월 {_day}일 ({WeekdayName}) {_hour:D2}:{_minute:D2}";
    }

    /// <summary>
    /// 시간만 표시
    /// </summary>
    public string ToTimeString()
    {
        return $"{_hour:D2}:{_minute:D2}";
    }

    /// <summary>
    /// 날짜만 표시
    /// </summary>
    public string ToDateString()
    {
        return $"{_year}년 {_month}월 {_day}일 ({WeekdayName})";
    }

    /// <summary>
    /// 디버그용 상세 정보 출력
    /// </summary>
    public void DebugPrint()
    {
        var holidays = GetHolidays();
        var holidayStr = holidays.Count > 0
            ? string.Join(", ", holidays.Select(h => h.Name))
            : "없음";

        GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        GD.Print($"  현재 시간: {_year}년 {_month}월 {_day}일 ({WeekdayName}) {_hour:D2}:{_minute:D2}");
        GD.Print($"  기념일: {holidayStr}");
        GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    }

    #region Static Calendar Methods

    /// <summary>
    /// 특정 월의 일 수 반환
    /// </summary>
    public static int GetDaysInMonth(int year, int month)
    {
        if (month < 1 || month > MonthsPerYear)
            throw new ArgumentException($"Month must be 1-{MonthsPerYear}");

        return _daysPerMonth[month - 1];
    }

    /// <summary>
    /// 1년 1월 1일부터의 총 일수 계산
    /// </summary>
    private static int GetTotalDays(int year, int month, int day)
    {
        int totalDays = 0;

        // 년 계산
        for (int y = 1; y < year; y++)
        {
            totalDays += GetDaysInYear();
        }

        // 월 계산
        for (int m = 1; m < month; m++)
        {
            totalDays += GetDaysInMonth(year, m);
        }

        // 일 계산
        totalDays += day - 1; // 1일은 0일째

        return totalDays;
    }

    /// <summary>
    /// 1년의 총 일수
    /// </summary>
    private static int GetDaysInYear()
    {
        return _daysPerMonth.Sum();
    }

    #endregion

    #region JSON Loading

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    /// <summary>
    /// JSON 파일에서 시간 및 달력 설정 업데이트
    /// </summary>
    public void UpdateFromFile(string filePath)
    {
        using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read)
            ?? throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
        var json = file.GetAsText();
        UpdateFromJson(json);
    }

    /// <summary>
    /// JSON 문자열에서 시간 및 달력 설정 업데이트
    /// </summary>
    public void UpdateFromJson(string json)
    {
        var data = JsonSerializer.Deserialize<GameTimeJsonData>(json, _jsonOptions);
        if (data is null)
            throw new InvalidOperationException("Failed to parse GameTime JSON data");

        // 달력 설정 업데이트 (정적)
        if (data.Calendar.DaysPerMonth.Length > 0)
        {
            _daysPerMonth = data.Calendar.DaysPerMonth;
        }
        if (data.Calendar.WeekdayNames.Length > 0)
        {
            _weekdayNames = data.Calendar.WeekdayNames;
        }

        // 기념일 로드
        _holidays.Clear();
        foreach (var holidayData in data.Holidays)
        {
            _holidays.Add(new Holiday(
                holidayData.Name,
                holidayData.Month,
                holidayData.StartDay,
                holidayData.EndDay
            ));
        }

        // 현재 시간 설정
        SetTime(
            data.CurrentTime.Year,
            data.CurrentTime.Month,
            data.CurrentTime.Day,
            data.CurrentTime.Hour,
            data.CurrentTime.Minute
        );
    }

    #endregion
}

/// <summary>
/// 기념일 정보
/// </summary>
public class Holiday
{
    public string Name { get; }
    public int Month { get; }
    public int StartDay { get; }
    public int EndDay { get; }

    public Holiday(string name, int month, int startDay, int endDay)
    {
        Name = name;
        Month = month;
        StartDay = startDay;
        EndDay = endDay;
    }

    /// <summary>
    /// 주어진 날짜가 이 기념일 범위에 포함되는지 확인
    /// </summary>
    public bool IsInRange(int month, int day)
    {
        if (month != Month) return false;
        return day >= StartDay && day <= EndDay;
    }

    public override string ToString()
    {
        if (StartDay == EndDay)
            return $"{Name} ({Month}월 {StartDay}일)";
        else
            return $"{Name} ({Month}월 {StartDay}일~{EndDay}일)";
    }
}
