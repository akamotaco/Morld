# Frozen 상태 (시간 정지) 시스템

## 개요

`Frozen` 상태는 시간 흐름을 멈추고 플레이어만 자유롭게 이동할 수 있게 하는 시스템입니다.
프롤로그(챕터 0) 등에서 NPC 없이 탐색만 하는 구간에서 사용됩니다.

---

## 핵심 원칙

> **플레이어 주도 이벤트는 모두 발생, NPC 주도 이벤트는 차단**

| 구분 | Frozen 시 동작 |
|------|---------------|
| 플레이어 주도 | ✅ 정상 동작 |
| NPC 주도 | ❌ 차단됨 |

---

## C# 시스템별 Frozen 처리

| 시스템 | Frozen 시 동작 | 파일:라인 |
|--------|---------------|-----------|
| **WorldSystem** | `_timeFrozen` 플래그 저장 | `world_system.cs:27` |
| **JobBehaviorSystem** | NPC 이동 스킵, 플레이어 즉시 텔레포트 | `job_behavior_system.cs:38` |
| **ThinkSystem** | NPC AI (think_all) 스킵 | `think_system.cs:37` |
| **EventSystem.DetectMeetings()** | `on_meet` 이벤트 스킵 | `event_system.cs:295` |
| **advance_time_simulate** | 시뮬레이션 스킵 | `script_system_data_api.cs:528` |

### 코드 예시

```csharp
// EventSystem.cs - on_meet 차단
public void DetectMeetings()
{
    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

    // 시간 정지 상태에서는 on_meet 이벤트 스킵
    if (_worldSystem.IsTimeFrozen())
        return;

    // ... 만남 감지 로직
}
```

```csharp
// ThinkSystem.cs - NPC AI 스킵
public void Proc(...)
{
    // 시간 정지 상태면 NPC AI 스킵
    if (_worldSystem.IsTimeFrozen())
        return;

    // ... NPC think 호출
}
```

---

## 이벤트 처리 상세

### Frozen에서 차단되는 것 (NPC 주도)

| 항목 | 담당 시스템 | 차단 위치 |
|------|-------------|----------|
| 시간 흐름 | JobBehaviorSystem | GameTime 업데이트 스킵 |
| NPC 이동 | JobBehaviorSystem | NPC Job 처리 스킵 |
| NPC AI | ThinkSystem | think_all() 호출 스킵 |
| `on_meet` 이벤트 | EventSystem | DetectMeetings() 스킵 |
| `on_time_elapsed` | JobBehaviorSystem | 이벤트 Enqueue 안 함 |
| 생존 시스템 | survival.py | 시간 경과 없으므로 자동 스킵 |
| NPC 주도 스킨십 | npc_initiative.py | `on_meet` 차단으로 트리거 불가 |

### Frozen에서 동작하는 것 (플레이어 주도)

| 항목 | 담당 시스템 | 설명 |
|------|-------------|------|
| 플레이어 이동 | JobBehaviorSystem | 즉시 텔레포트 (시간 소모 없음) |
| `on_reach` 이벤트 | EventSystem | 챕터 전환에 필요 |
| 아이템 조작 | MetaActionHandler | 줍기/버리기/사용 (시간 소모 없음) |
| `call:` 액션 | MetaActionHandler | NPC/오브젝트 클릭 후 액션 |
| 다이얼로그 | ScriptSystem | Generator 기반 대화 |

---

## NPC 주도 스킨십 차단 경로

NPC 주도 스킨십은 `on_meet` 이벤트를 통해 트리거됩니다.
Frozen 상태에서는 `on_meet` 자체가 차단되므로 NPC 주도 스킨십도 발생하지 않습니다.

```
EventSystem.DetectMeetings()   ← Frozen 시 여기서 차단됨 ✓
         ↓
FlushEvents() → Python events.on_single_event("on_meet", ...)
         ↓
_process_next_meet_event() → handler.on_meet_player(player_id)
         ↓
Character.on_meet_player() → should_initiate_skinship() → start_npc_initiative()
```

---

## Python API

```python
import morld

# 시간 정지 설정/해제
morld.set_time_frozen(True)   # 시간 정지
morld.set_time_frozen(False)  # 시간 흐름 복원

# 시간 정지 상태 확인
if morld.is_time_frozen():
    print("시간이 멈춰있음")
```

---

## 챕터별 사용 예시

### 챕터 0 (프롤로그)

```python
# chapter_0.py
def initialize():
    morld.set_time_frozen(True)  # 시간 정지
    # NPC 없이 탐색만 가능
```

### 챕터 1 (본편)

```python
# chapter_1.py
def post_restore():
    morld.set_time_frozen(False)  # 시간 흐름 복원
    # NPC AI, 만남 이벤트 등 정상 동작
```

---

## 관련 파일

- `scripts/system/world_system.cs` - `_timeFrozen` 플래그 저장
- `scripts/system/job_behavior_system.cs` - 플레이어 즉시 이동, NPC/시간 스킵
- `scripts/system/think_system.cs` - NPC AI 스킵
- `scripts/system/event_system.cs` - `on_meet` 스킵
- `scripts/system/script_system_data_api.cs` - Python API (`set_time_frozen`, `is_time_frozen`)
- `scenarios/scenario02/python/npc_initiative.py` - NPC 주도 스킨십 (Frozen 시 트리거 불가)
