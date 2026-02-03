# Morld 이벤트 시스템

이벤트 시스템은 게임 내에서 발생하는 다양한 상황을 감지하고 Python 핸들러로 전달하는 역할을 합니다.

---

## EventSystem 개요

**역할:** 게임 이벤트 수집, 감지 및 Python 전달

**핵심 설계:**
- **이벤트 배치 처리**: 이벤트를 수집해서 한 번에 Python으로 전달
- **위치 변경 감지**: OnReach 이벤트 자동 생성
- **만남 감지**: OnMeet 이벤트 자동 생성 (이동 중인 유닛 제외)
- **장비 변경 감지**: OnEquipChange 이벤트로 NPC 반응
- **Python 제어**: 이벤트 처리 순서/우선순위를 Python에서 결정

**파일 위치:**
- `scripts/system/event_system.cs`
- `scripts/morld/event/GameEvent.cs`
- `scenarios/scenario02/python/events/__init__.py`

---

## 이벤트 타입

| 이벤트 | 설명 | Args |
|--------|------|------|
| `game_start` | 게임 시작 | - |
| `on_reach` | 위치 도착 | unit_id, region_id, location_id |
| `on_meet` | 유닛 만남 | unit_id1, unit_id2, ... |
| `on_time_elapsed` | 시간 경과 | millis |
| `on_equip_change` | 장비 변경 | unit_id, item_id, is_equip |

### 1. on_reach (위치 도착)
플레이어나 NPC가 새로운 위치에 도착했을 때 발생

```python
# events/reach/front_yard.py
from events.registry import ReachEvent, register

@register
class ArriveAtFrontYard(ReachEvent):
    region_id = 0
    location_id = 12  # 앞마당

    def handle(self, player_id, region_id, location_id):
        yield morld.dialog("저택 앞마당에 도착했다.")
```

### 2. on_meet (유닛 만남)
플레이어가 같은 위치에서 NPC와 만났을 때 발생

**OnMeet 감지 로직 (Pi-World):**
```csharp
// 같은 Location에서 충돌 반경 내의 유닛
var unitsToMeet = _unitSystem.Units.Values
    .Where(u => u.Id != playerId
             && u.GeneratesEvents
             && u.CurrentLocation == playerLocation
             && location.CalculateDistance(player.PositionX, u.PositionX) <= COLLISION_RADIUS)
```

**캐릭터 핸들러:**
```python
# assets/characters/sera.py
class Sera(Character):
    def on_meet_player(self, player_id):
        """플레이어와 만났을 때 이벤트"""
        yield morld.dialog("...일어났군.")
        morld.set_npc_job(self.instance_id, "stay", 1_800_000)  # 30분간 현재 위치 유지
```

**Registry 이벤트:**
```python
# events/meet/first_meeting.py
from events.registry import MeetEvent, register

@register
class FirstMeetSera(MeetEvent):
    required_units = ["sera"]  # 세라가 있어야 트리거
    priority = 10              # 높은 우선순위
    once = True                # 일회성

    def handle(self, player_id, unit_ids):
        yield morld.dialog("첫 만남 이벤트...")
```

### 3. on_time_elapsed (시간 경과)
게임 내 시간이 경과했을 때 발생

**핵심 설계:**
- `JobBehaviorSystem`에서 시간 진행 후 이벤트 Enqueue
- `EventSystem`에서 누적 후 한 번에 Flush (중복 호출 방지)
- Python에서 구독하여 시스템별 처리

**이벤트 누적 처리:**
```csharp
// EventSystem.cs
private int _accumulatedTimeElapsed = 0;

public void Enqueue(GameEvent evt) {
    if (evt.Type == EventType.OnTimeElapsed) {
        _accumulatedTimeElapsed += (int)evt.Args[0];
        return;  // 큐에 추가하지 않고 누적만
    }
    _pendingEvents.Add(evt);
}
```

**Python 구독:**
```python
from events import subscribe_time_elapsed

def my_handler(millis):
    print(f"{millis}ms 경과")

# 매번 호출
subscribe_time_elapsed(my_handler)

# 60분마다 호출
subscribe_time_elapsed(my_hourly_handler, min_interval=3_600_000)
```

