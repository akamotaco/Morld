# Scenario02: 숲속 저택 - 설계 문서

## 개요

기억을 잃은 플레이어가 숲속 저택에서 생활하며 NPC들과 교류하는 시나리오.
NPC 스케줄 시스템과 AI 기반 자율 행동이 핵심.

---

## 설계 철학

### C# vs Python 역할 분리

**순수한 시뮬레이션은 C#으로, 게임 콘텐츠는 Python으로 구현한다.**

| 영역 | 언어 | 예시 |
|------|------|------|
| **시뮬레이션** | C# | 지형/지물, 길찾기, 캐릭터 이동/충돌, 시간 흐름, 날씨 변화 |
| **콘텐츠** | Python | 상호작용, 캐릭터 성격, AI 에이전트, 이벤트, 다이얼로그 |

**이점:**
- 시뮬레이션 로직은 성능이 중요하므로 C#으로 최적화
- 콘텐츠는 빠른 이터레이션이 중요하므로 Python으로 유연하게 작성
- 기획자/작가가 Python만으로 캐릭터와 스토리 추가 가능
- 엔진 수정 없이 시나리오별 콘텐츠 독립 관리

---

## 설계 원칙

### 에셋 자급자족 정책

**캐릭터/오브젝트/아이템은 하나의 파일로 구성하여 추가/삭제하는 것만으로도 에셋으로 인식 가능해야 한다.**

```python
# 캐릭터 파일 하나 = 완전한 에셋
# assets/characters/lina.py

from assets.base import Character
from think import BaseAgent, register_agent_class

# 1. 캐릭터 Asset 클래스 정의
class Lina(Character):
    unique_id = "lina"
    name = "리나"
    type = "female"
    props = {"외모:금발": 1, "성격:명랑함": 1, ...}
    actions = ["call:talk:대화", "call:debug_props:속성 보기"]
    mood = []

    # 묘사 텍스트 (메서드 오버라이드)
    def get_describe_text(self) -> str:
        """장소에서 보이는 묘사"""
        ...

    def get_focus_text(self) -> str:
        """클릭했을 때 묘사"""
        ...

    # 이벤트 핸들러 (인스턴스 메서드)
    def on_meet_player(self, player_id):
        ...

    def talk(self):
        """대화 - OOP 메서드 (Generator 기반)"""
        ...

# 2. AI Agent (데코레이터로 자동 등록)
@register_agent_class("lina")
class LinaAgent(BaseAgent):
    SCHEDULE = [...]

    def think(self):
        self.fill_schedule_jobs_from(self.SCHEDULE)
```

**이점:**
- 파일 추가만으로 새 캐릭터 사용 가능
- 파일 삭제만으로 캐릭터 제거
- `mansion.py`에서 개별 캐릭터 코드 수정 불필요
- 관련 코드가 한 파일에 모여 있어 유지보수 용이

---

## 핵심 개념

### Asset vs Instance
- **Asset**: 구조체 정의 (템플릿). `unique_id: str`로 식별
- **Instance**: 게임 내 실체. `instance_id: int`로 식별 (morld API에서 사용)

### Asset.instantiate() 메서드

Asset 클래스를 게임 내 Instance로 등록하는 핵심 메서드입니다.

```python
# assets/base.py
class Asset:
    unique_id = ""
    instance_id = None

    def instantiate(self, instance_id):
        """
        Asset을 게임 내 Instance로 등록

        Args:
            instance_id: 게임 내 고유 ID (morld API에서 사용)

        동작:
        1. instance_id 저장
        2. 인스턴스 레지스트리에 등록
        3. morld API로 C#에 데이터 전달
        """
        self.instance_id = instance_id
        _register_instance(instance_id, self)
        # C#에 데이터 등록 (캐릭터, 아이템, 오브젝트별로 다름)

# 서브클래스에서 확장
class Character(Asset):
    def instantiate(self, instance_id, region_id, location_id):
        super().instantiate(instance_id)
        morld.create_unit(instance_id, self.unique_id, self.name, ...)
        morld.set_unit_location(instance_id, region_id, location_id)

class Object(Asset):
    def instantiate(self, instance_id, region_id=None, location_id=None):
        super().instantiate(instance_id)
        # 자원 오브젝트는 resource_agent에 등록
        if hasattr(self, 'resource_item_unique_id'):
            from think.resource_agent import register_resource_object
            register_resource_object(instance_id, self.unique_id)
```

### Agent 자동 등록 시스템

```python
# think/__init__.py
@register_agent_class("unique_id")  # 데코레이터로 클래스 등록
class MyAgent(BaseAgent):
    ...

# mansion.py에서 사용
from think import create_agent_for
agent = create_agent_for("unique_id", instance_id)  # 팩토리로 인스턴스 생성
```

---

## 폴더 구조

