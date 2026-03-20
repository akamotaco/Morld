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

    /// <summary>
    /// 문자열 Prop 저장소 (세력, vehicle:status 등 문자열 값용)
    /// int PropSet과 병렬 — lazy 초기화
    /// </summary>
    private Dictionary<string, string>? _stringProps;

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

    #region String Props

    /// <summary>
    /// 문자열 Prop 설정 ("타입:이름" 형식)
    /// null 또는 빈 문자열이면 삭제
    /// </summary>
    public TraversalContext SetStringProp(string fullName, string? value)
    {
        if (string.IsNullOrEmpty(value))
        {
            _stringProps?.Remove(fullName);
            return this;
        }
        _stringProps ??= new Dictionary<string, string>();
        _stringProps[fullName] = value;
        return this;
    }

    /// <summary>
    /// 문자열 Prop 값 가져오기 (없으면 null)
    /// </summary>
    public string? GetStringProp(string fullName)
    {
        if (_stringProps == null) return null;
        return _stringProps.TryGetValue(fullName, out var value) ? value : null;
    }

    /// <summary>
    /// 문자열 Prop 존재 여부
    /// </summary>
    public bool HasStringProp(string fullName)
    {
        return _stringProps != null && _stringProps.ContainsKey(fullName);
    }

    /// <summary>
    /// 문자열 Prop 삭제
    /// </summary>
    public bool RemoveStringProp(string fullName)
    {
        return _stringProps?.Remove(fullName) ?? false;
    }

    /// <summary>
    /// 모든 문자열 Prop (없으면 null)
    /// </summary>
    public IReadOnlyDictionary<string, string>? StringProps => _stringProps;

    #endregion

    public override string ToString()
    {
        var intPart = _props.IsEmpty ? "" : _props.ToString();
        var strCount = _stringProps?.Count ?? 0;
        if (intPart == "" && strCount == 0) return "Context[]";
        var strPart = strCount > 0
            ? string.Join(", ", _stringProps!.Select(kv => $"{kv.Key}=\"{kv.Value}\""))
            : "";
        if (intPart != "" && strPart != "")
            return $"Context[{intPart}, {strPart}]";
        return $"Context[{(intPart != "" ? intPart : strPart)}]";
    }
}
