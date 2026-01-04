# Scenario02: 숲속 저택 - 설계 문서

## 개요

기억을 잃은 플레이어가 숲속 저택에서 생활하며 NPC들과 교류하는 시나리오.
NPC 스케줄 시스템과 AI 기반 자율 행동이 핵심.

---

## 설계 원칙

### 에셋 자급자족 정책

**캐릭터/오브젝트/아이템은 하나의 파일로 구성하여 추가/삭제하는 것만으로도 에셋으로 인식 가능해야 한다.**

```python
# 캐릭터 파일 하나 = 완전한 에셋
# assets/characters/lina.py

from assets import registry
from think import BaseAgent, register_agent_class

# 1. AI Agent (데코레이터로 자동 등록)
@register_agent_class("lina")
class LinaAgent(BaseAgent):
    def think(self):
        ...

# 2. Presence Text (캐릭터 존재감 묘사)
PRESENCE_TEXT = {
    "activity:채집": "{name}가 채집 준비를 하고 있다.",
    "default": "{name}가 밝은 표정으로 주변을 둘러본다."
}

# 3. 캐릭터 데이터 정의
LINA = {
    "unique_id": "lina",
    "name": "리나",
    ...
}

# 4. Asset 등록
def register():
    registry.register_character(LINA)

# 5. 이벤트 핸들러
class events:
    @staticmethod
    def on_meet_player(player_id):
        ...

    @staticmethod
    def npc_talk(context_unit_id):
        ...
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
│   ├── assets/               # Asset 정의 (템플릿)
│   │   ├── __init__.py       # AssetRegistry + load_all_assets()
│   │   │
│   │   ├── items/            # 아이템 Asset
│   │   │   ├── __init__.py
│   │   │   ├── resources.py  # 자원류 (밀가루, 쌀, 물 등)
│   │   │   └── tools.py      # 도구류 (칼, 주머니 등)
│   │   │
│   │   ├── objects/          # 오브젝트 Asset
│   │   │   ├── __init__.py
│   │   │   ├── furniture.py  # 가구류
│   │   │   └── outdoor.py    # 야외 오브젝트
│   │   │
│   │   └── characters/       # 캐릭터 Asset (★ 자급자족 구조)
│   │       ├── __init__.py   # get_character_event_handler()
│   │       ├── player.py     # 플레이어 정의
│   │       ├── lina.py       # 리나 (채집 담당) + Agent + Events
│   │       ├── sera.py       # 세라 (사냥 담당) + Agent + Events
│   │       ├── mila.py       # 밀라 (요리 담당) + Agent + Events
│   │       ├── yuki.py       # 유키 (청소 담당) + Agent + Events
│   │       └── ella.py       # 엘라 (관리자) + Agent + Events
│   │
│   ├── world/                # 지형 + 인스턴스화 (Region별)
│   │   ├── __init__.py       # initialize_terrain(), instantiate_all()
│   │   └── mansion.py        # 저택 Region (지형 + 배치)
│   │
│   ├── think/                # NPC AI 시스템
│   │   └── __init__.py       # BaseAgent, @register_agent_class
│   │
│   └── events/               # 이벤트 핸들러
│       ├── __init__.py       # on_event_list export
│       ├── handlers.py       # 이벤트 라우팅 + 스크립트 등록
│       ├── game_events.py    # 게임 시작/챕터 관리
│       ├── player_creation.py # 캐릭터 생성 흐름
│       └── location_events.py # 위치 도착 이벤트
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

### Think 시스템 흐름

```
1. ThinkSystem.Proc() (C#)
   └─> Python think.think_all() 호출

2. think_all() (Python)
   └─> 각 Agent의 think() 호출
       └─> 스케줄 확인, 경로 계산, set_route() 호출

3. MovementSystem.Proc() (C#)
   └─> PlannedRoute 기반으로 이동 실행
```

### Agent 구현 패턴

```python
@register_agent_class("lina")
class LinaAgent(BaseAgent):
    def think(self):
        # 1. 스케줄 확인
        entry = self.get_schedule_entry()
        if entry is None:
            return None

        # 2. 현재 위치 확인
        loc = self.get_location()
        if loc[0] == entry["region_id"] and loc[1] == entry["location_id"]:
            return None  # 이미 목적지

        # 3. 경로 계산 및 설정
        path = self.find_path(entry["region_id"], entry["location_id"])
        if path:
            self.set_route(path)

        return path
```

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
├── game_events.py      # 게임 시작, 챕터 관리
├── player_creation.py  # 이름/나이/체격/장비 선택
└── location_events.py  # 위치 도착 이벤트 (앞마당 쓰러짐 등)
```

---

## 확장 포인트

### 새 캐릭터 추가

1. `assets/characters/newchar.py` 파일 생성
2. 파일 내 필수 요소:
   - `@register_agent_class("newchar")` 데코레이터가 붙은 Agent 클래스
   - `NEWCHAR` 데이터 딕셔너리
   - `register()` 함수
   - `events` 클래스 (on_meet_player, npc_talk 등)
3. `world/mansion.py`의 `NPC_SPAWNS`에 배치 정보 추가

### 새 아이템 추가

1. `assets/items/`에 정의 추가
2. `world/mansion.py`의 `ITEMS`에 배치

### 새 이벤트 추가

1. 관련 이벤트 파일에 함수 추가 (`game_events.py`, `location_events.py` 등)
2. `handlers.py`에서 라우팅 추가

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
