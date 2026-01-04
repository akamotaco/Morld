# Morld - ECS 기반 유닛 시뮬레이션 시스템

## 프로젝트 개요

Morld는 ECS(Entity Component System) 아키텍처를 기반으로 한 게임 월드 시뮬레이션 시스템입니다.
유닛(캐릭터/오브젝트)의 JobList에 따라 자동으로 경로를 계획하고 이동하는 시스템을 제공합니다.

**핵심 기술:**
- Godot 4 엔진
- C# .NET
- ECS 아키텍처
- JSON 기반 데이터 관리
- Dijkstra Pathfinding
- **JobList 기반 행동 시스템** (시간 기반 선형 리스트)
- 통합 Unit 시스템 (캐릭터/오브젝트)
- sharpPy (Python 인터프리터) 기반 스크립트 시스템
- **Python Asset 클래스 기반 데이터 정의**

---

## 아키텍처 원칙

### ECS 시스템의 두 가지 역할

#### 1. Data Management Systems (데이터 관리 시스템)
게임 상태(persistent state)를 저장하고 관리하는 시스템

**특징:**
- ✅ JSON Import/Export (`UpdateFromFile()`, `SaveToFile()`)
- ❌ Proc 함수 없음 (순수 데이터 저장소)
- 세이브/로드 대상
- 게임 데이터의 원천(Source of Truth)

**구현 시스템:**
- `WorldSystem` - 지형(Terrain) 데이터 및 GameTime 보관
- `UnitSystem` - 유닛 데이터 (캐릭터/오브젝트 통합, 위치, JobList, CurrentEdge, "바닥" 오브젝트 포함)
- `ItemSystem` - 아이템 정의 데이터 (PassiveTags, EquipTags, Actions)
- `InventorySystem` - 인벤토리 데이터 (유닛별 아이템 소유, 장착, 가시성)

#### 2. Logic/Behavior Systems (로직 시스템)
매 Step마다 게임 로직을 실행하는 시스템

**특징:**
- ❌ JSON Import/Export 없음
- ✅ Proc 함수 구현 (`Proc(int step, Span<Component[]> allComponents)`)
- Data Systems의 데이터를 읽고 수정
- Stateless - 자체 상태를 저장하지 않음

**구현 시스템:**
- `ThinkSystem` - Python Agent의 think() 호출, JobList 채우기
- `JobBehaviorSystem` - JobList 기반 이동/행동 처리, GameTime 업데이트
- `PlayerSystem` - 플레이어 입력 기반 시간 진행 제어, Look 기능
- `DescribeSystem` - 묘사 텍스트 생성 (시간 기반 키 선택)
- `ActionSystem` - 유닛 행동 실행 (talk, trade, use 등)
- `TextUISystem` - RichTextLabel.Text 관리, 스택 기반 화면 전환, 토글 렌더링
- `ScriptSystem` - Python 스크립트 실행 (sharpPy 기반), 모놀로그/이벤트 처리
- `EventSystem` - 게임 이벤트 수집 및 Python 전달 (OnReach, OnMeet 감지)

### 시스템 실행 순서

```
ThinkSystem → JobBehaviorSystem → PlayerSystem → DescribeSystem
```

### 데이터 흐름

```
┌─────────────────────┐
│   GameEngine        │
│  _Ready()           │
└──────────┬──────────┘
           │
           ├─> RegisterAllSystems() (모든 시스템 등록)
           │   └─> ScriptSystem 등록 + SetScenarioPath()
           │
           └─[Python 모드]────────────────────────────────────────
               ├─> SetDataSystemReferences() (morld API 등록)
               ├─> CallInitializeScenario()
               │   ├─> import world → world.initialize_world()
               │   ├─> import items → items.initialize_items()
               │   ├─> from characters import initialize_characters()
               │   └─> from objects import initialize_objects()
               └─> LoadScenarioPackage() (이벤트 핸들러 로드)
```

**시나리오 타입 감지:**
- `IsPythonDataSource()`: `scenarios/{scenario}/python/__init__.py` 존재 여부로 판단
- Python 모드: morld API를 통해 데이터 직접 등록

---

## JobList 기반 행동 시스템

### 핵심 개념

**JobList**는 시간 기반 선형 리스트로, 각 유닛이 수행할 Job들을 관리합니다.
Python Agent의 `think()` 메서드가 JobList를 채우고, `JobBehaviorSystem`이 실행합니다.