```
scenario02/
├── python/
│   ├── __init__.py           # 시나리오 진입점
│   │
│   ├── assets/               # Asset 정의 (클래스 기반)
│   │   ├── __init__.py       # load_all_assets()
│   │   ├── base.py           # Character, Object, Item, Location 베이스 클래스
│   │   ├── registry.py       # AssetRegistry
│   │   │
│   │   ├── characters/       # 캐릭터 Asset (★ 자급자족 구조)
│   │   │   ├── __init__.py
│   │   │   ├── player.py     # 플레이어 정의
│   │   │   ├── lina.py       # 리나 + Agent + Events
│   │   │   ├── sera.py       # 세라 + Agent + Events
│   │   │   ├── mila.py       # 밀라 + Agent + Events
│   │   │   ├── yuki.py       # 유키 + Agent + Events
│   │   │   └── ella.py       # 엘라 + Agent + Events
│   │   │
│   │   ├── items/            # 아이템 Asset
│   │   │   ├── equipment.py  # 장비류
│   │   │   ├── resources.py  # 자원류
│   │   │   └── tools.py      # 도구류
│   │   │
│   │   ├── locations/        # 장소 Asset (Location별 파일)
│   │   │   ├── living_room.py
│   │   │   ├── dining_room.py
│   │   │   └── ...
│   │   │
│   │   └── objects/          # 오브젝트 Asset
│   │       ├── furniture.py  # 가구류
│   │       ├── grounds.py    # 바닥 오브젝트
│   │       └── outdoor.py    # 야외 오브젝트
│   │
│   ├── world/                # 지형 + 인스턴스화
│   │   ├── __init__.py       # initialize_terrain(), instantiate_all()
│   │   └── mansion.py        # 저택 Region 정의
│   │
│   ├── think/                # NPC AI 시스템
│   │   └── __init__.py       # BaseAgent, @register_agent_class
│   │
│   └── events/               # 이벤트 핸들러
│       ├── __init__.py       # on_event_list export
│       ├── base.py           # EventHandler 베이스
│       ├── registry.py       # 이벤트 핸들러 레지스트리
│       ├── game_start/       # 게임 시작 이벤트
│       │   └── prologue.py
│       ├── meet/             # OnMeet 이벤트 (캐릭터별)
│       ├── reach/            # OnReach 이벤트 (장소별)
│       │   └── front_yard.py
│       └── scripts/          # 스크립트 함수 (@morld.register_script)
│           ├── npc_talk.py
│           ├── player_creation.py
│           └── location_callbacks.py
│
├── chapters/                 # 챕터 관리
│   ├── __init__.py           # load_chapter(), get_current_chapter()
│   ├── persistence.py        # 플레이어 데이터 저장/복원
│   └── chapter_*.py          # 각 챕터 정의
│
└── DESIGN.md                 # 이 문서
```

---

## Instance ID 할당 규칙

```python
# world/mansion.py에서 정의
플레이어: 0
NPC: 1 ~ 99
아이템: 100 ~ 199
오브젝트: 200 ~ 299
바닥 유닛: 1000 + location_id
```

---

## 캐릭터 목록

### 저택 그룹 (Region 0)
| Instance ID | Unique ID | 이름 | 역할 | 특징 |
|-------------|-----------|------|------|------|
| 1 | lina | 리나 | 채집 + 빨래 | 활발하고 명랑함, 세라를 신뢰 |
| 2 | sera | 세라 | **리더** + 사냥 + 순찰 | 과묵하고 듬직함, 리더십 |
| 3 | mila | 밀라 | 요리 + 청소 | 다정하고 걱정 많음, 세라를 신뢰 |

### 도심 그룹 (Region 2 - 은신처)
| Instance ID | Unique ID | 이름 | 역할 | 특징 |
|-------------|-----------|------|------|------|
| 4 | yuki | 유키 | 은신처 생활 | 수줍고 얌전함, 엘라를 의지 |
| 5 | ella | 엘라 | **리더** + 정찰 + 물자수집 | 냉정하고 리더십, 외부인 불신 |

### 관계 구조
```
저택: 세라(리더) ← 밀라, 리나 (신뢰)
도심: 엘라(리더) ← 유키 (의지)
```

---

## NPC AI 시스템

### 시스템 실행 순서

```
[GameEngine._Process]
├─ while (HasPendingTime): world.Step()
│   ├─ ThinkSystem.Proc()      # JobList가 비어있으면 스케줄로 채움
│   └─ JobBehaviorSystem.Proc() # 현재 Job 실행 (이동/활동)
│
└─ if (!HasPendingTime):  # 시간 진행 완료 후
    ├─ DetectMeetings()        # 만남 감지 → OnMeet 이벤트
    ├─ FlushEvents()           # Python 이벤트 핸들러 호출 (npc_jobs 적용)
    ├─ DetectLocationChanges() # 위치 변경 감지 → OnReach 이벤트
    └─ FlushEvents()           # 추가 이벤트 처리
```

### JobList 기반 AI

```python
@register_agent_class("lina")
class LinaAgent(BaseAgent):
    def think(self):
        # JobList가 비어있으면 스케줄 기반으로 채움
        self.fill_schedule_jobs_from(SCHEDULE)
```

### npc_jobs 시스템 (이벤트 기반 행동 오버라이드)

```python
# 이벤트 핸들러에서 NPC 행동 오버라이드
# 이벤트 핸들러는 제너레이터가 아니므로 레거시 형식 사용 (C#에서 Dialog로 자동 변환)
def on_meet_player(context_unit_id):
    return {
        "type": "monologue",
        "pages": ["대화 내용..."],
        "time_consumed": 5,
        "button_type": "ok",
        "npc_jobs": {
            2: {"action": "follow", "duration": 120}  # 세라가 2시간 따라옴
        }
    }
```

**npc_jobs 동작:**
- monologue 결과에 `npc_jobs` 필드 포함 시 EventSystem.ApplyNpcJobs() 호출
- 지정된 NPC의 JobList를 클리어하고 새 Job 삽입
- 이동 중이었다면 중단 (CurrentEdge = null)

### npc_jobs + fill_schedule_jobs_from 동작 흐름

```
1. 이벤트 발생 → npc_jobs: {2: {"action": "follow", "duration": 30}}
   └─ InsertWithClear() → JobList: [따라가기 30분]

2. 시간 진행 중 ThinkSystem 호출
   └─ fill_schedule_jobs_from() → JobList: [따라가기 30분 → 스케줄A → 스케줄B...]
   └─ (기존 Job 보존, 뒤에 스케줄 Merge)

3. 30분 경과 → 따라가기 완료
   └─ JobList: [스케줄A → 스케줄B...]  (자연스럽게 스케줄 복귀)
```

**핵심:**
- `npc_jobs`는 Override (기존 클리어 후 새 Job)
- `fill_schedule_jobs_from`은 Merge (기존 보존, 뒤에 채움)
- 두 시스템이 조합되어 "일시적 행동 → 스케줄 복귀" 자연스럽게 동작

---

## 이벤트 시스템

### 이벤트 타입

