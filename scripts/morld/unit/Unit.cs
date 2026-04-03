namespace Morld;

using System;
using System.Collections.Generic;
using SE;
using Vec2 = Godot.Vector2;

/// <summary>
/// Unit (유닛) - 캐릭터와 오브젝트 통합
/// Note: Unit은 Appearance를 사용하고, IDescribable(DescribeText)은 Region/Location용
/// </summary>
public class Unit : IOwnable
{
	private readonly int _id;
	private LocationRef _currentLocation;
	private MovementProgress? _currentMovement;  // Pi-World 2D 이동

	/// <summary>
	/// 앉은 상태 해제 시 콜백 (UnitSystem에서 오브젝트 측 정리용)
	/// 파라미터: (unitId, objectId)
	/// </summary>
	public Action<int, int>? OnSeatedStateClearing;

	/// <summary>
	/// Unit 고유 ID
	/// </summary>
	public int Id => _id;

	/// <summary>
	/// Python Asset의 unique_id (예: "sera", "mila")
	/// </summary>
	public string UniqueId { get; set; }

	/// <summary>
	/// Unit 이름
	/// </summary>
	public string Name { get; set; }

	/// <summary>
	/// 소유자 unique_id (예: "sera", "mila") - null이면 공용
	/// </summary>
	public string? Owner { get; set; }

	/// <summary>
	/// 현재 Location (이동 중이면 출발지)
	/// </summary>
	public LocationRef CurrentLocation => _currentLocation;

	#region Pi-World 2D 위치

	/// <summary>
	/// Location 내 2D 위치 (Pi-World)
	/// 이동 중이면 보간된 현재 위치, 정지 상태면 저장된 위치 반환
	/// </summary>
	public Vec2 Position
	{
		get
		{
			float x = _currentMovement?.CurrentX ?? _position.X;
			float y = _position.Y;  // Y는 보간 없음 (v0.3.0 Phase 1)
			return new Vec2(x, y);
		}
		set => _position = value;
	}
	private Vec2 _position = Vec2.Zero;

	/// <summary>
	/// Location 내 X 좌표 — Position.X 래퍼 (하위 호환)
	/// </summary>
	public float PositionX
	{
		get => Position.X;
		set => _position = new Vec2(value, _position.Y);
	}

	/// <summary>
	/// Location 내 Y 좌표 — Position.Y 래퍼 (하위 호환)
	/// </summary>
	public float PositionY
	{
		get => Position.Y;
		set => _position = new Vec2(_position.X, value);
	}

	/// <summary>
	/// AABB 충돌 크기 (Pi-World 2D)
	/// 캐릭터 기본값: (30, 60), 오브젝트는 개별 설정
	/// </summary>
	public Vec2 CollisionSize { get; set; } = new Vec2(30f, 60f);

	/// <summary>
	/// 충돌 활성화 여부
	/// </summary>
	public bool CollisionEnabled { get; set; } = false;

	#region Physics (v0.3.0 Phase 2)

	/// <summary>속도 X (픽셀/초)</summary>
	public float VelocityX { get; set; } = 0f;

	/// <summary>속도 Y (픽셀/초, 양수=하강)</summary>
	public float VelocityY { get; set; } = 0f;

	/// <summary>이전 프레임 위치 (Swept 충돌 검사용)</summary>
	public Vec2 PrevPosition { get; set; } = Vec2.Zero;

	/// <summary>지면 위에 있는지 여부</summary>
	public bool IsGrounded { get; set; } = true;

	/// <summary>↓+점프 관통 중 (Semi-solid drop-through)</summary>
	public bool IsDropping { get; set; } = false;

	#endregion

	/// <summary>
	/// 2D 이동 진행 정보 (Pi-World)
	/// null이면 이동 중이 아님
	/// </summary>
	public MovementProgress? CurrentMovement
	{
		get => _currentMovement;
		set => _currentMovement = value;
	}

	/// <summary>
	/// 2D 이동 중인지 여부 (Pi-World)
	/// </summary>
	public bool IsMoving2D => _currentMovement != null;

	#endregion

