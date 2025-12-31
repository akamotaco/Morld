namespace Morld;

using System;

/// <summary>
/// Character (캐릭터)
/// </summary>
public class Character
{
	private readonly string _id;
	private LocationRef _currentLocation;
	private EdgeProgress? _currentEdge;
	private ScheduleEntry? _currentSchedule;

	/// <summary>
	/// Character 고유 ID
	/// </summary>
	public string Id => _id;

	/// <summary>
	/// Character 이름
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
	/// 이동 중인지 여부 (CurrentEdge 기반)
	/// </summary>
	public bool IsMoving => _currentEdge != null;

	/// <summary>
	/// 대기 중인지 여부 (CurrentEdge 기반)
	/// </summary>
	public bool IsIdle => _currentEdge == null;

	public Character(string id, string name, LocationRef startLocation)
	{
		_id = id ?? throw new ArgumentNullException(nameof(id));
		Name = name ?? throw new ArgumentNullException(nameof(name));
		_currentLocation = startLocation;
		_currentEdge = null;
		Schedule = new DailySchedule();
		TraversalContext = new TraversalContext();
	}

	public Character(string id, string name, int regionId, int localId)
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
		return $"Character[{Id}] {Name} @ {_currentLocation} ({state})";
	}
}
