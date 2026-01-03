# EventSystem 확장 기능 (미구현)

---

## Phase 7: Python 기반 콘텐츠 관리 시스템 (시나리오03)

### 목표

캐릭터별로 데이터와 이벤트를 개별 폴더로 분리하여 콘텐츠 관리를 용이하게 함.
JSON 대신 Python으로 모든 콘텐츠를 정의하여 동적 로직 포함 가능.

### 폴더 구조

```
scenarios/scenario03/
├─ scenario.json          # 시나리오 메타데이터 (name, version)
├─ 시나리오.md            # 설계 문서
├─ python/
│  ├─ __init__.py         # 패키지 초기화 (모든 모듈 import)
│  ├─ world.py            # 지도 데이터 (regions, edges, time)
│  ├─ items.py            # 아이템 정의
│  ├─ events.py           # 메인 이벤트 핸들러 (on_event_list)
│  │
│  └─ characters/         # 캐릭터별 폴더
│     ├─ __init__.py      # 캐릭터 모듈 집합 (all_characters 리스트)
│     ├─ player/
│     │  ├─ __init__.py   # 캐릭터 데이터 export
│     │  ├─ data.py       # 기본 정보 (name, tags, actions, schedule)
│     │  └─ events.py     # 플레이어 전용 이벤트 (게임 시작, 직업 선택)
│     ├─ cheolsu/
│     │  ├─ __init__.py
│     │  ├─ data.py       # 철수 기본 정보, appearance, mood, schedule
│     │  ├─ dialogues.py  # 철수 대화 데이터 (activity별 대사)
│     │  └─ events.py     # 철수 관련 이벤트 (만남, 퀘스트 등)
│     ├─ younghee/
│     │  ├─ __init__.py
│     │  ├─ data.py
│     │  ├─ dialogues.py
│     │  └─ events.py
│     └─ minsu/
│        ├─ __init__.py
│        ├─ data.py
│        ├─ dialogues.py
│        └─ events.py
│
└─ objects/               # 오브젝트 정의 (별도 폴더)
   ├─ __init__.py
   ├─ containers.py       # 상자, 책상 등 컨테이너
   ├─ furniture.py        # 거울, 의자 등 가구
   └─ grounds.py          # 바닥 오브젝트 자동 생성
```

### 핵심 파일 설계

#### 1. world.py - 지도 데이터

```python
# world.py - 지도 및 시간 설정

WORLD_NAME = "시뮬레이션 마을"

REGIONS = [
    {
        "id": 0,
        "name": "주거지역",
        "appearance": {
            "default": "조용한 주거지역이다."
        },
        "locations": [
            {"id": 0, "name": "주민1의 집"},
            {
                "id": 1,
                "name": "마을 광장",
                "appearance": {
                    "default": "돌로 포장된 광장에 분수대가 서 있다.",
                    "아침": "이른 아침 안개가 광장을 감싸고 있다.",
                    "낮": "햇살이 분수대 물방울을 반짝이게 한다."
                }
            },
            # ... 다른 위치들
        ],
        "edges": [
            {"a": 0, "b": 1, "timeAtoB": 10, "timeBtoA": 10},
            # ...
        ]
    },
    # ... 다른 지역들
]

REGION_EDGES = [
    {
        "id": 0,
        "name": "마을-상업지구 다리",
        "regionA": 0, "localA": 1,
        "regionB": 1, "localB": 0,
        "timeAtoB": 8, "timeBtoA": 8
    }
]

TIME_SETTINGS = {
    "year": 1,
    "month": 4,
    "day": 1,
    "hour": 6,
    "minute": 0
}

# C#에서 호출하는 함수
def get_world_data():
    """지도 데이터 반환 (C#에서 JSON으로 변환)"""
    return {
        "name": WORLD_NAME,
        "regions": REGIONS,
        "regionEdges": REGION_EDGES
    }

def get_time_data():
    """시간 데이터 반환"""
    return TIME_SETTINGS
```

#### 2. characters/cheolsu/data.py - 캐릭터 데이터

