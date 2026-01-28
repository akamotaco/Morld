# 이동 시스템 (Movement System)

> 이 문서는 Location/Edge 그래프 구조와 캐릭터 이동, 충돌 처리 시스템을 설명합니다.

---

## 1. 지형 그래프 구조

### 1.1 계층 구조

```
Terrain (전체 세계)
  ├─ Region (저택, 숲 등)
  │   ├─ Location (현관, 거실, 주방...)
  │   └─ Edge (같은 Region 내 Location 연결)
  └─ RegionEdge (다른 Region 간 연결)
```

### 1.2 Location (노드)

Region 내의 개별 위치를 나타냅니다.

| 속성 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `LocalId` | int | Region 내 로컬 ID | 필수 |
| `RegionId` | int | 소속 Region ID | 필수 |
| `GlobalId` | string | 전역 ID (`RegionId:LocalId`) | 계산됨 |
| `Name` | string | 위치 이름 | "unknown" |
| `StayDuration` | int | 경유 시 지체 시간(분) | 0 |
| `IsIndoor` | bool | 실내 여부 | true |
| `Owner` | string | 소유자 unique_id | null |
| `GroundUnitId` | int? | 바닥 오브젝트 Unit ID | null |

**파일:** [scripts/morld/terrain/Location.cs](../../../scripts/morld/terrain/Location.cs)

### 1.3 LocationRef (위치 참조)

Location을 참조할 때 사용하는 구조체입니다.

```csharp
public readonly struct LocationRef : IEquatable<LocationRef>
{
    public int RegionId { get; }
    public int LocalId { get; }
}

// 사용 예시
var ref1 = new LocationRef(0, 12);  // 저택 앞마당
var ref2 = new LocationRef(3, 20);  // 숲 입구
```

### 1.4 Edge (Region 내 연결)

같은 Region 내 인접한 두 Location 간의 연결입니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `LocationA`, `LocationB` | Location | 연결된 두 Location |
| `TravelTimeAtoB` | int | A → B 이동 시간(분) |
| `TravelTimeBtoA` | int | B → A 이동 시간(분) |
| `ConditionsAtoB` | Dict | A → B 이동 조건 |
| `ConditionsBtoA` | Dict | B → A 이동 조건 |
| `IsBlocked` | bool | 완전 차단 여부 |

**파일:** [scripts/morld/terrain/Edge.cs](../../../scripts/morld/terrain/Edge.cs)

```csharp
// Edge 생성 예시
var edge = region.AddEdge(1, 2, 3);  // Location 1 ↔ 2, 양방향 3분

// 조건 추가 예시
edge.AddConditionAtoB("level", 2);   // A→B 시 레벨 2 필요
```

### 1.5 RegionEdge (Region 간 연결)

서로 다른 두 Region을 연결하는 엣지입니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `Id` | int | 전역 고유 ID |
| `LocationA` | LocationRef | Region A의 연결 Location |
| `LocationB` | LocationRef | Region B의 연결 Location |
| `TravelTimeAtoB` | int | 이동 시간(분) |
| `TravelTimeBtoA` | int | 역방향 이동 시간(분) |
| `Name` | string | 연결 이름 |

**파일:** [scripts/morld/terrain/RegionEdge.cs](../../../scripts/morld/terrain/RegionEdge.cs)

```
예시: 저택 앞마당(0:12) ↔ 숲 입구(3:20), 이동 시간 10분
```

### 1.6 이동 조건 검사

Edge/RegionEdge의 `CanTraverse` 메서드로 이동 가능 여부를 확인합니다.

```csharp
public bool CanTraverse(Location from, TraversalContext? context = null)
{
    if (IsBlocked) return false;                    // 1. 완전 차단 확인
    var travelTime = GetTravelTime(from);
    if (travelTime < 0) return false;               // 2. 음수 시간 = 이동 불가
    var conditions = GetConditions(from);
    return CheckConditions(conditions, context);    // 3. 조건 검사
}
```

**TraversalContext:** 현재 유닛이 보유한 속성 (레벨, 아이템 등)

---

