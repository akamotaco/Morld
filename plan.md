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

# Plan: morld.dialog() - 통합 다이얼로그 시스템

## 목표
기존의 복잡한 모놀로그/메시지박스 시스템을 **단일 `morld.dialog()` API**로 통합.
C#은 최소한의 메시지 전달만, Python이 모든 UI 로직을 제어.

---

## 1. 설계 원칙

### Python에게 자유를, C#은 견고하게
- **C# 역할**: URL 파싱 + 메시지 전달 (로직 없음)
- **Python 역할**: 상태 관리, 페이지 전환, 조건 검사 등 모든 로직

### 제거 대상 (기존 시스템)
- `morld.messagebox()` - 별도 API 불필요
- `button_type: ok/yesno/none/none_on_last` - 복잡한 버튼 타입 분기
- `done_callback/cancel_callback` - 콜백 문자열 시스템
- `_pendingAction` - C# Action 델리게이트

---

## 2. API 설계

### 기본 사용법
```python
# 단일 API: morld.dialog(text)
result = yield morld.dialog("텍스트 내용")
```

### URL 패턴
| 패턴 | 동작 | 설명 |
|------|------|------|
| `@ret:값` | 다이얼로그 종료, yield에 값 반환 | 최종 선택 |
| `@proc:값` | generator에 값 전달, 다이얼로그 유지 | 상태 변경 |

### 사용 예시

#### 단순 확인 (기존 button_type: ok)
```python
yield morld.dialog("메시지입니다.\n\n[url=@ret:ok]확인[/url]")
```

#### Yes/No 선택 (기존 button_type: yesno)
```python
result = yield morld.dialog(
    "진행하시겠습니까?\n\n"
    "[url=@ret:yes]예[/url] [url=@ret:no]아니오[/url]"
)
if result == "yes":
    # 승낙 처리
```

#### 다중 선택지 (기존 script:xxx 패턴)
```python
name = yield morld.dialog(
    "이름을 선택하세요.\n\n"
    "[url=@ret:kim]김[/url]\n"
    "[url=@ret:lee]이[/url]\n"
    "[url=@ret:park]박[/url]"
)
```

#### 상호작용 다이얼로그 (새 기능)
```python
state = {"str": 5, "agi": 5, "points": 10}

while True:
    result = yield morld.dialog(
        f"스탯 배분\n\n"
        f"힘: {state['str']} [url=@proc:str+]+[/url] [url=@proc:str-]−[/url]\n"
        f"민첩: {state['agi']} [url=@proc:agi+]+[/url] [url=@proc:agi-]−[/url]\n"
        f"남은 포인트: {state['points']}\n\n"
        f"[url=@ret:confirm]확인[/url] [url=@ret:cancel]취소[/url]"
    )
    # result = "str+", "str-", "confirm", "cancel" 등 (prefix 없이 값만)

    if result in ("confirm", "cancel"):
        break

    # @proc: 값 처리
    if result == "str+" and state["points"] > 0:
        state["str"] += 1
        state["points"] -= 1
    elif result == "str-" and state["str"] > 1:
        state["str"] -= 1
        state["points"] += 1
    # ... 등등
```

#### 다중 페이지 (새 기능)
```python
pages = [
    "첫 번째 페이지입니다.\n\n[url=@proc:next]다음[/url]",
    "두 번째 페이지입니다.\n\n[url=@proc:prev]이전[/url] [url=@proc:next]다음[/url]",
    "마지막 페이지입니다.\n\n[url=@proc:prev]이전[/url] [url=@ret:done]완료[/url]"
]
page = 0

while True:
    result = yield morld.dialog(pages[page])
    # result = "next", "prev", "done" (prefix 없이 값만)

    if result == "done":
        break
    elif result == "next":
        page = min(page + 1, len(pages) - 1)
    elif result == "prev":
        page = max(page - 1, 0)
```

---

## 3. C# 구현

### PyDialogRequest 클래스
```csharp
// scripts/morld/ui/Dialog.cs
public class PyDialogRequest : PyObject
{
    public string Text { get; }

    public PyDialogRequest(string text)
    {
        Text = text;
    }

    public override string GetTypeName() => "DialogRequest";
}
```

### ScriptSystem - morld.dialog() 등록
```csharp
// script_system.cs
morldModule.ModuleDict["dialog"] = new PyBuiltinFunction("dialog", args => {
    string text = args[0].AsString();
    return new PyDialogRequest(text);
});
```

### ScriptSystem - ProcessGenerator 확장
```csharp
if (yieldedValue is PyDialogRequest dialogRequest)
{
    return new GeneratorScriptResult
    {
        Type = "generator_dialog",
        Generator = generator,
        DialogText = dialogRequest.Text
    };
}
```

### MetaActionHandler - URL 핸들러
```csharp
// @ret:xxx - 다이얼로그 종료, 값 반환
if (url.StartsWith("@ret:"))
{
    var value = url.Substring(5);  // "@ret:yes" → "yes"
    _textUISystem.Pop();
    ResumeGeneratorWithResult(generator, value);
    return;
}

// @proc:xxx - 다이얼로그 유지, 값 전달
if (url.StartsWith("@proc:"))
{
    // pendingGenerator가 없으면 에러 (버그)
    if (_pendingGenerator == null)
    {
        GD.PrintErr("[MetaActionHandler] @proc: called without pending generator - this is a bug!");
        return;
    }

    var value = url.Substring(6);  // "@proc:next" → "next"
    // Pop 안함 - 다이얼로그 유지, 텍스트는 다음 yield에서 갱신됨
    ResumeGeneratorWithResult(generator, value);
    return;
}
```