```python
# characters/cheolsu/data.py - 철수 캐릭터 정의

CHARACTER_ID = 1  # 고유 ID

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "철수",
    "comment": "npc_001",
    "type": "male",
    "regionId": 0,
    "locationId": 0,
    "tags": {},
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "평범한 청년이다. 차분한 표정을 짓고 있다.",
        "기쁨": "환하게 웃고 있다.",
        "슬픔": "어깨가 축 처져 있다.",
        "식사": "맛있게 음식을 먹고 있다.",
        "수면": "편안하게 잠들어 있다."
    },
    "mood": ["기쁨"],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 0,
                 "start": 360, "end": 420, "activity": "준비"},
                {"name": "아침식사", "regionId": 1, "locationId": 0,
                 "start": 420, "end": 480, "activity": "식사"},
                # ... 다른 스케줄
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
```

#### 3. characters/cheolsu/dialogues.py - 캐릭터 대화

```python
# characters/cheolsu/dialogues.py - 철수 대화

from characters.cheolsu.data import CHARACTER_ID

# activity별 대사 오버라이드
DIALOGUES = {
    "default": {
        "pages": [
            "안녕, 나는 철수야.",
            "오늘 날씨가 좋네."
        ]
    },
    "휴식": {
        "pages": [
            "(편하게 쉬고 있다)",
            "...오늘은 좀 피곤하네."
        ]
    },
    "식사": {
        "pages": [
            "(음식을 먹고 있다)",
            "이 식당 음식은 정말 맛있어."
        ]
    }
}

def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
```

#### 4. characters/cheolsu/events.py - 캐릭터 이벤트

```python
# characters/cheolsu/events.py - 철수 관련 이벤트

import morld
from characters.cheolsu.data import CHARACTER_ID
from characters.cheolsu.dialogues import get_dialogue

# 이벤트 플래그
_flags = {}

def on_meet_player(player_id):
    """플레이어와 처음 만났을 때"""
    if _flags.get("first_meet"):
        return None

    _flags["first_meet"] = True
    return {
        "type": "monologue",
        "pages": [
            "어? 처음 보는 얼굴이네.",
            "나는 철수라고 해. 반가워!",
            "이 마을에 처음 왔어? 둘러보려면 도움이 필요하면 말해."
        ],
        "time_consumed": 2,
        "button_type": "ok"
    }

def on_reach_together(location_id):
    """같은 장소에 도착했을 때"""
    # 특정 장소에서의 대화
    if location_id == 3:  # 공원
        return {
            "type": "monologue",
            "pages": ["오, 여기서 보네! 공원 좋지?"],
            "time_consumed": 1,
            "button_type": "ok"
        }
    return None

def npc_talk(context_unit_id):
    """대화 스크립트 함수"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None or unit_info.get("id") != CHARACTER_ID:
        return None

    activity = unit_info.get("activity")
    dialogue = get_dialogue(activity)

    name = unit_info.get("name", "???")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
```

#### 5. characters/__init__.py - 캐릭터 집합

```python
# characters/__init__.py - 모든 캐릭터 모듈 집합

from characters.player import data as player_data
from characters.cheolsu import data as cheolsu_data
from characters.younghee import data as younghee_data
from characters.minsu import data as minsu_data

# 캐릭터별 이벤트 핸들러 등록
from characters.cheolsu import events as cheolsu_events
from characters.younghee import events as younghee_events
from characters.minsu import events as minsu_events

CHARACTER_EVENTS = {
    cheolsu_data.CHARACTER_ID: cheolsu_events,
    younghee_data.CHARACTER_ID: younghee_events,
    minsu_data.CHARACTER_ID: minsu_events,
}

def initialize_characters():
    """C#에서 호출: 모든 캐릭터 등록"""
    import morld
    morld.add_unit(player_data.CHARACTER_DATA)
    morld.add_unit(cheolsu_data.CHARACTER_DATA)
    morld.add_unit(younghee_data.CHARACTER_DATA)
    morld.add_unit(minsu_data.CHARACTER_DATA)

def get_character_event_handler(unit_id):
    """특정 캐릭터의 이벤트 핸들러 반환"""
    return CHARACTER_EVENTS.get(unit_id)
```

#### 6. events.py - 메인 이벤트 핸들러

