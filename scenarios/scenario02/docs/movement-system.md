# 이동 시스템 (Movement System)

> 이 문서는 Pi-World 지형 구조와 캐릭터 이동, 충돌 처리 시스템을 설명합니다.

---

## 1. 지형 그래프 구조 (Pi-World)

### 1.1 계층 구조

```
Terrain (전체 세계)
  ├─ Region (저택, 숲 등)
  │   ├─ Location (1D 공간: line/ring)
  │   └─ Gate (Location 간 연결점)
  └─ RegionEdge (다른 Region 간 연결)
```

### Pi-World 핵심 개념
- **Location**: 점(0D) → 1D 공간 (line/ring)
- **Gate**: Location 간 연결점 (통과 시간 = 0, 즉시 이동)
- **이동 시간**: 거리 기반 계산 (`distance / speed`)

### 1.2 Location (1D 공간)

Region 내의 1차원 공간을 나타냅니다.

| 속성 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `LocalId` | int | Region 내 로컬 ID | 필수 |
| `RegionId` | int | 소속 Region ID | 필수 |
| `GlobalId` | string | 전역 ID (`RegionId:LocalId`) | 계산됨 |
| `Name` | string | 위치 이름 | "unknown" |
| `Geometry` | LocationGeometry | 지형 형태 (Line/Ring) | Ring |
| `Length` | float | 공간 길이 (0=레거시 점) | 0 |
| `BaseSpeed` | float | 기본 이동 속도 (단위/분) | 10 |
| `StayDuration` | int | 경유 시 지체 시간(분) | 0 |
| `IsIndoor` | bool | 실내 여부 | true |
| `Owner` | string | 소유자 unique_id | null |
| `GroundUnitId` | int? | 바닥 오브젝트 Unit ID | null |

**파일:** [scripts/morld/terrain/Location.cs](../../../scripts/morld/terrain/Location.cs)

#### Geometry 타입
| 값 | 설명 | 거리 계산 |
|----|------|----------|
| `Ring` (0) | 원형 공간 (순환) | `min(|dx|, length - |dx|)` |
| `Line` (1) | 선형 공간 (양 끝) | `|target_x - current_x|` |

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

### 1.4 Gate (Location 연결점)

Location 내 특정 X 좌표에 배치된 연결점입니다. 통과 시간은 0 (즉시 이동).

| 속성 | 타입 | 설명 |
|------|------|------|
| `Id` | int | Gate ID (Location 내 고유) |
| `X` | float | Gate 위치 (Location 내 X 좌표) |
| `ConnectedRegion` | int | 연결된 Region ID |
| `ConnectedLocation` | int | 연결된 Location ID |
| `ArrivalX` | float | 도착 시 X 좌표 |
| `ConditionsForward` | Dict | 통과 조건 |
| `IsBlocked` | bool | 차단 여부 |

**파일:** [scripts/morld/terrain/Gate.cs](../../../scripts/morld/terrain/Gate.cs)

```python
# Gate 정의 예시 (Python)
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
GATES = [
    (0, 0, 0, 30, 0, 1, 0),   # 현관(x=30) → 거실(x=0)에 도착
    (0, 1, 0, 0, 0, 0, 30),   # 거실(x=0) → 현관(x=30)에 도착
]
```

#### 이동 흐름
```
[현재 X] → 이동(거리 기반) → [Gate X] → [즉시] → [도착 Location의 arrival_x] → 이동 → [목적지 X]
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

### 2.1 이동 상태 표현 (Pi-World)

캐릭터의 위치는 **Location + X 좌표**로 표현됩니다.

```csharp
// Unit 클래스 (scripts/morld/unit/Unit.cs)
public LocationRef CurrentLocation { get; }   // 현재 Location
public float PositionX { get; set; }          // Location 내 X 좌표
public float PositionY { get; set; }          // 확장용 (현재 미사용)
public MovementProgress? CurrentMovement { get; }  // null이면 정지, 값이 있으면 이동 중

