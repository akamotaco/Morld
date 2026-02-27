# 시간 흐름 시스템

## 개요

게임 내 시간은 플레이어 액션에 의해 진행됩니다. 추가로 **자동 시간 흐름** 기능을 통해 플레이어가 행동하지 않아도 시간이 흐르도록 설정할 수 있습니다.

---

## 시간 진행 방식

### 1. 플레이어 액션 기반 (기본)

플레이어가 행동을 선택하면 해당 행동에 필요한 시간만큼 게임 시간이 진행됩니다.

```
플레이어 액션 → RequestTimeAdvance(밀리초) → PlayerSystem.HasPendingTime = true
→ ECS Step 실행 → 전체 시뮬레이션 수행
```

### 2. 시간 보내기 (Spend Time)

"시간 보내기" 토글 메뉴에서 세 가지 액션을 선택할 수 있습니다:

| 액션 | URL | 설명 |
|------|-----|------|
| 누군가를 기다리기 | `wait:300000` | 5분간 대기. 새 NPC 도착 시 자동 중단 |
| 멍때리기 | `idle:1800000` | 30분간 시간 경과 |
| 낮잠자기 | `idle:14400000` | 4시간 수면 (6시~18시만 가능) |

**기다리기 모드**: `wait` 액션은 `PlayerSystem._waitMode`를 활성화합니다.
시작 시점의 NPC 목록을 기록하고, 매 Step마다 새 NPC 도착을 감지하여 자동 중단합니다.
- 새 NPC 도착 → "누군가 다가오는 기척이 느껴졌다." + 시간 정지
- 5분 경과 아무도 안 옴 → "아무도 오지 않았다." + 시간 정지

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
| `GameTimeIntervalMillis` | 60,000 | 한 번에 흐르는 게임 시간 (밀리초, 기본 1분) |

### 프리셋 (settings.py)

| 이름 | 실시간 간격 | 게임 시간 | 설명 |
|------|------------|----------|------|
| 느리게 | 1초 | 1,000ms (1초) | X좌표 1단위씩 이동 |
| 보통 | 1초 | 30,000ms (30초) | 기본 속도 |
| 빠르게 | 1초 | 60,000ms (1분) | 시간 흐름 관찰용 |
| 매우 빠르게 | 1초 | 180,000ms (3분) | 스케줄 확인용 |
| 초고속 | 1초 | 300,000ms (5분) | 하루 빠르게 넘기기 |

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
기존 ECS 파이프라인 실행 (시간 보내기와 동일)
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

## DES 시뮬레이션 (v0.2.2)

플레이어 수면 등 대규모 시간 건너뛰기 시, NPC가 자율적으로 행동하도록 하는 시스템입니다.

> **아키텍처 참고**: DES 루프는 ECS Step(`GameEngine._Process → World.Step`)과 별도 경로로 실행됩니다.
> C#은 시스템 업데이트(이동, Job, 시간), Python은 컨텐츠 업데이트(think, 이벤트)를 담당하며,
> 이 분리가 유지되는 한 실질적으로 단일 호출입니다.
> 단, C# 시스템 로직(JobBehaviorSystem 등) 변경 시 DES 루프(`AdvanceTimeDES`)도 동기화해야 합니다.

### 시간 진행 API 비교

| API | NPC think() | 이동 처리 | 이벤트 | 용도 |
|-----|------------|----------|--------|------|
| `advance_time_des(ms)` | **O** | **O** | **O** | **모든 시간 진행** |

### 사용 예시

```python
# 수면 시 DES 시뮬레이션 (8시간)
morld.advance_time_des(480 * 60_000)
# → NPC들이 8시간 동안 자율적으로 행동 (채집, 요리, 이동 등)
```

### 동작 원리

```
advance_time_des(총시간) {
    while 남은시간 > 0:
        step = min(남은시간, 가장 짧은 NPC Job duration)
        이동 시뮬레이션 (step만큼)
        move job 완료된 NPC → 텔레포트
        Job duration 차감
        GameTime 증가
        survival 시간 경과 처리
        OnTimeElapsed 이벤트 발행
        think_all() → NPC 재결정
}
```

상세: [schedule.md#9](schedule.md#9-v022-des-discrete-event-simulation)

---

## 구현 파일

| 파일 | 역할 |
|------|------|
| `scripts/system/auto_time_flow_system.cs` | 자동 시간 흐름 시스템 |
| `scripts/GameEngine.cs` | AutoTimeFlowSystem 호출 및 시간 진행 |
| `scripts/system/text_ui_system.cs` | `CanAutoTimeFlow()` - Focus 기반 허용 여부 |
| `scripts/system/script_system.cs` | `EstimateMoveTravelTime()` - X좌표 기반 이동 시간 추정 (v0.2.2) |
| `scripts/system/script_system_data_api.cs` | `AdvanceTimeDES()` - DES 루프 (v0.2.2) |
| `scripts/morld/ui/Focus.cs` | `TimeFlows` 속성 |
| `scripts/morld/ui/Dialog.cs` | `PyDialogRequest.TimeFlows` 속성 |
| `scripts/MetaActionHandler/MetaActionHandler.Dialog.cs` | `TriggerDialogTick()` - tick 콜백 호출 |
| `scenarios/scenario02/python/map_ui.py` | 지도 UI (time_flows=True 사용 예시) |
| `scenarios/scenario02/python/settings.py` | 설정 UI에서 토글 |