```
JobList 예시 (NPC 세라):
┌─────────────────────────────────────────┐
│ Job: 순찰 (move, 숲 입구, 60분)          │ ← 현재 실행 중
├─────────────────────────────────────────┤
│ Job: 대기 (stay, 30분)                   │
├─────────────────────────────────────────┤
│ Job: 순찰 (move, 저택 앞마당, 60분)       │
└─────────────────────────────────────────┘

플레이어 JobList:
┌─────────────────────────────────────────┐
│ Job: 이동 (move, 목적지, 1440분)         │ ← 도착 시 완료
└─────────────────────────────────────────┘

오브젝트 (JobList 없음):
- IsObject = true
- JobList 비어있음
- 이동하지 않음
- 인벤토리 보유 가능
```

### Job 구조

```csharp
Job
├─ Name (string - "순찰", "이동", "대기", "따라가기" 등)
├─ Action (string - "move", "stay", "follow", "flee")
├─ Duration (int - 소요 시간, 분)
├─ RegionId (int? - move 액션의 목표 Region)
├─ LocationId (int? - move 액션의 목표 Location)
├─ TargetId (int? - follow/flee 액션의 대상 유닛 ID)
└─ Activity (string? - 현재 활동: "순찰", "식사", "수면" 등)
```

**Job Action 타입:**
| Action | 설명 | 필수 필드 |
|--------|------|----------|
| `move` | 목표 위치로 이동 | RegionId, LocationId |
| `stay` | 현재 위치에서 대기 | Duration |
| `follow` | 대상 유닛 따라가기 | TargetId, Duration |
| `flee` | 대상 유닛으로부터 도망 | TargetId, Duration |

### JobList 조작 패턴

```csharp
// 1. InsertWithClear - 기존 Job 모두 제거 후 새 Job 삽입
//    플레이어 명령, npc_jobs 오버라이드에 사용
unit.JobList.InsertWithClear(job);

// 2. FillFromSchedule - 스케줄 기반으로 빈 시간 채우기
//    NPC의 think()에서 사용 (기존 Job 유지)
unit.JobList.FillFromSchedule(schedule, currentTime, lookAhead);
```

---

## Python Asset 시스템 (scenario02)

### Asset 클래스 구조

Python에서 게임 데이터를 클래스로 정의합니다.

```python
# assets/base.py
class Unit:
    """유닛 기본 클래스"""
    unique_id: str = ""      # 고유 식별자 (예: "sera", "player")
    name: str = "Unknown"
    tags: dict = {}          # 스탯/태그
    actions: list = []       # 가능한 액션

class Character(Unit):
    """캐릭터 클래스"""
    type: str = "male"       # "male", "female"
    mood: list = []          # 현재 감정 상태

    def get_describe_text(self) -> str:
        """장소에 있을 때 묘사 (presence text)"""
        return None

    def get_focus_text(self) -> str:
        """Focus 상태일 때 묘사 (클릭했을 때)"""
        return None
```

### NPC 캐릭터 정의 예시

```python
# assets/characters/sera.py
from assets.base import Character
from think import BaseAgent, register_agent_class

class Sera(Character):
    unique_id = "sera"
    name = "세라"
    type = "female"
    tags = {"힘": 7, "민첩": 8}
    actions = ["script:npc_talk:대화"]

    # 스케줄 정의
    SCHEDULE = [
        {"name": "순찰", "region_id": 0, "location_id": 1, "start": 360, "end": 720, "activity": "순찰"},
        {"name": "휴식", "region_id": 0, "location_id": 0, "start": 720, "end": 780, "activity": "휴식"},
    ]

    def get_describe_text(self):
        """장소 묘사에 표시되는 텍스트"""
        return f"{self.name}(이)가 주변을 경계하고 있다."

    def get_focus_text(self):
        """클릭 시 표시되는 텍스트"""
        return "날카로운 눈매의 여성 사냥꾼이다."

    def on_meet_player(self, player_id):
        """플레이어와 만났을 때 이벤트"""
        return {
            "type": "monologue",
            "pages": ["...일어났군.", "...세라다."],
            "time_consumed": 2,
            "button_type": "ok",
            "npc_jobs": {self.instance_id: {"action": "follow", "duration": 2}}
        }

@register_agent_class("sera")
class SeraAgent(BaseAgent):
    def think(self):
        """스케줄 기반 JobList 채우기"""
        self.fill_schedule_jobs_from(Sera.SCHEDULE)
```

### ThinkSystem과 Agent