| 타입 | 발생 조건 | 처리 |
|------|-----------|------|
| game_start | 게임 시작 | 캐릭터 생성 흐름 |
| on_reach | 위치 도착 | 위치별 이벤트 |
| on_meet | 같은 위치 만남 | NPC별 첫 만남 이벤트 |
| on_time_elapsed | 시간 경과 | 생존/자원 시스템 처리 |

### C#에서 Python 이벤트 호출

C#의 `EventSystem`이 이벤트를 수집하고, `on_single_event()` API로 Python에 전달합니다.

```python
# events/__init__.py

def on_single_event(event):
    """
    단일 이벤트 순차 처리 (C#에서 호출)

    Args:
        event: (type, *args) 튜플

    Returns:
        ScriptResult 또는 None
    """
    event_type = event[0]

    if event_type == "on_time_elapsed":
        minutes = event[1]
        _handle_time_elapsed(minutes)
        return None

    elif event_type == "on_meet":
        # 이벤트 큐 수집 후 첫 번째 처리
        ...

    elif event_type == "on_reach":
        ...
```

### on_time_elapsed 구독 시스템

시간 경과 이벤트를 구독하여 시스템별로 처리합니다.

```python
# events/__init__.py
_time_elapsed_handlers = []

def subscribe_time_elapsed(handler):
    """
    on_time_elapsed 이벤트 구독

    Args:
        handler: callback(minutes: int) 함수

    Example:
        def my_handler(minutes):
            print(f"{minutes}분 경과")

        subscribe_time_elapsed(my_handler)
    """
    _time_elapsed_handlers.append(handler)

def _handle_time_elapsed(minutes):
    """내부: 등록된 핸들러 순차 호출"""
    for handler in _time_elapsed_handlers:
        handler(minutes)
```

**구독하는 시스템:**
- `survival.py` - 포만감 감소, 체력 증감
- `think/resource_agent.py` - 자원 생성

### 순차적 on_meet 이벤트 처리

한 위치에서 여러 NPC를 동시에 만났을 때, 이벤트가 순차적으로 처리됩니다.

**동작 흐름:**
```
1. 플레이어가 위치 도착 → 리나, 밀라와 동시에 만남
2. 이벤트 수집: [리나(priority -1), 밀라(priority -1)]
3. 첫 번째 이벤트 처리: 리나 on_meet_player() Dialog
4. Dialog 종료 → ExcessTime 확인:
   - ExcessTime > 0: 밀라 이벤트 스킵 (시간 흘러감)
   - ExcessTime == 0: 밀라 이벤트 처리 (순차 대화)
5. 모든 이벤트 완료 or 시간 경과 시 종료
```

**우선순위:**
- registry MeetEvent: priority 필드값 (높을수록 먼저)
- character on_meet_player: priority -1 (registry 이벤트 후에 처리)

**Python API:**
```python
# events/__init__.py
def has_pending_meet_events():
    """대기 중인 이벤트 존재 여부"""
    return len(_pending_meet_events) > 0

def clear_pending_meet_events():
    """대기 중인 이벤트 모두 제거 (ExcessTime > 0일 때 호출)"""
    global _pending_meet_events
    _pending_meet_events = []
```

**ExcessTime 발생 예시:**
```python
# 리나 on_meet_player에서 시간 경과 추가
def on_meet_player(self, player_id):
    yield morld.dialog(["대화 내용..."])
    morld.set_npc_time_consume(self.instance_id, "follow", 30, player_id)
    # → ExcessTime = 30 → 다음 NPC 이벤트 스킵
```

### 이벤트 파일 분리

```
events/
├── game_start/         # 게임 시작 이벤트
│   └── prologue.py     # 프롤로그 이벤트
├── meet/               # OnMeet 이벤트 (캐릭터 Asset에서 직접 처리)
├── reach/              # OnReach 이벤트 (장소별)
│   └── front_yard.py   # 앞마당 쓰러짐 등
└── scripts/            # 스크립트 함수 (@morld.register_script)
    ├── npc_talk.py     # NPC 대화 라우팅
    ├── player_creation.py  # 캐릭터 생성 흐름
    ├── container.py    # 컨테이너 아이템 가져오기/넣기
    └── location_callbacks.py  # 위치 콜백
```

---

## Dialog 시스템

### morld.dialog() API

스크립트 함수에서 상호작용 다이얼로그를 표시하는 제너레이터 기반 API.

```python
result = yield morld.dialog(
    text_or_pages,      # str 또는 list - 필수
    autofill="next",    # "next", "book", "scroll", "off"
    proc=None,          # @proc:값 클릭 시 호출될 콜백
    result=None         # @finish 시 반환할 값
)
```

### autofill 타입

| 타입 | 동작 | 용도 |
|------|------|------|
| `next` | [다음] 버튼만 (기본값) | 순차 모놀로그 |
| `book` | [이전][다음] 왕복 가능 | 일기, 문서 열람 |
| `scroll` | 텍스트 누적 + [다음] | 회상, 긴 독백 |
| `off` | 자동 버튼 없음 | 커스텀 UI |

### URL 패턴

| 패턴 | 동작 | 설명 |
|------|------|------|
| `@next` | 다음 페이지로 이동 | autofill 전용 |
| `@prev` | 이전 페이지로 이동 | book 전용 |
| `@finish` | 다이얼로그 종료, result 반환 | 최종 확인 |
| `@proc:값` | proc 콜백 호출 | 상태 변경/선택 |
| `@ret:값` | 다이얼로그 종료, 해당 값 반환 | 레거시 호환 |

### proc 콜백 반환값

`@proc:값` 클릭 시 proc 콜백의 반환값에 따라 동작이 결정됩니다:

| 반환값 | 동작 |
|--------|------|
| `True` | 다이얼로그 종료, result 반환 |
| 문자열 | 텍스트 업데이트, 다이얼로그 유지 |
| `None`/`False` | 변경 없음, 다이얼로그 유지 |

### proc('init') 자동 호출

Dialog가 처음 표시될 때 `proc('init')`이 자동 호출됩니다:
- 반환값이 문자열이면 초기 텍스트로 사용
- 반환값이 `None`이면 원래 텍스트 사용
- 이를 통해 Dialog 복귀 시 상태 기반 텍스트 갱신 가능