## 2. 캐릭터 이동 시스템

### 2.1 이동 상태 표현

캐릭터의 위치는 **Location (정지)** 또는 **Edge (이동 중)** 두 가지 상태로 표현됩니다.

```csharp
// Unit 클래스 (scripts/morld/unit/Unit.cs)
public LocationRef CurrentLocation { get; }  // 현재 위치 (이동 중이면 출발지)
public EdgeProgress? CurrentEdge { get; }    // null이면 정지, 값이 있으면 이동 중

public bool IsOnEdge => CurrentEdge != null;  // Edge 위에 있는지
public bool IsIdle => CurrentEdge == null;    // 정지 상태인지
```

### 2.2 EdgeProgress (이동 진행 상황)

이동 중인 캐릭터의 진행 상황을 추적합니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `From` | LocationRef | 출발 Location |
| `To` | LocationRef | 도착 Location |
| `BaseTravelTime` | int | 기본 이동 시간(분) |
| `TotalTime` | int | 실제 이동 시간 (이동속도 적용 후) |
| `ElapsedTime` | int | 경과 시간(분) |
| `MovementSpeed` | int | 이동 속도 (100=기본, 200=2배) |
| `RemainingTime` | int | 남은 시간 (계산됨) |
| `Progress` | float | 진행률 0.0~1.0 (계산됨) |
| `NormalizedPosition` | float | 정규화 위치 (충돌 감지용) |

**파일:** [scripts/morld/unit/ActionLog.cs](../../../scripts/morld/unit/ActionLog.cs)

```csharp
// 이동속도 계산
실제 이동 시간 = 기본 이동 시간 × 100 / 이동속도

// 예시
기본 20분, 속도 200 → 실제 10분 (2배 빠름)
기본 20분, 속도 50  → 실제 40분 (절반 속도)
```

### 2.3 시간 흐름 파이프라인

```
플레이어 액션 입력
    ↓
PlayerSystem.RequestCommand() → NextStepDuration 설정
    ↓
ECS Step 실행:
  1. ThinkSystem       : NPC Job 결정 (Python Agent 호출)
  2. EventPredictionSystem : 이벤트 예측 + NextStepDuration 조정
  3. JobBehaviorSystem : 실제 이동 처리
  4. EventSystem       : 이벤트 감지 및 Python 호출
```

### 2.4 JobBehaviorSystem 이동 처리

**파일:** [scripts/system/job_behavior_system.cs](../../../scripts/system/job_behavior_system.cs)

```csharp
private void ProcessMoveAction(Unit unit, LocationRef goalLocation, int duration, Terrain terrain)
{
    int remainingTime = duration;

    while (remainingTime > 0)
    {
        // 1. Edge 위에 있으면 계속 이동
        if (unit.CurrentEdge != null)
        {
            var edge = unit.CurrentEdge;
            var timeToComplete = edge.RemainingTime;

            if (remainingTime >= timeToComplete)
            {
                // 도착
                unit.SetCurrentLocation(edge.To);
                unit.CurrentEdge = null;
                remainingTime -= timeToComplete;

                // 경유지 지체 시간 처리
                var location = terrain.GetLocation(edge.To);
                if (location.StayDuration > 0 && edge.To != goalLocation)
                {
                    unit.RemainingStayTime = location.StayDuration;
                }
            }
            else
            {
                // 아직 도착 못함
                edge.ElapsedTime += remainingTime;
                remainingTime = 0;
            }
            continue;
        }

        // 2. 지체 중이면 대기
        if (unit.RemainingStayTime > 0)
        {
            int stayTime = Math.Min(remainingTime, unit.RemainingStayTime);
            unit.RemainingStayTime -= stayTime;
            remainingTime -= stayTime;
            continue;
        }

        // 3. 목적지 도착 확인
        if (unit.CurrentLocation == goalLocation)
            break;

        // 4. 새 이동 시작 - 경로 계산 및 EdgeProgress 생성
        var pathResult = terrain.FindPath(unit.CurrentLocation, goalLocation);
        // ... EdgeProgress 생성 및 이동 시작
    }
}
```

