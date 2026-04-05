# Pi-World Engine 설계

## 개요

Pi-World Engine은 Morld의 1D 시뮬레이션 게임을 위한 공통 Python 엔진 레이어.
시나리오 02/03/04 및 향후 시나리오가 동일한 엔진 위에서 동작한다.

```
┌──────────────────────────────────────────────────────┐
│  C# Core (Godot + SharpPy)                            │
│  ECS, Region/Location/Gate, DES, TextUI               │
└──────────────┬───────────────────────────────────────┘
               │ morld API
┌──────────────▼───────────────────────────────────────┐
│  Pi-World Engine (Python)                             │
│  환경 · 생존 · 행동 · 에셋 · 이벤트 · 렌더링        │
└──────────────┬───────────────────────────────────────┘
               │ import + 상속
┌──────────────▼───────────────────────────────────────┐
│  Scenario Content (Python)                            │
│  캐릭터 · 지형 · 스토리 · 퀘스트 · NPC AI           │
└──────────────────────────────────────────────────────┘
```

---

## 의존성 규칙

```
Engine → morld API (C#)       허용
Engine → Engine (내부 의존)    허용
Engine ✗→ Scenario Content     금지

Scenario → Engine              자유
Scenario → morld API           자유
Scenario → 다른 Scenario       금지
```

**엔진 모듈은 시나리오 콘텐츠를 절대 import하지 않는다.**
시나리오가 엔진을 import하고, 상속(inherit) 또는 등록(register) 패턴으로 콘텐츠를 주입한다.

---

## 디렉토리 구조 (현재 구현)

```
scenarios/common/python/
├── engine/                         ← Pi-World Engine
│   ├── __init__.py
│   │
│   ├── # ── 이벤트 ──
│   ├── event_core.py               # subscribe_time_elapsed + dispatch
│   │
│   ├── # ── 환경 시스템 ──
│   ├── temperature.py              # 위치 온도 + 캐릭터 체온
│   ├── humidity.py                 # 날씨/습도/젖음
│   ├── pollution.py                # 오염 전파
│   ├── congestion.py               # 혼잡도 (인구/수용력)
│   ├── lighting.py                 # 밝기 레벨
│   ├── sound.py                    # 소리 전파
│   ├── fuel.py                     # 열원 연료 소비
│   │
│   ├── # ── 생존 시스템 ──
│   ├── survival.py                 # HP/포만감/기절
│   ├── needs.py                    # 욕구 (배변/피로/청결)
│   ├── equipment.py                # 장비 슬롯 관리
│   ├── gender.py                   # 성별 속성
│   │
│   ├── # ── 행동 시스템 ──
│   ├── stealth.py                  # 은신/탐지
│   ├── carry.py                    # 운반 (Limbo + 포인터)
│   ├── build.py                    # 건축/파괴
│   ├── ground.py                   # 바닥 아이템
│   ├── spawner.py                  # 유닛 스폰
│   ├── combat.py                   # 전투 코어
│   ├── party_squad.py              # 분대(Squad) — 다중 스쿼드, 명령/지시, FSM 연동
│   ├── party_group.py              # 파티(Group) — 단일 파티, 공유 소비, 콜백 확장
│   ├── reputation.py               # 평판/세력
│   ├── garden.py                   # 텃밭/농업
│   ├── laundry.py                  # 세탁
│   ├── region_registry.py          # Region ID 동적 탐색
│   │
│   ├── # ── UI 프레임워크 ──
│   ├── ui_base.py                  # 공통 UI (상태/탭/대화/유틸)
│   │
│   ├── # ── 에셋 프레임워크 ──
│   ├── asset_base.py               # Asset/Unit/CharacterBase/ObjectBase/ItemBase/LocationBase
│   └── asset_registry.py           # ID 레지스트리, 클래스 등록 데코레이터
│
├── # ── 렌더링 유틸 ──
├── text_utils.py                   # 한글 폭 계산
├── grid_renderer.py                # GridBuffer, 선 그리기, MAP_FONT
├── grid_viewport.py                # 뷰포트 상태/줌/스크롤
├── map_coords.py                   # 2D 좌표 자동 배치 (Gate 그래프 기반)
├── region_map.py                   # 범용 지도 렌더러
├── ui_style.py                     # 색상/스타일 상수
└── lighting.py                     # engine/lighting.py 래퍼 (하위 호환)
```