### 사용 예시

```python
# 1. 기본 멀티페이지 (autofill="next" 기본값)
yield morld.dialog([
    "페이지1",
    "페이지2",
    "페이지3"
])
# 자동 생성: [다음] → [다음] → [종료]

# 2. 책 열람 (앞뒤 이동)
yield morld.dialog([
    "1장: 시작",
    "2장: 전개",
    "3장: 결말"
], autofill="book")
# 자동 생성: [이전][다음] 네비게이션

# 3. 커스텀 UI (proc + result)
state = {"str": 5, "points": 10}

def handle_action(action):
    if action == "str+" and state["points"] > 0:
        state["str"] += 1
        state["points"] -= 1
    return build_text()  # 새 텍스트 반환

result = yield morld.dialog(
    build_text(),
    autofill="off",
    proc=handle_action,
    result=state
)
# @finish 클릭 시 result = state

# 4. 선택 후 즉시 종료 (proc + return True)
state = {"choice": None}

def handle_choice(action):
    state["choice"] = action
    return True  # 다이얼로그 종료

result = yield morld.dialog(
    "어디로 갈까?\n\n"
    "[url=@proc:town]마을[/url]\n"
    "[url=@proc:forest]숲[/url]",
    autofill="off",
    proc=handle_choice,
    result=state
)
# result = state ({"choice": "town"} 또는 {"choice": "forest"})
```

### 레거시 호환

`@ret:값` 패턴은 기존 코드와의 호환성을 위해 계속 지원됩니다.
선택이 필요한 경우 `@proc:` 패턴을 사용하세요.

---

## 액션 시스템 (OOP 패턴)

### call: 액션 패턴

액션은 `call:` 패턴을 통해 Asset 인스턴스의 메서드를 직접 호출합니다.

```python
# assets/base.py - 베이스 클래스
class Character(Unit):
    def talk(self):
        """기본 대화 - 서브클래스에서 오버라이드"""
        yield morld.dialog(f"[{self.name}]\n...")

# assets/characters/lina.py - 개별 캐릭터
class Lina(Character):
    actions = ["call:talk:대화", "call:debug_props:속성 보기"]

    def talk(self):
        """리나 전용 대화"""
        yield morld.dialog([f"[{self.name}]", "안녕! 뭐야뭐야?"])
```

### 액션 문자열 형식

| 형식 | 설명 | 예시 |
|------|------|------|
| `call:메서드명:표시명` | 메서드 호출 | `call:talk:대화` |
| `call:메서드명:인자:표시명` | 인자 있는 메서드 | `call:sit:front:앉기` |

### 컨테이너 메서드

오브젝트에서 아이템을 가져오거나 넣는 기능은 OOP 메서드로 구현됩니다.

```python
# assets/base.py - Object 베이스 클래스

class Object(Unit):
    def take_from_object(self):
        """다이얼로그 방식으로 아이템 가져오기"""
        # ... 아이템 목록 다이얼로그 표시 ...

    def put_to_object(self):
        """다이얼로그 방식으로 아이템 넣기"""
        # ... 플레이어 인벤토리에서 선택 ...
```

**컨테이너 액션 사용:**
- 오브젝트의 `actions`에 `call:take_from_object:가져오기` 추가
- 인벤토리 내 개별 아이템은 `call:take_item:{item_id}:가져가기` 형식

**메서드 완료 후 Focus 처리:**
- Generator 완료 시 `PopIfInvalid()` 호출
- 빈 인벤토리면 상위 Focus로 자동 복귀
- 유효한 Focus면 현재 상태 유지

---

## 액션 필터링 시스템

### can: prop 기반 액션 필터링

캐릭터가 수행할 수 있는 액션만 UI에 표시됩니다.

**Whitelist 방식:**
- 캐릭터에 `can:메서드명` prop이 있어야 해당 액션 버튼이 표시됨
- 값이 1 이상이면 수행 가능 (추후 레벨별 분기 가능)

**액션 이름 추출:**
```
call:talk:대화          → talk
call:sit:front:앉기     → sit
rest                   → rest
```

### Player의 can: props

```python
# assets/characters/player.py
props = {
    # NPC 상호작용
    "can:talk": 1,

    # 이동/자세
    "can:sit": 1,
    "can:rest": 1,
    "can:sleep": 1,
    "can:wait": 1,

    # 아이템 조작
    "can:take": 1,
    "can:use": 1,
    "can:equip": 1,
    "can:putinobject": 1,
    "can:put_to_object": 1,
    "can:take_item": 1,

    # 오브젝트 상호작용 - OOP 메서드명
    "can:look": 1,
    "can:draw": 1,
    "can:drive": 1,

    # 아이템 사용
    "can:read_book": 1,

    # 디버그
    "can:debug_props": 1,
    "can:debug_self_props": 1,
}
```

### 새 액션 추가 시 체크리스트

1. 대상(유닛/오브젝트/아이템)의 `actions` 리스트에 액션 추가
2. 수행자(플레이어 등)의 props에 `can:액션명` 추가
3. 액션 핸들러 구현 (스크립트 함수 등)

### 조건부 액션

시간, 위치, 상태 등 조건에 따라 액션을 활성화/비활성화할 수 있습니다.

**구현 위치:** `ui.py`의 `get_action_text()`

```python
def get_action_text():
    lines = []

    # C# 기본 행동 가져오기
    default_actions = morld.get_actions_list()
    for action in default_actions:
        lines.append(action)

    # 시간 기반 조건부 행동
    minute_of_day = morld.get_game_time()  # 분 단위 (0~1439)
    hour = minute_of_day // 60

    # 낮잠 (6시~18시만 가능)
    if 6 <= hour < 18:
        lines.append("  [url=idle:240]낮잠 (4시간)[/url]")
    else:
        lines.append("  [color=gray]낮잠 (4시간)[/color]")  # 비활성화

    return "\n".join(lines)
```

