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
- `ItemSystem` - 아이템 정의 데이터 (PassiveProps, EquipProps, Actions)
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
- `ActionSystem` - 차량 액션 전용 (CanDrive, GetDrivableDestinations, ApplyDriveAction)
- `TextUISystem` - RichTextLabel.Text 관리, 스택 기반 화면 전환, 토글 렌더링
- `ScriptSystem` - Python 스크립트 실행 (sharpPy 기반), Dialog/이벤트 처리
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
    props: dict = {}         # 스탯/속성
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
    props = {"힘": 7, "민첩": 8}
    actions = ["call:talk:대화"]

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
        """플레이어와 만났을 때 이벤트 (Generator 방식)"""
        yield morld.dialog("...일어났군.")
        yield morld.dialog("...세라다.")
        morld.set_npc_job(self.instance_id, "follow", 2)

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

**NPC Job 제어 API:**
Generator 기반 이벤트 핸들러에서 NPC Job을 직접 제어:

```python
# 이벤트 핸들러에서 NPC Job 설정
def handle(self, player_id, unit_ids):
    yield morld.dialog("대화 내용...")
    # NPC Job 설정 (시간 경과 없음)
    morld.set_npc_job(unit_id, "follow", duration=30)
    # 또는 시간 경과 포함
    morld.set_npc_time_consume(unit_id, "stay", duration=30)
```

**이벤트 처리 순서 (_Process):**
```
1. DetectMeetings() → OnMeet 이벤트 생성
2. FlushEvents() → Generator 실행, Dialog 표시
3. DetectLocationChanges() → 위치 변경 감지
4. FlushEvents() → 추가 이벤트 처리
```

**순차적 on_meet 이벤트 처리:**
한 위치에서 여러 NPC를 동시에 만났을 때, 이벤트가 우선순위별로 순차 처리됩니다.

```python
# Python 이벤트 큐 (events/__init__.py)
_pending_meet_events = []  # 대기 중인 이벤트 목록

def _collect_meet_events(player_id, unit_ids):
    """조건에 맞는 모든 on_meet 이벤트 수집"""
    events = []
    # 1. registry MeetEvent (priority 기반)
    # 2. character on_meet_player (priority -1)
    events.sort(key=lambda e: -e["priority"])  # 높은 priority 먼저
    return events

# C#에서 호출하는 API
def has_pending_meet_events():
    """대기 중인 이벤트 존재 여부"""
    return len(_pending_meet_events) > 0

def clear_pending_meet_events():
    """ExcessTime > 0일 때 대기 중인 이벤트 모두 제거"""
    global _pending_meet_events
    _pending_meet_events = []
```

**ExcessTime과 이벤트 큐 연동:**
```
1. 플레이어가 위치 도착 → 여러 NPC와 만남
2. 이벤트 큐 생성 (우선순위 정렬)
3. 첫 번째 이벤트 처리 (Dialog 표시)
4. Dialog 종료 후 ExcessTime 확인:
   - ExcessTime > 0: 남은 이벤트 모두 스킵 (시간 흐름)
   - ExcessTime == 0: 다음 이벤트 처리 (순차 대화)
5. 모든 이벤트 처리 완료 or ExcessTime 발생 시 종료
```

**파일 위치:**
- `scripts/system/event_system.cs`
- `scripts/morld/event/GameEvent.cs`
- `scenarios/scenario02/python/events/__init__.py` - 이벤트 큐 관리

### UnitSystem (Data System)
**역할:** 게임 내 모든 유닛(캐릭터/오브젝트)의 데이터 관리

**데이터 구조:**
```csharp
Unit
├─ Id (int - 고유 식별자)
├─ UniqueId (string - Python Asset의 unique_id, 예: "sera", "mila")
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

**UniqueId 조회:**
```csharp
// unique_id로 유닛 찾기
Unit? unit = unitSystem.FindByUniqueId("sera");
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
**역할:** Python 스크립트 실행 (sharpPy 인터프리터), Dialog/이벤트 처리

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
morld.set_npc_job(unit_id, action, duration)  # NPC Job 즉시 설정
morld.set_npc_time_consume(unit_id, action, duration)  # 시간 경과 포함

