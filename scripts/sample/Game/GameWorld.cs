namespace PathFinding.Game;

using System;
using System.Collections.Generic;
using System.Linq;
using Morld;
using PathFinding.Core;

/// <summary>
/// 게임 월드 시뮬레이션
/// - World를 감싸서 시간/NPC 시뮬레이션 관리
/// - step() 함수로 시간 진행
/// </summary>
public class GameWorld
{
    private readonly World _world;
    private readonly PathFinder _pathFinder;
    private readonly Dictionary<string, NPC> _npcs = new();
    private readonly GameTime _currentTime;
    private readonly int _stepMinutes;

    /// <summary>
    /// 기반 World
    /// </summary>
    public World World => _world;

    /// <summary>
    /// 현재 게임 시간
    /// </summary>
    public GameTime CurrentTime => _currentTime;

    /// <summary>
    /// 1 Step당 경과 시간 (분)
    /// </summary>
    public int StepMinutes => _stepMinutes;

    /// <summary>
    /// 모든 NPC
    /// </summary>
    public IReadOnlyCollection<NPC> NPCs => _npcs.Values;

    /// <summary>
    /// NPC 수
    /// </summary>
    public int NPCCount => _npcs.Count;

    /// <summary>
    /// Step 이벤트 (Step 완료 시 발생)
    /// </summary>
    public event Action<GameWorld, StepEventArgs>? OnStep;

    /// <summary>
    /// NPC 도착 이벤트
    /// </summary>
    public event Action<GameWorld, NPCArrivalEventArgs>? OnNPCArrival;

    /// <summary>
    /// NPC 이동 시작 이벤트
    /// </summary>
    public event Action<GameWorld, NPCMovementEventArgs>? OnNPCMovementStart;

    /// <summary>
    /// GameWorld 생성자
    /// </summary>
    /// <param name="world">기반 World</param>
    /// <param name="stepMinutes">1 Step당 경과 시간 (기본: 15분)</param>
    public GameWorld(World world, int stepMinutes = 15)
    {
        _world = world ?? throw new ArgumentNullException(nameof(world));
        _pathFinder = new PathFinder(world);
        _stepMinutes = stepMinutes;
        _currentTime = new GameTime(1, 1, 6, 0); // 1월 1일 06:00 시작
    }

    /// <summary>
    /// 시작 시간 설정
    /// </summary>
    public void SetTime(int month, int day, int hour, int minute)
    {
        _currentTime.SetTime(month, day, hour, minute);
    }

    #region NPC Management

    /// <summary>
    /// NPC 추가
    /// </summary>
    public NPC AddNPC(string id, string name, int regionId, int localId)
    {
        if (_npcs.ContainsKey(id))
            throw new InvalidOperationException($"NPC with ID '{id}' already exists");

        // Location 유효성 확인
        var location = _world.GetLocation(regionId, localId);
        if (location == null)
            throw new ArgumentException($"Location {regionId}:{localId} not found");

        var npc = new NPC(id, name, regionId, localId);
        _npcs[id] = npc;
        return npc;
    }

    /// <summary>
    /// 기존 NPC 객체 추가
    /// </summary>
    public void AddNPC(NPC npc)
    {
        if (npc == null) throw new ArgumentNullException(nameof(npc));

        if (_npcs.ContainsKey(npc.Id))
            throw new InvalidOperationException($"NPC with ID '{npc.Id}' already exists");

        // Location 유효성 확인
        var location = _world.GetLocation(npc.CurrentLocation);
        if (location == null)
            throw new ArgumentException($"NPC's location {npc.CurrentLocation} not found");

        _npcs[npc.Id] = npc;
    }

    /// <summary>
    /// NPC 가져오기
    /// </summary>
    public NPC? GetNPC(string id)
    {
        return _npcs.TryGetValue(id, out var npc) ? npc : null;
    }

    /// <summary>
    /// NPC 제거
    /// </summary>
    public bool RemoveNPC(string id)
    {
        return _npcs.Remove(id);
    }

    /// <summary>
    /// 특정 Location에 있는 NPC들 찾기
    /// </summary>
    public List<NPC> GetNPCsAtLocation(LocationRef location)
    {
        return _npcs.Values
            .Where(n => n.IsIdle && n.CurrentLocation == location)
            .ToList();
    }

    /// <summary>
    /// 이동 중인 NPC들 찾기
    /// </summary>
    public List<NPC> GetMovingNPCs()
    {
        return _npcs.Values.Where(n => n.IsMoving).ToList();
    }

    #endregion

    #region Simulation