	/// <summary>
	/// 기본 스케줄 (DailySchedule) - JobList 채우기용
	/// </summary>
	public DailySchedule? BaseSchedule { get; set; }

	/// <summary>
	/// Job 목록 (시간 기반 선형 리스트)
	/// </summary>
	public JobList JobList { get; private set; } = new();

	/// <summary>
	/// 현재 Job
	/// </summary>
	public Job? CurrentJob => JobList.Current;

	/// <summary>
	/// 이동 조건 (태그)
	/// </summary>
	public TraversalContext TraversalContext { get; }

	/// <summary>
	/// 추가 데이터
	/// </summary>
	public object? Tag { get; set; }


	/// <summary>
	/// Unit 타입 (Character, Object)
	/// </summary>
	public UnitType Type { get; set; } = UnitType.Character;

	/// <summary>
	/// 오브젝트 여부 (Type == Object)
	/// </summary>
	public bool IsObject => Type == UnitType.Object;

	/// <summary>
	/// 생물 여부 (Type == Creature)
	/// </summary>
	public bool IsCreature => Type == UnitType.Creature;

	/// <summary>
	/// 인벤토리 아이템 개수를 이름 옆에 표시할지 여부 (오브젝트용)
	/// true: "바닥 (아이템 3개)" 형식으로 표시
	/// false: "서랍" 형식으로 이름만 표시 (기본값)
	/// </summary>
	public bool ItemVisible { get; set; } = false;

	/// <summary>
	/// 이벤트 추적 활성화 (오브젝트용 수동 활성화)
	/// 캐릭터는 자동으로 이벤트 생성, 오브젝트는 이 값이 true일 때만 생성
	/// </summary>
	public bool EventTracking { get; set; } = false;

	/// <summary>
	/// 이벤트 생성 여부
	/// 캐릭터: 자동으로 true
	/// 오브젝트: EventTracking이 true일 때만 true
	/// </summary>
	public bool GeneratesEvents => !IsObject || EventTracking;

	/// <summary>
	/// 가능한 액션 (통합: "talk", "trade", "use", "open" 등)
	/// </summary>
	public List<string> Actions { get; set; } = new();

	/// <summary>
	/// 액션별 활성화 상태 (액션명 = 값)
	/// 값이 1 이상이면 활성화, 0 이하면 비활성화
	/// 예: {"call:talk:대화": 1, "call:trade:거래": 1}
	/// </summary>
	public Dictionary<string, int> ActionProps { get; set; } = new();

	/// <summary>
	/// 상황별 외관 묘사 텍스트 (감정/Activity 기반)
	/// 감정/표정 태그 기반: "default", "기쁨", "슬픔", "분노", "긴장" 등
	/// Python에서는 focus_text로 대체됨
	/// </summary>
	public Dictionary<string, string> Appearance { get; set; } = new();

	/// <summary>
	/// 현재 감정/표정 상태 (Appearance 매칭용)
	/// </summary>
	public HashSet<string> Mood { get; set; } = new();

	/// <summary>
	/// 이동 중인지 여부 (Pi-World: CurrentMovement가 있음)
	/// </summary>
	public bool IsMoving => _currentMovement != null;

	/// <summary>
	/// 대기 중인지 여부 (이동 중이 아님)
	/// </summary>
	public bool IsIdle => _currentMovement == null;

	/// <summary>
	/// 목적지로 이동 중인지 여부 (논리적 상태: Job 목적지와 현재 위치 비교)
	/// true: 현재 위치 != Job 목적지, false: 도착했거나 Job이 없음
	/// </summary>
	public bool IsTraveling
	{
		get
		{
			var job = CurrentJob;
			if (job == null)
				return false;

			var jobLoc = job.GetLocationRef();
			return _currentLocation.RegionId != jobLoc.RegionId ||
				   _currentLocation.LocalId != jobLoc.LocalId;
		}
	}

	/// <summary>
	/// 경유지 지체 남은 시간 (밀리초)
	/// Location.StayDuration만큼 설정되어 지체 후 이동
	/// 0이면 지체 중이 아님
	/// </summary>
	public int RemainingStayTime { get; set; } = 0;

