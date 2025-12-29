namespace PathFinding.Game;

using System;
using System.Collections.Generic;
using Morld;

/// <summary>
/// NPC 상태
/// </summary>
public enum NPCState
{
    /// <summary>
    /// Location에서 대기/활동 중
    /// </summary>
    Idle,

    /// <summary>
    /// 이동 중
    /// </summary>
    Moving
}

/// <summary>
/// 이동 정보
/// </summary>
public class MovementInfo
{
    /// <summary>
    /// 출발 Location
    /// </summary>
    public LocationRef From { get; set; }

    /// <summary>
    /// 최종 목적지 Location
    /// </summary>
    public LocationRef FinalDestination { get; set; }

    /// <summary>
    /// 현재 이동 중인 다음 Location
    /// </summary>
    public LocationRef NextLocation { get; set; }

    /// <summary>
    /// 전체 경로
    /// </summary>
    public List<Location> FullPath { get; set; } = new();

    /// <summary>
    /// 현재 경로 인덱스
    /// </summary>
    public int CurrentPathIndex { get; set; }

    /// <summary>
    /// 현재 구간 총 이동 시간 (분)
    /// </summary>
    public float TotalTravelTime { get; set; }

    /// <summary>
    /// 현재 구간 경과 시간 (분)
    /// </summary>
    public float ElapsedTime { get; set; }

    /// <summary>
    /// 현재 구간 남은 시간 (분)
    /// </summary>
    public float RemainingTime => Math.Max(0, TotalTravelTime - ElapsedTime);

    /// <summary>
    /// 현재 구간 진행도 (0~100%)
    /// </summary>
    public float ProgressPercent => TotalTravelTime > 0 
        ? Math.Min(100, (ElapsedTime / TotalTravelTime) * 100) 
        : 100;

    /// <summary>
    /// 현재 구간 이동 완료 여부
    /// </summary>
    public bool IsSegmentComplete => ElapsedTime >= TotalTravelTime;

    /// <summary>
    /// 전체 경로 이동 완료 여부
    /// </summary>
    public bool IsPathComplete => CurrentPathIndex >= FullPath.Count - 1 && IsSegmentComplete;

    public override string ToString()
    {
        return $"Moving: {From} → {NextLocation} ({ProgressPercent:F1}%, {RemainingTime:F0}분 남음)";
    }
}

/// <summary>
/// NPC (Non-Player Character)
/// </summary>
public class NPC
{
    private readonly string _id;
    private LocationRef _currentLocation;
    private NPCState _state;
    private MovementInfo? _movement;
    private ScheduleEntry? _currentSchedule;

    /// <summary>
    /// NPC 고유 ID
    /// </summary>
    public string Id => _id;

    /// <summary>
    /// NPC 이름
    /// </summary>
    public string Name { get; set; }

    /// <summary>
    /// 현재 상태
    /// </summary>
    public NPCState State => _state;

    /// <summary>
    /// 현재 Location (이동 중이면 출발지)
    /// </summary>
    public LocationRef CurrentLocation => _currentLocation;

    /// <summary>
    /// 이동 정보 (이동 중일 때만 유효)
    /// </summary>
    public MovementInfo? Movement => _movement;

    /// <summary>
    /// 현재 수행 중인 스케줄
    /// </summary>
    public ScheduleEntry? CurrentSchedule => _currentSchedule;

    /// <summary>
    /// 하루 스케줄
    /// </summary>
    public DailySchedule Schedule { get; }

    /// <summary>
    /// 이동 조건 (태그)
    /// </summary>
    public TraversalContext TraversalContext { get; }

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    /// <summary>
    /// 이동 중인지 여부
    /// </summary>
    public bool IsMoving => _state == NPCState.Moving;

    /// <summary>
    /// 대기 중인지 여부
    /// </summary>
    public bool IsIdle => _state == NPCState.Idle;

    public NPC(string id, string name, LocationRef startLocation)
    {
        _id = id ?? throw new ArgumentNullException(nameof(id));
        Name = name ?? throw new ArgumentNullException(nameof(name));
        _currentLocation = startLocation;
        _state = NPCState.Idle;
        Schedule = new DailySchedule();
        TraversalContext = new TraversalContext();
    }

    public NPC(string id, string name, int regionId, int localId)
        : this(id, name, new LocationRef(regionId, localId))
    {
    }

    /// <summary>
    /// 이동 시작
    /// </summary>
    internal bool StartMovement(List<Location> path, LocationRef finalDestination)
    {
        if (path == null || path.Count < 2)
            return false;

        _movement = new MovementInfo
        {
            From = _currentLocation,
            FinalDestination = finalDestination,
            FullPath = path,
            CurrentPathIndex = 0,
            NextLocation = new LocationRef(path[1]),
            TotalTravelTime = 0,
            ElapsedTime = 0
        };

        _state = NPCState.Moving;
        return true;
    }

    /// <summary>
    /// 현재 구간 이동 시간 설정
    /// </summary>
    internal void SetSegmentTravelTime(float travelTime)
    {
        if (_movement != null)
        {
            _movement.TotalTravelTime = travelTime;
            _movement.ElapsedTime = 0;
        }
    }

    /// <summary>
    /// 이동 시간 경과
    /// </summary>
    internal void AddTravelTime(float minutes)
    {
        if (_movement != null)
        {
            _movement.ElapsedTime += minutes;
        }
    }

    /// <summary>
    /// 다음 구간으로 이동
    /// </summary>
    internal bool MoveToNextSegment()
    {
        if (_movement == null || _movement.IsPathComplete)
            return false;

        _movement.CurrentPathIndex++;

        if (_movement.CurrentPathIndex >= _movement.FullPath.Count - 1)
        {
            // 최종 목적지 도착
            return false;
        }

        var current = _movement.FullPath[_movement.CurrentPathIndex];
        var next = _movement.FullPath[_movement.CurrentPathIndex + 1];

        _currentLocation = new LocationRef(current);
        _movement.From = _currentLocation;
        _movement.NextLocation = new LocationRef(next);
        _movement.ElapsedTime = 0;
        _movement.TotalTravelTime = 0; // GameWorld에서 설정

        return true;
    }

    /// <summary>
    /// 목적지 도착 처리
    /// </summary>
    internal void ArriveAtDestination()
    {
        if (_movement != null)
        {
            _currentLocation = _movement.FinalDestination;
        }
        
        _movement = null;
        _state = NPCState.Idle;
    }

    /// <summary>
    /// 현재 위치로 즉시 이동 (디버그/초기화용)
    /// </summary>
    public void SetLocation(LocationRef location)
    {
        _currentLocation = location;
        _movement = null;
        _state = NPCState.Idle;
    }

    /// <summary>
    /// 현재 스케줄 설정
    /// </summary>
    internal void SetCurrentSchedule(ScheduleEntry? schedule)
    {
        _currentSchedule = schedule;
    }

    /// <summary>
    /// 상태 요약
    /// </summary>
    public string GetStatusSummary()
    {
        if (_state == NPCState.Idle)
        {
            var scheduleInfo = _currentSchedule != null 
                ? $" ({_currentSchedule.Name})" 
                : "";
            return $"{Name}: {_currentLocation}에서 대기 중{scheduleInfo}";
        }
        else if (_movement != null)
        {
            return $"{Name}: {_movement}";
        }
        return $"{Name}: 알 수 없는 상태";
    }

    public override string ToString()
    {
        return $"NPC[{Id}] {Name} @ {_currentLocation} ({_state})";
    }
}
