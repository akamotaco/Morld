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
    tags = {"외모:금발": 1, "성격:명랑함": 1, ...}
    actions = ["script:npc_talk:대화"]
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

    def npc_talk(self, player_id):
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
└── design.md                 # 이 문서
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

| Instance ID | Unique ID | 이름 | 역할 | 특징 |
|-------------|-----------|------|------|------|
| 1 | lina | 리나 | 채집 담당 | 활발하고 명랑함 |
| 2 | sera | 세라 | 사냥 담당 | 과묵하고 듬직함 |
| 3 | mila | 밀라 | 요리 담당 | 다정하고 걱정 많음 |
| 4 | yuki | 유키 | 청소 담당 | 수줍고 얌전함 |
| 5 | ella | 엘라 | 관리자 | 냉정하고 리더십 있음 |

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
- 모놀로그 결과에 `npc_jobs` 필드 포함 시 EventSystem.ApplyNpcJobs() 호출
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

### 이벤트 파일 분리

```
events/
├── game_start/         # 게임 시작 이벤트
│   └── prologue.py     # 프롤로그 이벤트
├── meet/               # OnMeet 이벤트 (캐릭터 Asset에서 직접 처리)
├── reach/              # OnReach 이벤트 (장소별)
│   └── front_yard.py   # 앞마당 쓰러짐 등
└── scripts/            # 스크립트 함수
    ├── npc_talk.py     # NPC 대화 라우팅
    └── player_creation.py  # 캐릭터 생성 흐름
```

---

## 확장 포인트

### 새 캐릭터 추가

1. `assets/characters/newchar.py` 파일 생성
2. 파일 내 필수 요소:
   - `Character` 상속 클래스 (unique_id, name, tags, actions 등)
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
