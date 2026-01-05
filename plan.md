# Plan: EventPredictionSystem

## 목표
시간 흐름 중 발생할 이벤트를 예측하고, 시간 중단이 필요한 이벤트가 있으면 `NextStepDuration`을 조정하는 시스템.

---

## 1. 핵심 개념

EventPredictionSystem은 **두 가지 소스**에서 이벤트를 예측:
1. **이동 경로 충돌** - 플레이어/NPC 경로가 교차하여 만남 발생
2. **JobList 액션** - 유닛의 스케줄/액션에 의한 이벤트 (종울림, 텔레파시 등)

**핵심 포인트:**
- C#에서 예측 로직 전체 처리, Python은 `event_log`만 활용
- 시간 중단이 필요한 이벤트를 미리 감지하여 `NextStepDuration` 조정
- 조정 시점 이후의 예측 이벤트는 삭제 (다음 시간 진행 시 다시 예측)

---

## 2. 시스템 순서

```
ThinkSystem → EventPredictionSystem → JobBehaviorSystem → EventSystem
     ↓              ↓                        ↓                ↓
  JobList 채움   1. 경로 충돌 예측        조정된 시간만큼    즉시 이벤트
               2. 액션 이벤트 예측       이동 실행         처리
               3. 최소 시간 계산
               4. NextStepDuration 조정
```

---

## 3. 대표 예시: 종 오브젝트

**설정:**
1. 뒷마당에 종(Bell) 오브젝트 설치
2. 종은 스케줄을 통해 매일 점심(12:00)마다 "종울림" 이벤트 발생
3. 이 이벤트는 플레이어의 시간 흐름을 중단 (`InterruptsTime = true`)

**시나리오:**
```
플레이어: 10:00에 숲에서 열매 채집 후 피곤해서 6시간 취침 요청

[예측 단계 - EventPredictionSystem]
1. 플레이어 요청: 6시간 (360분) 취침
2. 종 오브젝트 스케줄 확인: 12:00에 종울림 이벤트 예정
3. 종울림 이벤트가 InterruptsTime = true
4. 10:00 + 2시간 = 12:00에 이벤트 발생 예측
5. NextStepDuration을 6시간 → 2시간으로 조정

[실행 단계]
1. 2시간만 시간 진행 (10:00 → 12:00)
2. 종울림 이벤트 발생
3. 다이얼로그: "마을 쪽으로 부터 종소리가 들렸다. 점심인가 보다. [확인]"
4. 플레이어는 12:00부터 다시 조작 시작
```

---

## 4. 이벤트 소스 분류

| 소스 | 설명 | 예시 |
|------|------|------|
| **이동 충돌** | 플레이어/NPC 경로가 교차 | 플레이어가 이동 중 NPC와 만남 |
| **오브젝트 스케줄** | 오브젝트의 시간 기반 이벤트 | 종 울림, 폭탄 폭발 |
| **NPC 스케줄** | NPC의 시간 기반 액션 | 텔레파시, 습격, 방문 |
| **환경 이벤트** | 시간대별 환경 변화 | 해질녘, 폭풍 시작 |

---

## 5. 이벤트 로그 시점 기록

**핵심 원칙:** 예측된 이벤트에는 발생 시점(`TriggerMinutes`)이 기록되어야 하며, 시간 조정 시 조정 시점 이후의 이벤트는 삭제해야 함.

```
예시: 플레이어가 10:00에 6시간 취침 요청

[예측된 이벤트들]
- +120분 종울림 (InterruptsTime = true)
- +150분 NPC 만남 (InterruptsTime = true) ← 이동 충돌
- +240분 폭풍 시작 (InterruptsTime = true)

[처리]
1. 가장 빠른 +120분 종울림에서 break
2. 시간을 120분만 진행
3. TriggerMinutes > 120인 이벤트들 삭제 (NPC 만남, 폭풍 시작)
4. NPC 만남은 다음 시간 진행 시 다시 예측됨 (상황 변경 가능)
```