### 2.5 경유지(Waypoint) 처리

경로 중간 Location에 `StayDuration > 0`이 설정되면:

1. 도착 후 `RemainingStayTime` 설정
2. 목적지가 아니면 지정 시간 동안 대기
3. 대기 완료 후 다음 Location으로 이동

---

## 3. 충돌(만남) 감지 시스템

### 3.1 만남 감지 조건

**파일:** [scripts/system/event_system.cs](../../../scripts/system/event_system.cs)

| 조건 | 설명 |
|------|------|
| **A. 정지 상태** | 같은 Location에서 `CurrentEdge == null`인 유닛 |
| **B. 방금 도착** | 경유지를 통과하면서 같은 위치에 있는 경우 |
| **C. Edge 충돌** | 같은 Edge 위에서 위치 차이 5% 이내 |

```csharp
public void DetectMeetings()
{
    foreach (var unit in _unitSystem.Units.Values)
    {
        if (unit.CurrentLocation != playerLocation) continue;

        // 조건 A: 정지 상태
        if (unit.CurrentEdge == null)
        {
            unitsToMeet.Add(unit.Id);
            continue;
        }

        // 조건 B: 방금 도착 (이전 위치와 다름)
        if (_lastLocations[unit.Id] != unit.CurrentLocation)
        {
            unitsToMeet.Add(unit.Id);
        }
    }

    // 조건 C: Edge 위 충돌 감지
    if (player.CurrentEdge != null)
    {
        var edgeMeetings = DetectEdgeMeetings(player);
        unitsToMeet.AddRange(edgeMeetings);
    }
}
```

### 3.2 Edge 충돌 감지

**파일:** [scripts/system/edge_collision_detector.cs](../../../scripts/system/edge_collision_detector.cs)

#### EdgeKey (양방향 동일 경로 식별)

```csharp
public readonly struct EdgeKey : IEquatable<EdgeKey>
{
    public readonly LocationRef A;  // 항상 작은 쪽
    public readonly LocationRef B;  // 항상 큰 쪽

    // 정규화: A < B (RegionId 먼저, 같으면 LocalId로 비교)
}
```

#### 충돌 타입

**1. Encounter (반대 방향 만남)**
```
Unit A: ──────→ (From → To 방향)
Unit B: ←────── (To → From 방향, 반대)

서로 접근 → 충돌
```

**2. Overtake (같은 방향 추월)**
```
Unit A: ──────→ (빠름)
Unit B: ────→   (느림, A보다 앞)

A가 B를 추월 → 충돌
```

#### 충돌 감지 알고리즘

```csharp
// 같은 Edge인지 확인
var playerEdgeKey = new EdgeKey(playerEdge.From, playerEdge.To);
var unitEdgeKey = new EdgeKey(unitEdge.From, unitEdge.To);

if (!playerEdgeKey.Equals(unitEdgeKey)) continue;

// EdgeKey 기준으로 위치 정규화
float playerPos = playerEdge.From.Equals(playerEdgeKey.A)
    ? playerEdge.NormalizedPosition
    : 1.0f - playerEdge.NormalizedPosition;

float unitPos = /* 동일하게 계산 */;

// 위치 차이가 5% 이내면 충돌
if (Math.Abs(playerPos - unitPos) <= 0.05f)
{
    result.Add(unit.Id);
}
```

### 3.3 이벤트 예측 시스템

**파일:** [scripts/system/event_prediction_system.cs](../../../scripts/system/event_prediction_system.cs)

이벤트 발생 시점을 예측하고 `NextStepDuration`을 조정합니다.

```csharp
public class EventPredictionSystem : ECS.System
{
    protected override void Proc(int step, Span<Component[]> allComponents)
    {
        int pendingDuration = _playerSystem.NextStepDuration;

        // 이벤트 예측
        PredictMeetings(pendingDuration);
        PredictArrivals(pendingDuration);
        PredictEdgeCollisions(pendingDuration);

        // 가장 빠른 이벤트 시점으로 시간 조정
        var earliestInterrupt = FindEarliestInterrupt();
        if (earliestInterrupt != null && earliestInterrupt.TriggerMinutes < pendingDuration)
        {
            _playerSystem.AdjustNextStepDuration(earliestInterrupt.TriggerMinutes);
        }
    }
}
```

