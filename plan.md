# 로그 및 대화 시스템 설계

## 0. 아키텍처 결정사항

### 결정: Python 스크립트 기반 하이브리드 아키텍처

**핵심 원칙:** C#은 "언제" 체크할지, Python은 "무엇을" 할지 결정

```
┌─────────────────────────────────────────────────────────┐
│                    C# (Godot/ECS)                       │
├─────────────────────────────────────────────────────────┤
│  [이벤트 감지 레이어]                                    │
│    ├─ 도착 이벤트: MovementSystem에서 location 도달 감지  │
│    ├─ 충돌 이벤트: 같은 위치에 2+ 캐릭터 감지             │
│    └─ 액션 이벤트: MetaActionHandler에서 talk/trade 감지  │
│                          │                               │
│                          ▼                               │
│  [Python 호출] ──────────────────────────────────────────│
│                          │                               │
│                          ▼                               │
│  [결과 처리 레이어]                                       │
│    └─ 모놀로그/다이얼로그 Focus Push                      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Python                              │
├─────────────────────────────────────────────────────────┤
│  [조건 평가]                                             │
│    should_trigger(event_type, context) → bool            │
│                                                          │
│  [콘텐츠 결정]                                           │
│    get_dialogue(speaker_id, listener_id, context)        │
│    get_monologue(event_id, context)                      │
│                                                          │
│  [게임 데이터 수정] (godot 모듈 통해 직접 호출)           │
│    godot.give_item(unit_id, item_id, count)              │
│    godot.get_unit_location(unit_id)                      │
│                                                          │
│  [결과 반환]                                             │
│    {                                                     │
│      "dialogue": {...},                                  │
│      "timeConsumed": N                                   │
│    }                                                     │
└─────────────────────────────────────────────────────────┘
```

### 역할 분담

| 영역 | 담당 | 이유 |
|------|------|------|
| 이벤트 감지 (훅 포인트) | C# | 성능, 명확한 타이밍 |
| 이벤트 조건 평가 | Python | 복잡한 조건 분기 |
| 대화 콘텐츠 | Python | 콘텐츠 관리 용이 |
| 기본 Appearance | JSON + C# | 성능 (자주 호출) |
| 게임 데이터 변경 | Python (godot 모듈) | 로직 외부화 |

---

## 1. Python 연동 방식

### 결정: sharpPy 임베딩 (유력)

`util/sharpPy` - 순수 C#로 작성된 Python 3.12 인터프리터