### 4. game_start (게임 시작)
게임이 처음 시작될 때 한 번 발생

```python
from events.registry import GameStartEvent, register

@register
class Prologue(GameStartEvent):
    def handle(self, **ctx):
        yield morld.dialog(["게임 시작 모놀로그..."])
```

---

### 5. on_equip_change (장비 변경)

플레이어가 장비를 장착하거나 해제했을 때 발생

**C# 이벤트 발생:**
```csharp
// MetaActionHandler.Item.cs - 장착/해제 시
var eventSystem = _world.GetSystem("eventSystem") as EventSystem;
eventSystem?.Enqueue(GameEvent.OnEquipChange(player.Id, itemId, isEquip));
eventSystem?.FlushEvents();
```

**Python 처리 흐름:**
1. `events/__init__.py`의 `on_single_event()`에서 `on_equip_change` 감지
2. `_handle_equip_change()`가 플레이어 위치 확인
3. `_get_nearby_character_handlers()`로 같은 위치 NPC 목록 조회
4. 각 NPC의 `on_equip_change()` 메서드 호출

**NPC 핸들러 예시:**
```python
# assets/characters/sera.py
class Sera(Character):
    def on_equip_change(self, player_id, item_id, is_equip):
        """플레이어 장비 변경 시 반응"""
        import morld

        item_info = morld.get_item_info(item_id)
        if not item_info:
            return None

        # 무기(장착:손) 체크
        equip_props = item_info.get("equip_props", {})
        if not equip_props.get("장착:손"):
            return None  # 무기가 아니면 무시

        if is_equip:
            morld.add_action_log("세라가 무기를 힐끗 보더니 고개를 끄덕인다.")
        else:
            morld.add_action_log("세라가 빈 손을 보고 살짝 고개를 갸웃한다.")

        return None
```

**특징:**
- 별도 이벤트 타입으로 `on_meet`과 독립적
- 같은 위치에서 장착/해제해도 즉시 반응
- 시간 소모 없이 즉각적인 NPC 반응
- 이동 중인 NPC는 반응하지 않음

### 파일 구조

```
events/
├─ __init__.py           # 이벤트 시스템 메인
├─ reach/                # on_reach 이벤트
├─ meet/                 # on_meet 이벤트
└─ game_start/           # game_start 이벤트
```

---

## 통합 이벤트 핸들러 큐

한 위치에서 여러 NPC를 만나거나 다양한 이벤트가 동시에 발생할 때, C#에서 통합 관리하는 단일 큐로 순차 처리됩니다.

### 아키텍처

```
C# EventSystem                          Python events/
┌─────────────────────┐                ┌─────────────────────┐
│ _pendingHandlers    │ ←── 수집 ────  │ collect_event_      │
│ (List<EventHandler>)│                │ handlers()          │
│                     │                │                     │
│ ProcessNextHandler()│ ──── 호출 ──→ │ call_event_handler()│
│                     │                │                     │
│ ClearPendingHandlers│                │ (핸들러 실행)       │
│ (ExcessTime 시)     │                │                     │
└─────────────────────┘                └─────────────────────┘
```

### 핸들러 수집 (Python → C#)

```python
# events/__init__.py
def collect_event_handlers(event_type, player_id, unit_ids):
    """
    이벤트 타입별 핸들러 목록 반환 (C#이 큐로 관리)

    Args:
        event_type: "meet" | "contact" | "npc_meet"
        player_id: 플레이어 ID (npc_meet이면 None)
        unit_ids: 관련 유닛 목록

    Returns:
        list of dict: [{"source": "registry"|"character",
                        "event_type": ..., "event_id": ...,
                        "unit_id": ..., "priority": ..., "once": ...}]
    """
```

### 핸들러 실행 (C# → Python)

```python
# events/__init__.py
def call_event_handler(handler_info, player_id, unit_ids):
    """
    개별 핸들러 실행 (C#에서 호출)

    Returns:
        Generator (Dialog) 또는 None
    """
```

