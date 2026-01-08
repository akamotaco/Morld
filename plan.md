# Plan: 레거시 monologue 제거 및 이벤트 시스템 통합

## 핵심 원칙

1. **yield를 활용한 무중단 대화 프로세스**
   - 사용자 입출력 대기를 제외하고 대화 로직은 중단 없이 실행
   - Generator가 대화 흐름 전체를 제어
   - **yield 대기 중에는 게임 시간이 멈춤**
   - 이벤트 큐 불필요

2. **NPC 동행은 JobList 수정으로 처리**
   - `morld.set_npc_job()`으로 NPC Job을 덮어씌움 (override)
   - **고정 시점은 대화 시작이 아닌 "동행 결정 시"** (선택 후)
   - Job 종료 후 ThinkSystem에서 스케줄 기반으로 자동 복귀

3. **이벤트는 시간 순으로 처리**
   - 시스템 순서: `ThinkSystem → EventPredictionSystem → EventSystem → JobBehaviorSystem → PlayerSystem`
   - 이벤트 범위: `0 ~ NextStepDuration` (실제 시간 경과는 JobBehaviorSystem)
   - `lastEventTime`, `lastDialogTime`: **로컬 변수** (매 Step마다 0부터 시작, 상대 시간)
   - 일반 이벤트: `lastEventTime`만 갱신
   - 다이얼로그 이벤트: `lastDialogTime` 갱신 (+ `set_npc_time_consume()` duration)
   - `lastDialogTime` 이후 이벤트는 스킵 (이미 지나간 시간)
   - **ExcessTime은 EventSystem에서 계산 → PlayerSystem에서 적용 → 다음 Step에서 처리**

4. **동시 도착 우선순위**
   - 복합 이벤트 우선 체크 (A+B 함께 있을 때 발생하는 이벤트)
   - 없으면 개별 이벤트 순차 처리 (메모리상 우선순위)
   - 시간 경과 없으면 다음 이벤트 계속, 시간 경과 있으면 이후 이벤트 스킵

---

## 목표
1. 레거시 `{"type": "monologue", ...}` 형식 완전 제거
2. 이벤트 핸들러에서 `yield morld.dialog()` 지원
3. EventSystem과 EventPredictionSystem 중복 로직 통합

---

## 구현 단계

### Phase 1: 새 API 추가 ✅ 완료
- [x] `morld.set_npc_job(unit_id, action, duration)` 구현 (시간 경과 없음)
- [x] `morld.set_npc_time_consume(unit_id, action, duration)` 구현 (시간 경과 있음)
- [x] `EventSystem.AddDialogTimeConsumed(duration)` 메서드 추가 (→ Phase 2에서 lastDialogTime 방식으로 리팩터링 예정)
- [x] `DialogEvent`, `NpcMeetEvent` 기본 클래스 추가 (events/base.py)
- [x] scenario01/02 이벤트 시스템 구조 통일
- [x] GameEngine.cs 시스템 순서 변경 (EventPredictionSystem → EventSystem → JobBehaviorSystem)

### Phase 2: ExcessTime 처리 ✅ 완료
- [x] `EventSystem`에 `PlayerSystem` 참조 추가 (NextStepDuration 접근용)
- [x] `EventSystem`에서 ExcessTime 계산 및 보관
  - `lastDialogTime`: `_dialogTimeConsumed` 활용, 0부터 시작, job duration(상대 시간)으로 계산
  - `_excessTime = Math.Max(0, lastDialogTime - NextStepDuration)`
  - `FinalizeDialogTime()`: 이벤트 처리 완료 후 ExcessTime 계산 및 리셋
- [x] `PlayerSystem.AddExcessTime(minutes)` 메서드 추가
- [x] `PlayerSystem`에 `EventSystem` 참조 추가
- [x] `PlayerSystem`에서 `EventSystem.ConsumeExcessTime()` 호출하여 적용 (가져오고 리셋)
- [ ] 테스트: 다이얼로그 시간이 NextStepDuration 초과 시 자동 Step 진행 확인