#### 경유지 충돌 예측 (시간 범위 겹침)

```csharp
// 두 유닛의 경로에서 같은 Location의 시간 범위 비교
int playerStart = playerWaypoint.ArrivalTime;
int playerEnd = playerWaypoint.DepartureTime;  // 경유지면 ArrivalTime과 동일

int npcStart = npcWaypoint.ArrivalTime;
int npcEnd = npcWaypoint.DepartureTime;

// 시간 범위 겹침 확인
int overlapStart = Math.Max(playerStart, npcStart);
int overlapEnd = Math.Min(playerEnd, npcEnd);

if (overlapStart <= overlapEnd)
{
    // 만남 발생!
    meetingTime = overlapStart;
}
```

---

## 4. 시간 정지(Frozen) 상태

### 4.1 플레이어 즉시 이동

시간 정지 상태에서는 플레이어만 즉시 이동합니다.

```csharp
// job_behavior_system.cs
if (isTimeFrozen)
{
    var player = _playerSystem.FindPlayerUnit();
    if (player != null)
    {
        // 즉시 목적지로 이동 (이동 시간 없음)
        player.CurrentEdge = null;
        player.RemainingStayTime = 0;
        player.SetCurrentLocation(goalLocation);
    }
    _playerSystem.ClearPendingTime();
    return;
}
```

### 4.2 이벤트 동작

| 이벤트 | Freeze 시 동작 |
|--------|---------------|
| `on_meet` | 스킵 |
| `on_reach` | 정상 동작 |
| `on_time_elapsed` | 스킵 |
| `on_equip_change` | 정상 동작 |

---

## 5. 주요 파일 경로

### 지형 구조
| 파일 | 역할 |
|------|------|
| [scripts/morld/terrain/Location.cs](../../../scripts/morld/terrain/Location.cs) | Location, LocationRef |
| [scripts/morld/terrain/Edge.cs](../../../scripts/morld/terrain/Edge.cs) | Edge, TraversalContext |
| [scripts/morld/terrain/RegionEdge.cs](../../../scripts/morld/terrain/RegionEdge.cs) | RegionEdge |
| [scripts/morld/terrain/Region.cs](../../../scripts/morld/terrain/Region.cs) | Region (Location/Edge 관리) |
| [scripts/morld/terrain/Terrain.cs](../../../scripts/morld/terrain/Terrain.cs) | Terrain (Region/RegionEdge 관리) |

### 이동/충돌 시스템
| 파일 | 역할 |
|------|------|
| [scripts/morld/unit/ActionLog.cs](../../../scripts/morld/unit/ActionLog.cs) | EdgeProgress |
| [scripts/morld/unit/Unit.cs](../../../scripts/morld/unit/Unit.cs) | Unit 이동 상태 |
| [scripts/system/job_behavior_system.cs](../../../scripts/system/job_behavior_system.cs) | 이동 처리 |
| [scripts/system/event_system.cs](../../../scripts/system/event_system.cs) | 만남 감지 |
| [scripts/system/edge_collision_detector.cs](../../../scripts/system/edge_collision_detector.cs) | Edge 충돌 감지 |
| [scripts/system/event_prediction_system.cs](../../../scripts/system/event_prediction_system.cs) | 이벤트 예측 |

### 액션 핸들러
| 파일 | 역할 |
|------|------|
| [scripts/MetaActionHandler/MetaActionHandler.Navigation.cs](../../../scripts/MetaActionHandler/MetaActionHandler.Navigation.cs) | 플레이어 이동 액션 |

---

## 6. 관련 문서

- [terrain.md](terrain.md) - 지형 테스트 체크리스트
- [event.md](event.md) - 이벤트 시스템
- [time-flow.md](time-flow.md) - 시간 흐름 시스템
- [frozen.md](frozen.md) - 시간 정지 상태