```python
# events.py - 메인 이벤트 핸들러

import morld
from characters import get_character_event_handler

_triggered_events = set()

def on_event_list(ev_list):
    """이벤트 리스트 처리 (C#에서 호출)"""
    player_id = morld.get_player_id()

    for event in ev_list:
        event_type = event[0]

        if event_type == "game_start":
            result = handle_game_start()
            if result:
                return result

        elif event_type == "on_meet":
            unit_ids = event[1:]
            if player_id in unit_ids:
                # 플레이어가 포함된 만남
                other_ids = [uid for uid in unit_ids if uid != player_id]
                for other_id in other_ids:
                    handler = get_character_event_handler(other_id)
                    if handler and hasattr(handler, "on_meet_player"):
                        result = handler.on_meet_player(player_id)
                        if result:
                            return result

        elif event_type == "on_reach":
            unit_id = event[1]
            region_id = event[2]
            location_id = event[3]

            if unit_id == player_id:
                result = handle_player_reach(region_id, location_id)
                if result:
                    return result

    return None

def handle_game_start():
    """게임 시작 이벤트"""
    if "game_start" in _triggered_events:
        return None
    _triggered_events.add("game_start")

    # 플레이어 캐릭터의 게임 시작 이벤트 호출
    from characters.player import events as player_events
    if hasattr(player_events, "on_game_start"):
        return player_events.on_game_start()

    return None

def handle_player_reach(region_id, location_id):
    """플레이어 도착 이벤트"""
    # 위치별 이벤트 체크
    return None
```

### C# ScriptSystem 연동

```csharp
// ScriptSystem.cs - Python 데이터 초기화

public void CallInitializeScenario()
{
    // Python 모듈들을 직접 import하여 초기화 함수 호출
    var code = @"
import world
import items
from characters import initialize_characters
from objects import initialize_objects

world.initialize_world()
world.initialize_time()
items.initialize_items()
initialize_characters()
initialize_objects()
";
    _interpreter.Execute(code);
}
```

**morld 모듈 API:**
- `add_region(data)` - Region 등록
- `add_location(region_id, data)` - Location 등록
- `add_edge(region_id, data)` - Edge 등록
- `add_region_edge(data)` - RegionEdge 등록
- `set_time(data)` - GameTime 설정
- `add_item(data)` - Item 등록
- `add_unit(data)` - Unit 등록
- `set_player_id(id)` - 플레이어 ID 설정
- `add_inventory(unit_id, item_id, count)` - 인벤토리 추가
- `set_visibility(unit_id, visible)` - 가시성 설정

### 장점

1. **캐릭터별 독립 관리**: 캐릭터 추가/삭제가 폴더 단위로 가능
2. **이벤트 로직 분리**: 각 캐릭터의 이벤트가 해당 캐릭터 폴더에 집중
3. **동적 콘텐츠**: Python 로직으로 조건부 대사, 랜덤 이벤트 등 구현 가능
4. **협업 용이**: 캐릭터별로 작업자 분리 가능
5. **테스트 용이**: 개별 캐릭터 모듈 단위 테스트 가능

### 구현 순서

1. [x] ScriptSystem에 Python 데이터 로드 API 추가
2. [x] scenario03 폴더 구조 생성
3. [x] world.py 구현 (시나리오01 location_data.json 변환)
4. [x] items.py 구현 (시나리오01 item_data.json 변환)
5. [x] characters/ 폴더 구조 생성
6. [x] player 캐릭터 구현 (직업 선택 이벤트 포함)
7. [x] 철수/영희/민수 캐릭터 구현
8. [x] objects/ 폴더 구현 (상자, 거울, 바닥)
9. [x] events.py 메인 핸들러 구현
10. [x] GameEngine에서 Python 데이터 로드 지원

### 구현 완료 (2026-01-03)

- morld 모듈 API: `add_region`, `add_location`, `add_edge`, `add_region_edge`, `set_time`, `add_item`, `add_unit`, `set_player_id`, `add_inventory`, `set_visibility`
- Python 기반 데이터 로드: `IsPythonDataSource()`, `CallInitializeScenario()`
- 절대 import 방식 채택 (상대 import 이슈 해결)
- 캐릭터별 폴더 분리: data.py, dialogues.py, events.py
- 오브젝트 폴더 분리: containers.py, furniture.py, grounds.py
- 상세 문서: [ARCHITECTURE.md](scenarios/scenario03/ARCHITECTURE.md)

