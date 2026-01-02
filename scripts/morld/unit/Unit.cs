namespace Morld;

using System;
using System.Collections.Generic;
using SE;

/// <summary>
/// Unit (유닛) - 캐릭터와 오브젝트 통합
/// </summary>
public class Unit : IDescribable
{
	private readonly int _id;
	private LocationRef _currentLocation;
	private EdgeProgress? _currentEdge;
	private ScheduleEntry? _currentSchedule;

	/// <summary>
	/// Unit 고유 ID
	/// </summary>
	public int Id => _id;

	/// <summary>
	/// Unit 이름
	/// </summary>
	public string Name { get; set; }

	/// <summary>
	/// 현재 Location (이동 중이면 출발지)
	/// </summary>
	public LocationRef CurrentLocation => _currentLocation;

	/// <summary>
	/// 이동 중 Edge 위에 있는 경우의 정보 (저장 대상)
	/// null이면 Location에 있음, 값이 있으면 Edge 위에서 이동 중
	/// </summary>
	public EdgeProgress? CurrentEdge
	{
		get => _currentEdge;
		set => _currentEdge = value;
	}

	/// <summary>
	/// 현재 수행 중인 스케줄 엔트리 (시간 기반 스케줄에서)
	/// </summary>
	public ScheduleEntry? CurrentSchedule => _currentSchedule;

	/// <summary>
	/// 스케줄 스택 (LIFO)
	/// 최상위 레이어가 현재 활성 스케줄
	/// </summary>
	public Stack<ScheduleLayer> ScheduleStack { get; private set; } = new();

	/// <summary>
	/// 현재 활성 스케줄 레이어 (스택 최상위)
	/// </summary>
	public ScheduleLayer? CurrentScheduleLayer =>
		ScheduleStack.Count > 0 ? ScheduleStack.Peek() : null;

	/// <summary>
	/// 이동 조건 (태그)
	/// </summary>
	public TraversalContext TraversalContext { get; }

	/// <summary>
	/// 추가 데이터
	/// </summary>
	public object? Tag { get; set; }


	/// <summary>
	/// Unit 타입 (Male, Female, Object)
	/// </summary>
	public UnitType Type { get; set; } = UnitType.Male;

	/// <summary>
	/// 오브젝트 여부 (Type == Object)
	/// </summary>
	public bool IsObject => Type == UnitType.Object;

	/// <summary>
	/// 가능한 액션 (통합: "talk", "trade", "use", "open" 등)
	/// </summary>
	public List<string> Actions { get; set; } = new();

	/// <summary>
	/// 상황별 외관 묘사 텍스트 (IDescribable)
	/// 감정/표정 태그 기반: "default", "기쁨", "슬픔", "분노", "긴장" 등
	/// </summary>
	public Dictionary<string, string> Appearance { get; set; } = new();

	/// <summary>
	/// 현재 감정/표정 상태 (Appearance 매칭용)
	/// </summary>
	public HashSet<string> Mood { get; set; } = new();

	/// <summary>
	/// 이동 중인지 여부 (CurrentEdge 기반)
	/// </summary>
	public bool IsMoving => _currentEdge != null;

	/// <summary>
	/// 대기 중인지 여부 (CurrentEdge 기반)
	/// </summary>
	public bool IsIdle => _currentEdge == null;

	public Unit(int id, string name, LocationRef startLocation)
	{
		_id = id;
		Name = name ?? throw new ArgumentNullException(nameof(name));
		_currentLocation = startLocation;
		_currentEdge = null;
		TraversalContext = new TraversalContext();
	}

	public Unit(int id, string name, int regionId, int localId)
		: this(id, name, new LocationRef(regionId, localId))
	{
	}

	/// <summary>
	/// 현재 위치 설정 (MovementSystem에서 사용)
	/// </summary>
	public void SetCurrentLocation(LocationRef location)
	{
		_currentLocation = location;
	}