    /// <summary>
    /// 시뮬레이션 1 Step 진행
    /// </summary>
    public StepResult Step()
    {
        var result = new StepResult
        {
            PreviousTime = _currentTime.Clone(),
            StepMinutes = _stepMinutes
        };

        // 1. 시간 진행
        _currentTime.AddMinutes(_stepMinutes);
        result.CurrentTime = _currentTime.Clone();

        // 2. 각 NPC 처리
        foreach (var npc in _npcs.Values)
        {
            ProcessNPC(npc, result);
        }

        // 3. 이벤트 발생
        OnStep?.Invoke(this, new StepEventArgs(result));

        return result;
    }

    /// <summary>
    /// 여러 Step 진행
    /// </summary>
    public List<StepResult> Step(int count)
    {
        var results = new List<StepResult>();
        for (int i = 0; i < count; i++)
        {
            results.Add(Step());
        }
        return results;
    }

    /// <summary>
    /// 개별 NPC 처리
    /// </summary>
    private void ProcessNPC(NPC npc, StepResult result)
    {
        if (npc.IsMoving)
        {
            // 이동 중인 NPC 처리
            ProcessMovingNPC(npc, result);
        }
        else
        {
            // 대기 중인 NPC 처리 (스케줄 확인)
            ProcessIdleNPC(npc, result);
        }
    }

    /// <summary>
    /// 이동 중인 NPC 처리
    /// </summary>
    private void ProcessMovingNPC(NPC npc, StepResult result)
    {
        if (npc.Movement == null)
        {
            npc.ArriveAtDestination();
            return;
        }

        // 이동 시간 경과
        npc.AddTravelTime(_stepMinutes);

        // 현재 구간 완료 확인
        if (npc.Movement.IsSegmentComplete)
        {
            if (npc.Movement.IsPathComplete)
            {
                // 최종 목적지 도착
                var arrival = new NPCArrivalInfo
                {
                    NPC = npc,
                    Destination = npc.Movement.FinalDestination,
                    ArrivalTime = _currentTime.Clone()
                };

                npc.ArriveAtDestination();
                result.Arrivals.Add(arrival);

                OnNPCArrival?.Invoke(this, new NPCArrivalEventArgs(arrival));
            }
            else
            {
                // 다음 구간으로
                if (npc.MoveToNextSegment())
                {
                    // 다음 구간 이동 시간 계산
                    SetupNextSegment(npc);
                }
            }
        }
    }

    /// <summary>
    /// 대기 중인 NPC 처리 (스케줄 확인)
    /// </summary>
    private void ProcessIdleNPC(NPC npc, StepResult result)
    {
        // 현재 스케줄 확인
        var activeSchedule = npc.Schedule.GetActiveSchedule(_currentTime);

        if (activeSchedule != null)
        {
            // 이미 목적지에 있는 경우
            if (npc.CurrentLocation == activeSchedule.Destination)
            {
                npc.SetCurrentSchedule(activeSchedule);
                return;
            }

            // 목적지로 이동 필요
            if (TryStartMovement(npc, activeSchedule.Destination))
            {
                npc.SetCurrentSchedule(activeSchedule);
                
                var movementInfo = new NPCMovementInfo
                {
                    NPC = npc,
                    From = npc.Movement!.From,
                    To = activeSchedule.Destination,
                    Schedule = activeSchedule,
                    StartTime = _currentTime.Clone()
                };

                result.MovementStarts.Add(movementInfo);
                OnNPCMovementStart?.Invoke(this, new NPCMovementEventArgs(movementInfo));
            }
        }
        else
        {
            // 다음 스케줄 확인
            var nextSchedule = npc.Schedule.GetNextSchedule(_currentTime);
            
            if (nextSchedule != null && nextSchedule.TimeRange.IsStartTime(_currentTime))
            {
                // 스케줄 시작 시간
                if (npc.CurrentLocation != nextSchedule.Destination)
                {
                    if (TryStartMovement(npc, nextSchedule.Destination))
                    {
                        npc.SetCurrentSchedule(nextSchedule);
                        
                        var movementInfo = new NPCMovementInfo
                        {
                            NPC = npc,
                            From = npc.Movement!.From,
                            To = nextSchedule.Destination,
                            Schedule = nextSchedule,
                            StartTime = _currentTime.Clone()
                        };

                        result.MovementStarts.Add(movementInfo);
                        OnNPCMovementStart?.Invoke(this, new NPCMovementEventArgs(movementInfo));
                    }
                }
            }

            npc.SetCurrentSchedule(null);
        }
    }