---

## 남은 작업

### Phase 5: 확장 기능 (기본)

1. **플래그 영속성 (세이브/로드)**
   - [ ] `events.py`: `export_flags()`, `import_flags()` 함수
   - [ ] `ScriptSystem`: 세이브/로드 연동
   - [ ] `flags_data.json` 파일 생성/로드

2. **캐릭터 데이터 수정 API**
   - [ ] morld 모듈: `set_unit_tag`, `add_unit_tag`
   - [ ] morld 모듈: `add_mood`, `remove_mood`

---

## 참고: 플래그 세이브/로드 설계

### Python 측

```python
def export_flags():
    """세이브용 JSON 문자열 반환"""
    return json.dumps({
        "flags": _flags,
        "triggered_events": list(_triggered_events)
    }, ensure_ascii=False)

def import_flags(json_str):
    """로드용 JSON 파싱"""
    global _flags, _triggered_events
    if not json_str:
        _flags = {}
        _triggered_events = set()
        return

    data = json.loads(json_str)
    _flags = data.get("flags", {})
    _triggered_events = set(data.get("triggered_events", []))
```

### C# 측

```csharp
// 세이브 시
public void SaveGame(string path)
{
    var flagsJson = _scriptSystem?.CallFunctionString("events", "export_flags");
    // flagsJson을 세이브 파일에 포함
}

// 로드 시
public void LoadGame(string path)
{
    var flagsJson = // 세이브 파일에서 읽기
    _scriptSystem?.CallFunction("events", "import_flags", flagsJson);
}
```

---

## 참고: 캐릭터 데이터 수정 API 설계

### morld 모듈 확장

```csharp
// 유닛 태그(스탯) 수정
morldModule.ModuleDict["set_unit_tag"] = new PyBuiltinFunction("set_unit_tag", args =>
{
    int unitId = args[0].ToInt();
    string tagName = args[1].AsString();
    int value = args[2].ToInt();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        unit.TraversalContext.SetTag(tagName, value);
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 태그 증가/감소
morldModule.ModuleDict["add_unit_tag"] = new PyBuiltinFunction("add_unit_tag", args =>
{
    int unitId = args[0].ToInt();
    string tagName = args[1].AsString();
    int delta = args[2].ToInt();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        var current = unit.TraversalContext.GetTagValue(tagName);
        unit.TraversalContext.SetTag(tagName, current + delta);
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 무드 추가/제거
morldModule.ModuleDict["add_mood"] = new PyBuiltinFunction("add_mood", args =>
{
    int unitId = args[0].ToInt();
    string mood = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    unit?.Mood.Add(mood);
    return PyBool.FromBool(unit != null);
});

morldModule.ModuleDict["remove_mood"] = new PyBuiltinFunction("remove_mood", args =>
{
    int unitId = args[0].ToInt();
    string mood = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    return PyBool.FromBool(unit?.Mood.Remove(mood) ?? false);
});
```

### Python 사용 예시

```python
import morld

def on_reach_healing_spring():
    """치유의 샘 도착 이벤트"""
    player_id = morld.get_player_id()

    # HP 회복
    morld.add_unit_tag(player_id, "hp", 30)

    # 상태이상 제거
    morld.remove_mood(player_id, "독")
    morld.remove_mood(player_id, "피로")

    return {
        "type": "monologue",
        "pages": [
            "맑은 샘물이 흐르고 있다.",
            "물을 마시자 몸에 활력이 돌아온다.",
            "[HP가 30 회복되었다]"
        ],
        "time_consumed": 5,
        "button_type": "ok"
    }
```

---

## Phase 6: 고급 이벤트 시스템 (애정행각 시나리오)

### 개요

NPC 간 만남(on_meet) 시 동적으로 행동이 추가되고, 해당 행동 수행 중 시간이 흐르며, 제3자 도착 시 중단되는 복합 이벤트 시스템.

### 요구사항

1. **동적 액션 추가**: 남녀 NPC가 만나면 "애정행각" 액션이 동적으로 추가됨
2. **스케줄 중단**: 행동 수행 중 기존 스케줄 일시 중단
3. **시간 경과**: 행동 수행 중에도 게임 시간이 흐름
4. **제3자 인터럽트**: 같은 장소에 다른 유닛 도착 시 행동 중단
5. **우선순위 스케줄**: 수면 시간 등 중요 스케줄이 오면 행동 강제 종료

