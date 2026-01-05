namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// Region 간의 연결 (포탈, 게이트, 경계 등)
/// </summary>
public class RegionEdge
{
    private int _travelTimeAtoB;
    private int _travelTimeBtoA;
    private bool _isBlocked;

    /// <summary>
    /// 연결 고유 ID
    /// </summary>
    public int Id { get; }

    private LocationRef _locationA;
    private LocationRef _locationB;

    /// <summary>
    /// Region A의 연결 Location (운전 시 변경 가능)
    /// </summary>
    public LocationRef LocationA
    {
        get => _locationA;
        set
        {
            if (_locationA != value)
            {
                _locationA = value;
                OwnerWorld?.MarkRegionEdgeAsChanged();
            }
        }
    }

    /// <summary>
    /// Region B의 연결 Location (운전 시 변경 가능)
    /// </summary>
    public LocationRef LocationB
    {
        get => _locationB;
        set
        {
            if (_locationB != value)
            {
                _locationB = value;
                OwnerWorld?.MarkRegionEdgeAsChanged();
            }
        }
    }

    /// <summary>
    /// 소속 Terrain (변경 추적용)
    /// </summary>
    internal Terrain? OwnerWorld { get; set; }

    /// <summary>
    /// A → B 방향 이동 시간 (0 미만이면 이동 불가, 단위: 분)
    /// </summary>
    public int TravelTimeAtoB
    {
        get => _travelTimeAtoB;
        set
        {
            if (_travelTimeAtoB != value)
            {
                _travelTimeAtoB = value;
                OwnerWorld?.MarkRegionEdgeAsChanged();
            }
        }
    }

    /// <summary>
    /// B → A 방향 이동 시간 (0 미만이면 이동 불가, 단위: 분)
    /// </summary>
    public int TravelTimeBtoA
    {
        get => _travelTimeBtoA;
        set
        {
            if (_travelTimeBtoA != value)
            {
                _travelTimeBtoA = value;
                OwnerWorld?.MarkRegionEdgeAsChanged();
            }
        }
    }

    /// <summary>
    /// A → B 방향 이동 조건
    /// </summary>
    public Dictionary<string, int> ConditionsAtoB { get; } = new();

    /// <summary>
    /// B → A 방향 이동 조건
    /// </summary>
    public Dictionary<string, int> ConditionsBtoA { get; } = new();

    /// <summary>
    /// 연결 차단 여부
    /// </summary>
    public bool IsBlocked
    {
        get => _isBlocked;
        set
        {
            if (_isBlocked != value)
            {
                _isBlocked = value;
                OwnerWorld?.MarkRegionEdgeAsChanged();
            }
        }
    }

    /// <summary>
    /// 연결 이름/설명
    /// </summary>
    public string Name { get; set; } = "unknown";

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    public RegionEdge(int id, LocationRef locationA, LocationRef locationB)
    {
        Id = id;
        _locationA = locationA;
        _locationB = locationB;
    }

    public RegionEdge(int id, int regionIdA, int localIdA, int regionIdB, int localIdB)
        : this(id, new LocationRef(regionIdA, localIdA), new LocationRef(regionIdB, localIdB))
    {
    }

    /// <summary>
    /// 양방향 동일한 이동 시간 설정
    /// </summary>
    public RegionEdge SetTravelTime(int time)
    {
        _travelTimeAtoB = time;
        _travelTimeBtoA = time;
        OwnerWorld?.MarkRegionEdgeAsChanged();
        return this;
    }

    /// <summary>
    /// 방향별 이동 시간 설정
    /// </summary>
    public RegionEdge SetTravelTime(int aToB, int bToA)
    {
        _travelTimeAtoB = aToB;
        _travelTimeBtoA = bToA;
        OwnerWorld?.MarkRegionEdgeAsChanged();
        return this;
    }

    /// <summary>
    /// A → B 방향 조건 추가
    /// </summary>
    public RegionEdge AddConditionAtoB(string tag, int requiredValue)
    {
        ConditionsAtoB[tag] = requiredValue;
        OwnerWorld?.MarkRegionEdgeAsChanged();
        return this;
    }

    /// <summary>
    /// B → A 방향 조건 추가
    /// </summary>
    public RegionEdge AddConditionBtoA(string tag, int requiredValue)
    {
        ConditionsBtoA[tag] = requiredValue;
        OwnerWorld?.MarkRegionEdgeAsChanged();
        return this;
    }

    /// <summary>
    /// 양방향 동일한 조건 추가
    /// </summary>
    public RegionEdge AddCondition(string tag, int requiredValue)
    {
        ConditionsAtoB[tag] = requiredValue;
        ConditionsBtoA[tag] = requiredValue;
        OwnerWorld?.MarkRegionEdgeAsChanged();
        return this;
    }

    /// <summary>
    /// 주어진 위치에서 반대편 위치 반환
    /// </summary>
    public LocationRef GetOtherLocation(LocationRef from)
    {
        if (from == LocationA) return LocationB;
        if (from == LocationB) return LocationA;
        throw new ArgumentException("Location is not part of this edge", nameof(from));
    }

    /// <summary>
    /// 주어진 방향으로 이동 가능한지 확인
    /// </summary>
    public bool CanTraverse(LocationRef from, TraversalContext? context = null)
    {
        if (IsBlocked) return false;

        var travelTime = GetTravelTime(from);
        if (travelTime < 0) return false;

        var conditions = GetConditions(from);
        return CheckConditions(conditions, context);
    }

    /// <summary>
    /// 주어진 방향의 이동 시간 반환 (0 미만이면 이동 불가, -1이면 유효하지 않은 위치)
    /// </summary>
    public int GetTravelTime(LocationRef from)
    {
        if (from == LocationA) return TravelTimeAtoB;
        if (from == LocationB) return TravelTimeBtoA;
        return -1;
    }

    /// <summary>
    /// 주어진 방향의 조건 반환
    /// </summary>
    public Dictionary<string, int> GetConditions(LocationRef from)
    {
        if (from == LocationA) return ConditionsAtoB;
        if (from == LocationB) return ConditionsBtoA;
        return new Dictionary<string, int>();
    }

    private bool CheckConditions(Dictionary<string, int> conditions, TraversalContext? context)
    {
        if (conditions.Count == 0) return true;
        if (context == null) return false;

        foreach (var (propName, requiredValue) in conditions)
        {
            if (!context.HasProp(propName, requiredValue))
                return false;
        }
        return true;
    }

    /// <summary>
    /// 특정 Region에 연결되어 있는지 확인
    /// </summary>
    public bool ConnectsRegion(int regionId)
    {
        return LocationA.RegionId == regionId || LocationB.RegionId == regionId;
    }

    /// <summary>
    /// 특정 Region에서의 연결 Location 반환
    /// </summary>
    public LocationRef? GetLocationInRegion(int regionId)
    {
        if (LocationA.RegionId == regionId) return LocationA;
        if (LocationB.RegionId == regionId) return LocationB;
        return null;
    }

    public override string ToString()
    {
        var aToB = TravelTimeAtoB >= 0 ? TravelTimeAtoB.ToString() : "X";
        var bToA = TravelTimeBtoA >= 0 ? TravelTimeBtoA.ToString() : "X";
        return $"RegionEdge[{(Name != "unknown" ? Name : Id.ToString())}]: {LocationA} <--({bToA})--({aToB})--> {LocationB}";
    }
}
