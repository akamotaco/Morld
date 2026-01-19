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
| `on_time_elapsed` | 시간 경과 | minutes |
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

**OnMeet 감지 로직:**
```csharp
// 이동 중인 유닛(CurrentEdge != null)은 제외
var unitsToMeet = _unitSystem.Units.Values
    .Where(u => u.Id != playerId
             && u.GeneratesEvents
             && u.CurrentLocation == playerLocation
             && u.CurrentEdge == null)  // 이동 중이 아닌 유닛만
```

**캐릭터 핸들러:**
```python
# assets/characters/sera.py
class Sera(Character):
    def on_meet_player(self, player_id):
        """플레이어와 만났을 때 이벤트"""
        yield morld.dialog("...일어났군.")
        morld.set_npc_job(self.instance_id, "follow", 30)
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

def my_handler(minutes):
    print(f"{minutes}분 경과")

# 매번 호출
subscribe_time_elapsed(my_handler)

# 60분마다 호출
subscribe_time_elapsed(my_hourly_handler, min_interval=60)
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

## on_meet 순차 처리

한 위치에서 여러 NPC를 동시에 만났을 때, 이벤트가 우선순위별로 순차 처리됩니다.

```python
# Python 이벤트 큐 (events/__init__.py)
_pending_meet_events = []  # 대기 중인 이벤트 목록

def _collect_meet_events(player_id, unit_ids):
    """조건에 맞는 모든 on_meet 이벤트 수집"""
    events = []
    # 1. registry MeetEvent (priority 기반)
    # 2. character on_meet_player (priority -1)
    events.sort(key=lambda e: -e["priority"])  # 높은 priority 먼저
    return events

# C#에서 호출하는 API
def has_pending_meet_events():
    """대기 중인 이벤트 존재 여부"""
    return len(_pending_meet_events) > 0

def clear_pending_meet_events():
    """ExcessTime > 0일 때 대기 중인 이벤트 모두 제거"""
    global _pending_meet_events
    _pending_meet_events = []
```

**ExcessTime과 이벤트 큐 연동:**
```
1. 플레이어가 위치 도착 → 여러 NPC와 만남
2. 이벤트 큐 생성 (우선순위 정렬)
3. 첫 번째 이벤트 처리 (Dialog 표시)
4. Dialog 종료 후 ExcessTime 확인:
   - ExcessTime > 0: 남은 이벤트 모두 스킵 (시간 흐름)
   - ExcessTime == 0: 다음 이벤트 처리 (순차 대화)
5. 모든 이벤트 처리 완료 or ExcessTime 발생 시 종료
```

---

## NPC Job 제어

Generator 기반 이벤트 핸들러에서 NPC Job을 직접 제어:

```python
def handle(self, player_id, unit_ids):
    yield morld.dialog("대화 내용...")

    # NPC Job 설정 (시간 경과 없음)
    morld.set_npc_job(unit_id, "follow", duration=30)

    # 또는 시간 경과 포함
    morld.set_npc_time_consume(unit_id, "stay", duration=30)
```

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

## 파일 위치 요약

**C#:**
- `scripts/system/event_system.cs` - 이벤트 감지 및 처리
- `scripts/morld/event/GameEvent.cs` - 이벤트 타입 정의

**Python:**
- `scenarios/scenario02/python/events/__init__.py` - 이벤트 시스템 메인 (on_equip_change 처리 포함)
- `scenarios/scenario02/python/events/registry.py` - 이벤트 등록 시스템
- `scenarios/scenario02/python/events/reach/` - on_reach 핸들러
- `scenarios/scenario02/python/events/meet/` - on_meet 핸들러
- `scenarios/scenario02/python/events/game_start/` - game_start 핸들러
- `scenarios/scenario02/python/assets/characters/` - 캐릭터별 on_equip_change 핸들러