# 아이템 관련
morld.give_item(unit_id, item_id, count)
morld.has_item(unit_id, item_id)
morld.lost_item(unit_id, item_id, count)

# Prop/로그
morld.get_prop(prop_name)
morld.set_prop(prop_name, value)
morld.clear_prop(prop_name)
morld.add_action_log(message)
morld.mark_all_logs_read()  # 모든 행동 로그를 읽음 처리

# 시간 관련
morld.get_game_time()
morld.advance_time(minutes)

# Dialog API (Generator 전용)
morld.dialog(text_or_pages, autofill="next", proc=None, result=None)  # yield로 사용

# Unit 속성 설정
morld.set_unit(unit_id, field, value)  # name, type 등
```

**파일 위치:**
- `scripts/system/script_system.cs`
- `util/sharpPy/` (Python 인터프리터)

### Dialog 시스템
**역할:** Python 제너레이터 기반 대화형 UI

**morld.dialog() API:**
```python
result = yield morld.dialog(
    text_or_pages,      # str 또는 list - 필수
    autofill="next",    # "next", "book", "scroll", "off"
    proc=None,          # @proc:값 클릭 시 호출될 콜백
    result=None         # @finish 시 반환할 값 (dict/객체)
)
```

**autofill 타입:**
| 타입 | 동작 | 용도 |
|------|------|------|
| `next` | [다음] 버튼만 (기본값) | 순차 모놀로그 |
| `book` | [이전][다음] 왕복 가능 | 일기, 문서 열람 |
| `scroll` | 텍스트 누적 + [다음] | 회상, 긴 독백 |
| `off` | 자동 버튼 없음 | 커스텀 UI |

**URL 패턴:**
| 패턴 | 동작 | 설명 |
|------|------|------|
| `@ret:값` | 다이얼로그 종료, yield에 값 반환 | 최종 선택 (레거시) |
| `@finish` | 다이얼로그 종료, result 파라미터 값 반환 | |
| `@proc:값` | proc(값) 호출, 반환값에 따라 동작 | 상태 변경 |
| `@next` | 다음 페이지로 이동 | autofill 전용 |
| `@prev` | 이전 페이지로 이동 | book 전용 |

**proc 콜백 반환값:**
| 반환값 | 동작 |
|--------|------|
| `문자열` | 해당 문자열로 텍스트 업데이트, 다이얼로그 유지 |
| `True` | 다이얼로그 즉시 종료, result 반환 |
| `None`/`False` | 변경 없음, 다이얼로그 유지 |

**proc('init') 자동 호출:**
- Dialog가 처음 표시될 때 `proc('init')` 자동 호출
- 문자열 반환 시 초기 텍스트로 사용
- `None` 반환 시 원래 텍스트 사용
- 다이얼로그 복귀 시 상태 기반 텍스트 갱신에 활용

**예시 - 멀티페이지 모놀로그:**
```python
@register
class GameStart(GameStartEvent):
    def handle(self, **ctx):
        yield morld.dialog([
            "...어디지, 여기는?",
            "머리가 지끈거린다.\n기억이... 잘 나지 않는다.",
            "일단 이 저택에서 나가야 할 것 같다."
        ])  # autofill="next" 기본값
```

**예시 - proc + return True로 선택 후 즉시 종료:**
```python
state = {"choice": None}

def handle_choice(action):
    if action == "init":
        return None  # 초기 텍스트 유지
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
# result = state (state["choice"]에 선택값)
```

**예시 - 캐릭터 생성 (yield from 서브 제너레이터):**
```python
def handle(self, **ctx):
    from events.scripts.player_creation import (
        run_character_creation, apply_character_creation
    )

    yield morld.dialog(["도입 모놀로그..."])

    # yield from으로 sub-generator의 모든 yield를 전달
    state = yield from run_character_creation()
    apply_character_creation(state)

    yield morld.dialog([f"완료: {state['name']}"])
