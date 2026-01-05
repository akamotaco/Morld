namespace Morld;

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// Prop 집합 (Prop → int 매핑)
/// Dictionary&lt;string, int&gt; 형태로도 사용 가능
/// </summary>
public class PropSet : IEnumerable<KeyValuePair<Prop, int>>
{
	private readonly Dictionary<Prop, int> _props = new();

	/// <summary>
	/// Prop 개수
	/// </summary>
	public int Count => _props.Count;

	/// <summary>
	/// 비어있는지
	/// </summary>
	public bool IsEmpty => _props.Count == 0;

	/// <summary>
	/// 빈 PropSet
	/// </summary>
	public static PropSet Empty { get; } = new();

	/// <summary>
	/// 모든 Prop (읽기 전용)
	/// </summary>
	public IReadOnlyDictionary<Prop, int> Props => _props;

	/// <summary>
	/// 인덱서 (Prop)
	/// </summary>
	public int this[Prop prop]
	{
		get => Get(prop);
		set => Set(prop, value);
	}

	/// <summary>
	/// 인덱서 (문자열 - "타입:이름")
	/// </summary>
	public int this[string fullName]
	{
		get => Get(fullName);
		set => Set(fullName, value);
	}

	#region Get/Set

	/// <summary>
	/// Prop 값 가져오기 (없으면 0)
	/// </summary>
	public int Get(Prop prop)
	{
		return _props.TryGetValue(prop, out var value) ? value : 0;
	}

	/// <summary>
	/// Prop 값 가져오기 (문자열 키, 없으면 0)
	/// </summary>
	public int Get(string fullName)
	{
		var prop = Prop.Parse(fullName);
		return prop.IsValid ? Get(prop) : 0;
	}

	/// <summary>
	/// Prop 값 설정
	/// </summary>
	public PropSet Set(Prop prop, int value)
	{
		if (!prop.IsValid) return this;

		if (value == 0)
			_props.Remove(prop);
		else
			_props[prop] = value;

		return this;
	}

	/// <summary>
	/// Prop 값 설정 (문자열 키)
	/// </summary>
	public PropSet Set(string fullName, int value)
	{
		var prop = Prop.Parse(fullName);
		return prop.IsValid ? Set(prop, value) : this;
	}

	/// <summary>
	/// Prop 값 증가
	/// </summary>
	public PropSet Add(Prop prop, int delta)
	{
		if (!prop.IsValid || delta == 0) return this;
		return Set(prop, Get(prop) + delta);
	}

	/// <summary>
	/// Prop 값 증가 (문자열 키)
	/// </summary>
	public PropSet Add(string fullName, int delta)
	{
		var prop = Prop.Parse(fullName);
		return prop.IsValid ? Add(prop, delta) : this;
	}

	/// <summary>
	/// Prop 제거
	/// </summary>
	public bool Remove(Prop prop)
	{
		return _props.Remove(prop);
	}

	/// <summary>
	/// Prop 제거 (문자열 키)
	/// </summary>
	public bool Remove(string fullName)
	{
		var prop = Prop.Parse(fullName);
		return prop.IsValid && _props.Remove(prop);
	}

	/// <summary>
	/// 모든 Prop 제거
	/// </summary>
	public void Clear()
	{
		_props.Clear();
	}

	#endregion

	#region Query

	/// <summary>
	/// Prop 존재 여부 (값 > 0)
	/// </summary>
	public bool Has(Prop prop)
	{
		return Get(prop) > 0;
	}

	/// <summary>
	/// Prop 존재 여부 (문자열 키)
	/// </summary>
	public bool Has(string fullName)
	{
		return Get(fullName) > 0;
	}

	/// <summary>
	/// 필요 값 이상인지 확인
	/// </summary>
	public bool HasAtLeast(Prop prop, int requiredValue)
	{
		return Get(prop) >= requiredValue;
	}