**활성화/비활성화 표현:**
- 활성화: `[url=action:param]표시명[/url]`
- 비활성화: `[color=gray]표시명[/color]` (링크 없음, greyed out)

**활용 가능한 조건:**
- 시간: `morld.get_game_time()` (분 단위, 0~1439)
- 위치: `morld.get_unit_location(player_id)`
- 아이템: `morld.has_item(player_id, item_id)`
- 상태: `morld.get_prop(prop_name)`

---

## 챕터 시스템

### 챕터 전환

챕터 간 플레이어 데이터를 유지하면서 새로운 챕터를 로드합니다.

```python
from chapters import load_chapter

# 플레이어 데이터 유지하면서 챕터 로드 (기본값)
load_chapter("chapter_1")

# 새 게임 (플레이어 데이터 초기화)
load_chapter("chapter_0", preserve_player=False)
```

### 저장되는 플레이어 데이터

| 항목 | 설명 | 저장 여부 | 형식 |
|------|------|----------|------|
| 이름 | 캐릭터 이름 | ✅ | str |
| Props | 모든 속성 (`힘`, `can:*` 등) | ✅ | {"prop_name": value} |
| Mood | 감정 상태 | ✅ | [str, ...] |
| Inventory | 소지품 | ✅ | **{"unique_id": count}** |
| Location | 현재 위치 | ❌ | (챕터별 배치) |

### 인벤토리 저장 방식 (unique_id 기반)

챕터 간 item_id 충돌을 방지하기 위해 unique_id로 저장합니다.

```python
# 저장 시 (save_player_data)
inventory = morld.get_unit_inventory(player_id)  # {item_id: count}
inventory_by_unique = {}
for item_id, count in inventory.items():
    item_info = morld.get_item_info(item_id)
    unique_id = item_info["unique_id"]  # "apple", "old_knife" 등
    inventory_by_unique[unique_id] = count

# 복원 시 (restore_player_data)
for unique_id, count in saved_inventory.items():
    item_id = morld.get_item_id_by_unique(unique_id)
    if item_id:
        morld.give_item(player_id, item_id, count)
    else:
        # 새 챕터에 없는 아이템 → 동적 생성
        item_id = _instantiate_item_by_unique(unique_id)
        morld.give_item(player_id, item_id, count)
```

### persistence.py API

```python
from chapters.persistence import (
    save_player_data,      # 수동 저장
    restore_player_data,   # 수동 복원
    save_for_chapter_transition,     # 챕터 전환용 저장
    restore_after_chapter_transition, # 챕터 전환용 복원
    has_saved_data,        # 저장 데이터 존재 여부
)
```

### 행동 로그 처리

복원 시 생성되는 행동 로그(아이템 획득 등)는 자동으로 '읽음' 처리됩니다.

```python
# restore_player_data() 마지막에 자동 호출
morld.mark_all_logs_read()
```

### 폴더 구조

```
chapters/
├── __init__.py       # load_chapter(), get_current_chapter()
├── persistence.py    # save_player_data(), restore_player_data()
├── chapter_0.py      # 프롤로그 챕터
├── chapter_1.py      # 첫 번째 챕터
└── ...
```

---

## 소유자(Owner) 시스템

### 개념
- 아이템/장소에 **원래 소유자**를 지정
- 소유자는 아이템 획득/이동 시에도 **변경되지 않음**
- 향후 "훔치기" 기능, NPC 반응 등에 활용

### 사용법

**아이템 소유자:**
```python
# assets/items/tools.py
class KitchenKnife(Item):
    unique_id = "kitchen_knife"
    name = "부엌칼"
    owner = "mila"  # 밀라 소유
```

**장소 소유자:**
```python
# assets/locations/lina_room.py
class LinaRoom(Location):
    unique_id = "lina_room"
    name = "방2"
    owner = "lina"  # 리나 소유
```

### UI 표시
- 장소명: `방2 (리나 소유)`
- 아이템명: `부엌칼 [color=gray](밀라 소유)[/color]`

### 소유자가 있는 아이템 목록
| 아이템 | 소유자 | 설명 |
|--------|--------|------|
| 부엌칼 | 밀라 | 요리용 |
| 자명종 | 리나 | 개인 물품 |
| 낚시대 | 세라 | 취미용 |
| 사냥용 활 | 세라 | 전투용 |
| 약초 주머니 | 리나 | 채집용 |
| 냄비 | 밀라 | 요리용 |
| 일기장 | 유키 | 개인 물품 |
| 관리 장부 | 엘라 | 업무용 |

---

## 관계(Prop) 시스템

### Prop 키 네이밍 컨벤션
콜론(`:`)으로 구분하여 파싱 용이:
- `카테고리:값` - 기본 형식
- `관계:대상:유형` - 관계 표현

### 예시
```python
props = {
    # 외모
    "외모:금발": 1,
    "외모:단발": 1,

    # 성격
    "성격:명랑함": 1,
    "성격:활발함": 1,
    "성격:리더십": 1,

    # 관계
    "관계:세라:신뢰": 1,      # 세라를 신뢰
    "관계:플레이어:호감": 3,  # 플레이어 호감도 3

    # 수치
    "애정": 0,
    "피로": 0,
}
```

---

## 확장 포인트

### 새 캐릭터 추가

1. `assets/characters/newchar.py` 파일 생성
2. 파일 내 필수 요소:
   - `Character` 상속 클래스 (unique_id, name, props, actions 등)
   - `get_describe_text()`, `get_focus_text()` 메서드
   - `on_meet_player()`, `npc_talk()` 이벤트 핸들러
   - `@register_agent_class("newchar")` 데코레이터가 붙은 Agent 클래스
3. `world/mansion.py`의 `NPC_SPAWNS`에 배치 정보 추가

### 새 아이템 추가

1. `assets/items/`에 Item 클래스 정의 추가
2. `world/mansion.py`의 `ITEMS`에 배치

### 새 이벤트 추가

