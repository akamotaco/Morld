# 시간 흐름 시스템

## 개요

게임 내 시간은 플레이어 액션에 의해 진행됩니다. 추가로 **자동 시간 흐름** 기능을 통해 플레이어가 행동하지 않아도 시간이 흐르도록 설정할 수 있습니다.

---

## 시간 진행 방식

### 1. 플레이어 액션 기반 (기본)

플레이어가 행동을 선택하면 해당 행동에 필요한 시간만큼 게임 시간이 진행됩니다.

```
플레이어 액션 → RequestTimeAdvance(분) → PlayerSystem.HasPendingTime = true
→ ECS Step 실행 → 전체 시뮬레이션 수행
```

### 2. 멍때리기 (Idle)

플레이어가 "멍때리기" 액션을 선택하면 지정된 시간만큼 게임 시간이 진행됩니다.

```python
# Python ui.py에서 idle 액션 정의
"[url=idle:5]멍때리기 (5분)[/url]"
```

### 3. 자동 시간 흐름 (Auto Time Flow)

설정에서 활성화하면, 플레이어가 아무 행동도 하지 않아도 실시간 기준으로 일정 간격마다 게임 시간이 자동으로 흐릅니다.

---

## AutoTimeFlowSystem

### 위치
`scripts/system/auto_time_flow_system.cs`

### 설정값

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `Enabled` | false | 자동 시간 흐름 활성화 여부 |
| `RealTimeIntervalSeconds` | 5.0 | 실시간 간격 (초) |
| `GameTimeIntervalMinutes` | 1 | 한 번에 흐르는 게임 시간 (분) |

### 동작 원리

```
GameEngine._Process() 호출
  ↓
AutoTimeFlowSystem.Update(deltaSeconds)
  ↓
누적 시간 >= RealTimeIntervalSeconds 이면
  ↓
GameEngine에서 RequestTimeAdvance() 호출
  ↓
기존 ECS 파이프라인 실행 (멍때리기와 동일)
```

### 자동 시간 흐름 정지 조건

다음 조건에서는 자동 시간 흐름이 정지됩니다:

1. **시스템 비활성화**: `Enabled = false`
2. **시간 정지 상태**: `WorldSystem.IsTimeFrozen() = true`
3. **플레이어 시간 진행 중**: `PlayerSystem.HasPendingTime = true`
4. **Focus가 시간 흐름을 허용하지 않음**: `TextUISystem.CanAutoTimeFlow() = false`

---

## Focus와 시간 흐름

### TimeFlows 속성

`Focus` 클래스에 `TimeFlows` 속성이 있어 다이얼로그별로 시간 흐름 허용 여부를 설정할 수 있습니다.

| TimeFlows | 설명 | 예시 |
|-----------|------|------|
| `false` (기본) | 이 Focus가 활성화된 동안 자동 시간 흐름 정지 | 대화, 이벤트, 인벤토리 |
| `true` | 이 Focus가 활성화된 동안 자동 시간 흐름 계속 | 지도 보기 |

### Python에서 time_flows 설정

```python
# 지도 보기 - 시간이 흐르는 다이얼로그
yield morld.dialog(text, autofill="off", proc=handle_action, time_flows=True)

# 일반 대화 - 시간 정지 (기본)
yield morld.dialog("대화 내용")
```

### tick 콜백

`time_flows=True`인 다이얼로그에서 자동 시간 흐름이 발생하면, `proc("tick")` 콜백이 호출되어 UI를 갱신할 수 있습니다.

```python
def handle_action(action):
    if action == "init":
        return None

    if action == "tick":
        # 시간이 흐른 후 UI 갱신
        return render_updated_text()

    # 다른 액션 처리...
```

---

## 설정 UI 연동

Python `settings.py`에서 자동 시간 흐름 ON/OFF를 토글할 수 있습니다.

```python
# settings.py
def toggle_auto_time_flow():
    morld.toggle_auto_time_flow()
```

---

## 구현 파일

| 파일 | 역할 |
|------|------|
| `scripts/system/auto_time_flow_system.cs` | 자동 시간 흐름 시스템 |
| `scripts/GameEngine.cs` | AutoTimeFlowSystem 호출 및 시간 진행 |
| `scripts/system/text_ui_system.cs` | `CanAutoTimeFlow()` - Focus 기반 허용 여부 |
| `scripts/morld/ui/Focus.cs` | `TimeFlows` 속성 |
| `scripts/morld/ui/Dialog.cs` | `PyDialogRequest.TimeFlows` 속성 |
| `scripts/MetaActionHandler/MetaActionHandler.Dialog.cs` | `TriggerDialogTick()` - tick 콜백 호출 |
| `scenarios/scenario02/python/map_ui.py` | 지도 UI (time_flows=True 사용 예시) |
| `scenarios/scenario02/python/settings.py` | 설정 UI에서 토글 |