```python
# think/__init__.py
class BaseAgent:
    def __init__(self, unit_id):
        self.unit_id = unit_id

    def get_info(self):
        """현재 유닛 정보 조회"""
        return morld.get_unit_info(self.unit_id)

    def get_location(self):
        """현재 위치 (region_id, location_id) 튜플"""
        return morld.get_unit_location(self.unit_id)

    def fill_schedule_jobs_from(self, schedule):
        """스케줄 기반으로 JobList 채우기"""
        return morld.fill_schedule_jobs_from(self.unit_id, schedule)

    def think(self):
        """AI 로직 - 서브클래스에서 오버라이드"""
        return None

@register_agent_class("unique_id")
class MyAgent(BaseAgent):
    def think(self):
        # 커스텀 로직 또는 스케줄 기반
        self.fill_schedule_jobs_from(SCHEDULE)
```

---

## 시스템 상세

### ThinkSystem (Logic System)
**역할:** Python Agent의 think() 메서드 호출, JobList 채우기

**실행 로직:**
1. PlayerSystem에서 `HasPendingTime` 체크
2. 시간 진행 대기 중이면 Python `think.think_all()` 호출
3. 각 Agent가 `fill_schedule_jobs_from()` 등으로 JobList 채움

**파일 위치:**
- `scripts/system/think_system.cs`
- `scenarios/scenario02/python/think/__init__.py`

### JobBehaviorSystem (Logic System)
**역할:** JobList 기반 통합 행동 시스템 (MovementSystem + BehaviorSystem 통합)

**실행 로직:**
1. PlayerSystem에서 `NextStepDuration` 읽기
2. 각 유닛에 대해 (IsObject=true는 스킵):
   - 현재 Job의 Action에 따라 처리 (move, stay, follow, flee)
   - 경로 계산 및 이동 처리
   - Job Duration 감소, 완료 시 다음 Job으로
3. GameTime 업데이트

**파일 위치:**
- `scripts/system/job_behavior_system.cs`

### EventSystem (Logic System)
**역할:** 게임 이벤트 수집, 감지 및 Python 전달

**핵심 설계:**
- **이벤트 배치 처리**: 이벤트를 수집해서 한 번에 Python으로 전달
- **위치 변경 감지**: OnReach 이벤트 자동 생성
- **만남 감지**: OnMeet 이벤트 자동 생성 (이동 중인 유닛 제외)
- **Python 제어**: 이벤트 처리 순서/우선순위를 Python에서 결정

**OnMeet 감지 로직:**
```csharp
// 이동 중인 유닛(CurrentEdge != null)은 제외
var unitsToMeet = _unitSystem.Units.Values
    .Where(u => u.Id != playerId
             && u.GeneratesEvents
             && u.CurrentLocation == playerLocation
             && u.CurrentEdge == null)  // 이동 중이 아닌 유닛만
```

**npc_jobs 시스템:**
모놀로그 결과에서 `npc_jobs`로 NPC의 Job을 즉시 오버라이드:

```python
return {
    "type": "monologue",
    "pages": ["대화 내용..."],
    "time_consumed": 2,
    "button_type": "ok",
    "npc_jobs": {
        unit_id: {"action": "follow", "duration": 2}
    }
}
```

**ApplyNpcJobs 동작:**
- 지정된 유닛의 CurrentEdge = null (이동 중단)
- 이동 추적 상태 동기화 (`_wasMoving`, `_lastLocations`)
- JobList.InsertWithClear()로 새 Job 삽입

**이벤트 처리 순서 (_Process):**
```
1. DetectMeetings() → OnMeet 이벤트 생성
2. FlushEvents() → ApplyNpcJobs 실행 (이동 상태 변경)
3. DetectLocationChanges() → 위치 변경 감지 (ApplyNpcJobs 후)
4. FlushEvents() → 추가 이벤트 처리
```

**파일 위치:**
- `scripts/system/event_system.cs`
- `scripts/morld/event/GameEvent.cs`

### UnitSystem (Data System)
**역할:** 게임 내 모든 유닛(캐릭터/오브젝트)의 데이터 관리

**데이터 구조:**
```csharp
Unit
├─ Id (int - 고유 식별자)
├─ Name (이름)
├─ IsObject (bool - true: 오브젝트, false: 캐릭터)
├─ CurrentLocation (현재 위치 - LocationRef)
├─ CurrentEdge (이동 중 Edge 진행 상태 - EdgeProgress?)
├─ JobList (시간 기반 Job 리스트)
│  └─ CurrentJob (현재 실행 중인 Job)
├─ TraversalContext (기본 태그/스탯)
├─ Actions (List<string> - 가능한 행동)
├─ Mood (HashSet<string> - 현재 감정 상태)
├─ IsMoving (CurrentEdge != null)
└─ IsIdle (CurrentEdge == null)
```