```

**파일 위치:**
- `scripts/morld/ui/Dialog.cs` - PyDialogRequest 클래스
- `scripts/morld/ui/Focus.cs` - FocusType.Dialog
- `scenarios/scenario02/python/events/scripts/player_creation.py` - 캐릭터 생성 예시

### 스크립트 시스템 (Script System)
**역할:** Python 스크립트 함수 등록 및 실행, 액션 처리

**@morld.register_script 데코레이터:**
```python
@morld.register_script
def my_script(context_unit_id, *args):
    """스크립트 함수 - context_unit_id는 Focus 대상 유닛"""
    # Generator 반환 시 Dialog 지원
    result = yield morld.dialog("선택하세요\n\n[url=@ret:yes]예[/url]")
    if result == "yes":
        morld.give_item(context_unit_id, item_id)
```

**액션 문자열 형식:**
| 형식 | 설명 | 예시 |
|------|------|------|
| `call:메서드명:표시명` | Asset 인스턴스 메서드 호출 | `call:talk:대화` |
| `call:메서드명:인자:표시명` | 인자 있는 메서드 호출 | `call:sit:front:앉기` |

**OOP 메서드 호출 예시:**
```python
# assets/base.py - Character 베이스 클래스

class Character(Unit):
    def talk(self):
        """기본 대화 - 서브클래스에서 오버라이드"""
        yield morld.dialog(f"[{self.name}]\n...")

# assets/characters/sera.py - 개별 캐릭터
class Sera(Character):
    actions = ["call:talk:대화", "call:debug_props:속성 보기"]

    def talk(self):
        """세라 전용 대화 - Generator 기반"""
        yield morld.dialog([f"[{self.name}]", "...무슨 일이냐?"])
```

**OOP 메서드 완료 후 Focus 처리:**
- Generator 완료 시 `PopIfInvalid()` 호출로 무효화된 Focus 제거
- 아이템 이동 후 빈 인벤토리면 자동으로 상위 Focus로 복귀
- 유효한 Focus면 현재 상태 유지 (UpdateDisplay)

**파일 위치:**
- `scripts/MetaActionHandler/` - BBCode URL 클릭 핸들러 (partial class)
  - `MetaActionHandler.cs` - 필드, 생성자, HandleAction 진입점, 이벤트 처리
  - `MetaActionHandler.Dialog.cs` - @ret, @proc, @finish, @next, @prev 핸들러
  - `MetaActionHandler.Navigation.cs` - move, back, toggle, idle 핸들러
  - `MetaActionHandler.Item.cs` - 아이템 관련 핸들러
  - `MetaActionHandler.Script.cs` - call:, ProcessScriptResult
- `scenarios/scenario02/python/assets/` - Asset 클래스 및 메서드

### 챕터 전환 시스템 (Chapter Transition)
**역할:** 챕터 간 플레이어 데이터 저장/복원

**핵심 설계:**
- **위치 제외**: 플레이어 위치는 저장하지 않음 (챕터별로 다르게 배치)
- **데이터 저장**: 이름, props, mood, 인벤토리
- **행동 로그 처리**: 복원 후 `mark_all_logs_read()`로 로그 숨김

**저장되는 데이터:**
```python
{
    "name": str,                        # 플레이어 이름
    "props": {"타입:이름": value},      # 모든 속성 (flat dict)
    "mood": [str, ...],                 # 감정 상태 (현재 미사용)
    "inventory": {"unique_id": count}   # 소지품 (unique_id 기반)
}
```

**인벤토리 저장 방식 (unique_id 기반):**
- 챕터 간 item_id 충돌 방지를 위해 unique_id로 저장
- 복원 시 새 챕터의 item_id로 매핑
- 새 챕터에 없는 아이템은 동적 생성 시도

**API:**
```python
from chapters import load_chapter
from chapters.persistence import save_player_data, restore_player_data