---

## 에셋 프레임워크 (Template Method 패턴)

엔진이 **프레임워크(골격)**를 제공하고, 시나리오가 **콘텐츠(살)**를 채운다.

### 상속 구조

```
engine/asset_base.py                    scenario/assets/base.py
┌─────────────────────┐                ┌──────────────────────────┐
│ Asset               │                │                          │
│ ├── Unit            │                │                          │
│ │   ├── CharacterBase ◄──────────── │ Character(CharacterBase) │
│ │   └── ObjectBase    ◄──────────── │ Object(ObjectBase)       │
│ ├── ItemBase          ◄──────────── │ Item(ItemBase)           │
│ └── LocationBase      ◄──────────── │ Location(LocationBase)   │
└─────────────────────┘                └──────────────────────────┘
```

### 엔진 베이스가 제공하는 것

| 클래스 | 엔진 제공 | 시나리오 제공 |
|--------|----------|-------------|
| **CharacterBase** | TextSelector, _build_context(), get_describe/focus_text(), talk() 골격, 이벤트 프레임워크, 데이터 슬롯(RULES, QUESTS) | romance(), give_gift(), 아키타입 빌더, 반응 데이터, 스토리 이벤트 |
| **ObjectBase** | 좌석/운반/컨테이너 메서드, 속성 정의 | instantiate(), 시나리오 고유 오브젝트 |
| **ItemBase** | 속성 정의 (passive/equip/action props) | instantiate(), 아이템 데이터 |
| **LocationBase** | get_describe_text(), 속성 정의 | instantiate(), add_ground/object, 장소 데이터 |

### 데이터 슬롯 (시나리오에서 채움)

```python
# engine/asset_base.py — 프레임워크
class CharacterBase(Unit):
    DESCRIBE_RULES = None    # 묘사 규칙 리스트
    FOCUS_RULES = None       # Focus 묘사 규칙
    TALK_RULES = None        # 대화 규칙 (list 또는 dict)
    TALK_TOPICS = None       # 대화 주제 리스트
    EVENT_DIALOGS = None     # 이벤트별 대화 dict
    CHARACTER_QUESTS = []    # 캐릭터 개인 퀘스트

# scenario02/assets/base.py — S02 콘텐츠
class Character(CharacterBase):
    ROMANCE_REACTIONS = None     # S02 전용
    GIFT_PREFERENCES = None      # S02 전용
    SEXUAL_PREFERENCES = None    # S02 전용
```

---

## 엔진 모듈 공통 인터페이스

모든 엔진 모듈은 다음 인터페이스를 **반드시** 제공한다.

### 필수: `reset()`

```python
def reset():
    """챕터 전환 시 모듈 상태 초기화"""
```

- 모든 내부 상태(`_registry`, `_accumulated`, `_initialized` 등)를 초기값으로 복원
- 상태가 없는 모듈(equipment, lighting)도 빈 `reset()` 제공 (인터페이스 통일)
- 시나리오의 `chapters/__init__.py`에서 `module.reset()` 호출을 보장

**왜 필수인가**: 시나리오가 엔진 모듈을 `import` 후 `reset()` 호출하는 것은 **보편적 계약**이다.
S02에서 호출하지 않더라도 S04에서 호출할 수 있고, 향후 시나리오도 마찬가지.
`reset()` 없으면 `AttributeError`로 초기화 실패 → 전체 시나리오 부팅 차단.