1. 관련 이벤트 폴더에 핸들러 추가:
   - `events/reach/` - 위치 도착 이벤트
   - `events/meet/` - 만남 이벤트 (또는 캐릭터 Asset의 on_meet_player)
   - `events/game_start/` - 게임 시작 이벤트
2. `events/registry.py`에 핸들러 등록

---

## JobList 시스템 (구현 완료)

### Job 구조

```csharp
class Job {
    string Name;          // "이동", "따라가기", "대기" 등
    string Action;        // "move", "follow", "stay" 등
    int? RegionId;
    int? LocationId;
    int Duration;         // 분 단위
    int? TargetId;        // 따라갈 유닛 ID (follow 시)
}
```

### JobList 핵심 메서드

```csharp
class JobList {
    List<Job> Jobs;

    Job? Current { get; }           // 첫 번째 Job
    bool IsEmpty { get; }
    void Add(Job job);              // 뒤에 추가
    void InsertWithClear(Job job);  // 클리어 후 삽입 (Override용)
    void RemoveFirst();             // 완료된 Job 제거
    void Clear();
}
```

### 시스템 구성

```
ThinkSystem.Proc()
├─ JobList가 비어있으면 Python think_all() 호출
└─ 각 Agent가 fill_schedule_jobs_from(SCHEDULE)로 JobList 채움

JobBehaviorSystem.Proc()
├─ 현재 Job 조회 (JobList.Current)
├─ Action별 처리:
│   ├─ "move": 목적지로 이동
│   ├─ "follow": 대상 유닛 따라가기
│   └─ "stay": 제자리 대기
└─ Job 완료 시 RemoveFirst()
```

### 이벤트 기반 Override (npc_jobs)

```python
# 모놀로그 결과에서 NPC 행동 오버라이드
return {
    "type": "monologue",
    "npc_jobs": {
        2: {"action": "follow", "duration": 120}
    }
}
```

**EventSystem.ApplyNpcJobs() 동작:**
1. 이동 중단 (CurrentEdge = null, RemainingStayTime = 0)
2. 추적 상태 동기화 (_wasMoving, _lastLocations)
3. JobList.InsertWithClear()로 새 Job 삽입

### Job 삽입 방식 비교

| API | 동작 | 사용 시점 |
|-----|------|----------|
| `fill_schedule_jobs_from(schedule)` | 스케줄 기반으로 JobList **뒤에 Merge** (기존 유지) | Think에서 스케줄 채울 때 |
| `InsertWithClear(job)` | JobList **클리어 후** 삽입 (Override) | npc_jobs로 행동 교체 |
| `Prepend(job)` | JobList **앞에 삽입** (기존 유지) | 기존 Job 보존하며 앞에 추가 |
| `InsertOverride(job)` | 기존 시간 **잘라서 덮어쓰기** | duration만큼 기존 Job 잘라냄 |
| `InsertMerge(job)` | **빈 공간에 끼워넣기** (기존 우선) | 기존 Job과 겹치지 않게 삽입 |

---

## 초기화 흐름

```python
# __init__.py - initialize_scenario()

1. initialize_terrain()    # 지형 데이터 (Region, Location, Edge)
2. initialize_time()       # 게임 시간 설정
3. load_all_assets()       # Asset 정의 로드
4. instantiate_player()    # 플레이어만 먼저 생성 (프롤로그)
# NPC는 챕터 1 진입 시 instantiate_npcs() 호출
```

---

## 장비 시스템 (Equipment)

### 개념
아이템을 장착하여 캐릭터에 효과를 부여하는 시스템. 같은 슬롯의 아이템은 자동 교체됩니다.

### 핵심 설계
- **슬롯 직접 정의**: `equip_props`에 `"장착:{슬롯}": 1` 형식으로 정의
- **슬롯 충돌 자동 처리**: 같은 슬롯 키를 가진 장비는 기존 것을 해제 후 장착
- **장비 효과**: `equip_props`가 `Unit.GetActualProps()`에 자동 합산

### 아이템 정의

```python
# assets/items/tools.py
class FishingRod(Item):
    unique_id = "fishing_rod"
    name = "낚시대"
    owner = "sera"
    equip_props = {"can:fish": 1, "장착:손": 1}  # 장착 시 낚시 가능
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

class Torch(Item):
    unique_id = "torch"
    name = "횃불"
    equip_props = {"밝기": 3, "장착:손": 1}  # 장착 시 밝기 +3
    actions = ["take@container", "call:use:사용하기@inventory", "equip@inventory"]
```

### 슬롯 종류

| 슬롯 | 키 형식 | 설명 | 예시 아이템 |
|------|---------|------|------------|
| 손 | `장착:손` | 무기, 도구 | 낚시대, 횃불, 부엌칼 |
| 머리 | `장착:머리` | 헬멧, 모자 | (미구현) |
| 몸통 | `장착:몸통` | 갑옷, 의류 | (미구현) |

### 장착 동작 흐름

```
1. 플레이어가 인벤토리에서 아이템 클릭
2. "장착" 버튼 표시 (equip@inventory 액션)
3. 클릭 시 HandleEquipAction 호출:
   a. 아이템의 슬롯 키 조회 (GetEquipPropKey("장착:"))
   b. 장착 중인 아이템에서 같은 슬롯 키 검색
   c. 충돌 시 기존 아이템 해제
   d. 새 아이템 장착
4. UI Pop → 인벤토리로 복귀
```

### 장비 효과 적용

장착된 아이템의 `equip_props`는 `Unit.GetActualProps()`에서 자동 합산됩니다.

```python
# 낚시대 장착 전
player_props = {"can:talk": 1, ...}

# 낚시대 장착 후 (can:fish 추가)
player_actual_props = {"can:talk": 1, "can:fish": 1, ...}

# 결과: 낚시터에서 "낚시" 액션이 표시됨 (can:fish 필터링 통과)
```

### C# 구현