### MetaActionHandler - ProcessScriptResult (다이얼로그 생명주기)
```csharp
case "generator_dialog":
    if (result is GeneratorScriptResult genResult)
    {
        _pendingGenerator = genResult.Generator;

        // Win32 DialogBox 스타일: Push → Update → Pop
        // 현재 다이얼로그가 열려있으면 텍스트만 갱신 (lazy 아님, 즉시 갱신)
        // 없으면 새로 Push
        if (_textUISystem?.CurrentFocus?.Type == FocusType.Dialog)
        {
            _textUISystem.UpdateDialogText(genResult.DialogText);  // 즉시 텍스트 갱신
        }
        else
        {
            _textUISystem?.PushDialog(genResult.DialogText);  // 새 다이얼로그 Push
        }
    }
    break;
```

### TextUISystem - 새 메서드
```csharp
/// <summary>
/// 다이얼로그 Push (첫 yield morld.dialog() 호출 시)
/// </summary>
public void PushDialog(string text)
{
    var focus = new FocusState
    {
        Type = FocusType.Dialog,
        Text = text,
        ButtonType = MonologueButtonType.None  // 버튼 없음, BBCode URL로 제어
    };
    _focusStack.Push(focus);
    RequestRender();  // 즉시 렌더링
}

/// <summary>
/// 다이얼로그 텍스트 갱신 (@proc: 후 다음 yield 호출 시)
/// lazy 방식 아님 - 즉시 RichTextLabel 텍스트 갱신
/// </summary>
public void UpdateDialogText(string text)
{
    if (CurrentFocus?.Type != FocusType.Dialog)
    {
        GD.PrintErr("[TextUISystem] UpdateDialogText called but no dialog is open - this is a bug!");
        return;
    }

    CurrentFocus.Text = text;
    // 즉시 RichTextLabel 텍스트 갱신 (lazy 아님)
    _richTextLabel.Text = text;
}
```

---

## 4. 구현 단계

### Phase 1: 기본 구조 ✅ 완료
1. [x] `PyDialogRequest` 클래스 생성 (`Dialog.cs`)
2. [x] `morld.dialog()` 함수 등록 (`script_system.cs`)
3. [x] `ProcessGenerator()`에서 `PyDialogRequest` 감지
4. [x] `GeneratorScriptResult`에 `DialogText` 필드 추가
5. [x] `FocusType.Dialog` enum 값 추가
6. [x] `TextUISystem.PushDialog()` 메서드 추가
7. [x] `TextUISystem.UpdateDialogText()` 메서드 추가

### Phase 2: URL 핸들러 ✅ 완료
1. [x] `@ret:` 패턴 처리 (Pop + 값 반환)
2. [x] `@proc:` 패턴 처리 (값만 반환, 다이얼로그 유지)
3. [x] `ProcessScriptResult`에서 `generator_dialog` 케이스 추가 (Push/Update 분기)

### Phase 3: 기존 시스템 정리 ✅ 완료
1. [x] `morld.messagebox()` 제거
2. [x] `MessageBox.cs` 삭제
3. [x] `FocusType.Monologue` 제거
4. [x] `MonologueButtonType` enum 제거
5. [x] Dialog 큐 시스템 구현 (연쇄 다이얼로그 지원)

### Phase 4: 레거시 호환성 ✅ 완료
레거시 `{"type": "monologue", ...}` 형식은 C#에서 자동으로 Dialog로 변환됨:
- `ProcessScriptResult()` - MetaActionHandler에서 변환
- `ProcessEventResult()` - EventSystem에서 변환
- 이벤트 핸들러는 제너레이터가 아니므로 레거시 형식 유지 필수
- 스크립트 함수는 `yield morld.dialog()` 또는 레거시 형식 모두 사용 가능

---

## 5. 파일 변경 목록

### 신규
- `scripts/morld/ui/Dialog.cs` - PyDialogRequest 클래스

### 수정
- `scripts/system/script_system.cs`
  - `morld.dialog()` 함수 등록
  - `ProcessGenerator()`에서 `PyDialogRequest` 감지
  - `GeneratorScriptResult`에 `DialogText` 필드 추가
- `scripts/MetaActionHandler.cs`
  - `@ret:` / `@proc:` URL 핸들러 추가
  - `ProcessScriptResult`에 `generator_dialog` 케이스 추가
- `scripts/system/text_ui_system.cs`
  - `FocusType.Dialog` enum 값 추가
  - `PushDialog()` 메서드 추가
  - `UpdateDialogText()` 메서드 추가 (즉시 갱신, lazy 아님)
- `scripts/morld/ui/FocusState.cs` (있다면)
  - `FocusType` enum에 `Dialog` 추가

### 삭제 완료 (Phase 3)
- `scripts/morld/ui/MessageBox.cs` - 삭제됨
- `FocusType.Monologue` - 제거됨
- `MonologueButtonType` enum - 제거됨

---

## 6. 장점

1. **단일 API** - `morld.dialog()` 하나로 모든 UI 상호작용
2. **Python 제어** - 버튼, 페이지, 선택지 모두 BBCode로 통일
3. **C# 단순화** - URL 파싱만, 로직 없음
4. **확장성** - 새 기능 추가 시 Python만 수정
5. **디버깅 용이** - Python 코드만 보면 흐름 파악

---

## 7. 해결된 이슈

### 기존 버그: YES 버튼 클릭 후 화면 진행 안됨
- ✅ 새 Dialog 시스템으로 해결됨
- `@ret:` 패턴으로 통일되어 버튼 타입별 분기 불필요