### 수동 큐 주입

로맨스 중단, 특수 이벤트 등에서 on_meet 이벤트를 수동으로 큐에 추가:

```python
# 로맨스 중단 후 방해자와의 만남 이벤트 주입
morld.queue_event("meet", player_id, [player_id, interrupter_id])
```

### ExcessTime과 이벤트 큐 연동

```
1. 플레이어가 위치 도착 → on_meet/on_contact 발생
2. C#에서 Python collect_event_handlers() 호출 → 핸들러 목록 수집
3. C# _pendingHandlers 큐에 저장 (우선순위 정렬됨)
4. ProcessNextHandler()로 하나씩 처리
5. Dialog 종료 후 dialogTimeConsumed 확인:
   - dialogTimeConsumed > 0: ClearPendingHandlers() → 남은 이벤트 스킵
   - dialogTimeConsumed == 0: 다음 핸들러 처리
6. 모든 핸들러 처리 완료 or ExcessTime 발생 시 종료
```

### 지원 이벤트 타입

| 타입 | 설명 | 핸들러 소스 |
|------|------|------------|
| `meet` | 플레이어-NPC 만남 | registry MeetEvent, character on_meet_player |
| `contact` | 2D 충돌 접촉 | registry ContactEvent, character on_contact_player |
| `npc_meet` | NPC 간 만남 | registry NpcMeetEvent |

---

## NPC Job 제어

Generator 기반 이벤트 핸들러에서 NPC Job을 직접 제어:

```python
def handle(self, player_id, unit_ids):
    yield morld.dialog("대화 내용...")

    # NPC Job 설정 (시간 경과 없음)
    morld.set_npc_job(unit_id, "stay", duration=1_800_000)  # 30분간 현재 위치 유지

    # 또는 시간 경과 포함 (대화 후 NPC가 현재 위치에 머무름)
    morld.set_npc_time_consume(unit_id, "stay", duration=1_800_000)  # 30분
```

### EVENT_DIALOGS 자동 처리

캐릭터 클래스의 `EVENT_DIALOGS`를 사용하면 대화 후 NPC 동작이 자동 처리됩니다:

```python
class Sera(Character):
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": ["......", "...세라다."],
            "time_consume": 1 * _M,     # 대화로 1분 경과
            "stay_duration": 2 * _M,    # 대화 후 2분간 현재 위치에 머무름
        },
    }
```

| Job Action | 설명 |
|------------|------|
| `stay` | 현재 위치에서 대기 (target 불필요) |
| `follow` | 대상을 따라다님 (target_id 필요) |
| `flee` | 대상에게서 도망 (target_id 필요) |
| `move` | 특정 위치로 이동 |

---

## 이벤트 처리 순서

```
1. DetectMeetings() → OnMeet 이벤트 생성
2. FlushEvents() → Generator 실행, Dialog 표시
3. DetectLocationChanges() → 위치 변경 감지
4. FlushEvents() → 추가 이벤트 처리
```

---

## 시간 정지와 이벤트

시간 정지(Time Freeze) 상태에서의 이벤트 동작:

| 이벤트 | Freeze 시 동작 |
|--------|---------------|
| on_meet | 스킵 (DetectMeetings 스킵) |
| on_reach | 정상 동작 (챕터 전환에 필요) |
| on_time_elapsed | 스킵 (시간 진행 없음) |
| on_equip_change | 정상 동작 (즉시 반응) |

---

## 이동 중 충돌 감지 시스템

Location 내에서 이동 중인 유닛 간의 정밀한 충돌을 감지합니다.

### 충돌 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| **Encounter** | 반대 방향에서 만남 | A→B와 B→A가 중간에서 만남 |
| **Overtake** | 같은 방향에서 추월 | 빠른 유닛이 느린 유닛을 따라잡음 |

### 이동속도 시스템

캐릭터의 `이동:속도` Prop으로 이동 속도를 조절합니다.