**이유:**
- 예측된 이벤트 ≠ 발생한 이벤트
- 시간이 조정되면 조정 시점 이후의 예측 이벤트들은 무효화
- 다음 시간 진행 시 다시 예측해야 함 (상황이 변했을 수 있음)

---

## 6. 스케줄 기반 이벤트 구조 (미구현)

```python
# 오브젝트 스케줄 예시
class Bell(Object):
    SCHEDULE = [
        {
            "time": "12:00",           # 매일 12:00
            "event": "bell_ring",      # 이벤트 타입
            "interrupts_time": True,   # 시간 중단 여부
            "range": "region",         # 영향 범위 (same_location, region, global)
            "dialog": {
                "type": "monologue",
                "pages": ["마을 쪽으로 부터 종소리가 들렸다. 점심인가 보다."],
                "button_type": "ok"
            }
        }
    ]
```

---

## 7. 구현 상태

**완료:**
- [x] EventPredictionSystem 기본 구조 (C# 로직)
- [x] 이동 경로 충돌 예측 (PredictMeetings)
- [x] 도착 이벤트 예측 (PredictArrivals)
- [x] 시간 조정 로직 (AdjustNextStepDuration)

**미구현:**
- [ ] JobList 액션 기반 이벤트 예측 (PredictActions)
- [ ] 시간 조정 시 이후 이벤트 삭제 로직
- [ ] 이벤트 범위(range) 시스템
- [ ] 다이얼로그 연동

---

## 8. 열린 질문들

### 자전거 (Future)
- 탑승자 동시 이동 로직
- 이동 속도 (travelTime 비율)

### EventPredictionSystem
- 예측 범위는 얼마로 할 것인가? (요청된 시간 전체? 최대 N분?)
- NPC 행동 예측의 정확도는? (확정적 vs 확률적)

### Vehicle 시스템 관련
- 자동차 소유권/열쇠 시스템?
- 연료/내구도 시스템 필요?
- NPC도 자동차 운전 가능하게 할 것인가?

---

# Plan: yield 기반 모놀로그/다이얼로그 시스템

## 목표
기존 콜백 기반 모놀로그 시스템을 **yield 기반 제너레이터 패턴**으로 통합하여 Python에서 전체 흐름을 제어할 수 있도록 개선

## 현재 문제점

### 1. 복잡한 콜백 구조
```python
# 현재 방식 - 콜백 문자열 기반
return {
    "type": "monologue",
    "pages": ["대화..."],
    "button_type": "yesno",
    "done_callback": "on_accept:param1",    # 문자열 파싱 필요
    "cancel_callback": "on_reject"
}

# on_accept, on_reject 함수를 별도로 정의해야 함
```

### 2. 분산된 상태 관리
- `_pendingAction` - C# Action 델리게이트
- `_pendingGenerator` - Python 제너레이터
- `DoneCallback` / `CancelCallback` - 문자열 콜백
- 우선순위 관리 복잡 (3가지 경로)

### 3. Python-C# 경계 넘나들기
- Python → C# (ScriptResult) → 사용자 선택 → C# (콜백 파싱) → Python
- 흐름 추적 어려움, 디버깅 복잡

## 제안: yield 기반 통합 패턴

### 새로운 API
```python
# 제안 방식 - yield 기반
def on_meet_player(player_id):
    # 모놀로그 표시 후 사용자 응답 대기
    result = yield morld.monologue(
        pages=["대화 내용...", "계속..."],
        button_type="YESNO",
        time_consumed=2
    )

    if result == "YES":
        morld.add_action_log("승낙했습니다.")
        # 후속 처리...
    else:
        morld.add_action_log("거절했습니다.")
        # 거절 처리...

    # 연속 다이얼로그도 자연스럽게
    result2 = yield morld.messagebox("확인", "정말로?", "YESNO")
```

### 장점
1. **단일 함수에서 전체 흐름** - 콜백 분산 없음
2. **직관적인 코드** - 위에서 아래로 읽으면 됨
3. **상태 관리 단순화** - `_pendingGenerator` 하나로 통합
4. **디버깅 용이** - Python 코드만 보면 흐름 파악

## 구현 계획

### Phase 1: morld.monologue() API 추가
1. `PyMonologueRequest` 클래스 생성 (MessageBox.cs 확장)
   - pages, button_type, time_consumed 포함

2. `morld.monologue()` 함수 등록 (script_system.cs)
   ```csharp
   morldModule.ModuleDict["monologue"] = new PyBuiltinFunction("monologue", args => {
       // pages, button_type, time_consumed 파싱
       return new PyMonologueRequest(pages, buttonType, timeConsumed);
   });
   ```

3. `ProcessGenerator()`에서 PyMonologueRequest 감지 추가
   ```csharp
   if (yieldedValue is PyMonologueRequest monoRequest)
   {
       return new GeneratorScriptResult
       {
           Type = "generator_monologue",
           Generator = generator,
           MonologueRequest = monoRequest.Request
       };
   }
   ```

### Phase 2: MetaActionHandler 처리
1. `ProcessScriptResult()`에 `"generator_monologue"` 케이스 추가
   ```csharp
   case "generator_monologue":
       _pendingGenerator = genResult.Generator;
       _textUISystem?.ShowMonologue(
           monoRequest.Pages,
           monoRequest.TimeConsumed,
           monoRequest.ButtonType,
           doneCallback: null,  // 콜백 불필요
           cancelCallback: null
       );
       break;
   ```

2. `HandleMonologueDoneAction()` 수정
   - pendingGenerator 체크 추가 (Yes와 동일하게)
   ```csharp
   if (_pendingGenerator != null)
   {
       ResumeGeneratorWithResult(generator, "OK");
       return;
   }
   ```

### Phase 3: 기존 시스템과 호환성 유지
- 기존 `return {"type": "monologue", ...}` 방식 계속 지원
- 새로운 `yield morld.monologue(...)` 방식 추가
- 점진적 마이그레이션 가능

### Phase 4: 이벤트 핸들러 통합 (선택적)
GameStartEvent, ReachEvent, MeetEvent의 handle() 메서드도 제너레이터로 변환 가능
```python
class PrologueStart(GameStartEvent):
    def handle(self, **ctx):
        # 첫 번째 다이얼로그
        yield morld.monologue(pages=["...", "..."], button_type="OK")

        # 이름 선택
        name = yield morld.select(options=["이름1", "이름2", "이름3"])

        # 나이 선택
        age = yield morld.select(options=["청년", "중년", "노년"])

        # 완료
        morld.set_prop("player_name", name)
```

## 파일 변경 목록

### 수정
- `scripts/morld/ui/MessageBox.cs` - PyMonologueRequest 추가
- `scripts/system/script_system.cs` - morld.monologue() 함수 + ProcessGenerator 확장
- `scripts/MetaActionHandler.cs` - generator_monologue 처리 + HandleMonologueDoneAction 수정

### 신규 (선택적)
- `scripts/morld/ui/MonologueRequest.cs` - 별도 파일로 분리 가능

## 마이그레이션 전략

### 단계별 적용
1. 새 API 구현 (기존 코드 영향 없음)
2. 새로운 이벤트/스크립트부터 yield 방식 사용
3. 기존 콜백 방식 코드는 필요 시 점진적 변환

### 호환성
- `done_callback`, `cancel_callback` 필드는 deprecated 표시 후 유지
- 기존 `return {"type": "monologue", ...}` 방식 계속 동작

## 현재 버그 (우선 수정 필요)

### YES 버튼 클릭 후 화면 진행 안됨
**증상**: MessageBox 테스트에서 YES 클릭 시 다음으로 넘어가지 않음 (NO는 정상)

**원인 추정**:
- `ResumeGenerator`에서 StopIteration 발생 시 반환값 처리 문제
- 또는 `ProcessScriptResult`에서 `"message"` 타입 처리 후 화면 갱신 누락

**디버깅 포인트**:
1. `ResumeGenerator` 로그 확인 - StopIteration.value가 제대로 파싱되는지
2. `ProcessScriptResult`에서 `"message"` 타입 처리 후 `RequestUpdateSituation()` 호출 필요 여부