	/// <summary>
	/// 필요 값 이상인지 확인 (문자열 키)
	/// </summary>
	public bool HasAtLeast(string fullName, int requiredValue)
	{
		return Get(fullName) >= requiredValue;
	}

	/// <summary>
	/// 특정 타입의 Prop만 가져오기
	/// </summary>
	public IEnumerable<(Prop Prop, int Value)> GetByType(string type)
	{
		return _props
			.Where(kv => kv.Key.Type == type)
			.Select(kv => (kv.Key, kv.Value));
	}

	/// <summary>
	/// 특정 타입의 Prop 이름과 값만 가져오기
	/// </summary>
	public IEnumerable<(string Name, int Value)> GetNamesByType(string type)
	{
		return _props
			.Where(kv => kv.Key.Type == type)
			.Select(kv => (kv.Key.Name, kv.Value));
	}

	/// <summary>
	/// 모든 타입 가져오기 (중복 제거)
	/// </summary>
	public IEnumerable<string> GetTypes()
	{
		return _props.Keys.Select(p => p.Type).Distinct();
	}

	/// <summary>
	/// 조건 충족 여부 확인 (모든 조건 충족 시 true)
	/// </summary>
	public bool MeetsConditions(PropSet conditions)
	{
		if (conditions == null || conditions.IsEmpty) return true;

		foreach (var (prop, requiredValue) in conditions)
		{
			if (Get(prop) < requiredValue)
				return false;
		}
		return true;
	}

	/// <summary>
	/// 조건 충족 여부 확인 (Dictionary 형태)
	/// </summary>
	public bool MeetsConditions(Dictionary<string, int>? conditions)
	{
		if (conditions == null || conditions.Count == 0) return true;

		foreach (var (fullName, requiredValue) in conditions)
		{
			if (Get(fullName) < requiredValue)
				return false;
		}
		return true;
	}

	#endregion

	#region Merge/Clone

	/// <summary>
	/// 다른 PropSet 병합 (값 합산)
	/// </summary>
	public PropSet Merge(PropSet other)
	{
		if (other == null) return this;

		foreach (var (prop, value) in other)
		{
			Add(prop, value);
		}
		return this;
	}

	/// <summary>
	/// Dictionary에서 병합
	/// </summary>
	public PropSet Merge(Dictionary<string, int>? dict)
	{
		if (dict == null) return this;

		foreach (var (fullName, value) in dict)
		{
			Add(fullName, value);
		}
		return this;
	}

	/// <summary>
	/// 복제본 생성
	/// </summary>
	public PropSet Clone()
	{
		var clone = new PropSet();
		foreach (var (prop, value) in _props)
		{
			clone._props[prop] = value;
		}
		return clone;
	}

	#endregion

	#region Conversion

	/// <summary>
	/// Dictionary&lt;string, int&gt;로 변환 (FullName 키)
	/// </summary>
	public Dictionary<string, int> ToDictionary()
	{
		return _props.ToDictionary(kv => kv.Key.FullName, kv => kv.Value);
	}

	/// <summary>
	/// Dictionary&lt;string, int&gt;에서 생성
	/// </summary>
	public static PropSet FromDictionary(Dictionary<string, int>? dict)
	{
		var set = new PropSet();
		if (dict != null)
		{
			foreach (var (fullName, value) in dict)
			{
				set.Set(fullName, value);
			}
		}
		return set;
	}

	#endregion

	#region IEnumerable

	public IEnumerator<KeyValuePair<Prop, int>> GetEnumerator()
	{
		return _props.GetEnumerator();
	}

	IEnumerator IEnumerable.GetEnumerator()
	{
		return GetEnumerator();
	}

	#endregion

	public override string ToString()
	{
		if (_props.Count == 0) return "PropSet (empty)";

		var items = _props.Select(kv => $"{kv.Key}={kv.Value}");
		return $"PropSet[{string.Join(", ", items)}]";
	}
}
