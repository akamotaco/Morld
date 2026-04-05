# Pi-World Engine 설계

## 개요

Pi-World Engine은 Morld의 1D 시뮬레이션 게임을 위한 공통 Python 엔진 레이어.
시나리오 02/03/04 및 향후 시나리오가 동일한 엔진 위에서 동작한다.

```
┌──────────────────────────────────────────────────────┐
│  C# Core (Godot)                                      │
│  ECS, Region/Location/Gate, DES, TextUI, SharpPy     │
└──────────────┬───────────────────────────────────────┘
               │ morld API
┌──────────────▼───────────────────────────────────────┐
│  Pi-World Engine (Python)                             │
│  환경 · 생존 · 행동 · 렌더링 · 이벤트               │
└──────────────┬───────────────────────────────────────┘
               │ import
┌──────────────▼───────────────────────────────────────┐
│  Scenario Content (Python)                            │
│  캐릭터 · 지형 · 스토리 · 퀘스트 · NPC AI           │
└──────────────────────────────────────────────────────┘
```

## 의존성 규칙

```
Engine → morld API (C#)
Engine → Engine (내부 의존 허용)
Engine ✗→ Scenario Content (금지)

Scenario → Engine (자유)
Scenario → morld API (자유)
Scenario → 다른 Scenario (금지)
```

**엔진 모듈은 시나리오 콘텐츠를 절대 import하지 않는다.**
시나리오가 엔진을 import하고, 등록(register) 패턴으로 데이터를 주입한다.

---

## 디렉토리 구조

```
scenarios/common/python/
├── engine/                    ← Pi-World Engine
│   ├── __init__.py
│   │
│   ├── # === 환경 시스템 ===
│   ├── temperature.py         # 위치 온도 + 캐릭터 체온
│   ├── humidity.py            # 날씨/습도/젖음
│   ├── pollution.py           # 오염 전파
│   ├── congestion.py          # 혼잡도 (인구/수용력)
│   ├── lighting.py            # 밝기 레벨
│   ├── sound.py               # 소리 전파
│   ├── fuel.py                # 열원 연료 소비
│   │
│   ├── # === 생존 시스템 ===
│   ├── survival.py            # HP/포만감/기절
│   ├── needs.py               # 욕구 (배변/피로/청결)
│   ├── equipment.py           # 장비 슬롯 관리
│   ├── gender.py              # 성별 속성
│   │
│   ├── # === 행동 시스템 ===
│   ├── stealth.py             # 은신/탐지
│   ├── carry.py               # 운반 (Limbo + 포인터)
│   ├── build.py               # 건축/파괴
│   ├── ground.py              # 바닥 아이템
│   ├── spawner.py             # 유닛 스폰
│   ├── combat.py              # 전투 코어 (판정/데미지)
│   ├── party.py               # 파티/분대 관리
│   ├── reputation.py          # 평판/세력
│   │
│   ├── # === 콘텐츠 시스템 ===
│   ├── garden.py              # 텃밭/농업
│   ├── laundry.py             # 세탁
│   ├── crafting.py            # 제작 UI
│   ├── crafting_recipes.py    # 제작 레시피 레지스트리
│   ├── vehicle.py             # 차량
│   │
│   ├── # === 이벤트 시스템 ===
│   ├── event_core.py          # subscribe_time_elapsed + 이벤트 디스패치
│   │
│   ├── # === 에셋 프레임워크 ===
│   ├── asset_base.py          # Asset/Unit/Character/Object/Item/Location 기본 클래스
│   ├── asset_registry.py      # ID 레지스트리
│   │
│   ├── # === 로맨스 엔진 (선택적) ===
│   ├── romance/
│   │   ├── __init__.py
│   │   ├── core.py            # 상태 머신
│   │   ├── actions.py         # 행동 정의
│   │   ├── mode.py            # 모드 전환
│   │   ├── ui.py              # 로맨스 UI
│   │   ├── stimulation.py     # 감각 추적
│   │   └── ...
│   │
│   └── # === 던전 엔진 (선택적) ===
│       └── dungeon/
│           ├── generator.py   # BSP 던전 생성
│           ├── builder.py     # morld Region/Location 변환
│           ├── manager.py     # 던전 라이프사이클
│           ├── fog.py         # 전장의 안개
│           └── scheduler.py   # 던전 이벤트 스케줄
│
├── # === 렌더링 유틸 (기존) ===
├── text_utils.py              # 한글 폭 계산
├── grid_renderer.py           # GridBuffer, 선 그리기
├── grid_viewport.py           # 뷰포트 상태/줌/스크롤
├── map_coords.py              # 2D 좌표 자동 배치
├── region_map.py              # 범용 지도 렌더러
└── ui_style.py                # 색상/스타일 상수
```