### 권장: `register_*()`

시나리오가 데이터를 주입하는 등록 함수. 모듈에 따라 이름이 다름:

```python
# survival.py
def register_character(unit_id): ...

# pollution.py
def register_location(region_id, loc_id, max, rate): ...

# spawner.py
def register_spawn_source(source_id, ...): ...
```

### 권장: 시간 구독

시간 기반 업데이트가 필요한 모듈은 모듈 로드 시 자동 구독:

```python
from engine.event_core import subscribe_time_elapsed
subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)
```

### 인터페이스 체크리스트

새 엔진 모듈 추가 시:
- [ ] `reset()` 함수 있는가?
- [ ] `from engine.event_core import subscribe_time_elapsed` 사용하는가? (시간 의존 시)
- [ ] `from engine.region_registry import get_region_ids` 사용하는가? (region 순회 시)
- [ ] 시나리오 콘텐츠를 import하지 않는가?
- [ ] 내부 상태는 `_` prefix로 private인가?

---

## S02 래퍼 패턴

S02의 기존 모듈은 engine으로 이동 후 **sys.modules 교체 래퍼**로 대체:

```python
# scenarios/scenario02/python/temperature.py
import sys
from engine import temperature as _engine_module
sys.modules[__name__] = _engine_module
```

이 패턴으로 기존 `import temperature`가 engine/temperature.py를 반환.
SharpPy의 `LoadModuleFromFile()`이 실행 후 `sys.modules` 재조회하여 교체된 모듈 반환.

---

## 엔진 모듈 설계 원칙

### 1. 선택적 속성 (Optional Props)

prop이 없으면 기본값(최적 상태)으로 동작.

```python
def get_durability(item_id):
    durability = morld.get_unit_prop(item_id, "durability")
    return 1.0 if durability is None else durability
```

### 2. 등록 패턴 (Register Pattern)

시나리오가 엔진에 데이터를 주입. 엔진은 시나리오를 모른다.

```python
# engine/survival.py
_characters = set()
def register_character(unit_id):
    _characters.add(unit_id)

# scenario/chapters/chapter_1.py
from engine import survival
survival.register_character(player_id)
```

### 3. Lazy Init (지연 초기화)

Region/Location 데이터는 게임 시작 후에만 접근 가능.

```python
_initialized = False
def _ensure_initialized():
    global _initialized
    if _initialized:
        return
    # morld API로 데이터 수집
    _initialized = True
```

### 4. 시간 구독 (Time Subscription)

엔진 모듈은 `engine.event_core.subscribe_time_elapsed()`로 시간 이벤트 수신.
시나리오의 `events/__init__.py`가 `event_core.dispatch_time_elapsed()`를 호출.

```python
# engine/temperature.py
from engine.event_core import subscribe_time_elapsed
subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)

# scenario/events/__init__.py
from engine.event_core import subscribe_time_elapsed  # re-export
def _handle_time_elapsed(millis):
    from engine.event_core import dispatch_time_elapsed
    dispatch_time_elapsed(millis)
```

### 5. 챕터 전환 리셋 (Reset)

모든 엔진 모듈은 `reset()` 함수를 제공.

```python
def reset():
    global _initialized
    _initialized = False
    _registry.clear()
```

---

## 시나리오별 확장

### Scenario 02: 생존 시뮬레이션 (숲속 저택)

**엔진 사용**: 전 모듈
**S02 전용**: romance, pregnancy, story.py, 아키타입 빌더, NPC AI (think/)

```
scenario02/python/
├── assets/base.py          # Character(CharacterBase) — 로맨스/아키타입 확장
├── think/                  # NPC AI (5-tier 인터럽트)
├── romance*.py             # 연애 시스템 (향후 engine으로 이동 가능)
├── story.py                # 스토리 분기
├── quest/                  # 퀘스트 정의
└── ui.py                   # S02 전용 UI
```