```python
# 캐릭터 정의
class FastRunner(Character):
    props = {
        "이동:속도": 150,  # 1.5배 빠름
    }

# 아이템으로 속도 부여
class SpeedBoots(Item):
    equip_props = {
        "이동:속도": 50,  # +50% 속도
    }
```

**속도 계산:**
- 100 = 기본 속도
- 200 = 2배 빠름 (이동 시간 절반)
- 50 = 절반 속도 (이동 시간 2배)

**실제 이동 시간:**
```
actualTime = baseTravelTime * 100 / movementSpeed
```

### MovementProgress 구조 (Pi-World)

```csharp
public class MovementProgress
{
    public float StartX { get; set; }          // 출발 X 좌표
    public float TargetX { get; set; }         // 목표 X 좌표
    public int? TargetGateId { get; set; }     // Gate 통과 시 Gate ID
    public float TotalDistance { get; set; }   // 총 이동 거리
    public float TraveledDistance { get; set; } // 이동한 거리
    public float Speed { get; set; }           // 이동 속도 (단위/밀리초)
    public int ElapsedTime { get; set; }       // 경과 시간 (밀리초)

    // 계산 속성
    public float Progress => TraveledDistance / TotalDistance;  // 0.0~1.0
    public int RemainingTime => TotalTime - ElapsedTime;
    public bool IsComplete => TraveledDistance >= TotalDistance;
    public bool IsGateMovement => TargetGateId.HasValue;
}
```

### 충돌 감지 알고리즘 (Pi-World)

**Location 내 2D 충돌:**
```csharp
// 같은 Location에서 X 좌표 기반 충돌 감지
float distance = location.CalculateDistance(player.PositionX, unit.PositionX);
if (distance <= COLLISION_RADIUS)  // 기본값 5.0
{
    // 충돌 (만남) 발생
}
```

### Gate 교차 충돌 감지 (Pi-World)

서로 다른 Location에서 같은 Gate 쌍을 반대 방향으로 통과할 때 충돌을 감지합니다.

**시나리오:**
```
Location A -- Gate_A --> Location B
             <-- Gate_B --

P: Location A에서 Gate_A로 이동 중 (→ B로 갈 예정)
N: Location B에서 Gate_B로 이동 중 (→ A로 갈 예정)

둘이 Gate에서 교차 → on_meet 발생
```

**감지 조건:**
| 조건 | 설명 |
|------|------|
| P가 Gate로 이동 중 | `player.CurrentMovement?.TargetGateId != null` |
| N이 연결된 Location에 있음 | `npc.CurrentLocation == playerGate.ConnectedLocation` |
| N이 반대 Gate로 이동 중 | `npcGate.ConnectedLocation == player.CurrentLocation` |

**NPC 위치 처리 (플레이어 전용 특수 케이스):**
```
플레이어-NPC 교차 시:
  다이얼로그는 플레이어 중심이므로, NPC를 플레이어의 목적지(B)로 즉시 이동시킴.
  교차 전:  P → A에서 이동 중, N → B에서 이동 중
  교차 후:  P → B로 도착 예정, N → B로 즉시 이동 (이동 취소)
  → 다이얼로그 종료 후 P와 N이 같은 Location(B)에 있음

NPC끼리 교차 시:
  플레이어가 관여하지 않으므로 위치 조정 없음.
  N1과 N2가 교차해도 각자 원래 목적지로 이동.
  교차 후:  N1 → B, N2 → A (서로 반대 위치)
```

**감지 로직:**
```csharp
// event_system.cs - DetectGateCrossingMeetings()
if (unitGate.ConnectedLocation == player.CurrentLocation)
{
    // Gate 교차 발생!
    // ※ 다이얼로그는 플레이어 중심이므로, NPC를 플레이어의 목적지(B)로 이동
    unit.CurrentMovement = null;  // 이동 취소
    unit.SetLocation(connectedLocation);  // 플레이어 목적지로 이동
    unit.PositionX = playerGate.ArrivalX;  // Gate 도착 위치
}
```