```csharp
// MetaActionHandler.Item.cs
private void HandleEquipAction(string[] parts)
{
    // 슬롯 충돌 확인
    var slotKey = item.GetEquipPropKey("장착:");
    if (slotKey != null)
    {
        var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);
        foreach (var equippedId in equippedItems)
        {
            var equippedItem = itemSystem.FindItem(equippedId);
            if (equippedItem?.EquipProps?.ContainsKey(slotKey) == true)
            {
                inventorySystem.UnequipItemFromUnit(player.Id, equippedId);
                break;
            }
        }
    }
    // 새 아이템 장착
    inventorySystem.EquipItemOnUnit(player.Id, itemId);
}

// Item.cs
public string GetEquipPropKey(string prefix)
{
    // "장착:" prefix로 시작하는 키 반환
    foreach (var key in EquipProps.Keys)
    {
        if (key.StartsWith(prefix))
            return key;
    }
    return null;
}
```

### 장착 가능 아이템 목록

| 아이템 | unique_id | 슬롯 | 장비 효과 | 소유자 |
|--------|-----------|------|----------|--------|
| 낚시대 | fishing_rod | 손 | can:fish +1 | 세라 |
| 횃불 | torch | 손 | 밝기 +3 | - |
| 부엌칼 | kitchen_knife | 손 | 공격력 +2 | 밀라 |
| 사냥용 활 | hunting_bow | 손 | 공격력 +5, 사거리 +3 | 세라 |
| 랜턴 | lantern | 손 | 밝기 +2 | - |
| 낡은 칼 | old_knife | 손 | 공격 +2, 사냥 +1 | - |

### 파일 위치

```
scripts/
├── MetaActionHandler/MetaActionHandler.Item.cs  # HandleEquipAction
├── morld/item/Item.cs                           # GetEquipPropKey()
└── system/inventory_system.cs                   # 장착 상태 관리

scenarios/scenario02/python/assets/items/
├── tools.py       # FishingRod, Torch, Lantern 등
└── equipment.py   # OldKnife 등
```

---

## 생존 시스템 (Survival)

### 개념
캐릭터의 체력과 포만감을 관리하는 시스템. 시간 경과에 따라 포만감이 감소하고, 음식을 먹어 회복합니다.

### 활성화 조건
- `생존:활성화` prop이 1 이상이면 활성화
- 챕터 0 (프롤로그): 비활성화
- 챕터 1 이후: 활성화

### 수치 설계

| 상수 | 값 | 설명 |
|------|-----|------|
| SATIETY_DECAY_RATE | 1 | 1시간당 포만감 감소 |
| HEALTH_REGEN_RATE | 1 | 포만감 50+일 때 1시간당 체력 회복 |
| HEALTH_DECAY_RATE | 2 | 포만감 0일 때 1시간당 체력 감소 |
| MAX_SATIETY | 100 | 최대 포만감 |
| MAX_HEALTH | 100 | 최대 체력 |

**생존 기간:** 최대 포만감(100) ÷ 시간당 감소(1) = 약 4일

### 상태 경고

| 상태 | 조건 | 메시지 |
|------|------|--------|
| 배고픔 | 포만감 ≤ 30 | 배가 고프다. |
| 굶주림 | 포만감 ≤ 10 | 매우 배고프다. |
| 공복 | 포만감 = 0 | 굶주리고 있다! (체력 감소 시작) |
| 위험 | 체력 ≤ 20 | 몸이 너무 힘들다. |

### Props (플레이어)

```python
# assets/characters/player.py - 챕터 1에서 설정
props = {
    "생존:활성화": 1,      # 생존 시스템 활성화
    "생존:체력": 100,
    "생존:최대체력": 100,
    "생존:포만감": 100,
    "생존:최대포만감": 100,
}
```

### 음식 아이템

| 아이템 | unique_id | 포만감 | 획득처 |
|--------|-----------|--------|--------|
| 산딸기 | wild_berry | 10 | 산딸기 덤불 |
| 사과 | apple | 25 | 사과나무 |
| 버섯 | mushroom | 15 | 버섯 군락 |
| 구운 고기 | cooked_meat | 50 | 조리 |
| 구운 생선 | cooked_fish | 35 | 조리 |

### 음식 섭취

```python
# assets/items/food.py
class FoodItem(Item):
    food_satiety = 0      # 포만감 회복량
    eat_time = 1          # 먹는 시간 (분)
    eat_message = []      # 먹을 때 메시지

    def eat(self):
        # 포만감 최대치 확인
        if stats["satiety"] >= stats["max_satiety"]:
            yield morld.dialog("배가 불러서 더 먹을 수 없다.")
            return

        survival.add_satiety(player_id, self.food_satiety)
        morld.lost_item(player_id, self.instance_id)
        yield morld.dialog(self.eat_message)
        morld.advance_time(self.eat_time)
```

### 파일 구조

```
scenarios/scenario02/python/
├── survival.py              # 생존 시스템 메인
├── assets/items/food.py     # 음식 아이템 정의
└── ui.py                    # get_status_bar() - UI 표시
```

---

## 자원 생성 시스템 (Resource Spawning)

### 개념
자연 오브젝트(사과나무, 산딸기 덤불 등)가 시간 경과에 따라 자원을 자동 생성합니다.

### 핵심 설계
- **이벤트 기반**: `on_time_elapsed` 이벤트 구독
- **시간 누적**: 오브젝트별로 경과 시간 누적
- **최대 개수 제한**: 최대치 도달 시 생성 중단, 시간 누적 없음

### 자원 생성 설정

```python
# think/resource_agent.py
RESOURCE_CONFIG = {
    # unique_id: (spawn_interval분, max_resources)
    "apple_tree": (720, 3),      # 12시간마다, 최대 3개
    "berry_bush": (480, 5),      # 8시간마다, 최대 5개
    "mushroom_patch": (600, 4),  # 10시간마다, 최대 4개
}
```

### 자원 균형

| 자원 | 생성 주기 | 최대 | 포만감 | 하루 최대 획득 |
|------|-----------|------|--------|----------------|
| 사과 | 12시간 | 3 | 25 | 2개 = 50 |
| 산딸기 | 8시간 | 5 | 10 | 3개 = 30 |
| 버섯 | 10시간 | 4 | 15 | 2.4개 ≈ 36 |