### 설계

#### 1. 동적 액션 시스템

```python
# events.py

# 현재 활성 동적 액션 (유닛 ID → 액션 리스트)
_dynamic_actions = {}

def add_dynamic_action(unit_id, action):
    """유닛에 동적 액션 추가"""
    if unit_id not in _dynamic_actions:
        _dynamic_actions[unit_id] = []
    if action not in _dynamic_actions[unit_id]:
        _dynamic_actions[unit_id].append(action)

def remove_dynamic_action(unit_id, action):
    """유닛에서 동적 액션 제거"""
    if unit_id in _dynamic_actions:
        _dynamic_actions[unit_id] = [a for a in _dynamic_actions[unit_id] if a != action]

def get_dynamic_actions(unit_id):
    """유닛의 동적 액션 조회"""
    return _dynamic_actions.get(unit_id, [])
```

#### 2. morld API 확장

```csharp
// ScriptSystem.cs - morld 모듈 확장

// 유닛 액션 동적 추가
morldModule.ModuleDict["add_unit_action"] = new PyBuiltinFunction("add_unit_action", args =>
{
    int unitId = args[0].ToInt();
    string action = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null && !unit.Actions.Contains(action))
    {
        unit.Actions.Add(action);
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 액션 동적 제거
morldModule.ModuleDict["remove_unit_action"] = new PyBuiltinFunction("remove_unit_action", args =>
{
    int unitId = args[0].ToInt();
    string action = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    return PyBool.FromBool(unit?.Actions.Remove(action) ?? false);
});

// 스케줄 레이어 Push (Python에서 호출)
morldModule.ModuleDict["push_schedule"] = new PyBuiltinFunction("push_schedule", args =>
{
    int unitId = args[0].ToInt();
    string name = args[1].AsString();
    string? endType = args.Count > 2 ? args[2].AsString() : null;
    string? endParam = args.Count > 3 ? args[3].AsString() : null;

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        unit.PushSchedule(new ScheduleLayer
        {
            Name = name,
            Schedule = null,
            EndConditionType = endType,
            EndConditionParam = endParam
        });
        return PyBool.True;
    }
    return PyBool.False;
});

// 스케줄 레이어 Pop
morldModule.ModuleDict["pop_schedule"] = new PyBuiltinFunction("pop_schedule", args =>
{
    int unitId = args[0].ToInt();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null && unit.ScheduleStack.Count > 1)
    {
        unit.PopSchedule();
        return PyBool.True;
    }
    return PyBool.False;
});

// 같은 위치의 유닛 목록 조회
morldModule.ModuleDict["get_units_at_location"] = new PyBuiltinFunction("get_units_at_location", args =>
{
    int regionId = args[0].ToInt();
    int locationId = args[1].ToInt();

    var units = _unitSystem?.GetUnitsAtLocation(regionId, locationId);
    var pyList = new PyList();
    if (units != null)
    {
        foreach (var unit in units)
        {
            pyList.Append(PyInt.Create(unit.Id));
        }
    }
    return pyList;
});
```

#### 3. 이벤트 처리 흐름