# 챕터 로드 (플레이어 데이터 자동 유지)
load_chapter("chapter_1")  # preserve_player=True 기본값

# 새 게임 (플레이어 데이터 초기화)
load_chapter("chapter_0", preserve_player=False)

# 수동 저장/복원
saved = save_player_data()
restore_player_data(saved)
```

**load_chapter() 동작 흐름:**
```
1. 기존 플레이어 데이터 저장 (preserve_player=True면)
2. morld.clear_world()로 월드 초기화
3. 새 챕터 모듈 import 및 initialize() 호출
4. 저장된 플레이어 데이터 복원
5. morld.reinitialize_locations()
6. 현재 챕터 기록
```

**파일 위치:**
- `scenarios/scenario02/python/chapters/__init__.py` - load_chapter() 함수
- `scenarios/scenario02/python/chapters/persistence.py` - save/restore 함수

### 액션 필터링 시스템 (can: prop 기반)
**역할:** 캐릭터가 수행 가능한 액션만 UI에 표시

**핵심 개념:**
- **Whitelist 방식**: `can:액션명` prop이 있어야 해당 액션 버튼이 표시됨
- **Actor 기준**: 플레이어의 캐릭터 props로 필터링 (NPC도 동일 로직)
- **레벨 시스템**: `can:액션명` 값이 1 이상이면 수행 가능

**액션 이름 추출 규칙:**
| 액션 형식 | 추출되는 이름 | 예시 |
|-----------|--------------|------|
| `call:메서드명:표시명` | 메서드명 | `call:talk:대화` → `talk` |
| `call:메서드명:인자:표시명` | 메서드명 | `call:sit:front:앉기` → `sit` |
| 단순 액션 | 그대로 | `rest` → `rest` |

**필터링 적용 위치:**
- `GetUnitLookText()` - 유닛/오브젝트 클릭 시 액션 버튼
- `GetItemMenuText()` - 아이템 메뉴 액션 버튼

**예시:**
```python
# Player props
props = {
    "can:talk": 1,      # NPC 대화 가능
    "can:sit": 1,       # 앉기 가능
    "can:take": 1,      # 가져오기 가능
    "can:look": 1,      # 살펴보기 가능
    # ...
}

# Target NPC actions
actions = ["call:talk:대화", "call:trade:거래"]

# 필터링 결과: ["call:talk:대화"]
# (can:trade가 없으므로 거래 버튼 숨김)
```

**파일 위치:**
- `scripts/system/describe_system.cs` - `FilterActionsByActor()`, `CanPerformAction()`, `ExtractActionName()`
- `scenarios/scenario02/python/assets/characters/player.py` - Player의 `can:` props 정의

### 조건부 액션 및 토글 메뉴 (ui.py)
**역할:** 시간, 위치, 상태 등 조건에 따라 액션 활성화/비활성화, 토글 메뉴 제공

**구현 위치:** `scenarios/scenario02/python/ui.py`의 `get_action_text()`

**토글 마크업 형식:**
- `[url=toggle:ID]▶텍스트[/url]` - 토글 버튼
- `[hidden=ID]...[/hidden=ID]` - 펼침 시 표시되는 내용
- C#의 `ToggleRenderer`가 펼침/접힘 상태에 따라 `[hidden]` 영역 표시/숨김 처리

**패턴:**
```python
def get_action_text():
    lines = []

    # C# 기본 행동 가져오기
    default_actions = morld.get_actions_list()
    for action in default_actions:
        lines.append(action)

    # 멍때리기 (토글 메뉴)
    lines.append("  [url=toggle:idle]▶멍때리기[/url]")
    lines.append("[hidden=idle]")
    lines.append("    [url=idle:15]15분[/url]")
    lines.append("    [url=idle:30]30분[/url]")
    lines.append("    [url=idle:60]1시간[/url]")
    lines.append("    [url=idle:240]4시간[/url]")
    lines.append("[/hidden=idle]")

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
- 비활성화: `[color=gray]표시명[/color]` (링크 없음)