**예측 로직:**
```csharp
// event_prediction_system.cs - PredictGateCrossings()
int playerTimeToGate = player.CurrentMovement.RemainingTime;
int npcTimeToGate = unit.CurrentMovement.RemainingTime;
int crossingTime = Math.Max(playerTimeToGate, npcTimeToGate);
// crossingTime에 NextStepDuration 조정
```

### 파일 위치

- `scripts/system/event_prediction_system.cs` - 이동 예측 및 시간 조정
- `scripts/system/event_system.cs` - 실시간 충돌 감지 (2D 거리 기반)
- `scripts/morld/unit/ActionLog.cs` - MovementProgress 정의

---

## Awareness (인식) 시스템

플레이어 근처에서 이동 중인 NPC를 감지하여 액션 로그로 알려줍니다.

### 동작 원리 (Pi-World)

```
1. 플레이어 이동 명령 입력 시
2. 같은 Location에서 이동 중인 NPC 또는 Gate로 접근 중인 NPC 감지
3. "세라가 앞마당 쪽에서 다가온다" 형태로 액션 로그 표시
```

### 감지 조건

| 조건 | 설명 |
|------|------|
| 같은 Location | 플레이어와 같은 Location에서 이동 중 |
| 인접 Gate | 플레이어의 출발지/도착지와 연결된 Gate |
| 접근 방향 | 플레이어 방향으로 이동 중 |

### 메시지 형식

```
{NPC이름}(이)가 {방향}에서 다가온다.
{NPC이름}(이)가 {방향}(으)로 향하고 있다.
```

**방향 결정:**
- NPC의 출발지 Location 이름 사용
- 플레이어 기준 상대적 위치

### 구현 위치

- `scripts/MetaActionHandler/MetaActionHandler.cs` - `GenerateNearbyAwarenessLogs()`

---

## EventPredictionSystem

미래 이벤트를 예측하여 NextStepDuration을 자동 조정합니다.

### 예측 대상

| 이벤트 | 예측 방법 |
|--------|----------|
| on_meet (위치) | 경로 시뮬레이션으로 만남 시점 계산 |
| on_meet (Gate 교차) | Gate 교차 충돌 시점 계산 |
| on_reach | 경로 시뮬레이션으로 도착 시점 계산 |

### 시간 조정 흐름

```
1. ThinkSystem: NPC Job 결정
2. EventPredictionSystem: 이벤트 예측, NextStepDuration 조정
3. JobBehaviorSystem: 실제 이동 처리
4. EventSystem: 이벤트 감지 및 처리
```

### RouteWaypoint 구조

```csharp
public struct RouteWaypoint
{
    public LocationRef Location { get; set; }  // 위치
    public int ArrivalTime { get; set; }       // 도착 시간
    public int StayDuration { get; set; }      // 체류 시간 (0=경유 통과)
    public int DepartureTime => ArrivalTime + StayDuration;  // 출발 시간
    public bool IsFinalDestination { get; set; }  // 최종 목적지 여부
}
```

### 파일 위치

- `scripts/system/event_prediction_system.cs`

---

## 파일 위치 요약

**C#:**
- `scripts/system/event_system.cs` - 이벤트 감지 및 처리
- `scripts/system/event_prediction_system.cs` - 이벤트 예측 및 시간 조정
- `scripts/system/event_system.cs` - Gate 교차 충돌 계산 (통합)
- `scripts/morld/event/GameEvent.cs` - 이벤트 타입 정의
- `scripts/morld/unit/ActionLog.cs` - MovementProgress 정의

**Python:**
- `scenarios/scenario02/python/events/__init__.py` - 이벤트 시스템 메인 (on_equip_change 처리 포함)
- `scenarios/scenario02/python/events/registry.py` - 이벤트 등록 시스템
- `scenarios/scenario02/python/events/reach/` - on_reach 핸들러
- `scenarios/scenario02/python/events/meet/` - on_meet 핸들러
- `scenarios/scenario02/python/events/game_start/` - game_start 핸들러
- `scenarios/scenario02/python/assets/characters/` - 캐릭터별 on_equip_change 핸들러
