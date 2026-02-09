namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// Region 간의 연결 (포탈, 게이트, 경계 등)
/// </summary>
public class RegionGate
{
    private float _distanceAtoB;
    private float _distanceBtoA;
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
                OwnerWorld?.MarkRegionGateAsChanged();
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
                OwnerWorld?.MarkRegionGateAsChanged();
            }
        }
    }

    /// <summary>
    /// 소속 Terrain (변경 추적용)
    /// </summary>
    internal Terrain? OwnerWorld { get; set; }

    /// <summary>
    /// A → B 방향 거리 (0 미만이면 이동 불가, 단위: location units)
    /// 이동 시간은 Location.DistanceToTime()으로 계산
    /// </summary>
    public float DistanceAtoB
    {
        get => _distanceAtoB;
        set
        {
            if (_distanceAtoB != value)
            {
                _distanceAtoB = value;
                OwnerWorld?.MarkRegionGateAsChanged();
            }
        }
    }

    /// <summary>
    /// B → A 방향 거리 (0 미만이면 이동 불가, 단위: location units)
    /// 이동 시간은 Location.DistanceToTime()으로 계산
    /// </summary>
    public float DistanceBtoA
    {
        get => _distanceBtoA;
        set
        {
            if (_distanceBtoA != value)
            {
                _distanceBtoA = value;
                OwnerWorld?.MarkRegionGateAsChanged();
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
                OwnerWorld?.MarkRegionGateAsChanged();
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

    public RegionGate(int id, LocationRef locationA, LocationRef locationB)
    {
        Id = id;
        _locationA = locationA;
        _locationB = locationB;
    }

    public RegionGate(int id, int regionIdA, int localIdA, int regionIdB, int localIdB)
        : this(id, new LocationRef(regionIdA, localIdA), new LocationRef(regionIdB, localIdB))
    {
    }

    /// <summary>
    /// 양방향 동일한 거리 설정
    /// </summary>
    public RegionGate SetDistance(float distance)
    {
        _distanceAtoB = distance;
        _distanceBtoA = distance;
        OwnerWorld?.MarkRegionGateAsChanged();
        return this;
    }

    /// <summary>
    /// 방향별 거리 설정
    /// </summary>
    public RegionGate SetDistance(float aToB, float bToA)
    {
        _distanceAtoB = aToB;
        _distanceBtoA = bToA;
        OwnerWorld?.MarkRegionGateAsChanged();
        return this;
    }

    /// <summary>
    /// A → B 방향 조건 추가
    /// </summary>
    public RegionGate AddConditionAtoB(string tag, int requiredValue)
    {
        ConditionsAtoB[tag] = requiredValue;
        OwnerWorld?.MarkRegionGateAsChanged();
        return this;
    }

    /// <summary>
    /// B → A 방향 조건 추가
    /// </summary>
    public RegionGate AddConditionBtoA(string tag, int requiredValue)
    {
        ConditionsBtoA[tag] = requiredValue;
        OwnerWorld?.MarkRegionGateAsChanged();
        return this;
    }

    /// <summary>
    /// 양방향 동일한 조건 추가
    /// </summary>
    public RegionGate AddCondition(string tag, int requiredValue)
    {
        ConditionsAtoB[tag] = requiredValue;
        ConditionsBtoA[tag] = requiredValue;
        OwnerWorld?.MarkRegionGateAsChanged();
        return this;
    }

    /// <summary>
    /// 주어진 위치에서 반대편 위치 반환
    /// </summary>
    public LocationRef GetOtherLocation(LocationRef from)
    {
        if (from == LocationA) return LocationB;
        if (from == LocationB) return LocationA;
        throw new ArgumentException("Location is not part of this gate", nameof(from));
    }

    /// <summary>
    /// 주어진 방향으로 이동 가능한지 확인
    /// </summary>
    public bool CanTraverse(LocationRef from, TraversalContext? context = null)
    {
        if (IsBlocked) return false;

        var distance = GetDistance(from);
        if (distance < 0) return false;

        var conditions = GetConditions(from);
        return CheckConditions(conditions, context);
    }

    /// <summary>
    /// 주어진 방향의 거리 반환 (0 미만이면 이동 불가, -1이면 유효하지 않은 위치)
    /// </summary>
    public float GetDistance(LocationRef from)
    {
        if (from == LocationA) return DistanceAtoB;
        if (from == LocationB) return DistanceBtoA;
        return -1f;
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
        var aToB = DistanceAtoB >= 0 ? DistanceAtoB.ToString("F0") : "X";
        var bToA = DistanceBtoA >= 0 ? DistanceBtoA.ToString("F0") : "X";
        return $"RegionGate[{(Name != "unknown" ? Name : Id.ToString())}]: {LocationA} <--({bToA})--({aToB})--> {LocationB}";
    }
}