### Phase 3: CallEventHandler Generator 전용화 ✅ 완료
- [x] `CallEventHandler()`에서 `PyGenerator` 반환 감지 추가 ✅
- [x] `GeneratorScriptResult` 반환 시 EventSystem에서 처리 로직 추가 ✅
  - `FlushEvents()`에서 `generator_dialog` 타입 처리
  - `MetaActionHandler.SetPendingGenerator()` 메서드 추가
  - `EventSystem.SetMetaActionHandler()` 메서드 추가

**목표:** Phase 4 완료 후 `PyDict` 분기 완전 제거 → Generator 전용

### Phase 4: Python 마이그레이션 ✅ 완료
- [x] 기존 이벤트 핸들러를 Generator 방식으로 변환
  - scenario01: reach/bedroom.py, reach/game_start.py
  - scenario02: game_start/prologue.py (PrologueStart)
- [x] `on_event_list()` 반환값을 Generator로 통일
- [x] registry.py에서 Generator 결과 처리 개선

### Phase 5: 레거시 완전 제거 ✅ 완료
- [x] `CallEventHandler()`에서 `PyDict` 분기 제거
- [x] `ProcessEventResult()`에서 monologue 변환 코드 제거
- [x] `ParseDictResult()` monologue 처리 제거 (message 타입만 유지)
- [x] `MonologueScriptResult` 클래스 제거
- [x] `NpcJobInfo`, `ApplyNpcJobs()` 제거
- [x] `MetaActionHandler`에서 monologue 케이스 제거

### Phase 6: EventSystem 통합 (선택적)
- [ ] EventPredictionSystem + EventSystem 역할 정리
- [ ] GameEngine._Process()의 이벤트 처리 로직 단순화

---

## ExcessTime: 초과 시간 처리

### 개념

```
NextStepDuration = 3시간 (13:00 ~ 16:00 예정)

이벤트 처리 중:
- 13:00: time_consume=0 이벤트 → lastDialogTime = 0분 (상대시간)
- 14:00: time_consume=2시간 이벤트 → lastDialogTime = 60 + 120 = 180분

ExcessTime = lastDialogTime - NextStepDuration
           = 180 - 180 = 0분 (초과 없음)

만약 time_consume=3시간이었다면:
  lastDialogTime = 60 + 180 = 240분
  ExcessTime = 240 - 180 = 60분 (1시간 초과)
```

→ 플레이어는 이미 초과분만큼 시간을 "소비"함 (대화하느라)
→ 초과분은 플레이어 입력 없이 자동 처리

### 핵심 의미

| 변수 | 의미 |
|------|------|
| `NextStepDuration` | 예정된 행동 시간 |
| `lastDialogTime` | 마지막 다이얼로그 종료 시점 (상대 시간, 로컬 변수) |
| `ExcessTime` | 초과분 = `max(0, lastDialogTime - NextStepDuration)` |

**참고**: `_dialogTimeConsumed` 변수 불필요. `lastDialogTime`으로 계산 가능.

### 처리 흐름

```
PlayerSystem._remainingDuration 활용:

1. 플레이어가 "4시간 수면" 선택
   → RequestTimeAdvance(240)
   → _remainingDuration = 240

2. Step 1: NextStepDuration = 60 (이벤트로 조정됨)
   → 60분 처리
   → _remainingDuration = 180

3. Step 2: NextStepDuration = 180
   → 180분 처리
   → _remainingDuration = 0
   → 완료
```

이미 "여러 Step에 걸쳐 처리"하는 구조가 있음!

### HasPendingTime과의 관계

```csharp
// PlayerSystem
public bool HasPendingTime => _remainingDuration > 0;

// ExcessTime 추가 시:
_remainingDuration += excessTime;

// → HasPendingTime = true
// → 플레이어 입력 대기 없이 다음 Step 자동 진행
```

기존 구조를 그대로 활용:
- `_remainingDuration > 0` → `HasPendingTime = true` → 자동 Step 진행
- `_remainingDuration = 0` → `HasPendingTime = false` → 플레이어 입력 대기

### ExcessTime 계산 및 적용

