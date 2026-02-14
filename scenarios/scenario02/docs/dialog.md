# 대화 시스템

NPC와의 상호작용을 위한 대화/리액션/묘사 시스템입니다.

> **시간 기반 연출이 필요한 경우**: 컷씬, 회고록, 전투 애니메이션 등 시간 기반 자동 진행이 필요하면 **Animlog**를 사용하세요. → [system-ui.md](system-ui.md#animlog-애니메이션-시퀀스)

---

## 3분류 체계

| 분류 | 설명 | 예시 |
|------|------|------|
| **대화** | 플레이어 주도 상호작용 | 말 걸기, 주제 선택 |
| **리액션** | 이벤트/행동에 대한 반응 | 스킨십 반응, 은신 반응 |
| **묘사** | 상태/외형 설명 | 위치 묘사, 클릭 묘사 |

---

## 대화 (Dialog)

플레이어가 NPC에게 말을 거는 상황에서 사용됩니다.

### 4가지 타입

| 타입 | 영문 | 평가 방식 | 용도 |
|------|------|----------|------|
| 단답형 | Lines | 즉시 (bool) | 조건부 한 마디 |
| 연속형 | Sequence | - | 페이지 진행 |
| 누적형 | Conversation | - | 선택지 + 히스토리 |
| 규칙형 | Rules | 지연 (dict) | 선언적 조건-결과 |

---

### Lines (단답형)

조건에 따라 다른 대사를 출력합니다. "확인" 버튼만 표시됩니다.

```python
import ui

lines = ui.Lines("세라")
lines.when(affection >= 80, "...다음에 또 와.", "...조심해서 가.")
lines.when(affection >= 50, "...또 뭐야.")
lines.default("...")
yield lines.end()
```

**특징:**
- 위에서 아래로 조건 평가, 첫 번째 True인 조건 사용
- 모든 조건 불만족 시 `default()` 대사 출력
- **호출 시점에 조건 평가** (즉시 평가)

**용도:**
- 인사말, 상태 메시지
- 간단한 조건부 응답

---

### Sequence (연속형)

페이지가 교체되며 진행됩니다. `+` 접두사로 연쇄 출력을 지원합니다.

```python
import ui

seq = ui.Sequence("세라")
seq.add("첫 번째 페이지")
seq.add("+두 번째 (연쇄)")   # 이전 내용 유지 + 새 내용 타이핑
seq.add("세 번째 (새로)")    # 새로 시작
yield seq.end()
```

**특징:**
- "다음" 버튼으로 페이지 이동
- `+` 접두사: 이전 내용 유지 + 새 내용 추가
- `\+`: `+` 리터럴 (이스케이프)

**용도:**
- 나레이션, 설명문
- 프롤로그, 모놀로그

---

### Conversation (누적형)

CRPG 스타일의 선택지 대화입니다. 히스토리가 화면에 쌓입니다.

```python
import ui

conv = ui.Conversation("세라")
conv.narration("눈앞에 낯선 여성이 서 있다.")
conv.say("...일어났군.", "...기억은 있나?")
conv.ask([
    ("기억이 없다", "no_memory"),
    ("여기가 어디야?", "where"),
    ("(헤어지기)", "@exit"),  # 대화 즉시 종료
])
conv.respond("no_memory", "...그렇군.", "...너만 그런 건 아니다.")
conv.respond("where", "...저택이다.", "...숲 속에 있는.")
conv.say("...무리하지 마라.")
yield conv.end()
```

**메서드:**

| 메서드 | 설명 |
|--------|------|
| `say(*lines)` | NPC 대사 (이름 자동 추가) |
| `narration(*lines)` | 나레이션 (이름 없이) |
| `ask(options)` | 선택지 `[("표시", "값"), ...]` |
| `respond(value, *lines)` | 특정 선택에 대한 응답 |
| `branch(conditions)` | 여러 선택 응답 `{"값": ["대사"], ...}` |
| `end()` | 다이얼로그 반환 (yield용) |

**특수 값:**
- `@exit`: 대화 즉시 종료 (respond 없이 다이얼로그 닫힘)

**타이핑 효과:**
- 선택지 클릭 후: 이전 내용 + 선택 표시 → 즉시 출력
- 새 응답 내용 → 타이핑 연출
- 내부적으로 `[!][/!]` 태그 자동 처리

**용도:**
- 첫 만남 이벤트
- 퀘스트 대화
- 분기가 있는 대화

---

### Rules (규칙형)

클래스 변수로 선언하는 조건-결과 규칙입니다. `TextSelector`를 통해 런타임에 평가됩니다.

```python
class Sera(Character):
    TALK_RULES = {
        "잡담": [
            # (조건 dict, 결과)
            ({"mood": "분노"}, {"pages": ["......", "...가까이 오지 마."]}),
            ({"activity": "사냥"}, {"pages": ["조용히 해.", "...사냥 중이야."]}),
            ({"호감": 70}, "_talk_friendly_high"),  # 메서드 위임
            ({"호감": 50}, {"pages": ["...또 뭐야."]}),
            ({}, {"pages": ["..."]}),  # 기본값
        ],
    }
```

**조건 평가 규칙:**

| 조건 형태 | 평가 방식 | 예시 |
|----------|----------|------|
| 빈 dict `{}` | 항상 True | 기본값 |
| 문자열 값 | `==` 비교 | `{"activity": "사냥"}` |
| 숫자 값 | `>=` 비교 | `{"호감": 50}` |
| 리스트 context | `in` 체크 | `{"mood": "기쁨"}` |

**결과 형태:**

| 형태 | 동작 |
|------|------|
| `{"pages": [...]}` | 해당 대사 출력 |
| `"_메서드명"` | 해당 메서드 호출 (Generator 반환) |

**특징:**
- **클래스 변수로 선언** (선언적)
- **런타임에 context 빌드 후 평가** (지연 평가)
- 메서드 위임으로 복잡한 대화 처리 가능

**용도:**
- NPC 일반 대화 (`TALK_RULES`)
- 주제별 대화 분기

---

### Lines vs Rules 비교

| 항목 | Lines | Rules |
|------|-------|-------|
| 조건 형태 | `bool` (즉시 평가) | `dict` (지연 평가) |
| 정의 위치 | 메서드 내부 | 클래스 변수 |
| 메서드 위임 | 미지원 | `"_메서드명"` 지원 |
| 사용 시점 | 이벤트 핸들러 | `talk()` 메서드 |

**Lines 사용:**
```python
def on_meet_player(self, player_id):
    affection = self._get_affection(player_id)
    lines = ui.Lines(self.name)
    lines.when(affection >= 80, "...또 왔군.")
    lines.when(affection >= 50, "...뭐야.")
    lines.default("...")
    yield lines.end()
```

**Rules 사용:**
```python
# 클래스 정의 시 선언
TALK_RULES = [
    ({"호감": 80}, {"pages": ["...또 왔군."]}),
    ({"호감": 50}, {"pages": ["...뭐야."]}),
    ({}, {"pages": ["..."]}),
]

# talk() 호출 시 TextSelector가 평가
```

---

## 리액션 (Reaction)

이벤트나 행동에 대한 NPC 반응입니다. 딕셔너리 형태로 정의합니다.

### ROMANCE_REACTIONS (스킨십 반응)

네임드 NPC의 **특수 조건 반응**만 정의합니다. 일반 반응은 Generator가 자동 생성합니다.

```python
ROMANCE_REACTIONS = {
    # 특수 조건만 유지 (일반 반응은 Generator fallback)
    "french_kiss:start": [
        ({"미경험:기억:첫키스": 1}, [
            ((80, 70), ["......!", "......(얼굴이 빨개진다)"]),
            ((20, 20), ["...갑자기 뭐하는...!"]),
        ]),
        ((80, 70), ["...응...", "...좋다..."]),
    ],
    "nipple_suck:start": [
        ({"상태:수유": 1}, ["빨지 마...! 나, 나오잖아..."]),
    ],
    # :during 항목 (3인칭 묘사)
    "hug:during": [
        ({"성욕": 50}, ["세라가 숨을 거칠게 몰아쉬고 있다."]),
        ({}, ["세라가 가만히 있다."]),
    ],
}
```

**구조:** `"action:timing" → [(조건, 대사 리스트), ...]`

**timing 값:**
- `start`: 행위 시작 시 (1인칭 대사)
- `during`: 행위 진행 중 (3인칭 묘사, 토글형 행위만)

**조회 방식 — 2단계 fallback:**
```python
# 1) ROMANCE_REACTIONS에서 조건 매칭 시도
key = f"{action_id}:{timing}"  # 예: "hug:start"
rules = self.ROMANCE_REACTIONS.get(key)

# 2) 매칭 실패 시 Generator fallback
#    :start → LineGenerator (1인칭 대사, 아키타입 × 말투 × 톤)
#    :during → ReactionGenerator (3인칭 묘사, 아키타입 × 톤)
```

**Generator 시스템** (`romance_line_generator.py`, `romance_reaction_generator.py`):
- **10 아키타입**: stoic, gentle, cheerful, timid, cold, seductive, fierce, proud, innocent, devoted
- **2D 좌표**: (호감, 욕망) → 톤 (romance/platonic/lust/rejection)
- **3단 말투**: formal(존대) / casual(평어) / rough(하대)
- **흥분 단계**: base → high(70+) → extreme(90+)
- 모브 NPC는 `REACTION_PROFILE`만으로 전체 대사/묘사 자동 생성

---

### STEALTH_REACTIONS (은신 반응)

```python
STEALTH_REACTIONS = {
    "text": [
        ({"성욕": 50}, ["......", "...(긴장한 표정)"]),
        ({"애정": 40}, ["...위험했다.", "...조심해야 한다."]),
        ({}, ["......", "...(차갑게 주위를 경계한다)"]),
    ],
    "effects": {"애정": 1},  # 함께 위기를 넘겨서 유대감 증가
}
```

---

### INITIATIVE_REACTIONS (NPC 주도 반응)

```python
INITIATIVE_REACTIONS = {
    "start": [
        ({"성욕": 80}, ["...가만히 있어.", "......(다가온다)"]),
        ({}, ["......", "...잠깐."]),
    ],
    "during_hug": [ ... ],
    "satisfied": [ ... ],
}
```

---

## 묘사 (Description)

NPC의 상태나 외형을 설명하는 텍스트입니다. Rules 형식을 사용합니다.

### DESCRIBE_RULES (장소 묘사)

장소에서 NPC가 보일 때의 묘사입니다. `build_describe_rules()` 빌더로 생성합니다.

```python
from assets.base import build_describe_rules

# 아키타입 기반 빌더 — 정액/체내정액/성욕/호감/피로도 묘사 자동 상속
DESCRIBE_RULES = build_describe_rules(
    "stoic",  # archetype
    traveling=[
        ({"is_traveling": True, "activity": "순찰"}, "{name}가 정찰을 위해 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),
    ],
    activities=[
        ("순찰", "{name}가 주변을 경계하고 있다."),
        ("수면", "{name}가 잠들어 있다."),
    ],
    locations=[
        ({"location": (0, 24)}, "{name}가 사냥감을 추적하고 있다."),
    ],
    default_text="{name}가 과묵하게 서 있다.",
    order=None,  # 기본 순서 사용 (Ella는 커스텀 순서 지정)
)
```

**빌더 섹션 순서** (기본):
`specials → traveling → activity → weather → location → semen → internal_semen → desire → affection → default → fatigue`

**특징:**
- `{name}` 플레이스홀더 자동 치환
- 위에서 아래로 평가, 첫 번째 매칭 사용
- 모브 NPC: archetype + activities + default_text만 지정하면 완전한 DESCRIBE_RULES 생성

---

### FOCUS_RULES (클릭 묘사)

NPC를 클릭했을 때의 상세 묘사입니다. `build_focus_rules()` 빌더로 생성합니다.

```python
from assets.base import build_focus_rules

# 아키타입 기반 빌더 — 정액/체내정액/성욕/호감/mood 묘사 자동 상속
FOCUS_RULES = build_focus_rules(
    "stoic",  # archetype
    activities=[
        ("순찰", "날카로운 눈으로 주변을 경계하고 있다."),
        ("수면", "경계심 없이 잠들어 있다."),
    ],
    default_text="긴 흑발을 묶은 과묵한 여성.",
    specials=[  # 선택적 — NPC 고유 특수 조건
        ({"도구분실:can:chop": 1}, "벌목 도구가 보이지 않는 모양이다."),
    ],
)
```

**빌더 섹션 순서** (기본):
`specials → semen → internal_semen → activity → mood → desire → affection → default`

---

## TextSelector

Rules 형식의 조건-결과 매칭을 처리하는 유틸리티입니다.

```python
from assets.base import TextSelector

rules = [
    ({"호감": 70, "activity": "휴식"}, "result_a"),
    ({"호감": 50}, "result_b"),
    ({}, "default"),
]

context = {"호감": 65, "activity": "휴식", "mood": ["기쁨"]}
result = TextSelector.select(rules, context)  # "result_b"
```

**메서드:**

| 메서드 | 설명 |
|--------|------|
| `select(rules, context)` | 첫 번째 매칭 결과 반환 |
| `match(conditions, context)` | 조건 충족 여부 확인 |
| `format_result(result, context)` | `{name}` 등 플레이스홀더 치환 |

---

## 파일 위치

| 파일 | 내용 |
|------|------|
| `python/ui.py` | Lines, Sequence, Conversation 클래스 |
| `python/assets/base.py` | TextSelector, Character, build_focus_rules(), build_describe_rules() |
| `python/assets/characters/*.py` | 캐릭터별 RULES 정의 (빌더 호출 + 특수 조건) |
| `python/romance_line_generator.py` | :start 1인칭 대사 Generator (아키타입 × 말투 × 톤) |
| `python/romance_reaction_generator.py` | :during 3인칭 묘사 Generator (아키타입 × 톤) |

---

## 요약

```
대화 (Dialog)
├── Lines (단답형) ─────── 즉시 평가, 이벤트용
├── Sequence (연속형) ──── 페이지 진행, 나레이션용
├── Conversation (누적형) ─ 선택지, 첫 만남용
└── Rules (규칙형) ──────── 지연 평가, NPC 대화용

리액션 (Reaction)
├── ROMANCE_REACTIONS ──── 스킨십 반응 (특수 조건만)
│   └── Generator fallback ── LineGenerator(:start) / ReactionGenerator(:during)
├── STEALTH_REACTIONS ──── 은신 반응
└── INITIATIVE_REACTIONS ─ NPC 주도 반응

묘사 (Description)
├── DESCRIBE_RULES ─────── 장소에서 보이는 묘사 (build_describe_rules 빌더)
└── FOCUS_RULES ────────── 클릭 시 상세 묘사 (build_focus_rules 빌더)
```
