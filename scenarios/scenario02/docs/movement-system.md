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
  └─ RegionGate (다른 Region 간 연결)
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

### 1.5 RegionGate (Region 간 연결)

서로 다른 두 Region을 연결하는 게이트입니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `Id` | int | 전역 고유 ID |
| `LocationA` | LocationRef | Region A의 연결 Location |
| `LocationB` | LocationRef | Region B의 연결 Location |
| `TravelTimeAtoB` | int | 이동 시간(분) |
| `TravelTimeBtoA` | int | 역방향 이동 시간(분) |
| `Name` | string | 연결 이름 |

**파일:** [scripts/morld/terrain/RegionGate.cs](../../../scripts/morld/terrain/RegionGate.cs)

```
예시: 저택 앞마당(0:12) ↔ 숲 입구(3:20), 이동 시간 10분
```

### 1.6 이동 조건 검사

Gate/RegionGate의 `CanTraverse` 메서드로 이동 가능 여부를 확인합니다.

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
| `TotalDistance` | float | 총 이동 거리 (Location 내 X좌표 기반) |
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

### 2.6 Gate Transit System (NPC 숨김 이동) — v0.2.3

NPC가 다른 Location으로 이동할 때 (Gate 통과), 이동 시작 시 즉시 숨기고 이동 시간 후 목적지에 텔레포트시킵니다.

#### 배경
Gate까지 걸어가는 동안 (BaseSpeed=0.001 units/ms) NPC가 노출되어 공격/탈진당할 수 있는 문제를 해결합니다.

#### FSM 기반 구현 (v0.2.3)

Gate Transit은 **스택 기반 FSM**(`think/fsm.py`)의 `GateTransitState`로 구현됩니다.
`_move_to()`가 cross-location 이동을 감지하면 FSM 스택에 push하여 think() 로직을 차단합니다.

직접 Gate 연결이 없는 경우 **BFS multi-hop 경로탐색**(`_find_path()`)으로 경유지를 자동 계산합니다.
예: `R2:L5 → R2:L0` (직통 Gate 없음) → `R2:L5 → R2:L3 → R2:L0` (2-hop)

```
_move_to() — cross-location 감지
    ↓
FSM: GateTransitState push
  → enter(): BFS 경로 탐색, 행동 로그, 첫 hop approaching 시작
    ↓
첫 hop approaching: Gate x좌표로 같은 location 내 이동 (보임)
  → Gate 도달 → transiting: 상태:이동중=1 + cross-location move job (숨김)
    ↓
DES step 5: 텔레포트 + 상태:이동중=0 해제
    ↓
다음 think() 호출
  → 중간 hop 있으면: 상태:이동중=1 재설정, 다음 hop 즉시 transit (숨김 유지)
  → 최종 도착이면: pop → False → Life 로직(5-tier) 진행
```

#### FSM 레벨 계층
```
LV_LIFE       =  0  생활 (root, 불변)
LV_COMBAT     = 10  전투
LV_COMBAT_SUB = 20  전투 하위 (도주/체념/필사)
LV_TRANSIT    = 30  Gate 이동 (최상위 — 어디서든 push, 아무것도 pop 안 함)
```
GateTransitState는 LV_TRANSIT(30)이므로 어떤 상태 위에도 push 가능합니다.
예: `[Life, Combat, Flee]` → push GateTransit → `[Life, Combat, Flee, GateTransit]`

#### `상태:이동중` Prop
| 항목 | 설명 |
|------|------|
| 설정 | `GateTransitState._start_transiting()` — 첫 hop approaching 완료 후 |
| 해제 (DES) | C# DES step 5 — 텔레포트 완료 후 |
| 해제 (ECS) | C# `JobBehaviorSystem.ProcessMoveAction2D()` — goalLocation 도착 시 (3곳) |
| 해제 (안전장치) | `GateTransitState.exit()` — pop 시 잔여 prop 정리 |
| 효과 | Look/LookUnit 필터링, get_characters/units_at_location 제외 |

> **역할 분리**: `상태:이동중`은 C# 가시성 숨김 전용. think() 차단은 FSM 스택이 담당.

#### 가시성 필터링 (C#)
| 함수 | 파일 | 동작 |
|------|------|------|
| `Look()` | unit_system.cs | transit NPC를 목록에서 제외 (절대 감지 불가) |
| `LookUnit()` | unit_system.cs | transit NPC에 대해 null 반환 → Focus 자동 해제 |
| `get_characters_at_location` | script_system_morld_api.cs | transit NPC 제외 |
| `get_units_at_location` | script_system_morld_api.cs | transit 캐릭터 제외 (오브젝트/생물은 해당 없음) |

> **지도 UI**: transit NPC는 `get_actor_ids()` + `is_moving_2d` 경로로 여전히 지도에 표시됩니다 (map_ui.py).

#### 동일 location 이동 가드
`_move_to()`는 동일 location 이동 시 기존 move job이 있으면 보존합니다 (매 step 리셋 방지).
```python
# _move_to() — 동일 location
job = morld.get_current_job(self.unit_id)
if job and job.get("action") == "move":
    self._action_taken = True
    return  # 기존 job 보존
```

> **NOTE**: 상위 tier 인터럽트로 목적지가 바뀔 경우, 기존 job의 목적지가 다를 수 있음. 전투 등은 별도 State에서 처리 예정.

#### 행동 로그
cross-location 이동 시작 시 플레이어가 **같은 Location에 있을 때만** 행동 로그 출력:
```
리나이(가) 주방(으)로 이동을 시작했다.
```