```python
# events.py

def handle_npc_meet(unit_ids):
    """NPC끼리 만남 - 조건 체크 후 동적 액션 추가"""
    # 남녀 조합 체크
    male_ids = []
    female_ids = []

    for unit_id in unit_ids:
        unit_info = morld.get_unit_info(unit_id)
        if unit_info:
            unit_type = unit_info.get("type", "")
            if unit_type == "male":
                male_ids.append(unit_id)
            elif unit_type == "female":
                female_ids.append(unit_id)

    # 남녀가 모두 있으면 동적 액션 추가
    if male_ids and female_ids:
        for unit_id in male_ids + female_ids:
            add_dynamic_action(unit_id, "script:romance_action:애정행각")
            morld.add_unit_action(unit_id, "script:romance_action:애정행각")


def romance_action(context_unit_id):
    """애정행각 액션 시작"""
    unit_info = morld.get_unit_info(context_unit_id)
    if not unit_info:
        return None

    region_id = unit_info.get("region_id")
    location_id = unit_info.get("location_id")

    # 같은 위치의 이성 찾기
    partner_id = find_opposite_gender_at_location(context_unit_id, region_id, location_id)
    if partner_id is None:
        return {
            "type": "monologue",
            "pages": ["상대방이 없다."],
            "time_consumed": 0,
            "button_type": "ok"
        }

    # 두 유닛 모두 "애정행각" 스케줄 Push
    morld.push_schedule(context_unit_id, "애정행각", "interrupt", f"{region_id}:{location_id}")
    morld.push_schedule(partner_id, "애정행각", "interrupt", f"{region_id}:{location_id}")

    # 플래그 설정
    set_flag(f"romance:{context_unit_id}:{partner_id}", True)

    return {
        "type": "monologue",
        "pages": [
            "둘은 서로를 바라본다...",
            "(시간이 흐른다...)"
        ],
        "time_consumed": 60,  # 1시간 소요
        "button_type": "ok"
    }


def handle_romance_interrupt(unit_id, intruder_id):
    """제3자 도착으로 애정행각 중단"""
    # 스케줄 Pop
    morld.pop_schedule(unit_id)

    # 파트너도 Pop
    partner_id = get_romance_partner(unit_id)
    if partner_id:
        morld.pop_schedule(partner_id)

    # 플래그 정리
    clear_romance_flags(unit_id)

    # 동적 액션 제거
    remove_dynamic_action(unit_id, "script:romance_action:애정행각")
    morld.remove_unit_action(unit_id, "script:romance_action:애정행각")

    if partner_id:
        remove_dynamic_action(partner_id, "script:romance_action:애정행각")
        morld.remove_unit_action(partner_id, "script:romance_action:애정행각")
```

#### 4. 인터럽트 종료 조건 타입

```csharp
// ScheduleLayer.cs - 새로운 종료 조건 타입 추가

// EndConditionType: "interrupt"
// EndConditionParam: "region_id:location_id"
// 의미: 해당 위치에 제3자가 도착하면 종료

public bool IsComplete(Unit unit, UnitSystem unitSystem)
{
    if (EndConditionType == "interrupt")
    {
        // 현재 위치에 다른 유닛이 도착했는지 체크
        var parts = EndConditionParam?.Split(':');
        if (parts?.Length == 2)
        {
            int regionId = int.Parse(parts[0]);
            int locationId = int.Parse(parts[1]);

            // 같은 위치의 유닛 수 체크 (2명 초과면 제3자 도착)
            var unitsAtLocation = unitSystem.GetUnitsAtLocation(regionId, locationId);
            if (unitsAtLocation.Count > 2)
            {
                return true;  // 인터럽트 발생
            }
        }
    }
    // ... 기존 조건들
}
```

#### 5. 우선순위 스케줄 처리

```python
# events.py

# 우선순위 스케줄 정의 (이 스케줄이 되면 현재 행동 강제 종료)
PRIORITY_SCHEDULES = ["수면", "식사"]

def check_priority_schedule(unit_id):
    """우선순위 스케줄 체크 - 해당 시간이 되면 현재 행동 중단"""
    unit_info = morld.get_unit_info(unit_id)
    if not unit_info:
        return False

    # 현재 스케줄 레이어가 우선순위 스케줄인지 체크
    # (BehaviorSystem에서 매 Step마다 호출)
    schedule_name = unit_info.get("schedule_name", "")

    # 하위 스케줄 레이어에 우선순위 스케줄이 있으면 현재 레이어 Pop
    # (구현: C# 측에서 스택 순회)

    return False
```

### 구현 순서

1. [ ] morld API 확장 (`add_unit_action`, `remove_unit_action`, `push_schedule`, `pop_schedule`, `get_units_at_location`)
2. [ ] 동적 액션 관리 Python 함수 (`add_dynamic_action`, `remove_dynamic_action`, `get_dynamic_actions`)
3. [ ] "interrupt" 종료 조건 타입 구현
4. [ ] `handle_npc_meet` 남녀 조합 체크 로직
5. [ ] `romance_action` 애정행각 액션 구현
6. [ ] `handle_romance_interrupt` 인터럽트 처리
7. [ ] 우선순위 스케줄 체크 로직
8. [ ] 테스트 시나리오 작성
