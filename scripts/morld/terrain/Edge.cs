namespace Morld;

using System;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// Region 내 Location 간의 양방향 엣지
/// </summary>
public class Edge
{
    private int _travelTimeAtoB;
    private int _travelTimeBtoA;
    private bool _isBlocked;

    /// <summary>
    /// Location A
    /// </summary>
    public Location LocationA { get; }

    /// <summary>
    /// Location B
    /// </summary>
    public Location LocationB { get; }

    /// <summary>
    /// 소속 Region (변경 추적용)
    /// </summary>
    internal Region? OwnerRegion { get; set; }

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
                OwnerRegion?.MarkAsChanged();
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
                OwnerRegion?.MarkAsChanged();
            }
        }
    }

    /// <summary>
    /// A → B 방향 이동 조건 (태그:필요값)
    /// </summary>
    public Dictionary<string, int> ConditionsAtoB { get; } = new();

    /// <summary>
    /// B → A 방향 이동 조건 (태그:필요값)
    /// </summary>
    public Dictionary<string, int> ConditionsBtoA { get; } = new();

    /// <summary>
    /// 엣지 완전 차단 여부
    /// </summary>
    public bool IsBlocked
    {
        get => _isBlocked;
        set
        {
            if (_isBlocked != value)
            {
                _isBlocked = value;
                OwnerRegion?.MarkAsChanged();
            }
        }
    }

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    public Edge(Location locationA, Location locationB)
    {
        LocationA = locationA ?? throw new ArgumentNullException(nameof(locationA));
        LocationB = locationB ?? throw new ArgumentNullException(nameof(locationB));
    }

    /// <summary>
    /// 양방향 동일한 이동 시간 설정
    /// </summary>
    public Edge SetTravelTime(int time)
    {
        _travelTimeAtoB = time;
        _travelTimeBtoA = time;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// 방향별 이동 시간 설정
    /// </summary>
    public Edge SetTravelTime(int aToB, int bToA)
    {
        _travelTimeAtoB = aToB;
        _travelTimeBtoA = bToA;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// A → B 방향 조건 추가
    /// </summary>
    public Edge AddConditionAtoB(string tag, int requiredValue)
    {
        ConditionsAtoB[tag] = requiredValue;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// B → A 방향 조건 추가
    /// </summary>
    public Edge AddConditionBtoA(string tag, int requiredValue)
    {
        ConditionsBtoA[tag] = requiredValue;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// 양방향 동일한 조건 추가
    /// </summary>
    public Edge AddCondition(string tag, int requiredValue)
    {
        ConditionsAtoB[tag] = requiredValue;
        ConditionsBtoA[tag] = requiredValue;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// A → B 방향 조건 제거
    /// </summary>
    public Edge RemoveConditionAtoB(string tag)
    {
        if (ConditionsAtoB.Remove(tag))
            OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// B → A 방향 조건 제거
    /// </summary>
    public Edge RemoveConditionBtoA(string tag)
    {
        if (ConditionsBtoA.Remove(tag))
            OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// 양방향 조건 제거
    /// </summary>
    public Edge RemoveCondition(string tag)
    {
        bool changed = ConditionsAtoB.Remove(tag);
        changed |= ConditionsBtoA.Remove(tag);
        if (changed)
            OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// 주어진 Location에서 반대편 Location 반환
    /// </summary>
    public Location GetOtherLocation(Location from)
    {
        if (from.Equals(LocationA)) return LocationB;
        if (from.Equals(LocationB)) return LocationA;
        throw new ArgumentException("Location is not part of this edge", nameof(from));
    }

    /// <summary>
    /// 주어진 방향으로 이동 가능한지 확인
    /// </summary>
    public bool CanTraverse(Location from, TraversalContext? context = null)
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
    public int GetTravelTime(Location from)
    {
        if (from.Equals(LocationA)) return TravelTimeAtoB;
        if (from.Equals(LocationB)) return TravelTimeBtoA;
        return -1;
    }

    /// <summary>
    /// 주어진 방향의 조건 반환
    /// </summary>
    public Dictionary<string, int> GetConditions(Location from)
    {
        if (from.Equals(LocationA)) return ConditionsAtoB;
        if (from.Equals(LocationB)) return ConditionsBtoA;
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

    public override string ToString()
    {
        var aToB = TravelTimeAtoB >= 0 ? TravelTimeAtoB.ToString() : "X";
        var bToA = TravelTimeBtoA >= 0 ? TravelTimeBtoA.ToString() : "X";
        return $"Edge[{LocationA} <--({bToA})--({aToB})--> {LocationB}]";
    }
}

/// <summary>
/// 경로 탐색 시 사용되는 컨텍스트 (현재 보유 Prop)
/// PropSet 기반
/// </summary>
public class TraversalContext
{
    private readonly PropSet _props = new();

    public static TraversalContext Empty { get; } = new();

    /// <summary>
    /// PropSet 직접 접근
    /// </summary>
    public PropSet Props => _props;

    /// <summary>
    /// Prop 설정 ("타입:이름" 형식)
    /// </summary>
    public TraversalContext SetProp(string fullName, int value)
    {
        _props.Set(fullName, value);
        return this;
    }

    /// <summary>
    /// Prop 설정 (Prop 구조체)
    /// </summary>
    public TraversalContext SetProp(Prop prop, int value)
    {
        _props.Set(prop, value);
        return this;
    }

    /// <summary>
    /// 여러 Prop 설정 (Dictionary)
    /// </summary>
    public TraversalContext SetProps(Dictionary<string, int> props)
    {
        foreach (var (fullName, value) in props)
            _props.Set(fullName, value);
        return this;
    }

    /// <summary>
    /// Prop 값 가져오기 ("타입:이름" 형식, 없으면 0)
    /// </summary>
    public int GetProp(string fullName)
    {
        return _props.Get(fullName);
    }

    /// <summary>
    /// Prop 값 가져오기 (Prop 구조체, 없으면 0)
    /// </summary>
    public int GetProp(Prop prop)
    {
        return _props.Get(prop);
    }

    /// <summary>
    /// 필요 값 이상인지 확인
    /// </summary>
    public bool HasProp(string fullName, int requiredValue) =>
        GetProp(fullName) >= requiredValue;

    /// <summary>
    /// Prop 존재 여부 (값 > 0)
    /// </summary>
    public bool HasProp(string fullName) =>
        GetProp(fullName) > 0;

    /// <summary>
    /// Prop 존재 여부 (Prop 구조체)
    /// </summary>
    public bool HasProp(Prop prop) =>
        _props.Has(prop);

    /// <summary>
    /// 특정 타입의 Prop만 가져오기
    /// </summary>
    public IEnumerable<(Prop Prop, int Value)> GetByType(string type) =>
        _props.GetByType(type);

    /// <summary>
    /// 모든 타입 가져오기
    /// </summary>
    public IEnumerable<string> GetTypes() =>
        _props.GetTypes();

    /// <summary>
    /// 조건 충족 여부 확인
    /// </summary>
    public bool MeetsConditions(Dictionary<string, int>? conditions) =>
        _props.MeetsConditions(conditions);

    public override string ToString()
    {
        if (_props.IsEmpty) return "Context[]";
        return $"Context[{_props}]";
    }
}