---

## 시나리오별 확장 패턴

### Scenario 02: 생존 시뮬레이션 (숲속 저택)

```
scenario02/python/
├── __init__.py                # 부트스트랩
├── chapters/                  # 챕터 0 (프롤로그), 챕터 1 (본편)
├── world/                     # 6개 Region 정의 (저택/도시/숲/광산/유적)
├── assets/
│   ├── characters/            # 리나, 세라, 밀라, 유키, 엘라
│   ├── items/                 # 장비, 음식, 도구, 소모품
│   └── locations/             # 25+ Location 정의
├── events/                    # on_meet/on_reach 핸들러, 스토리 이벤트
├── think/                     # NPC AI (BaseAgent, 5-tier 인터럽트)
├── quest/                     # 퀘스트 정의
├── tone_templates/            # NPC 대사 아키타입
├── ui.py                      # S02 전용 UI (자세/은신/환경 표시)
├── story.py                   # 스토리 분기 (신뢰/굴복 루트)
└── pregnancy.py               # 임신/출산 시스템
```

**엔진 사용**: 전 모듈 사용 + 로맨스 엔진 + 던전 엔진

### Scenario 03: Mind The Gap (CRPG)

```
scenario03/python/
├── __init__.py
├── chapters/
├── world/
├── assets/
├── events/
├── ui.py                      # S03 전용 UI
└── squad.py                   # 분대 시스템 (party.py 확장)
```

**엔진 사용**: 핵심 모듈만 (survival, build, combat, party)
**미사용**: 로맨스, 던전, garden, laundry

### Scenario 04: 마을과 던전 (JRPG 파티 전투)

```
scenario04/python/
├── __init__.py
├── chapters/
├── assets/
├── events/
├── ui.py                      # S04 전용 UI (침식/신뢰/사기)
├── erosion.py                 # 침식 시스템 (S04 전용)
├── morale.py                  # 사기 시스템 (S04 전용)
├── trust.py                   # 신뢰도 시스템 (S04 전용)
├── quirk.py                   # 기벽 시스템 (S04 전용)
├── corrosion.py               # 부식 시스템 (S04 전용)
├── encounter.py               # 대결 시스템 (S04 전용, combat.py 확장)
├── npc_generator.py           # 랜덤 NPC 생성
├── village_map.py             # 마을 지도 래퍼
├── village_schedule.py        # 마을 NPC 스케줄
└── world_knowledge.py         # 세계의 지식 / 혼란도
```

**엔진 사용**: 환경 + 생존 + 행동 + 던전
**미사용**: 로맨스 (향후 확장 가능), garden, laundry
**S04 전용**: erosion, morale, trust, quirk, corrosion, encounter

---

## 엔진 모듈 설계 원칙

### 1. 선택적 속성 (Optional Props)

새로운 prop은 없어도 동작하도록 설계. 없으면 기본값(최적 상태).

```python
# GOOD: prop이 없으면 기본값
def get_durability(item_id):
    durability = morld.get_unit_prop(item_id, "durability")
    if durability is None:
        return 1.0
    return durability
```

### 2. 등록 패턴 (Register Pattern)

시나리오가 엔진에 데이터를 주입. 엔진은 시나리오를 모른다.

