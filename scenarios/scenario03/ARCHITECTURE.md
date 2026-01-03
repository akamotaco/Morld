# Scenario03 Python 아키텍처

## 개요

scenario03은 JSON 파일 대신 **Python 스크립트로 게임 데이터를 정의**하는 방식을 사용합니다.
`morld` 모듈 API를 통해 C# 게임 시스템에 직접 데이터를 등록합니다.

## 핵심 차이점

| 구분 | scenario01/02 (JSON) | scenario03 (Python) |
|------|---------------------|---------------------|
| 데이터 정의 | `data/*.json` 파일 | `python/*.py` 모듈 |
| 데이터 로드 | C#에서 JSON 파싱 | Python에서 morld API 호출 |
| 초기화 감지 | `__init__.py` 없음 | `python/__init__.py` 존재 |
| 이벤트 처리 | C# EventSystem | Python events.py |

## 폴더 구조

```
scenario03/
├── python/
│   ├── __init__.py          # 패키지 진입점 (initialize_scenario)
│   ├── world.py              # 지역/위치 데이터 + initialize_world()
│   ├── items.py              # 아이템 데이터 + initialize_items()
│   ├── events.py             # 메인 이벤트 핸들러 (on_event_list)
│   │
│   ├── characters/           # 캐릭터 모듈
│   │   ├── __init__.py       # initialize_characters(), CHARACTER_EVENTS
│   │   ├── player/
│   │   │   ├── data.py       # CHARACTER_DATA 딕셔너리
│   │   │   └── events.py     # on_game_start, job_select 등
│   │   ├── cheolsu/
│   │   │   ├── data.py
│   │   │   ├── dialogues.py  # activity별 대화
│   │   │   └── events.py     # on_meet_player, npc_talk
│   │   ├── younghee/
│   │   └── minsu/
│   │
│   └── objects/              # 오브젝트 모듈
│       ├── __init__.py       # initialize_objects()
│       ├── containers.py     # CONTAINERS 리스트
│       ├── furniture.py      # FURNITURE 리스트 + mirror_look
│       └── grounds.py        # 바닥 오브젝트 자동 생성
│
└── ARCHITECTURE.md           # 이 파일
```

## 초기화 흐름

```
GameEngine._Ready()
    │
    ├── RegisterAllSystems()
    │       └── ScriptSystem 등록 + SetScenarioPath()
    │
    └── LoadDataFromPython()  (IsPythonDataSource() == true)
            │
            ├── SetDataSystemReferences()  # morld.add_unit 등 API 등록
            │
            ├── CallInitializeScenario()
            │       │
            │       ├── import world → world.initialize_world()
            │       ├── import items → items.initialize_items()
            │       ├── from characters import initialize_characters()
            │       └── from objects import initialize_objects()
            │
            └── LoadScenarioPackage()
                    └── from events import * (on_event_list 등록)
```

## morld 모듈 API

Python에서 사용 가능한 C# 연동 API:

### 데이터 등록 (초기화 시)
```python
morld.add_region(id, name, appearance)
morld.add_location(region_id, id, name, appearance)
morld.add_edge(region_id, location_a, location_b, travel_time)
morld.set_time(year, month, day, hour, minute)
morld.add_item(id, name, passive_tags, equip_tags, value, actions)
morld.add_unit(id, name, region_id, location_id, type, actions, appearance, mood)
morld.set_unit_tags(unit_id, tags_dict)
morld.push_schedule(unit_id, name, end_type, end_param, schedule_entries)
morld.add_inventory(unit_id, item_id, count)
morld.set_inventory_visible(unit_id, visible)
```

### 런타임 조회/조작
```python
morld.get_player_id()           # 플레이어 유닛 ID
morld.get_unit_info(unit_id)    # 유닛 정보 딕셔너리
morld.give_item(unit_id, item_id, count)  # 아이템 지급
```

## Import 규칙

**절대 import 사용** (상대 import 사용 금지)

```python
# 올바른 예
from characters.cheolsu.data import CHARACTER_ID
from objects.furniture import mirror_look

# 잘못된 예 (패키지 컨텍스트 없이 로드되면 실패)
from .data import CHARACTER_ID
from ..world import REGIONS
```

이유: sharpPy에서 모듈을 로드할 때 패키지 컨텍스트 없이 단독 모듈로 로드되므로,
상대 import (`from .xxx`)는 "no known parent package" 에러 발생.

## 이벤트 처리

### C# → Python 호출 흐름
```
EventSystem.FlushEvents()
    │
    └── ScriptSystem.CallEventHandler(events)
            │
            └── on_event_list([["game_start"], ["on_reach", 0, 0, 1], ...])
                    │
                    └── 이벤트별 핸들러 호출 → 모놀로그 결과 반환
```

### 이벤트 결과 포맷
```python
{
    "type": "monologue",
    "pages": ["첫 번째 페이지", "두 번째 페이지"],
    "time_consumed": 5,
    "button_type": "ok"  # "ok", "none", "yesno", "none_on_last"
}
```

## 캐릭터 데이터 구조

```python
# characters/cheolsu/data.py
CHARACTER_ID = 1
CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "철수",
    "type": "male",
    "regionId": 0,
    "locationId": 0,
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "평범한 청년이다.",
        "식사": "맛있게 음식을 먹고 있다."
    },
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "아침식사", "regionId": 0, "locationId": 1,
                 "start": 420, "end": 480, "activity": "식사"}
            ]
        }
    ]
}
```

## NPC 대화 시스템

`script:npc_talk` 액션으로 대화 시작:

1. `events.py`의 `npc_talk(context_unit_id)` 호출
2. `get_character_event_handler(unit_id)`로 캐릭터별 핸들러 조회
3. 해당 캐릭터의 `events.py`에서 `npc_talk()` 호출
4. `dialogues.py`에서 activity 기반 대사 조회

```python
# characters/cheolsu/dialogues.py
DIALOGUES = {
    "default": {"pages": ["안녕, 나는 철수야."]},
    "식사": {"pages": ["(음식을 먹고 있다)", "지금은 식사 중이야."]},
}

def get_dialogue(activity):
    return DIALOGUES.get(activity) or DIALOGUES["default"]
```
