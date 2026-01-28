namespace Morld;

using System.Collections.Generic;
using System.Linq;

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