**장점:**
- 프로세스/Socket 통신 오버헤드 없음 (직접 호출)
- 외부 의존성 없음 (100% managed C# code)
- Godot 호환성 확보 (`#if GODOT` 조건부 컴파일 지원)
- PyObject ↔ C# 타입 직접 변환 가능
- 동기 호출 (async 복잡성 없음)

**단점:**
- CPython 대비 성능 (해석 실행)
- 일부 표준 라이브러리 미구현 (core modules만)
- C 확장 미지원 (순수 Python만)

### sharpPy 주요 API

```csharp
// 인터프리터 초기화
var interpreter = new IntegratedPythonInterpreter();

// Python 코드 실행
PyObject result = interpreter.Execute(pythonCode);
PyObject result = interpreter.Execute(pythonCode, fileName, false, false, false);

// VM 인스턴스 (싱글톤)
PyVM vm = PyVM.Instance;
```

### 타입 시스템

| Python | C# (sharpPy) |
|--------|--------------|
| int | PyInt |
| float | PyFloat |
| str | PyString |
| bool | PyBool |
| list | PyList |
| dict | PyDict |
| tuple | PyTuple |
| set | PySet |
| None | PyNone.Instance |
| function | PyFunction |

### ScriptSystem 사용 예시

ScriptSystem은 ScriptBridge 역할을 겸합니다.

```csharp
// 현재 구현된 ScriptSystem API
public class ScriptSystem : ECS.System
{
    // Python 코드 직접 실행
    public PyObject Execute(string code);
    public PyObject ExecuteFile(string filePath);

    // BBCode script: prefix 용 함수 호출
    public string CallFunction(string functionName, string[] args);
}

// 사용 예시: 이벤트 처리
var scriptSystem = _world.FindSystem("scriptSystem") as ScriptSystem;

// Python 함수 호출
var result = scriptSystem.CallFunction("handle_event", new[] { "arrive", "0" });

// 결과 처리
if (!string.IsNullOrEmpty(result))
{
    _textUISystem?.ShowResult(result);
}
```

**향후 확장:** Python 스크립트 파일 로드, dict 변환 등은 필요 시 추가

### 파일 구조

```
util/
└─ sharpPy/                    # Python 인터프리터 (기존)
   ├─ sharppy.csproj
   ├─ core/
   ├─ runtime/
   └─ ...

scripts/
├─ system/
│  └─ script_system.cs         # C# ↔ Python 통신 (구현 완료 ✓)
├─ python/                     # Python 스크립트 (신규)
│  ├─ monologues.py            # 모놀로그 데이터
│  ├─ dialogues.py             # 다이얼로그 (추후)
│  ├─ event_handler.py         # 이벤트 처리 (추후)
│  └─ flags.py                 # 플래그 관리 (추후)
└─ MetaActionHandler.cs        # script: 처리 (구현 완료 ✓)
```

### 미확인 사항

1. **Godot 빌드 통합**
   - sharpPy를 Godot 프로젝트에 포함하는 방법
   - `GODOT` 컴파일 플래그 활성화

2. **전역 스코프 공유**
   - Python 스크립트 간 상태 공유 방식
   - C#에서 Python 전역 변수 접근

3. **성능 테스트**
   - 이벤트당 호출 시간 측정 필요
   - 복잡한 조건 분기 성능

### 대안: 기존 통신 방식

sharpPy가 적합하지 않을 경우:

1. **프로세스 실행 + JSON stdin/stdout**
   - 장점: 단순, 언어 독립적
   - 단점: 프로세스 생성 오버헤드

2. **Named Pipe / Socket**
   - 장점: 지속 연결, 빠름
   - 단점: 복잡도 증가

3. **Python.NET 임베딩**
   - 장점: CPython 직접 사용
   - 단점: 네이티브 의존성, Godot 호환성 불확실

### 상태 전달

Python에 전달할 컨텍스트:
```python
context = {
    "event_type": "arrive",           # arrive, meet, action
    "actor_id": 0,                    # 이벤트 주체
    "target_ids": [1, 2],             # 관련 유닛들
    "location": {"regionId": 0, "localId": 1},
    "time": {"hour": 14, "minute": 30, "day": 1},
    "flags": {"met_철수": True, ...},
    "inventories": {...},             # 필요시
}
```

---

## 2. EventSystem 아키텍처

### 개요

이벤트 기반 아키텍처로 기반 시스템(MovementSystem 등)과 플러그인 시스템(DialogueSystem 등)을 분리합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                    기반 시스템 (Pure)                        │
│  MovementSystem, BehaviorSystem 등                          │
│                          │                                   │
│                    이벤트 감지 & 생성                        │
│                          ▼                                   │
├─────────────────────────────────────────────────────────────┤
│                    EventSystem (Data)                        │
│                    이벤트 저장소                              │
│                          │                                   │
│                    이벤트 조회                                │
│                          ▼                                   │
├─────────────────────────────────────────────────────────────┤
│                  플러그인 시스템 (분리 가능)                  │
│  DialogueSystem, MonologueSystem 등                          │
│                          │                                   │
│                    Python 호출                               │
│                          ▼                                   │
│                    ScriptSystem                              │
└─────────────────────────────────────────────────────────────┘
```

### 설계 결정사항

| 항목 | 결정 | 이유 |
|------|------|------|
| EventSystem 형태 | 독립 Data System (Option A) | 플러그인 분리, 명확한 책임 |
| 이벤트 소비 | 여러 시스템이 조회 가능 | DialogueSystem, QuestSystem 등 동시 처리 |
| 이벤트 정리 | EventSystem.Proc() 시작 시 전체 Clear | 단순, 명확 |
| 이벤트 생성 | 상태 변경 시점만 (도착/출발/만남) | 중복 방지 |

### 이벤트 타입

| 타입 | 생성 시점 | 생성 주체 | 설명 |
|------|----------|----------|------|
| `arrive` | 유닛이 위치에 도착 | MovementSystem | 이동 완료 시 |
| `depart` | 유닛이 위치에서 출발 | MovementSystem | 이동 시작 시 |
| `meet` | 두 유닛이 같은 위치에 있게 됨 | MovementSystem | 도착 시 해당 위치의 다른 유닛마다 생성 |
| `action` | 유닛이 행동 수행 | ActionSystem | talk, trade, use 등 |

### 이벤트 생성 예시 (meet)

```
상황: 철수가 광장에 있고, 영희가 광장에 도착

MovementSystem에서 생성하는 이벤트:
1. { type: "arrive", actor: 영희, location: 광장 }
2. { type: "meet", actor: 영희, target: 철수, location: 광장 }
```

### EventSystem 구조

```csharp
public class EventSystem : ECS.System
{
    private List<GameEvent> _events = new();

    // 이벤트 추가 (MovementSystem 등에서 호출)
    public void AddEvent(GameEvent ev);

    // 이벤트 조회 (DialogueSystem 등에서 호출)
    public IEnumerable<GameEvent> GetEvents();
    public IEnumerable<GameEvent> GetEventsByType(string type);
    public IEnumerable<GameEvent> GetEventsByActor(int actorId);

    // 특정 이벤트 삭제 (소비 완료 시)
    public void RemoveEvent(GameEvent ev);

    // Proc: Step 시작 시 전체 Clear
    public void Proc(int step, Span<Component[]> allComponents)
    {
        _events.Clear();
    }
}
```

### GameEvent 구조

```csharp
public class GameEvent
{
    public string Type { get; set; }           // "arrive", "meet", "action" 등
    public int ActorId { get; set; }           // 이벤트 주체
    public int? TargetId { get; set; }         // 대상 (meet, action 등)
    public LocationRef? Location { get; set; } // 발생 위치
    public string? ActionType { get; set; }    // action 이벤트: "talk", "trade" 등
    public Dictionary<string, object>? Extra { get; set; } // 추가 데이터
}
```

### 시스템 실행 순서

```
MovementSystem.Proc() (이동 처리 + 이벤트 생성)
    ↓
EventSystem 체크 (이벤트 발생 확인)
    ↓
DialogueSystem? (이벤트 처리 + Python 호출)
    ↓
BehaviorSystem.Proc() (스케줄 완료 체크)
    ↓
PlayerSystem.Proc()
    ↓
DescribeSystem.Proc()
```

**참고:** 이벤트 Clear 타이밍은 구현 시 조정 가능

### 경로 꼬임 문제 해결

이벤트가 발생해도 현재 Step의 이동은 완료됩니다:

1. MovementSystem: 이동 처리 완료 + 이벤트 생성
2. DialogueSystem: 이벤트 조회 → 대화 필요 시 Focus push
3. 대화 중: PlayerSystem의 `NextStepDuration = 0` 또는 스케줄 push
4. 대화 완료: 자연스럽게 다음 행동으로 이어짐

이동 중단이 필요한 경우 (대화 시작 시):
- DialogueSystem이 "대화 중" 스케줄을 스택에 push
- 또는 PlayerSystem에 시간 진행 차단 플래그 설정

---

## 3. 필요한 신규 시스템

### ~~FlagSystem (Data System)~~ → Python 전용

~~게임 진행 플래그 관리 (Python과 공유)~~

**결정:** Flag는 개념적인 것이며, 실제 구현은 Python에서 전담합니다.
- C#에서 FlagSystem 구현하지 않음
- Python에서 자체적으로 flag 딕셔너리 관리
- 매일 00:00에 데일리 리셋: 스케줄 시스템에서 00:00에 끊기는 것 활용 (필요시 구현)
- 저장: Python에서 JSON 파일로 직접 관리

### ScriptSystem (Logic System) - 구현 완료 ✓

C# ↔ Python 통신 담당

```csharp
public class ScriptSystem : ECS.System
{
    private IntegratedPythonInterpreter _interpreter;

    // Python 코드 실행
    public PyObject Execute(string code);
    public PyObject ExecuteFile(string filePath);

    // BBCode script: prefix 용 함수 호출 (결과 파싱 포함)
    public ScriptResult CallFunctionEx(string functionName, string[] args);
}

// 스크립트 결과 타입
public class ScriptResult
{
    public string Type { get; set; }     // "monologue", "message", "error"
    public string Message { get; set; }
}

public class MonologueScriptResult : ScriptResult
{
    public List<string> Pages { get; set; }
    public int TimeConsumed { get; set; }
    public MonologueButtonType ButtonType { get; set; }
    public string YesCallback { get; set; }
    public string NoCallback { get; set; }
}
```

**주요 기능:**
- Godot `res://` 경로를 sys.path에 추가 (AddGodotPathsToSysPath)
- `morld` 모듈 등록 (Python에서 C# 시스템 호출 가능)
- Python dict 결과를 ScriptResult로 자동 파싱

---

## 4. 해결된 이슈

### ~~이슈 1: Python 통신 방식 결정~~ (해결됨)

- ✅ **결정:** sharpPy 임베딩
- ScriptSystem 구현 완료, Hello World 테스트 성공

### ~~이슈 2: Python 스크립트 로딩 전략~~ (해결됨)

- ✅ **결정:** 데이터베이스 개념으로 사용
- 게임 시작 시 1회 로드, 핫 리로드 불필요

### ~~이슈 3: 컨텍스트 전달~~ (해결됨)

- ✅ **결정:** 최소 전달 방식
- C# → Python: 이벤트 + 캐릭터 ID 정도만 전달
- Python → C#: 필요 시 C# System 역호출로 정보 획득
- Flag 데이터: Python 측에서 자체 관리 + JSON 파일 저장

### ~~이슈 4: 대화 선택지 BBCode 연동~~ (해결됨)

- ✅ **결정:** `[url=script:함수이름:arg1:arg2]텍스트[/url]` 형태로 Python 함수 호출
- MetaActionHandler에서 `script:` prefix 감지 → ScriptSystem.CallFunction() 호출
- **테스트 완료:** 문자열/한글/숫자 인자 모두 정상 동작 확인

### ~~이슈 5: Override 복잡도~~ (해결됨)

- ✅ **결정:** FIFO 단순 적용
- 지워지는 이벤트는 에러로 처리

### ~~이슈 6: 모놀로그/다이얼로그 출력 방식~~ (해결됨)

- ✅ **결정:** Text UI 통합 사용
- 별도 Graphic UI (이미지+오디오)는 Text UI 옆에 추후 구현

### ~~이슈 7: 이벤트 우선순위~~ (해결됨)

- ✅ **결정:** FIFO (First In First Out)

### ~~이슈 8: 세이브/로드~~ (해결됨)

- ✅ **결정:** Python 측에서 자체 JSON 관리
- C#은 EventSystem 저장 불필요 (매 Step Clear)
- Flag 데이터는 Python 스크립트에서 JSON 파일로 저장

### ~~이슈 9: 이벤트 시스템 아키텍처~~ (해결됨)

- ✅ **결정:** 섹션 3 참조
- EventSystem: 독립 Data System
- 이벤트 정리: Proc() 시작 시 Clear
- 이벤트 생성: 상태 변경 시점만 (arrive/depart/meet)

---

## 5. 희망사항 (이상적인 구현 방향)

1. **별도 System 파일로 구현** - DialogSystem처럼 플러그인 형식
2. **외부 파일 분리** - 대화/상호작용 콘텐츠는 Python으로 분리
3. **Data System 형태** - 데이터만 관리 + API

---

## 6. Text UI 포맷팅 개선

### 현재 구조
```
[위치 묘사]
[유닛/오브젝트 목록]
[이동 가능 경로]
[행동 옵션]
```

### 제안 구조
```
┌─────────────────────────────┐
│ 헤더: 날짜/시간/날씨         │  ← 상단 고정
├─────────────────────────────┤
│ 로그 영역 (스크롤 가능)      │  ← 중간
│ - 이동 로그                  │
│ - 이벤트 로그                │
│ - 대화 로그                  │
│                              │
│ 묘사 영역                    │
│ - 위치 외관                  │
│ - 상황 묘사                  │
├─────────────────────────────┤
│ 행동 영역                    │  ← 하단
│ - 주변 사물/유닛             │
│ - 이동/인벤토리 등           │
└─────────────────────────────┘
```

### 예시
```
7월 30일 / 흐림

**방에서 마루로 이동하였습니다.**
**마루에서 광장으로 이동하였습니다.**

광장의 날씨는 매우 흐리다. 곧이라도 비가 올 것 같은 느낌이다.
주변에는 아직 사람들이 많이 모여 있고 듬성 듬성 우산을 들고 있다.

주변 사물: [바닥]
[이동] [인벤토리]
```

### 구현 고려사항
- RichTextLabel의 스크롤 기능 활용
- 헤더/푸터 고정 방식 검토 (단일 RichTextLabel vs 분리)
- 로그 버퍼 관리 (최대 라인 수, 오래된 로그 제거)

---

## 7. 대화 시스템 개요

### 대화의 종류
| 종류 | 설명 | 예시 |
|------|------|------|
| 모놀로그 | 단일 화자 (내면 독백, 나레이션) | 플레이어 생각, 상황 설명 |
| 다이얼로그 | 복수 화자 (대화) | NPC와의 대화, 선택지 |

### 시스템 종류
| 종류 | 설명 | 예시 |
|------|------|------|
| 비영향 대화 | 게임 데이터 변경 없음 | 일상 대화, 정보 제공 |
| 영향 대화 | 게임 데이터 변경 있음 | 퀘스트 수락, 아이템 획득, 관계 변화 |

---

## 8. 모놀로그 시스템 (구현 완료 ✓)

### 흐름
```
이벤트 발생 (BBCode script: 링크 클릭)
    ↓
Python 함수 호출 → 모놀로그 데이터 반환
    ↓
모놀로그 Focus Push (페이지 데이터 직접 전달)
    ↓
텍스트 표시
    ↓
[계속] 클릭 → 다음 페이지 (있으면)
    ↓
[확인]/[승낙]/[거절] 클릭 → 소요 시간 반환 + Pop
    ↓
콜백 실행 (있으면)
```

### MonologueButtonType
```csharp
public enum MonologueButtonType
{
    Ok,      // [확인] 버튼 (기본)
    None,    // 버튼 없음 (선택지가 본문에 포함된 경우)
    YesNo    // [승낙] [거절] 버튼
}
```

### Python 스크립트 결과 타입

```python
# 일반 모놀로그
{
    "type": "monologue",
    "pages": ["첫 번째 페이지", "두 번째 페이지"],
    "time_consumed": 5,
    "button_type": "ok"  # "ok", "none", "yesno"
}

# 선택지 모놀로그 (버튼 없음, 본문에 script: 링크 포함)
{
    "type": "monologue",
    "pages": [
        "직업을 선택하세요:\n[url=script:job_select:warrior]검사[/url]\n[url=script:job_select:mage]마법사[/url]"
    ],
    "time_consumed": 0,
    "button_type": "none"
}

# YesNo 다이얼로그
{
    "type": "monologue",
    "pages": ["검사의 길을 선택하시겠습니까?"],
    "time_consumed": 0,
    "button_type": "yesno",
    "yes_callback": "job_confirm:warrior",  # 승낙 시 호출
    "no_callback": None  # None이면 단순 Pop (이전 화면으로)
}
```

### YesNo 다이얼로그 흐름

```
1. 선택지 모놀로그 Push (button_type: "none")
    ↓
2. 선택지 클릭 → HandleScriptAction → job_select() 호출
    ↓
3. YesNo 다이얼로그 Push (button_type: "yesno")
    ↓
4-a. [승낙] → Pop → yes_callback 실행 → 결과 모놀로그 Push
4-b. [거절] → Pop → 이전 선택 화면으로 복귀
```

**핵심:** Pop은 HandleMonologueYesAction/NoAction에서 수행, HandleScriptAction에서는 Pop하지 않음

### Focus.Monologue
```csharp
public class Focus
{
    // Monologue 타입 전용
    public List<string>? MonologuePages { get; set; }
    public int MonologueTimeConsumed { get; set; }
    public int CurrentPage { get; set; }
    public MonologueButtonType MonologueButtonType { get; set; }
    public string? YesCallback { get; set; }  // "함수명:인자1:인자2" 형식
    public string? NoCallback { get; set; }

    public static Focus Monologue(List<string> pages, int timeConsumed,
        MonologueButtonType buttonType = MonologueButtonType.Ok,
        string? yesCallback = null, string? noCallback = null);
}
```

### TextUISystem
```csharp
// 모놀로그 표시 (페이지 데이터 직접 전달)
public void ShowMonologue(List<string> pages, int timeConsumed,
    MonologueButtonType buttonType, string? yesCallback, string? noCallback);

// 다음 페이지
public void MonologueNextPage();

// 완료 (시간 반환)
public int MonologueDone();
```

### MetaActionHandler
```csharp
// monologue_next: 다음 페이지
// monologue_done: 완료 + 시간 소요
// monologue_yes: Pop → yes_callback 실행
// monologue_no: Pop → no_callback 실행 (없으면 이전 화면으로)
```

---

## 9. 로그 시스템

### 로그 타입
```csharp
public enum LogType
{
    Move,       // 이동 로그
    Action,     // 행동 로그
    Event,      // 이벤트 로그
    System      // 시스템 메시지
}
```

### 로그 표시 규칙
- 이동 로그: 굵은 글씨 (`**텍스트**`)
- 이벤트 로그: 색상 강조 (`[color=yellow]텍스트[/color]`)
- 최근 N개만 표시 (기본 5개?)
- 오래된 로그는 자동 fade 또는 제거

---

## 10. 남은 논의 항목

### ~~10.1 Python → C# 역방향 호출~~ (해결됨)

**문제:** Python에서 게임 상태를 조회하거나 수정해야 할 때 어떻게 할 것인가?

**해결:** `morld` 모듈 구현 완료
- ScriptSystem에서 `morld` 모듈을 Python에 등록
- Python에서 `import morld` 형태로 사용

```python
import morld

player_id = morld.get_player_id()
morld.give_item(player_id, item_id, count)
```

**현재 구현된 API:**
- `morld.get_player_id()` - 플레이어 유닛 ID 반환
- `morld.give_item(unit_id, item_id, count)` - 아이템 지급

### 10.2 DialogueSystem 위치 (고민 중)

**문제:** SE.World가 pending일 때 이를 다룰 manager를 어디에 둘 것인가?

**고민 포인트:**
- SE.World의 System으로 넣고 싶음 → ECS 구조 유지
- 하지만 대부분의 이벤트는 유저 대상 → GameEngine 쪽이 맞을 수도

**잠정 결론:** 추후 결정 (구현하면서 판단)

### ~~10.3 Monologue 데이터 소스~~ (해결됨)

**문제:** 모놀로그 텍스트를 어디에 저장할 것인가?

**해결:** Pure Python 방식으로 구현 완료
- Python에서 데이터 관리 (Python 코드 내 딕셔너리/클래스로 정의)
- Python이 필요 시 JSON 불러와서 사용 (`with open("res://...")`)
- sharpPy에서 Godot `res://` 경로 지원 추가됨

**구현 예시:**
```python
# scripts/python/monologues.py
def get_job_blessing(job_type):
    import json
    with open("res://scripts/python/job_blessings.json", "r") as f:
        data = json.load(f)
    return data[job_type]["pages"]
```

### 10.4 EventSystem.Proc() 타이밍 (방향 결정)

**결정:** MovementSystem → EventSystem 체크 순서로 진행

**시스템 실행 순서:**
```
MovementSystem.Proc() (이동 처리 + 이벤트 생성)
    ↓
EventSystem 체크 (이벤트 발생 확인)
    ↓
DialogueSystem? (이벤트 처리)
    ↓
BehaviorSystem.Proc() (스케줄 완료 체크)
    ↓
PlayerSystem.Proc()
```

**참고:** 복잡한 부분이므로 실제 구현 시 조정 가능

### 10.5 시간 Pending 구현 (방향 결정)

**문제:** 대화/모놀로그 중 시간이 흐르지 않아야 함.

**결정 방향:** idle처럼 처리
- 대화 시작 시 시간 소요 0인 상태 유지
- 대화 완료 시 소요 시간 일괄 적용
- 기존 idle 메커니즘과 유사하게 구현

**구현 아이디어:**
```csharp
// 대화 시작
_playerSystem.RequestTimeAdvance(0, "대화");  // 시간 0으로 pending

// 대화 완료 시
_playerSystem.RequestTimeAdvance(dialogue.TimeConsumed, "대화 완료");
```

---

## 11. 기타 미해결 질문

### 포맷팅 관련
1. 헤더(날짜/시간)를 별도 RichTextLabel로 분리할지, 단일 텍스트로 유지할지?
2. 스크롤 시 헤더가 함께 스크롤되어도 괜찮은지?
3. 로그 최대 보관 개수?

### 모놀로그 관련
1. 모놀로그 스킵 기능 필요 여부?
2. 모놀로그 텍스트에 변수 치환 필요 여부? (예: `{playerName}`)

### 이벤트 시스템 관련
1. 이벤트 트리거 조건 정의 방식?
2. 이벤트 → 모놀로그 연결 방식?
3. 이벤트의 1회성 vs 반복성 처리?

---

## 12. 구현 우선순위

### ~~Phase 1: 기본 모놀로그~~ (완료 ✓)
1. ✅ FocusType.Monologue 추가
2. ✅ Python 모놀로그 스크립트 작성 (monologues.py)
3. ✅ ScriptSystem에서 Python 스크립트 로드 + morld 모듈 등록
4. ✅ ShowMonologue/RenderMonologue 구현
5. ✅ monologue_next/monologue_done 핸들러
6. ✅ YesNo 버튼 타입 (MonologueButtonType.YesNo)
7. ✅ YesNo 콜백 (yes_callback, no_callback)
8. ✅ sharpPy에서 Godot res:// 경로 지원 (import json 포함)

### Phase 2: 로그 시스템
1. LogSystem 또는 기존 시스템 확장
2. 이동 로그 자동 기록
3. Text UI에 로그 영역 표시

### Phase 3: UI 포맷팅 개선
1. 헤더 영역 (날짜/시간/날씨)
2. 로그 + 묘사 영역
3. 행동 영역 분리

### Phase 4: 다이얼로그 (별도 설계 필요)
1. 선택지 시스템
2. 조건부 분기
3. 게임 데이터 영향

---

## 13. 관련 파일

```
scripts/
├─ system/
│  ├─ script_system.cs          # ✓ ScriptSystem (morld 모듈, sys.path 설정)
│  └─ text_ui_system.cs         # ✓ ShowMonologue, MonologueNextPage, MonologueDone
├─ morld/
│  └─ ui/
│     └─ Focus.cs               # ✓ FocusType.Monologue, MonologueButtonType, YesNo 콜백
├─ python/
│  ├─ monologues.py             # ✓ intro, job_select, job_confirm, get_job_blessing
│  └─ job_blessings.json        # ✓ 직업별 축복 메시지 데이터
├─ MetaActionHandler.cs         # ✓ script:, monologue_yes, monologue_no 처리
│
└─ (추후 구현)
   ├─ python/dialogues.py       # 다이얼로그
   ├─ python/event_handler.py   # 이벤트 처리
   └─ python/flags.py           # 플래그 관리

util/
└─ sharpPy/
   ├─ core/PyContextManager.cs  # ✓ Godot res:// 경로 지원 (open() 함수)
   └─ platform/helper_godot.cs  # ✓ IsGodotPath, ReadAllText, WriteAllText
```