```python
# engine/survival.py
_characters = set()
def register_character(unit_id):
    _characters.add(unit_id)

# scenario02/chapters/chapter_1.py
import survival
survival.register_character(player_id)
survival.register_character(npc_id)
```

### 3. Lazy Init (지연 초기화)

Region/Location 데이터는 게임 시작 후에만 접근 가능. `_ensure_initialized()` 패턴.

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

엔진 모듈은 `event_core.subscribe_time_elapsed()`로 시간 이벤트 수신.
시나리오의 events.py가 event_core를 래핑.

```python
# engine/event_core.py
_subscribers = []
def subscribe_time_elapsed(callback, min_interval=None):
    _subscribers.append((callback, min_interval, 0))

def dispatch_time_elapsed(millis):
    for i, (cb, interval, acc) in enumerate(_subscribers):
        ...

# scenario02/events/__init__.py
from engine.event_core import subscribe_time_elapsed  # re-export
```

### 5. 챕터 전환 리셋 (Reset)

모든 엔진 모듈은 `reset()` 함수를 제공. 챕터 전환 시 호출.

```python
def reset():
    global _initialized
    _initialized = False
    _registry.clear()
```

---

## 마이그레이션 전략

### Phase 1: event_core 분리 (핵심)

`subscribe_time_elapsed`를 engine/event_core.py로 추출.
S02/S04의 events/__init__.py가 re-export.

### Phase 2: 환경 시스템 이동

temperature, humidity, pollution, congestion, lighting, sound, fuel
→ 모두 `morld` + `event_core` + `region_registry`에만 의존
→ `region_registry`도 engine으로 이동 (또는 lazy init 패턴)

### Phase 3: 생존 시스템 이동

survival, needs, equipment, gender
→ `morld` + `event_core`에만 의존

### Phase 4: 행동 시스템 이동

stealth, carry, build, ground, spawner, combat, party, reputation

### Phase 5: 콘텐츠 시스템 이동 (선택적)

garden, laundry, crafting, vehicle — 사용하는 시나리오만 import

### Phase 6: 로맨스/던전 엔진 이동 (선택적)

romance/, instant_dungeon/ — 대규모 서브시스템, 별도 패키지로 관리

---

## 새 시나리오 만들기

### 최소 구성 (신규 시나리오)

```python
# scenarios/scenario_new/python/__init__.py

# 1. 엔진 임포트
from engine import event_core, survival, temperature, humidity, needs

# 2. 에셋 정의
import assets.characters
import assets.items

# 3. 이벤트 연결
from engine.event_core import subscribe_time_elapsed
import events

# 4. 챕터 로드
from chapters import load_chapter
```

### 엔진 모듈 선택 가이드

| 시나리오 유형 | 필수 엔진 | 선택 엔진 |
|-------------|----------|----------|
| 텍스트 어드벤처 | survival, event_core | lighting, stealth |
| 생존 시뮬레이션 | survival, needs, temperature, humidity, pollution | garden, crafting, fuel |
| JRPG 던전 탐험 | survival, combat, party, dungeon | stealth, spawner |
| 연애 시뮬레이션 | survival, needs, romance | garden, crafting |
| 도시 경영 | survival, congestion, reputation | build, crafting, vehicle |

---

## 기존 코드 호환성

### import 경로 호환

엔진 이동 후에도 기존 `import survival`이 동작하도록,
시나리오 디렉토리에 래퍼 파일을 둔다:

```python
# scenarios/scenario02/python/survival.py (래퍼)
from engine.survival import *
```

또는 sys.path에 engine/ 경로를 추가하여 직접 import.

### S02/S03 무중단 마이그레이션

1. engine/에 복사 (S02에서 가져옴)
2. S02의 원본을 래퍼로 교체
3. S02 테스트 통과 확인
4. S04에서 engine/ 직접 import
5. S04 스텁 삭제

각 단계에서 S02가 정상 동작함을 확인한 후 다음 단계 진행.
