# 데모 흐름 (Demo Flow)

## 개요

시나리오03의 데모는 플레이어가 오퍼레이터로서 지저 세계에 투입되어, 플랫폼(베이스캠프)을 건설하고, 분대를 편성하여 첫 탐사 임무를 수행하는 과정을 다룬다.

---

## 구현 상태

| 구분 | 상태 | 테스트 |
|------|------|--------|
| 챕터/월드 초기화 | 구현 완료 | 10개 통과 |
| 진행 시스템 (14단계) | 구현 완료 | 24개 통과 |
| 건축 시스템 | 구현 완료 | 20개 통과 |
| 프롤로그 이벤트 (Step 1-3) | 이벤트 핸들러 구현 | 4개 통과 |
| 건축 튜토리얼 (Step 5-6) | 이벤트 핸들러 구현 | - |
| 에이전트/NPC | 기본 Agent 구현 | 6개 통과 |
| 퀘스트 정의 | 데이터 정의 완료 | 5개 통과 |
| 분대 시스템 | 구현 완료 (squad.py) | 26개 통과 |
| 동적 맵 생성 | 구현 완료 (mapgen.py, BSP) | 17개 통과 |
| 원정 시스템 | 구현 완료 (expedition.py) | 19개 통과 |
| 전투 시스템 | 구현 완료 (combat.py, 자동해결) | 8개 통과 |
| 이벤트 연결 (Step 8-14) | 구현 완료 | 통합 테스트 포함 |
| 플레이어 UI (CRTConsole) | 구현 완료 (분대편성/진군/퇴각) | 6개 통과 |
| CRT 뷰 | 미구현 (C# 확장 필요) | - |

**총 테스트: 13 modules, 155 passed**

---

## 데모 흐름 요약

| Step | 내용 | 핵심 시스템 | 트리거 |
|------|------|------------|--------|
| 1 | 계약 | Dialog (Conversation) | auto |
| 2 | 지저철 탑승 | Vehicle + Dialog | auto |
| 3 | 플랫폼 도착 | Region/Location + CRT 뷰 | auto |
| 4 | 플랫폼 탐색 | Quest | quest 완료 |
| 5 | 건축 튜토리얼 | Dialog | auto |
| 6 | 에이전트 증원 | NPC 동적 생성 | auto |
| 7 | 기본 건설 | build.py + NPC Activity | build 완료 |
| 8 | 첫 임무 브리핑 | Dialog + Quest | auto |
| 9 | 분대 편성 | squad.py + CRTConsole UI | player |
| 10 | 탐사 출발 | expedition.py + mapgen.py | auto |
| 11 | 탐사 수행 | expedition.py + combat.py | player |
| 12 | 귀환 | expedition.py + CRTConsole UI | player |
| 13 | 임무 완료 | Dialog | auto |
| 14 | 엔딩 | Dialog | auto |

---

## 파일 구조

```
scenarios/scenario03/python/
├── build.py                        # 건축 시스템 (레시피/뼈대/진척도/원격지정)
├── squad.py                        # 분대 시스템 (편성/해산/공세레벨/대열순번)
├── mapgen.py                       # BSP 동적 맵 생성 (Region/Location/Gate)
├── expedition.py                   # 원정 라이프사이클 (준비→탐사→귀환→완료)
├── combat.py                       # 자동 전투 해결 (위협코드/공세보정/대열피해)
├── chapters/
│   ├── __init__.py                 # load_chapter() (시나리오02 패턴)
│   └── demo.py                     # 데모 챕터 초기화
├── world/
│   ├── __init__.py                 # initialize_world() + RegionGate
│   ├── platform.py                 # Region 0: 플랫폼 (3 locations, 6 gates)
│   └── train.py                    # Region 1: 지저철 내부 (1 location)
├── assets/
│   ├── base.py                     # Asset/Unit/Character/Object/Item/Location
│   ├── registry.py                 # unique_id <-> instance_id 매핑
│   ├── characters/
│   │   ├── secretary.py            # 비서 NPC
│   │   └── squad_member.py         # 분대원 NPC (동적 configure)
│   ├── locations/
│   │   ├── platform_locations.py   # Station/PlatformCorridor/CommRoom
│   │   └── train_locations.py      # TrainCar
│   ├── objects/
│   │   ├── train.py                # SubwayTrain + CRTConsole
│   │   └── construction.py         # ConstructionSite (건설현장)
│   └── items/
│       └── materials.py            # MetalPipe/ConcreteBlock/Plank/Wire
├── events/
│   ├── __init__.py                 # 이벤트 모듈 등록
│   ├── progression.py              # 14단계 진행 추적 시스템
│   ├── prologue.py                 # Step 1-3: 계약/탑승/도착
│   ├── tutorial.py                 # Step 5-6: 건축 튜토리얼/증원
│   ├── first_mission.py            # Step 8-13: 임무 브리핑/탐사/완료
│   └── ending.py                   # Step 14: 엔딩
├── think/
│   ├── __init__.py                 # BaseAgent + 레지스트리 export
│   ├── registry.py                 # Agent 레지스트리
│   ├── agents/
│   │   ├── secretary_agent.py      # SecretaryAgent (통신실 상주)
│   │   └── squad_agent.py          # SquadMemberAgent (FSM 스택)
│   └── activities/
│       ├── __init__.py             # ACTIVITY_HANDLERS dict
│       └── build_activity.py       # NPC 건설 3-phase 핸들러
├── quest/
│   └── __init__.py                 # DEMO_QUESTS + BUILD_RECIPES 정의
└── tests/
    ├── mock_morld.py               # MockMorld (C# API 스텁)
    ├── run_tests.py                # 테스트 러너 (13 modules)
    ├── test_assets.py              # 10 tests
    ├── test_world.py               # 6 tests
    ├── test_chapters.py            # 4 tests
    ├── test_agents.py              # 6 tests
    ├── test_events.py              # 4 tests
    ├── test_quest.py               # 5 tests
    ├── test_progression.py         # 24 tests
    ├── test_build.py               # 20 tests
    ├── test_squad.py               # 26 tests
    ├── test_mapgen.py              # 17 tests
    ├── test_expedition.py          # 19 tests
    ├── test_combat.py              # 8 tests
    └── test_integration.py         # 6 tests
```

---

## Region/Location/Gate 설계

### Region 0: 플랫폼 (베이스캠프)

```
                    ┌──────────┐
                    │ 통신실(2) │ <- 플레이어 시점 (CRT)
                    │ len=40   │
                    └────┬─────┘
                         │ Gate (L1:x=50 <-> L2:x=40)
    ┌──────────┐    ┌────┴─────┐    ┌──────────┐
    │ 승강장(0) ├────┤중앙통로(1)├────┤ 확장공간  │
    │ len=200  │    │ len=100  │    │ (건축)    │
    └──────────┘    └──────────┘    └──────────┘
         │           Gate (L0:x=200 <-> L1:x=0)
         │ Gate (L0:x=100 <-> R1:L0:x=0, 동적 재연결)
    ┌────┴──────┐
    │ 지저철(R1) │
    └───────────┘
```

#### Location 정의

| ID | 이름 | length | 용도 | 초기 상태 |
|----|------|--------|------|----------|
| 0 | 승강장 | 200 | 지저철 정차/탑승 | 존재 |
| 1 | 중앙 통로 | 100 | 이동 허브, 건축 분기점 | 존재 |
| 2 | 통신실 | 40 | 플레이어 CRT 시점 | 존재 |
| 3+ | 확장 공간 | 가변 | 건축으로 동적 생성 | build.py |

#### Gate 정의 (platform.py)

```python
GATES = [
    # 승강장(0) <-> 중앙 통로(1)
    (0, 0, 0, 200, 0, 1, 0),     # 승강장 우측 -> 통로 좌측
    (0, 1, 0, 0,   0, 0, 200),   # 통로 좌측 -> 승강장 우측

    # 중앙 통로(1) <-> 통신실(2)
    (0, 1, 1, 50,  0, 2, 0),     # 통로 x=50 -> 통신실 좌측
    (0, 2, 0, 40,  0, 1, 50),    # 통신실 우측 -> 통로 x=50

    # 승강장(0) <-> 지저철 내부(R1, L0) -- 동적 재연결 대상
    (0, 0, 2, 100, 1, 0, 0),     # 승강장 중앙 -> 객차 입구
    (1, 0, 0, 0,   0, 0, 100),   # 객차 입구 -> 승강장 중앙
]
```

### Region 1: 지저철 내부

| ID | 이름 | length | 용도 |
|----|------|--------|------|
| 0 | 객차 | 150 | 이동 중 대기/대화 공간 |

---

## 진행 시스템 (progression.py)

14단계 데모 흐름을 추적하는 모듈 수준 상태 머신.

### API

```python
from events.progression import (
    reset,              # 진행 초기화 (챕터 로드 시)
    get_current_step,   # 현재 단계 (0-14)
    get_step_name,      # 단계 이름
    advance_to,         # 지정 단계로 진행
    complete_step,      # 현재 단계 완료 -> 다음 단계
    is_step,            # 현재 단계 확인
    is_step_at_least,   # 최소 단계 확인
    on_step,            # 단계 진입 콜백 등록
    trigger_step_event, # 단계별 이벤트 핸들러 실행
    get_demo_status,    # 진행 상황 요약 dict
)
```

### Step -> 이벤트 핸들러 매핑

| Step | 핸들러 | 위치 |
|------|--------|------|
| 1 | `handle_contract()` | events/prologue.py |
| 5 | `handle_build_tutorial()` | events/tutorial.py |
| 6 | `handle_reinforcement()` | events/tutorial.py |
| 8 | `handle_mission_briefing()` | events/first_mission.py |
| 10 | `start_expedition()` | events/first_mission.py |
| 13 | `handle_mission_complete()` | events/first_mission.py |
| 14 | `handle_ending()` | events/ending.py |

Step 2-3은 Step 1 핸들러 내부에서 `yield from`으로 연쇄 호출.
Step 4, 7, 9, 11, 12는 외부 트리거 대기 (퀘스트/건설/플레이어 액션).

---

## 건축 시스템 (build.py)

시나리오02 build.py의 간소화 버전. Location 건설만 지원.

### 핵심 차이점

- **원격 건축 지정**: CRTConsole -> `designate_build()` -> `build:designated` prop
- **에이전트 실행**: 오퍼레이터는 지정만, NPC가 건설 Activity 수행

### API

```python
import build

# 레시피
build.register_recipe(BuildRecipe(...))
build.get_recipe(recipe_id)
build.get_all_recipes()
build.register_demo_recipes()  # quest/__init__.py의 BUILD_RECIPES 등록

# 건설
build.build_location_frame(builder_id, source_region, source_location,
                           gate_x, recipe_id, room_name)
# -> (success, region_id, location_id, site_id, msg)

build.build_location_progress(builder_id, site_id, materials_used)
# -> (success, new_progress, msg)

build.designate_build(recipe_id, source_region, source_location, gate_x)
# -> (success, region_id, location_id, site_id, msg)

build.is_construction_complete(site_id) -> bool
```

### 건설 흐름

```
1. designate_build() 호출 (CRTConsole UI)
   -> build_location_frame():
      - 새 Location 생성 (recipe.base_length)
      - Gate 양방향 연결
      - ConstructionSite 오브젝트 배치
      - Props: 건설:진척도=0, 건설:레시피, 건설:소유자

2. NPC handle_build() 활동 (think/activities/build_activity.py)
   Phase: idle -> going_to_site -> building
   - idle: _find_construction_site() -- Region 내 미완료 현장 탐색
   - going_to_site: 현장 Location으로 이동
   - building: build_location_progress() 호출 (진척도 +10%)

3. 진척도 100% -> 건설 완료
```

### Props

| Prop | 대상 | 타입 | 값 |
|------|------|------|-----|
| `건설:진척도` | ConstructionSite | int | 0-100 |
| `건설:레시피` | ConstructionSite | str | recipe unique_id |
| `건설:소유자` | ConstructionSite | str | "operator" 또는 builder name |

### 건축 레시피 (데모용)

| recipe_id | 이름 | 자재 | 진행/투입 | 길이 |
|-----------|------|------|----------|------|
| `barracks` | 임시 막사 | plank x5, concrete_block x3 | 10% | 60 |
| `storage_room` | 보관소 | metal_pipe x3, plank x3 | 10% | 50 |
| `med_bay` | 의료실 | metal_pipe x2, wire x3, plank x2 | 10% | 40 |
| `armory` | 무기고 | metal_pipe x5, concrete_block x2 | 10% | 50 |

---

## 주요 오브젝트

### SubwayTrain (지저철)

```python
# assets/objects/train.py
class SubwayTrain(Object):
    unique_id = "subway_train"
    props = {
        "vehicle:type": "train",
        "vehicle:speed": 5.0,
        "vehicle:fuel": 100, "vehicle:fuel_max": 100,
        "vehicle:hp": 500, "vehicle:hp_max": 500,
        "vehicle:interior": "R1:L0",
        "vehicle:part:engine": 100, "vehicle:part:body": 100,
    }
    # actions: inspect (상태 점검)
```

### CRTConsole (통신실 콘솔)

```python
# assets/objects/train.py
class CRTConsole(Object):
    unique_id = "crt_console"
    actions = [
        "call:view_status:상황 확인",       # 플랫폼 상황 요약
        "call:designate_build:건축 지정",   # 원격 건축 (build.py 연동)
        "call:manage_squad:분대 관리",      # 분대 편성/해산/공세레벨
        "call:order_advance:진군 명령",     # 탐사 중 다음 방 이동 + 전투
        "call:order_retreat:퇴각 명령",     # 귀환 + 원정 완료 + 진행 전환
    ]
```

### ConstructionSite (건설현장)

```python
# assets/objects/construction.py
class ConstructionSite(Object):
    unique_id = "construction_site"
    actions = ["call:check_progress:진척도 확인"]
    # get_focus_text(): 진척도별 다른 묘사
```

---

## NPC 정의

### 비서 (Secretary)

- 통신실(R0, L2) 상주
- SecretaryAgent: 이동 없음, 보고/안내 역할
- 프롤로그부터 엔딩까지 이벤트 안내

### Echo 시리즈 (분대원, 동적 생성)

| 시리얼 번호 | 역할 | 역할 props |
|------------|------|-----------|
| Echo-01 | assault | `squad:combat_style=aggressive` |
| Echo-02 | support | `squad:combat_style=defensive` |
| Echo-03 | sniper | `squad:combat_style=ranged` |
| Echo-04 | medic | `squad:combat_style=support` |

```python
# assets/characters/squad_member.py
class SquadMember(Character):
    unique_id = "squad_member"  # configure()로 동적 변경
    def configure(self, unique_id, name, role):
        # ROLE_PROPS에서 역할별 props 적용
```

---

## 챕터 초기화 (demo.py)

```python
def initialize():
    # 1. 시간 정지 + UI Lock
    # 2. 월드 초기화 (Region 0,1 + Gate + RegionGate)
    # 3. 시간 설정 (Y1/M1/D1 09:00)
    # 4. NPC 배치 (비서 -> R0,L2)
    # 5. 오브젝트 배치 (지저철 -> R0,L0, CRT -> R0,L2)
    # 6. 건축 레시피 등록 (4개)

def post_restore():
    # 1. progression.reset() + advance_to(1)
    # 2. trigger_prologue()
```

---

## 이벤트 시퀀스 전체 흐름

```
post_restore()
  |
  +- set_time_frozen(True)
  +- set_ui_lock(True)
  +- progression.advance_to(1)
  |
  v
Step 1: handle_contract()         <- progression.trigger_step_event(1)
  | ui.dialog: 계약서 + 서명/거부
  | (거부 -> 게임 종료)
  v
Step 2: _start_train_sequence()   <- yield from (Step 1 내부)
  | ui.dialog: 비서 소개 x4
  | advance_time_des(2시간)
  v
Step 3: _arrive_at_platform()     <- yield from (Step 2 내부)
  | set_time_frozen(False)
  | set_ui_lock(False)
  | TODO: give_quest("demo_explore_platform")
  v
Step 4: (퀘스트 완료 대기)         <- quest 트리거
  v
Step 5: handle_build_tutorial()   <- progression.trigger_step_event(5)
  | ui.dialog: 건축 안내 x3
  v
Step 6: handle_reinforcement()    <- progression.trigger_step_event(6)
  | NPC 동적 생성 x4 (Echo-01~04)
  | 건축 자재 배달
  v
Step 7: (건설 완료 대기)           <- build 완료 트리거
  | NPC handle_build() Activity
  | 플레이어: CRT -> 건축 지정
  v
Step 8: handle_mission_briefing() <- progression.trigger_step_event(8)
  | ui.dialog: 임무 설명 + 선택지 (자세히/수락)
  v
Step 9: (분대 편성 대기)           <- CRTConsole.manage_squad()
  | _create_new_squad(): echo_* 에이전트 자동 편성
  | 분대장 지정 + 대열 순번(Rank) 배정
  | complete_step(9) → Step 10 자동 진행
  v
Step 10: start_expedition()       <- progression._handle_step_10()
  | expedition.prepare_expedition(squad_id, "easy")
  | expedition.start_expedition() → mapgen BSP 맵 생성
  | 분대 입구 배치 + 출발 대화
  v
Step 11: (탐사 자유 플레이)        <- CRTConsole.order_advance()
  | expedition.move_to_room() → 미탐색 방 이동
  | combat.resolve_room_combat() → 자동 전투 해결
  | 방 이벤트 대화 (전투 결과/전리품)
  v
Step 12: (귀환 명령 대기)          <- CRTConsole.order_retreat()
  | first_mission.retreat_expedition() → 귀환 대화
  | expedition.complete_expedition() → 요약 반환
  | complete_step(12) → Step 13 자동 진행
  v
Step 13: handle_mission_complete() <- progression.trigger_step_event(13)
  | ui.dialog: 임무 완료 보고 x2
  v
Step 14: handle_ending()          <- progression.trigger_step_event(14)
  | ui.dialog: 종합 보고 + 데모 종료 메시지
  | -- 데모 종료 --
```

---

## 시나리오02 필요 확장 목록

| 시스템 | 확장 내용 | 난이도 | 상태 |
|--------|----------|--------|------|
| build.py | `builder_id=None` 허용 (원격 지정) | 낮음 | **시나리오03 자체 구현** |
| party.py | `set_member_rank()` API | 낮음 | **시나리오03 자체 구현 (squad.py)** |
| Quest | `source="squad"` 조건 (분대원 인벤 합산) | 중간 | 미구현 |
| vehicle.py | `vehicle:type="train"` 지원 | 중간 | 미구현 |
| TextUI | `set_view_mode("crt")` | 높음 | 미구현 (C#) |
| mapgen | BSP -> Location/Gate 파이프라인 | 낮음 | **구현 완료 (mapgen.py)** |
| expedition | 원정 라이프사이클 (준비→탐사→귀환) | 중간 | **구현 완료 (expedition.py)** |
| combat | 자동 전투 해결 (데모용) | 낮음 | **구현 완료 (combat.py)** |

---

## 테스트

```bash
cd scenarios/scenario03/python/tests
python run_tests.py        # 전체 실행
python run_tests.py -v     # verbose
python run_tests.py build  # test_build만 실행
```

테스트 패턴: 시나리오02와 동일 (`_T` 베이스 클래스 + MockMorld 주입)

---

## 구현 완료 시스템 상세

### 분대 시스템 (squad.py)

시나리오02 party.py 패턴을 간소화. FSM/follow 스케줄 없이 분대 관리만 수행.

- Squad 클래스: squad_id, leader_id, members (최대 3), aggression
- 공세 레벨: retreat(-2) ~ combat_aggressive(+2)
- 대열 순번: 1=전위, 2=중위(기본), 3=후위
- Order: order_type, target, priority, stealth

### 동적 맵 생성 (mapgen.py)

BSP 알고리즘으로 탐사 맵 생성. Region/Location/Gate API 사용.

- DifficultyConfig: easy(5-8방), normal(8-12), hard(12-18)
- BSPNode: 재귀 분할 → 리프 노드에 방 배치
- 방 타입: entrance(첫 방), room(중간), objective(마지막)
- 위협 코드: P=Pest(3), R=Raider(5), B=Beast(2), W=Wraith(7)
- cleanup_expedition(): 탐사 완료 후 동적 Region 삭제

### 원정 시스템 (expedition.py)

원정 라이프사이클 관리. 분대/맵생성/전투를 조율.

- 상태 흐름: preparing → active → returning → completed
- prepare_expedition(): 분대 검증 + 상태 생성
- start_expedition(): mapgen 호출 + 분대 입구 배치
- move_to_room(): 연결 검증 + 이동 + 탐색 표시
- retreat_expedition(): 분대 R0/L0 복귀 + 맵 정리
- complete_expedition(): 요약 반환 (탐색 수/전투 수)

### 자동 전투 (combat.py)

데모용 자동 해결. 마이크로턴 전투(MicroTurnCombatState)의 전신.

- 분대 전력 = vita 합산, 승률 = 0.5 + (비율-1)*0.3 (0.1~0.95)
- 공세 보정: power_mod = 1.0 + val*0.1, damage_mod = 1.0 + val*0.15
- 대열 피해: 전위 1.4x, 중위 1.0x, 후위 0.6x
- HP 최소 1 보존, 승리 시 위협 제거

### CRTConsole 플레이어 UI

- manage_squad(): 분대 없으면 자동 편성, 있으면 관리 (공세 변경/해산)
- order_advance(): 미탐색 방 이동 → 전투 → 목표 도달 체크
- order_retreat(): 귀환 → 원정 완료 → Step 12→13 진행

---

## 미정 사항

- [ ] 비서 NPC 시리얼 번호/성격 결정
- [ ] CRT 뷰 UI 상세 설계 (C# TextUI 확장 범위)
- [ ] 데모 에이전트 장비 목록
- [ ] 탐사 지역 자원 배치 밸런스
- [ ] 건축 진행률 시각적 표현
- [ ] 프롤로그 연출 (사운드, 화면 효과)
- [ ] AutoTimeFlow 배속 UI
- [ ] NPC 건설 시 자재 소비 구현 (현재 진척도만 증가)
- [ ] quest_manager 연동 (현재 데이터 정의만)
- [ ] 마이크로턴 전투 (MicroTurnCombatState) — 현재 자동 해결로 대체