	/// <summary>
	/// Python Agent가 계획한 이동 경로
	/// ThinkSystem에서 설정, JobBehaviorSystem에서 실행
	/// </summary>
	public List<LocationRef> PlannedRoute { get; set; } = new();

	/// <summary>
	/// 현재 경로 진행 위치 (PlannedRoute 인덱스)
	/// </summary>
	public int RouteIndex { get; set; } = 0;

	/// <summary>
	/// 계획된 경로가 있는지 여부
	/// </summary>
	public bool HasPlannedRoute => PlannedRoute.Count > 0 && RouteIndex < PlannedRoute.Count;

	/// <summary>
	/// 다음 이동 목적지 (PlannedRoute[RouteIndex])
	/// </summary>
	public LocationRef? NextRouteDestination =>
		HasPlannedRoute ? PlannedRoute[RouteIndex] : null;

	/// <summary>
	/// 경로 설정 (Python Agent에서 호출)
	/// </summary>
	public void SetRoute(List<LocationRef> route)
	{
		PlannedRoute = route ?? new List<LocationRef>();
		RouteIndex = 0;
	}

	/// <summary>
	/// 경로 진행 (다음 위치로)
	/// </summary>
	public void AdvanceRoute()
	{
		if (RouteIndex < PlannedRoute.Count)
			RouteIndex++;
	}

	/// <summary>
	/// 경로 초기화
	/// </summary>
	public void ClearRoute()
	{
		PlannedRoute.Clear();
		RouteIndex = 0;
	}

	public Unit(int id, string name, LocationRef startLocation)
	{
		_id = id;
		Name = name ?? throw new ArgumentNullException(nameof(name));
		_currentLocation = startLocation;
		TraversalContext = new TraversalContext();
	}

	public Unit(int id, string name, int regionId, int localId)
		: this(id, name, new LocationRef(regionId, localId))
	{
	}

	/// <summary>
	/// 현재 위치 설정 (JobBehaviorSystem에서 사용)
	/// 다른 위치로 이동 시 앉은 상태 자동 해제
	/// </summary>
	public void SetCurrentLocation(LocationRef location)
	{
		// 위치가 변경되면 앉은 상태 해제 (다른 장소의 의자에 앉아있는 버그 방지)
		if (_currentLocation != location)
		{
			ClearSeatedState();
		}
		_currentLocation = location;
	}

	/// <summary>
	/// 현재 위치로 즉시 이동 (디버그/초기화용)
	/// 다른 위치로 이동 시 앉은 상태 자동 해제
	/// </summary>
	public void SetLocation(LocationRef location)
	{
		// 위치가 변경되면 앉은 상태 해제
		if (_currentLocation != location)
		{
			ClearSeatedState();
		}
		_currentLocation = location;
		_currentMovement = null;  // Pi-World: 이동 초기화
	}

	/// <summary>
	/// 2D 위치로 즉시 이동 (Pi-World)
	/// </summary>
	public void SetLocation2D(LocationRef location, float x, float y = 0f)
	{
		SetLocation(location);
		Position = new Vec2(x, y);
	}

	/// <summary>
	/// 앉은 상태 해제 (위치 변경 시 자동 호출)
	/// 캐릭터 측 seated_on 제거 + 콜백으로 오브젝트 측 seated_by 정리
	/// </summary>
	private void ClearSeatedState()
	{
		var seatedOn = TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
		if (seatedOn.Prop.IsValid)
		{
			// 오브젝트 측 정리를 위해 objectId 추출 후 콜백 호출
			if (int.TryParse(seatedOn.Prop.Name, out int objectId))
			{
				OnSeatedStateClearing?.Invoke(_id, objectId);
			}
			TraversalContext.Props.Remove(seatedOn.Prop);
		}
	}

	/// <summary>
	/// JobList Clear 후 삽입 (기존 job 모두 제거 후 새 job 추가)
	/// 플레이어처럼 스케줄이 없는 유닛용
	/// </summary>
	public void InsertJobWithClear(Job job)
	{
		JobList.InsertWithClear(job);
	}