**파일 위치:**
- `scripts/system/unit_system.cs`
- `scripts/morld/unit/Unit.cs`
- `scripts/morld/unit/UnitJsonFormat.cs`
- `scripts/morld/schedule/Job.cs`
- `scripts/morld/schedule/JobList.cs`

### DescribeSystem (Logic System)
**역할:** 묘사 텍스트 생성 (시간/상태 기반 키 선택)

**Python 모드에서의 텍스트 생성:**
- `GetLocationDescribeText()` - Location의 describe_text
- `GetUnitAppearance()` - Python Asset의 `get_focus_text()` 호출
- `GetPresenceText()` - Python Asset의 `get_describe_text()` 호출

**파일 위치:**
- `scripts/system/describe_system.cs`

### ScriptSystem (Logic System)
**역할:** Python 스크립트 실행 (sharpPy 인터프리터), 모놀로그/이벤트 처리

**morld 모듈 API:**
```python
import morld

# 유닛 관련
morld.get_player_id()
morld.get_unit_info(unit_id)
morld.get_unit_location(unit_id)
morld.set_unit_location(unit_id, region_id, location_id)

# JobList 관련
morld.fill_schedule_jobs_from(unit_id, schedule)

# 아이템 관련
morld.give_item(unit_id, item_id, count)
morld.has_item(unit_id, item_id)
morld.lost_item(unit_id, item_id, count)

# 플래그/로그
morld.get_flag(flag_name)
morld.set_flag(flag_name, value)
morld.add_action_log(message)

# 시간 관련
morld.get_game_time()
morld.advance_time(minutes)
```

**파일 위치:**
- `scripts/system/script_system.cs`
- `util/sharpPy/` (Python 인터프리터)

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ MetaActionHandler.cs (BBCode URL 클릭 핸들러)
├─ system/ (ECS Systems)
│  ├─ world_system.cs (WorldSystem - Data)
│  ├─ unit_system.cs (UnitSystem - Data)
│  ├─ item_system.cs (ItemSystem - Data)
│  ├─ inventory_system.cs (InventorySystem - Data)
│  ├─ think_system.cs (ThinkSystem - Logic, Python Agent)
│  ├─ job_behavior_system.cs (JobBehaviorSystem - Logic, 이동/행동)
│  ├─ player_system.cs (PlayerSystem - Logic)
│  ├─ describe_system.cs (DescribeSystem - Logic)
│  ├─ text_ui_system.cs (TextUISystem - Logic)
│  ├─ script_system.cs (ScriptSystem - Logic, sharpPy)
│  ├─ event_system.cs (EventSystem - Logic, 이벤트 감지)
│  └─ action_system.cs (ActionSystem - Logic)
├─ morld/ (Core Data Structures)
│  ├─ unit/
│  │  ├─ Unit.cs (JobList, CurrentEdge 등)
│  │  └─ UnitJsonFormat.cs
│  ├─ schedule/
│  │  ├─ Job.cs (Job 구조체)
│  │  ├─ JobList.cs (JobList 클래스)
│  │  ├─ GameTime.cs
│  │  ├─ DailySchedule.cs
│  │  └─ ScheduleEntry.cs
│  ├─ terrain/
│  ├─ item/
│  ├─ action/
│  ├─ player/
│  ├─ ui/
│  └─ event/
scenarios/
├─ scenario02/
│  └─ python/
│     ├─ __init__.py (시나리오 초기화)
│     ├─ world.py (지형 데이터)
│     ├─ items.py (아이템 데이터)
│     ├─ events.py (이벤트 핸들러)
│     ├─ assets/
│     │  ├─ base.py (Unit, Character, Location 등 기본 클래스)
│     │  ├─ characters/ (캐릭터별 Python 파일)
│     │  │  ├─ player.py
│     │  │  ├─ sera.py
│     │  │  └─ lina.py
│     │  └─ objects/ (오브젝트별 Python 파일)
│     └─ think/
│        └─ __init__.py (BaseAgent, register_agent_class)
└─ util/sharpPy/ (Python 인터프리터 - 서브모듈)
```

---

## 빌드 및 실행

### 빌드
```bash
dotnet build
```

### 디버그 로그
`#define DEBUG_LOG` 활성화 시:
- **초기화:** World 구조, GameTime 정보, Unit 목록 및 JobList, System 개수 출력
- **런타임:** JobBehaviorSystem에서 시간 진행, 유닛 상태 출력
- **런타임:** EventSystem에서 이벤트 감지/처리 로그

### 실행
Godot 에디터에서 프로젝트 실행