**하루 소모 포만감:** 24 (1시간당 1)
**자원으로 획득 가능:** 50 + 30 + 36 = 116 (여유 있음)

### 자원 오브젝트 정의

```python
# assets/objects/nature.py
class AppleTree(Object):
    unique_id = "apple_tree"
    name = "사과나무"
    resource_item_unique_id = "apple"
    initial_resources = 2

    def instantiate(self, instance_id):
        super().instantiate(instance_id)
        # 자원 생성 시스템에 등록
        from think.resource_agent import register_resource_object
        register_resource_object(instance_id, self.unique_id)
        # 초기 자원 생성
        self._spawn_initial_resources()

    def get_resource_count(self):
        """현재 보유 자원 개수"""
        return len(morld.get_unit_inventory(self.instance_id) or {})

    def spawn_resource(self):
        """자원 1개 생성"""
        item_id = morld.get_item_id_by_unique(self.resource_item_unique_id)
        if item_id:
            morld.give_item(self.instance_id, item_id, 1)
            return True
        return False
```

### 동작 흐름

```
1. 오브젝트 instantiate 시 resource_agent에 등록
2. on_time_elapsed 이벤트 발생
3. 등록된 모든 자원 오브젝트에 대해:
   a. 현재 자원 개수 확인
   b. 최대치 미만이면 시간 누적
   c. spawn_interval 이상이면 자원 생성
4. 플레이어가 자원 획득 (take 액션)
5. 다시 시간 누적 시작
```

### 파일 구조

```
scenarios/scenario02/python/
├── think/resource_agent.py      # 자원 생성 로직
├── assets/objects/nature.py     # 자원 오브젝트 정의
└── assets/items/food.py         # 생성되는 음식 아이템
```

---

## 자세(Posture) 시스템

### 개념
- 캐릭터 상태: `standing` (서기), `sitting` (앉기)
- 기본 상태: `standing`
- 이동 시 자동으로 `standing`으로 변경

### 구현 (Prop 기반)
**Prop 시스템을 활용한 양방향 참조**

캐릭터 측:
- `seated_on:{object_id}` → 좌석 이름 (예: `seated_on:230` → `"front"`)
- 값이 없으면 서있는 상태

오브젝트 측:
- `seated_by:{seat_name}` → 앉은 캐릭터 ID (예: `seated_by:front` → `0`)
- 값이 -1이면 빈 좌석

```
자전거 (ID: 230) - 초기 상태
├── seated_by:front  → -1  (빈 좌석, 운전석)
└── seated_by:rear   → -1  (빈 좌석)

[플레이어(0)가 앞좌석에 앉음]
├── seated_by:front  → 0   (플레이어)
└── seated_by:rear   → -1  (빈 좌석)

플레이어 (ID: 0)
└── seated_on:230    → "front"  (자전거 앞좌석에 앉음)
```

### 앉은 상태의 액션 표시
**앉으면 캐릭터에 액션이 추가됨** (오브젝트가 아닌 캐릭터)

describe text에서 자세와 함께 표시:
```
[앉음: 의자] - 일어나기
[앉음: 운전석] - 일어나기, 운전
[앉음: 자전거] - 일어나기, 운전
```

- 기본: "일어나기" 액션 항상 추가
- 운전석(`driver_seat: 1`): "운전" 액션 추가

---

## 탈것(Vehicle) 시스템

### 탈것 분류: 밀폐형 vs 개방형

#### 밀폐형 (Location 타입)
- **자동차**: 자체 Location, 외부 정보 차단
- 항상 "실내" 취급
- 연결된 외부 Location의 날씨/묘사 영향 없음

#### 개방형 (Object 타입)
- **의자, 자전거**: 배치된 Location의 정보 유지
- 날씨, 묘사, 시간대 등 외부 환경 그대로 적용
- 같은 Location의 다른 캐릭터와 상호작용 가능

### 자동차형 (밀폐형)

**자동차 = 하나의 Location**

```
자동차 Location (예: "내 자동차")
├── 운전석 (Object) - passive_props: {driver_seat: 1}, 앉으면 운전 가능
├── 조수석 (Object) - 앉기만 가능
├── 뒷좌석 (Object) - 앉기만 가능
└── 트렁크 (Object) - 인벤토리 보유, 아이템 보관
```

#### 자동차 이동 메커니즘
**핵심: 자동차 이동 = RegionEdge 변경 (Location 변경 아님)**

```
[이동 전]
Region 0: 주차장(29) ←RegionEdge→ Region 1: 자동차(0)

[운전 이동 후 - RegionEdge의 LocationA만 변경]
Region 0: 도시 입구(25) ←RegionEdge→ Region 1: 자동차(0)
```

- 자동차는 별도 Region (Region 1)에 속함
- **RegionEdge의 LocationA (외부 Region 쪽)**가 변경됨
- 탑승자들은 자동차 Location에 계속 머무름

### 의자형 (정적 탈것)

- 오브젝트 타입
- 앉은 상태에서 이동 불가
- Location의 describe 정보는 그대로 유지

**핵심 규칙:**
1. **앉은 상태에서 이동 차단** - "일어나기" 후에만 이동 가능
2. **Location 변경 시 자동 일어남** - 버그 방지

---

## Region 구조

| Region ID | 이름 | 파일 | 설명 |
|-----------|------|------|------|
| 0 | 숲속 저택 | `world/mansion.py` | 저택, 마당, 숲 |
| 1 | 차량 | `world/vehicle.py` | 차량 전용 Region |
| 2 | 황폐화된 도시 | `world/city.py` | 도시 지역 |

### 오브젝트 ID 할당
```
의자 (DiningChair): 220
소파 (LivingSofa): 221
자전거 (Bicycle): 230
운전석 (CarDriverSeat): 231
조수석 (CarPassengerSeat): 232
트렁크 (CarTrunk): 233
```