	/// <summary>
	/// 현재 위치로 즉시 이동 (디버그/초기화용)
	/// </summary>
	public void SetLocation(LocationRef location)
	{
		_currentLocation = location;
		_currentEdge = null;
	}

	/// <summary>
	/// 현재 스케줄 엔트리 설정 (시간 기반 스케줄에서)
	/// </summary>
	internal void SetCurrentSchedule(ScheduleEntry? schedule)
	{
		_currentSchedule = schedule;
	}

	/// <summary>
	/// 스케줄 레이어 push
	/// </summary>
	public void PushSchedule(ScheduleLayer layer)
	{
		ScheduleStack.Push(layer);
	}

	/// <summary>
	/// 스케줄 레이어 pop (스택이 비어있으면 null 반환)
	/// </summary>
	public ScheduleLayer? PopSchedule()
	{
		return ScheduleStack.Count > 0 ? ScheduleStack.Pop() : null;
	}

	/// <summary>
	/// 스케줄 스택 초기화
	/// </summary>
	public void ClearScheduleStack()
	{
		ScheduleStack.Clear();
	}

	/// <summary>
	/// 아이템 효과가 반영된 최종 태그 계산 (매 호출 시 계산)
	/// inventoryData: (inventory, equippedItems) 튜플
	/// </summary>
	public TraversalContext GetActualTags(
		ItemSystem? itemSystem,
		IReadOnlyDictionary<int, int>? inventory = null,
		IReadOnlyList<int>? equippedItems = null)
	{
		var result = new TraversalContext();

		// 1. 기본 태그 복사
		foreach (var (tag, value) in TraversalContext.Tags)
		{
			result.SetTag(tag, value);
		}

		if (itemSystem == null)
			return result;

		// 2. 인벤토리 아이템의 PassiveTags 합산 (소유 효과)
		if (inventory != null)
		{
			foreach (var (itemId, count) in inventory)
			{
				if (count <= 0) continue;
				var item = itemSystem.GetItem(itemId);
				if (item == null) continue;

				foreach (var (tag, bonus) in item.PassiveTags)
				{
					var current = result.GetTagValue(tag);
					result.SetTag(tag, current + bonus);
				}
			}
		}

		// 3. 장착 아이템의 EquipTags 합산 (장착 효과)
		if (equippedItems != null)
		{
			foreach (var itemId in equippedItems)
			{
				var item = itemSystem.GetItem(itemId);
				if (item == null) continue;

				foreach (var (tag, bonus) in item.EquipTags)
				{
					var current = result.GetTagValue(tag);
					result.SetTag(tag, current + bonus);
				}
			}
		}

		return result;
	}

	/// <summary>
	/// 주어진 조건들을 모두 충족하는지 확인
	/// </summary>
	public bool CanPass(
		Dictionary<string, int>? conditions,
		ItemSystem? itemSystem,
		IReadOnlyDictionary<int, int>? inventory = null,
		IReadOnlyList<int>? equippedItems = null)
	{
		if (conditions == null || conditions.Count == 0)
			return true;

		var actualTags = GetActualTags(itemSystem, inventory, equippedItems);

		foreach (var (tag, requiredValue) in conditions)
		{
			if (actualTags.GetTagValue(tag) < requiredValue)
				return false;
		}

		return true;
	}

	/// <summary>
	/// 상태 요약
	/// </summary>
	public string GetStatusSummary()
	{
		if (_currentEdge != null)
		{
			return $"{Name}: {_currentEdge}";
		}
		else
		{
			var scheduleInfo = _currentSchedule != null
				? $" ({_currentSchedule.Name})"
				: "";
			return $"{Name}: {_currentLocation}에서 대기 중{scheduleInfo}";
		}
	}

	public override string ToString()
	{
		var state = _currentEdge != null ? "Moving" : "Idle";
		return $"Unit[{Id}] {Name} ({Type}) @ {_currentLocation} ({state})";
	}
}