    /// <summary>
    /// NPC 이동 시작 시도
    /// </summary>
    private bool TryStartMovement(NPC npc, LocationRef destination)
    {
        // 이미 목적지에 있으면 불필요
        if (npc.CurrentLocation == destination)
            return false;

        // 경로 탐색
        var pathResult = _pathFinder.FindPath(npc.CurrentLocation, destination, npc.TraversalContext);

        if (!pathResult.Found || pathResult.Path.Count < 2)
            return false;

        // 이동 시작
        if (npc.StartMovement(pathResult.Path, destination))
        {
            // 첫 구간 이동 시간 설정
            SetupNextSegment(npc);
            return true;
        }

        return false;
    }

    /// <summary>
    /// NPC의 다음 이동 구간 설정
    /// </summary>
    private void SetupNextSegment(NPC npc)
    {
        if (npc.Movement == null)
            return;

        var path = npc.Movement.FullPath;
        var idx = npc.Movement.CurrentPathIndex;

        if (idx >= path.Count - 1)
            return;

        var current = path[idx];
        var next = path[idx + 1];

        // 같은 Region 내 이동인지 확인
        if (current.RegionId == next.RegionId)
        {
            var region = _world.GetRegion(current.RegionId);
            var edge = region?.GetEdgeBetween(current.LocalId, next.LocalId);
            
            if (edge != null)
            {
                var travelTime = edge.GetTravelTime(current);
                npc.SetSegmentTravelTime(travelTime >= 0 ? travelTime : 1);
                return;
            }
        }
        else
        {
            // Region 간 이동 - RegionEdge 찾기
            foreach (var regionEdge in _world.RegionEdges)
            {
                var locA = regionEdge.LocationA;
                var locB = regionEdge.LocationB;

                if ((locA.RegionId == current.RegionId && locA.LocalId == current.LocalId &&
                     locB.RegionId == next.RegionId && locB.LocalId == next.LocalId))
                {
                    var travelTime = regionEdge.TravelTimeAtoB >= 0 ? regionEdge.TravelTimeAtoB : 1;
                    npc.SetSegmentTravelTime(travelTime);
                    return;
                }
                else if ((locB.RegionId == current.RegionId && locB.LocalId == current.LocalId &&
                          locA.RegionId == next.RegionId && locA.LocalId == next.LocalId))
                {
                    var travelTime = regionEdge.TravelTimeBtoA >= 0 ? regionEdge.TravelTimeBtoA : 1;
                    npc.SetSegmentTravelTime(travelTime);
                    return;
                }
            }
        }

        // 기본값
        npc.SetSegmentTravelTime(1);
    }

    #endregion

    /// <summary>
    /// 현재 상태 요약
    /// </summary>
    public string GetStatusSummary()
    {
        var lines = new List<string>
        {
            $"=== {_world.Name ?? "GameWorld"} ===",
            $"Time: {_currentTime}",
            $"NPCs: {_npcs.Count}",
            ""
        };

        foreach (var npc in _npcs.Values)
        {
            lines.Add(npc.GetStatusSummary());
        }

        return string.Join(Environment.NewLine, lines);
    }
}

#region Event Args & Results

/// <summary>
/// Step 결과
/// </summary>
public class StepResult
{
    public GameTime PreviousTime { get; set; } = new();
    public GameTime CurrentTime { get; set; } = new();
    public int StepMinutes { get; set; }
    public List<NPCArrivalInfo> Arrivals { get; } = new();
    public List<NPCMovementInfo> MovementStarts { get; } = new();
}

/// <summary>
/// NPC 도착 정보
/// </summary>
public class NPCArrivalInfo
{
    public required NPC NPC { get; init; }
    public LocationRef Destination { get; init; }
    public GameTime ArrivalTime { get; init; } = new();
}

/// <summary>
/// NPC 이동 시작 정보
/// </summary>
public class NPCMovementInfo
{
    public required NPC NPC { get; init; }
    public LocationRef From { get; init; }
    public LocationRef To { get; init; }
    public ScheduleEntry? Schedule { get; init; }
    public GameTime StartTime { get; init; } = new();
}

/// <summary>
/// Step 이벤트 인자
/// </summary>
public class StepEventArgs : EventArgs
{
    public StepResult Result { get; }
    public StepEventArgs(StepResult result) => Result = result;
}

/// <summary>
/// NPC 도착 이벤트 인자
/// </summary>
public class NPCArrivalEventArgs : EventArgs
{
    public NPCArrivalInfo Arrival { get; }
    public NPCArrivalEventArgs(NPCArrivalInfo arrival) => Arrival = arrival;
}

/// <summary>
/// NPC 이동 시작 이벤트 인자
/// </summary>
public class NPCMovementEventArgs : EventArgs
{
    public NPCMovementInfo Movement { get; }
    public NPCMovementEventArgs(NPCMovementInfo movement) => Movement = movement;
}

#endregion