public bool IsMoving2D => CurrentMovement != null;  // Location 내 이동 중
public bool IsIdle => CurrentMovement == null;      // 정지 상태
```

### 2.2 MovementProgress (Location 내 이동)

Location 내 이동 중인 캐릭터의 진행 상황을 추적합니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `StartX` | float | 출발 X 좌표 |
| `TargetX` | float | 도착 X 좌표 |
| `TargetGateId` | int? | Gate 통과 시 Gate ID |
| `TotalDistance` | float | 총 이동 거리 |
| `TraveledDistance` | float | 이동한 거리 |
| `Speed` | float | 이동 속도 (단위/분) |
| `ElapsedTime` | int | 경과 시간(분) |
| `TotalTime` | int | 총 이동 시간 (계산됨) |
| `RemainingTime` | int | 남은 시간 (계산됨) |
| `Progress` | float | 진행률 0.0~1.0 (계산됨) |

**파일:** [scripts/morld/unit/ActionLog.cs](../../../scripts/morld/unit/ActionLog.cs)

```csharp
// 이동 시간 계산 (Pi-World)
이동 시간 = 거리 / (base_speed × speed_modifier)

// 예시: length=60, base_speed=10
X:0 → X:30 이동 = 30 / 10 = 3분
X:0 → X:50 (Ring) = min(50, 60-50) / 10 = 1분 (최단 경로)
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
        // 1. 이동 중이면 계속 이동
        if (unit.CurrentMovement != null)
        {
            var movement = unit.CurrentMovement;
            var timeToComplete = movement.RemainingTime;

            if (remainingTime >= timeToComplete)
            {
                // 이동 완료
                unit.PositionX = movement.TargetX;
                remainingTime -= timeToComplete;

                // Gate 통과 처리
                if (movement.TargetGateId != null)
                {
                    var gate = location.GetGate(movement.TargetGateId.Value);
                    unit.SetCurrentLocation(gate.ConnectedLocation);
                    unit.PositionX = gate.ArrivalX;
                }

                unit.CurrentMovement = null;
            }
            else
            {
                // 진행 중
                movement.ElapsedTime += remainingTime;
                movement.TraveledDistance += remainingTime * movement.Speed;
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

        // 4. 새 이동 시작 - 다음 Gate로 MovementProgress 생성
        var nextGate = FindNextGate(unit.CurrentLocation, goalLocation);
        // ... MovementProgress 생성 및 이동 시작
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

### 3.1 만남 감지 조건 (Pi-World)

**파일:** [scripts/system/event_system.cs](../../../scripts/system/event_system.cs)

| 조건 | 설명 |
|------|------|
| **A. 같은 Location** | 같은 Location에 있는 유닛 |
| **B. 근접 거리** | X 좌표 차이가 충돌 반경 이내 |
| **C. Gate 통과** | 동시에 같은 Gate 쌍 통과 시 |

```csharp
// Pi-World 충돌 감지
private List<int> DetectLocationMeetings(Unit player, Location location)
{
    var result = new List<int>();
    float collisionRadius = 5f;  // 충돌 반경

    foreach (var unit in _unitSystem.Units.Values)
    {
        if (unit.CurrentLocation != player.CurrentLocation) continue;
        if (unit.Id == player.Id) continue;

        // 거리 계산 (Geometry에 따라 다름)
        float distance = location.Geometry == LocationGeometry.Ring
            ? DistanceRing(player.PositionX, unit.PositionX, location.Length)
            : Math.Abs(player.PositionX - unit.PositionX);

        if (distance <= collisionRadius)
            result.Add(unit.Id);
    }

    return result;
}
```

### 3.2 Gate 통과 충돌 감지

두 유닛이 동시에 같은 Gate를 통과할 때 충돌을 감지합니다.

**파일:** [scripts/system/event_system.cs](../../../scripts/system/event_system.cs)

#### 충돌 조건

1. 같은 Location에서 같은 Gate로 이동 중
2. Gate 도착 시점이 동일 (±1분)

```csharp
// Gate 통과 충돌 감지
if (player.CurrentMovement?.TargetGateId != null)
{
    var playerGateId = player.CurrentMovement.TargetGateId.Value;

    foreach (var unit in unitsInSameLocation)
    {
        if (unit.CurrentMovement?.TargetGateId == playerGateId)
        {
            // 같은 Gate로 이동 중 → 충돌 가능
            result.Add(unit.Id);
        }
    }
}
```

#### Location 내 이동 충돌

```
Unit A: ──────→ (X=10 → X=50)
Unit B: ←────── (X=60 → X=40)

X 좌표가 충돌 반경 이내로 접근 → 충돌
```

### 3.3 Gate 교차 충돌 감지

서로 다른 Location에서 연결된 Gate 쌍을 반대 방향으로 통과할 때 충돌을 감지합니다.

**시나리오:**
```
Location A ──[Gate_A]──> Location B
           <──[Gate_B]──

P: A에서 Gate_A로 이동 (→ B로 진입 예정)
N: B에서 Gate_B로 이동 (→ A로 진입 예정)

→ Gate에서 교차하며 on_meet 발생
```

**파일:** [scripts/system/event_system.cs](../../../scripts/system/event_system.cs)

**감지 조건:**
1. P가 Gate_A로 이동 중 (`player.CurrentMovement?.TargetGateId != null`)
2. Gate_A가 Location B로 연결됨 (`playerGate.ConnectedLocation == B`)
3. N이 Location B에 있음 (`npc.CurrentLocation == B`)
4. N이 Gate_B로 이동 중 (`npc.CurrentMovement?.TargetGateId != null`)
5. Gate_B가 Location A로 연결됨 (`npcGate.ConnectedLocation == A`)

**NPC 위치 처리 (플레이어 전용 특수 케이스):**

- **플레이어-NPC 교차**: 다이얼로그는 플레이어 중심이므로, NPC를 플레이어의 목적지(B)로 즉시 이동시킴. 다이얼로그 종료 후 P와 N이 같은 Location(B)에 있게 됨.
- **NPC끼리 교차**: 위치 조정 없음. 각자 원래 목적지로 이동 (N1→B, N2→A, 서로 반대 위치)

```csharp
// Gate 교차 감지 (DetectGateCrossingMeetings)
if (unitGate.ConnectedLocation == player.CurrentLocation)
{
    // Gate 교차 발생!
    // ※ 다이얼로그는 플레이어 중심이므로, NPC를 플레이어의 목적지(B)로 이동
    unit.CurrentMovement = null;  // 이동 취소
    unit.SetLocation(connectedLocation);  // 플레이어 목적지로 이동
    unit.PositionX = playerGate.ArrivalX;  // Gate 도착 위치
}
```

**예측:**
```csharp
// 교차 시점 = 둘 중 늦게 Gate에 도착하는 시점
int crossingTime = Math.Max(playerTimeToGate, npcTimeToGate);
```

### 3.4 이벤트 예측 시스템

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
        player.CurrentMovement = null;
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
| [scripts/morld/terrain/Location.cs](../../../scripts/morld/terrain/Location.cs) | Location (1D 공간), LocationRef |
| [scripts/morld/terrain/Gate.cs](../../../scripts/morld/terrain/Gate.cs) | Gate (연결점) |
| [scripts/morld/terrain/RegionEdge.cs](../../../scripts/morld/terrain/RegionEdge.cs) | RegionEdge (Region 간 연결) |
| [scripts/morld/terrain/Region.cs](../../../scripts/morld/terrain/Region.cs) | Region (Location/Gate 관리) |
| [scripts/morld/terrain/Terrain.cs](../../../scripts/morld/terrain/Terrain.cs) | Terrain (Region/RegionEdge 관리) |

### 이동/충돌 시스템
| 파일 | 역할 |
|------|------|
| [scripts/morld/unit/ActionLog.cs](../../../scripts/morld/unit/ActionLog.cs) | MovementProgress (Location 내 이동) |
| [scripts/morld/unit/Unit.cs](../../../scripts/morld/unit/Unit.cs) | Unit 위치 (PositionX/Y) |
| [scripts/system/job_behavior_system.cs](../../../scripts/system/job_behavior_system.cs) | 이동 처리 |
| [scripts/system/event_system.cs](../../../scripts/system/event_system.cs) | 만남 감지 (2D 근접) |
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