**EventSystem에서 계산:**
```csharp
// EventSystem.Proc() 끝에서:
// lastDialogTime은 로컬 변수로 이벤트 처리 중 갱신됨
_excessTime = Math.Max(0, lastDialogTime - _playerSystem.NextStepDuration);

#if DEBUG_LOG
if (_excessTime > 0)
    GD.Print($"[EventSystem] ExcessTime 계산: {lastDialogTime} - {_playerSystem.NextStepDuration} = {_excessTime}분");
#endif
```

**PlayerSystem에서 적용:**
```csharp
// PlayerSystem.Proc()에서:
int excessTime = _eventSystem.ConsumeExcessTime();  // 가져오고 리셋
if (excessTime > 0)
{
    AddExcessTime(excessTime);
}
```

### 구현 위치

**EventSystem에 추가:**
```csharp
private int _excessTime = 0;

/// <summary>
/// ExcessTime 반환 및 리셋
/// PlayerSystem에서 호출하여 적용
/// </summary>
public int ConsumeExcessTime()
{
    int result = _excessTime;
    _excessTime = 0;
    return result;
}
```

**PlayerSystem에 추가:**
```csharp
/// <summary>
/// 초과 시간 추가 (다이얼로그에서 NextStepDuration 초과 시)
/// 플레이어가 이미 소비한 시간이므로 입력 없이 자동 처리됨
/// </summary>
public void AddExcessTime(int minutes)
{
    _remainingDuration += minutes;
#if DEBUG_LOG
    GD.Print($"[PlayerSystem] ExcessTime 추가: +{minutes}분 (총 대기: {_remainingDuration}분)");
#endif
}
```

### ExcessTime Step 흐름

```
Step N: (NextStepDuration = 10분)
  ThinkSystem      → NPC think() 호출
  EventSystem      → 이벤트 처리, lastDialogTime = 30분
                   → ExcessTime = 30 - 10 = 20분 계산/보관
  JobBehaviorSystem → 10분 시간 경과 처리
  PlayerSystem     → ConsumeExcessTime() → 20분 가져오고 리셋
                   → AddExcessTime(20) → _remainingDuration += 20
                   → HasPendingTime = true

Step N+1: (자동 진행, NextStepDuration = 20분)
  ThinkSystem      → NPC think() 호출 (20분 분량 스케줄)
  EventSystem      → 이벤트 처리 (중복 이벤트는 once 플래그로 방지)
  JobBehaviorSystem → 20분 시간 경과 처리
  PlayerSystem     → ConsumeExcessTime() → 0분 (초과 없음)
                   → _remainingDuration = 0
                   → HasPendingTime = false → 플레이어 입력 대기
```

### 중복 이벤트 방지

```python
# once=True로 일회성 이벤트 설정
class SeraFirstMeet(DialogEvent):
    once = True  # 한 번만 발생

    def handle(self, player_id, unit_ids):
        yield morld.dialog("...")
        morld.set_npc_time_consume(npc_id, "stay", 30)
```

### 대화 자체 시간 경과

모든 선택지에서 `set_npc_time_consume` 호출:
```python
result = yield morld.dialog(
    "어떻게 할까?\n"
    "[url=@ret:yes]예[/url]\n"
    "[url=@ret:no]아니오[/url]"
)

# 선택과 관계없이 대화 시간 30분 소비
if result == "yes":
    morld.set_npc_time_consume(npc_id, "follow", 30)
else:
    morld.set_npc_time_consume(npc_id, "stay", 30)

# 나중에 헬퍼 함수로 우아하게 처리 가능
```

---

## 관련 파일

### C# 수정
- `scripts/system/script_system.cs` - `set_npc_job`, `set_npc_time_consume` API ✅
- `scripts/system/event_system.cs` - `AddDialogTimeConsumed()` ✅
- `scripts/GameEngine.cs` - 시스템 순서 변경 ✅

### Python 수정
- `scenarios/scenario01/python/events/base.py` - 이벤트 기본 클래스 ✅
- `scenarios/scenario01/python/events/registry.py` - 이벤트 라우팅 ✅
- `scenarios/scenario02/python/events/base.py` - 이벤트 기본 클래스 ✅
- `scenarios/scenario02/python/events/registry.py` - 이벤트 라우팅 ✅