**활용 가능한 조건:**
- 시간: `morld.get_game_time()` (분 단위)
- 위치: `morld.get_unit_location(player_id)`
- 아이템: `morld.has_item(player_id, item_id)`
- 상태: `morld.get_prop(prop_name)`

### 소유자(Owner) 시스템
**역할:** 아이템/장소의 원래 소유자를 추적하여 "훔치기" 등의 기능 지원

**핵심 개념:**
- `Owner`는 **원래 소유자**를 나타내며, 아이템을 획득해도 변경되지 않음
- UI에서 `(XXX 소유)` 형태로 표시
- 소유자가 없으면(null) 공용 아이템/장소

**데이터 구조:**
```csharp
// Item.cs
public string Owner { get; set; }  // 예: "sera", "mila", null

// Location.cs
public string Owner { get; set; }  // 예: "player", "lina", null
```

**Python Asset 정의:**
```python
# 아이템에 소유자 지정
class KitchenKnife(Item):
    unique_id = "kitchen_knife"
    name = "부엌칼"
    owner = "mila"  # 밀라 소유

# 장소에 소유자 지정
class LinaRoom(Location):
    unique_id = "lina_room"
    name = "방2"
    owner = "lina"  # 리나 소유
```

**소유자 이름 조회:**
```csharp
// describe_system.cs
string ownerName = GetOwnerName(ownerUniqueId);  // "sera" → "세라"
string locationName = GetLocationNameWithOwner(location);  // "방2 (리나 소유)"
```

### 관계(Prop) 형식
**역할:** NPC 간 관계를 표현하는 Prop 키 네이밍 컨벤션

**형식:** `관계:{대상}:{유형}`
- 콜론(`:`)으로 구분하여 파싱 용이
- 예: `관계:세라:신뢰` → 세라를 신뢰함

**사용 예시:**
```python
# NPC props
props = {
    "외모:금발": 1,
    "성격:명랑함": 1,
    "관계:세라:신뢰": 1,   # 세라를 신뢰
    "관계:플레이어:호감": 3,  # 플레이어에게 호감 레벨 3
}
```

### 생존 시스템 (Survival System)
**역할:** 캐릭터의 체력과 포만감 관리

**핵심 설계:**
- 시간 경과에 따른 포만감 감소
- 포만감 상태에 따른 체력 증감
- 음식 섭취로 포만감 회복

**수치 설계:**
| 상수 | 값 | 설명 |
|------|-----|------|
| SATIETY_DECAY_RATE | 1 | 1시간당 포만감 감소 |
| HEALTH_REGEN_RATE | 1 | 포만감 50+일 때 1시간당 체력 회복 |
| HEALTH_DECAY_RATE | 2 | 포만감 0일 때 1시간당 체력 감소 |

**활성화 조건:**
- `생존:활성화` prop이 1 이상이면 활성화
- 챕터 0에서는 비활성화, 챕터 1에서 활성화

**Python API:**
```python
import survival

# 스탯 조회
stats = survival.get_survival_stats(unit_id)
# {"health": 100, "max_health": 100, "satiety": 80, "max_satiety": 100}

# 스탯 수정
survival.add_satiety(unit_id, 25)  # 포만감 추가
survival.add_health(unit_id, -10)  # 체력 감소

# UI 표시
bar = survival.get_status_bar(unit_id)
# "체력: [color=lime]████████░░[/color] 80  포만감: [color=cyan]██████░░░░[/color] 60"
```

**파일 위치:**
- `scenarios/scenario02/python/survival.py`
- `scenarios/scenario02/python/assets/items/food.py` - 음식 아이템

### 자원 생성 시스템 (Resource Spawning)
**역할:** 이벤트 기반 자원 오브젝트의 아이템 자동 생성

**핵심 설계:**
- `on_time_elapsed` 이벤트 구독
- 오브젝트별 시간 누적 후 자원 생성
- 최대 개수 도달 시 생성 중단