	/// <summary>
	/// JobList에 Override Job 삽입 (기존 job 잘라내고 끼워넣기)
	/// </summary>
	public void InsertJobOverride(Job job)
	{
		JobList.InsertOverride(job);
	}

	/// <summary>
	/// JobList에 Merge Job 삽입 (기존 job 우선, 빈 공간에 끼워넣기)
	/// </summary>
	public void InsertJobMerge(Job job)
	{
		JobList.InsertMerge(job);
	}

	/// <summary>
	/// JobList 시간 경과 처리
	/// </summary>
	public void AdvanceJobs(int millis)
	{
		JobList.Advance(millis);
	}

	/// <summary>
	/// BaseSchedule로부터 JobList 채우기
	/// </summary>
	public void FillJobsFromSchedule(int currentTimeOfDay, int lookAheadMillis = GameTime.MillisPerDay)
	{
		JobList.FillFromSchedule(BaseSchedule, currentTimeOfDay, lookAheadMillis);
	}

	/// <summary>
	/// 아이템 효과가 반영된 최종 Prop 계산 (매 호출 시 계산)
	/// inventoryData: (inventory, equippedItems) 튜플
	/// </summary>
	public TraversalContext GetActualProps(
		ItemSystem? itemSystem,
		IReadOnlyDictionary<int, int>? inventory = null,
		IReadOnlyList<int>? equippedItems = null)
	{
		var result = new TraversalContext();

		// 1. 기본 Prop 복사
		foreach (var (prop, value) in TraversalContext.Props)
		{
			result.SetProp(prop, value);
		}

		if (itemSystem == null)
			return result;

		// 2. 인벤토리 아이템의 PassiveProps 합산 (소유 효과)
		if (inventory != null)
		{
			foreach (var (itemId, count) in inventory)
			{
				if (count <= 0) continue;
				var item = itemSystem.FindItem(itemId);
				if (item == null) continue;

				foreach (var (propName, bonus) in item.PassiveProps)
				{
					var current = result.GetProp(propName);
					result.SetProp(propName, current + bonus);
				}
			}
		}

		// 3. 장착 아이템의 EquipProps 합산 (장착 효과)
		if (equippedItems != null)
		{
			foreach (var itemId in equippedItems)
			{
				var item = itemSystem.FindItem(itemId);
				if (item == null) continue;

				foreach (var (propName, bonus) in item.EquipProps)
				{
					var current = result.GetProp(propName);
					result.SetProp(propName, current + bonus);
				}
			}
		}

		return result;
	}

	/// <summary>
	/// 이동 속도 계산 (퍼센트, 100=기본)
	/// "이동:속도" Prop을 아이템 효과 포함하여 계산
	/// 자세(posture)에 따른 속도 계수도 적용
	/// - standing: 100% (기본)
	/// - crouch: 50%
	/// - prone: 25%
	/// </summary>
	/// <returns>이동 속도 (100=기본, 200=2배 빠름, 50=절반 속도)</returns>
	public int GetMovementSpeed(
		ItemSystem? itemSystem,
		IReadOnlyDictionary<int, int>? inventory = null,
		IReadOnlyList<int>? equippedItems = null)
	{
		var actualProps = GetActualProps(itemSystem, inventory, equippedItems);
		var baseSpeed = actualProps.GetProp("이동:속도");
		if (baseSpeed <= 0) baseSpeed = 100;  // 기본값 100

		// 자세별 속도 계수 적용
		int postureModifier = GetPostureSpeedModifier();
		int result = baseSpeed * postureModifier / 100;

		// 혼잡도 감속 (Python congestion.py에서 설정)
		// 이동:혼잡 = 퍼센트 (100=보통, 50=반감). 0 또는 미설정=감속 없음.
		var congestionSpeed = TraversalContext.GetProp("이동:혼잡");
		if (congestionSpeed > 0 && congestionSpeed < 100)
			result = result * congestionSpeed / 100;

		// 부상 감속 (Python combat.py에서 설정)
		// 이동:부상 = 퍼센트 (50=절반 속도). 0 또는 미설정=감속 없음.
		var injurySpeed = actualProps.GetProp("이동:부상");
		if (injurySpeed > 0 && injurySpeed < 100)
			result = result * injurySpeed / 100;

		// 달리기 가속 (Python settings.py에서 토글)
		// 이동:달리기 = 1이면 속도 1.5배
		var sprintMode = actualProps.GetProp("이동:달리기");
		if (sprintMode > 0)
			result = result * 150 / 100;

		return Math.Max(result, 10);  // 최소 10%
	}