#### 자동 식사
transit 중 HP < 50% 또는 배고픔 시 인벤토리 음식을 자동 소비합니다:
1. `_transit_auto_eat()` — 이동 시작 전 (Python `_move_to`)
2. `_process_npc_time()` — 이동 중 매 time_elapsed (survival.py)

**파일:**
- [think/fsm.py](../python/think/fsm.py) — FSMState, LifeState, GateTransitState, `_find_path()` (BFS)
- [think/__init__.py](../python/think/__init__.py) — `_move_to()`, `_transit_auto_eat()`, FSM 스택 관리
- [survival.py](../python/survival.py) — `_process_npc_time()` transit auto-eat
- [unit_system.cs](../../../scripts/system/unit_system.cs) — Look/LookUnit 필터
- [script_system_morld_api.cs](../../../scripts/system/script_system_morld_api.cs) — API 필터
- [script_system_data_api.cs](../../../scripts/system/script_system_data_api.cs) — DES step 5 해제

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
        PredictGateCrossings(pendingDuration);

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

## 4. 자세(Posture) 시스템

캐릭터의 자세에 따라 이동 가능 여부가 결정됩니다.

### 4.1 자세 종류

| 자세 | prop 키 | 이름 | 이동 가능 |
|------|---------|------|----------|
| standing | (없음) | 통상 | O |
| sitting | `posture:sitting` | 앉기 | X |
| lying | `posture:lying` | 눕기 | X |
| crouch | `posture:crouch` | 은신 | O |

**파일:** [scenarios/scenario02/python/ui.py](../python/ui.py) - `POSTURE_INFO`

### 4.2 Props 구조

```python
# 캐릭터 props (Unit.TraversalContext.Props)
posture:sitting = 1       # 현재 자세 (없으면 standing)
seated_on:123 = 456       # object_id=123에 앉아있음 (hash=456으로 추적)

# 오브젝트 props
seated_by:front = 1       # front 슬롯에 unit_id=1이 앉아있음
```

### 4.3 이동 제한 동작

1. **Footer 표시**: 현재 자세 항상 표시 (이동 불가 시 노란색)
2. **이동 UI**: 항상 표시하되 이동 불가 시 회색으로 비활성화
3. **행동 메뉴**: 이동 불가 시 `[오브젝트명]에서 일어나기` 액션 추가

```
[현재 자세: 눕기 (이동 불가)]  ← Footer

[이동]                        ← 항상 표시
  ▶ 거실 (회색, 클릭 불가)
  ▶ 복도 (회색, 클릭 불가)

[행동]
  ▶ 침대에서 일어나기         ← 자동 추가
```

### 4.4 API 함수

| 함수 | 설명 |
|------|------|
| `morld.sit_on(unit_id, object_id, slot, posture)` | 오브젝트에 앉기/눕기 |
| `morld.stand_up(unit_id)` | 일어나기 |

**파일:** [scripts/system/script_system_data_api.cs](../../../scripts/system/script_system_data_api.cs)

**sit_on 부가 효과:**
- 캐릭터를 오브젝트 X 좌표로 이동 (`unit.PositionX = obj.PositionX`)
- 플레이어: 이동 거리 기반 시간 소모 (`CalculateTravelTime` + `RequestTimeAdvance`)
- 시간 정지: 즉시 이동 (시간 소모 없음)
- 은신 자동 해제 (`status:stealth → 0`)

### 4.5 상태 일관성 검사

`ui.py`에서 매 프레임 상태 일관성을 검사합니다:

| 상황 | 경고 |
|------|------|
| `posture:sitting` 있는데 `seated_on:*` 없음 | WARNING: posture but no seated_on |
| `seated_on:*` 있는데 posture=standing | WARNING: seated_on but standing |
| `posture:*` prop이 2개 이상 | ERROR: Multiple posture props |

### 4.6 오브젝트 전환 처리

침대 A에서 침대 B로 바로 앉을 때:

1. `sit_on()` 호출 시 기존 `seated_on:*` 확인
2. 이미 앉아있으면 자동으로 이전 오브젝트에서 일어남:
   - 이전 오브젝트의 `seated_by:*` 정리
   - 캐릭터의 이전 `seated_on:*` 제거
3. 새 오브젝트에 앉기 처리

---

## 5. 시간 정지(Frozen) 상태

### 5.1 플레이어 즉시 이동

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

### 5.2 이벤트 동작

| 이벤트 | Freeze 시 동작 |
|--------|---------------|
| `on_meet` | 스킵 |
| `on_reach` | 정상 동작 |
| `on_time_elapsed` | 스킵 |

---

## 6. 주요 파일 경로

### 지형 구조
| 파일 | 역할 |
|------|------|
| [scripts/morld/terrain/Location.cs](../../../scripts/morld/terrain/Location.cs) | Location (1D 공간), LocationRef |
| [scripts/morld/terrain/Gate.cs](../../../scripts/morld/terrain/Gate.cs) | Gate (연결점) |
| [scripts/morld/terrain/RegionGate.cs](../../../scripts/morld/terrain/RegionGate.cs) | RegionGate (Region 간 연결) |
| [scripts/morld/terrain/Region.cs](../../../scripts/morld/terrain/Region.cs) | Region (Location/Gate 관리) |
| [scripts/morld/terrain/Terrain.cs](../../../scripts/morld/terrain/Terrain.cs) | Terrain (Region/RegionGate 관리) |

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

## 7. 관련 문서

- [terrain.md](terrain.md) - 지형 테스트 체크리스트
- [event.md](event.md) - 이벤트 시스템
- [time-flow.md](time-flow.md) - 시간 흐름 시스템
- [frozen.md](frozen.md) - 시간 정지 상태
- [system-api.md](system-api.md) - morld API (sit_on/stand_up)