**자원 생성 설정:**
```python
# think/resource_agent.py
RESOURCE_CONFIG = {
    "apple_tree": (720, 3),      # 12시간마다, 최대 3개 (포만감 25)
    "berry_bush": (480, 5),      # 8시간마다, 최대 5개 (포만감 10)
    "mushroom_patch": (600, 4),  # 10시간마다, 최대 4개 (포만감 15)
}
```

**자원 오브젝트 등록:**
```python
# assets/objects/nature.py
class AppleTree(Object):
    unique_id = "apple_tree"
    resource_item_unique_id = "apple"  # 생성할 아이템
    initial_resources = 2              # 초기 자원 개수

    def instantiate(self, instance_id):
        super().instantiate(instance_id)
        # 자원 생성 시스템에 등록
        from think.resource_agent import register_resource_object
        register_resource_object(instance_id, self.unique_id)
```

**파일 위치:**
- `scenarios/scenario02/python/think/resource_agent.py` - 자원 생성 로직
- `scenarios/scenario02/python/assets/objects/nature.py` - 자원 오브젝트 정의

### on_time_elapsed 이벤트
**역할:** 시간 경과 시 Python 시스템에 알림

**핵심 설계:**
- `JobBehaviorSystem`에서 시간 진행 후 이벤트 Enqueue
- `EventSystem`에서 누적 후 한 번에 Flush (중복 호출 방지)
- Python에서 구독하여 시스템별 처리

**이벤트 누적 처리:**
```csharp
// EventSystem.cs
private int _accumulatedTimeElapsed = 0;

public void Enqueue(GameEvent evt) {
    if (evt.Type == EventType.OnTimeElapsed) {
        _accumulatedTimeElapsed += (int)evt.Args[0];
        return;  // 큐에 추가하지 않고 누적만
    }
    _pendingEvents.Add(evt);
}

public bool FlushEvents() {
    if (_accumulatedTimeElapsed > 0) {
        var timeEvent = GameEvent.OnTimeElapsed(_accumulatedTimeElapsed);
        _accumulatedTimeElapsed = 0;
        _scriptSystem.CallSingleEventHandler(timeEvent);
    }
    // ... 나머지 이벤트 처리
}
```

**Python 구독:**
```python
# events/__init__.py
_time_elapsed_handlers = []

def subscribe_time_elapsed(handler):
    """on_time_elapsed 이벤트 구독"""
    _time_elapsed_handlers.append(handler)

# survival.py, resource_agent.py에서 구독
subscribe_time_elapsed(_on_time_elapsed)
```

**파일 위치:**
- `scripts/system/event_system.cs` - 이벤트 누적 및 Flush
- `scenarios/scenario02/python/events/__init__.py` - 구독 시스템

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ MetaActionHandler/ (BBCode URL 클릭 핸들러 - partial class)
│  ├─ MetaActionHandler.cs (필드, 생성자, 진입점, 이벤트 처리)
│  ├─ MetaActionHandler.Dialog.cs (@ret, @proc, @finish, @next, @prev)
│  ├─ MetaActionHandler.Navigation.cs (move, back, toggle, idle)
│  ├─ MetaActionHandler.Item.cs (아이템 관련)
│  └─ MetaActionHandler.Script.cs (call:, ProcessScriptResult)
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
│     ├─ events/
│     │  ├─ scripts/ (@morld.register_script 함수들)
│     │  │  ├─ player_creation.py (캐릭터 생성 플로우)
│     │  │  ├─ npc_talk.py (NPC 대화 라우팅)
│     │  │  ├─ container.py (컨테이너 아이템 가져오기/넣기)
│     │  │  └─ location_callbacks.py (위치 콜백)
│     │  ├─ reach/ (OnReach 이벤트)
│     │  └─ meet/ (OnMeet 이벤트)
│     ├─ chapters/ (챕터 관리)
│     │  ├─ __init__.py (load_chapter, get_current_chapter)
│     │  ├─ persistence.py (플레이어 데이터 저장/복원)
│     │  └─ chapter_*.py (각 챕터 정의)
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