### Scenario 04: 마을과 던전 (JRPG 파티 전투)

**엔진 사용**: 환경 + 생존 + 행동
**S04 전용**: erosion, morale, trust, quirk, corrosion, encounter, dungeon

```
scenario04/python/
├── assets/base.py          # Character(CharacterBase) — 4스탯/클래스 확장
├── erosion.py              # 침식 시스템
├── encounter.py            # 대결 시스템
├── dungeon.py              # 던전 시스템
├── morale.py, trust.py     # 사기/신뢰
├── village_map.py          # 마을 지도 (region_map 래퍼)
└── ui.py                   # S04 전용 UI
```

---

## 새 시나리오 만들기

### 최소 구성

```python
# scenarios/scenario_new/python/__init__.py

# 1. 엔진 모듈 import (필요한 것만)
from engine import event_core, survival, temperature

# 2. 에셋 정의
import assets.characters
import assets.items

# 3. 이벤트 시스템
from engine.event_core import subscribe_time_elapsed
from events import on_single_event, collect_event_handlers

# 4. 챕터 로드
from chapters import load_chapter
```

### 에셋 정의

```python
# scenarios/scenario_new/python/assets/base.py
from engine.asset_base import CharacterBase, ObjectBase, ItemBase, LocationBase

class Character(CharacterBase):
    """이 시나리오의 캐릭터"""
    # 시나리오 고유 속성/메서드 추가
    pass

class Object(ObjectBase):
    pass

class Item(ItemBase):
    pass

class Location(LocationBase):
    pass
```

### 엔진 모듈 선택 가이드

| 시나리오 유형 | 필수 엔진 | 선택 엔진 |
|-------------|----------|----------|
| 텍스트 어드벤처 | event_core, survival | lighting, stealth |
| 생존 시뮬레이션 | event_core, survival, needs, temperature, humidity | garden, fuel, build |
| JRPG 던전 탐험 | event_core, survival, combat, party_group | stealth, spawner |
| CRPG 분대 운용 | event_core, survival, combat, party_squad | stealth, spawner |
| 연애 시뮬레이션 | event_core, survival, needs | (romance 엔진) |
| 도시 경영 | event_core, survival, congestion, reputation | build, garden |

---

## 엔진 모듈 일람

| 분류 | 모듈 | 역할 | 의존성 |
|------|------|------|--------|
| **이벤트** | event_core | 시간 구독/배포 | morld |
| **환경** | temperature | 위치 온도 + 체온 | event_core, region_registry |
| | humidity | 날씨/습도/젖음 | event_core, region_registry |
| | pollution | 오염 전파 | event_core |
| | congestion | 혼잡도 | event_core, region_registry |
| | lighting | 밝기 레벨 | morld |
| | sound | 소리 전파 | region_registry |
| | fuel | 열원 연료 | event_core |
| **생존** | survival | HP/포만감/기절 | event_core, ui_style |
| | needs | 욕구 (배변/피로/청결) | event_core |
| | equipment | 장비 슬롯 | morld |
| | gender | 성별 속성 | morld |
| **행동** | stealth | 은신/탐지 | lighting |
| | carry | 운반 | morld |
| | build | 건축/파괴 | map_coords, asset_registry |
| | ground | 바닥 아이템 | morld |
| | spawner | 유닛 스폰 | event_core |
| | combat | 전투 코어 | event_core |
| | party_squad | 분대(다중, 명령/지시) | morld |
| | party_group | 파티(단일, 콜백 확장) | morld |
| | reputation | 평판/세력 | morld |
| | garden | 텃밭/농업 | morld |
| | laundry | 세탁 | event_core |
| | region_registry | Region ID 탐색 | morld |
| **UI** | ui_base | 공통 UI 프레임워크 | morld, ui_style |
| **에셋** | asset_base | 에셋 클래스 계층 | morld |
| | asset_registry | ID 레지스트리 | morld |