	/// <summary>
	/// 현재 자세의 이동 속도 계수 반환 (퍼센트)
	/// - standing (통상): 100
	/// - crouch (은신): 50
	/// - sitting/lying: 0 (이동 불가)
	/// </summary>
	public int GetPostureSpeedModifier()
	{
		// posture:crouch = 1 형태로 저장됨
		if (TraversalContext.GetProp("posture:crouch") > 0)
			return 50;
		if (TraversalContext.GetProp("posture:sitting") > 0 || TraversalContext.GetProp("posture:lying") > 0)
			return 0;  // 이동 불가
		return 100;  // standing (통상)
	}

	/// <summary>
	/// 아이템 효과가 반영된 최종 Prop 계산 (특정 타입만 필터링)
	/// </summary>
	/// <param name="types">가져올 Prop 타입들 (예: ["스탯", "상태"]). null이면 모든 타입</param>
	public TraversalContext GetActualPropsEx(
		IEnumerable<string>? types,
		ItemSystem? itemSystem,
		IReadOnlyDictionary<int, int>? inventory = null,
		IReadOnlyList<int>? equippedItems = null)
	{
		// 타입 필터가 없으면 전체 반환
		if (types == null)
			return GetActualProps(itemSystem, inventory, equippedItems);

		var typeSet = new HashSet<string>(types);
		if (typeSet.Count == 0)
			return new TraversalContext();

		var result = new TraversalContext();

		// 1. 기본 Prop 중 해당 타입만 복사
		foreach (var (prop, value) in TraversalContext.Props)
		{
			if (typeSet.Contains(prop.Type))
				result.SetProp(prop, value);
		}

		if (itemSystem == null)
			return result;

		// 2. 인벤토리 아이템의 PassiveProps 중 해당 타입만 합산
		if (inventory != null)
		{
			foreach (var (itemId, count) in inventory)
			{
				if (count <= 0) continue;
				var item = itemSystem.FindItem(itemId);
				if (item == null) continue;

				foreach (var (propName, bonus) in item.PassiveProps)
				{
					var prop = Prop.Parse(propName);
					if (prop.IsValid && typeSet.Contains(prop.Type))
					{
						var current = result.GetProp(prop);
						result.SetProp(prop, current + bonus);
					}
				}
			}
		}

		// 3. 장착 아이템의 EquipProps 중 해당 타입만 합산
		if (equippedItems != null)
		{
			foreach (var itemId in equippedItems)
			{
				var item = itemSystem.FindItem(itemId);
				if (item == null) continue;

				foreach (var (propName, bonus) in item.EquipProps)
				{
					var prop = Prop.Parse(propName);
					if (prop.IsValid && typeSet.Contains(prop.Type))
					{
						var current = result.GetProp(prop);
						result.SetProp(prop, current + bonus);
					}
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

		var actualProps = GetActualProps(itemSystem, inventory, equippedItems);

		foreach (var (propName, requiredValue) in conditions)
		{
			if (actualProps.GetProp(propName) < requiredValue)
				return false;
		}

		return true;
	}

	/// <summary>
	/// 상태 요약
	/// </summary>
	public string GetStatusSummary()
	{
		if (_currentMovement != null)
		{
			return $"{Name}: {_currentMovement}";
		}
		else
		{
			var jobInfo = CurrentJob != null
				? $" ({CurrentJob.Name})"
				: "";
			return $"{Name}: {_currentLocation}에서 대기 중{jobInfo}";
		}
	}

	public override string ToString()
	{
		var state = _currentMovement != null ? "Moving" : "Idle";
		return $"Unit[{Id}] {Name} ({Type}) @ {_currentLocation} ({state})";
	}
}
