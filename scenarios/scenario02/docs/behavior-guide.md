# NPC 행동 제어 가이드

캐릭터 유형별 행동 시스템 구조와 제어 방법을 설명합니다.
향후 캐릭터 행동을 수정하거나 새 캐릭터를 추가할 때 참고하세요.

---

## 목차

1. [캐릭터 유형 분류](#1-캐릭터-유형-분류)
2. [일반 캐릭터 (BaseAgent)](#2-일반-캐릭터-baseagent)
3. [크리처 (CreatureAgent)](#3-크리처-creatureagent)
4. [특수 캐릭터 — 상인 페이 (FayeAgent)](#4-특수-캐릭터--상인-페이-fayeagent)
5. [공통 규칙: _action_taken 패턴](#5-공통-규칙-_action_taken-패턴)
6. [활동 핸들러 Phase 패턴](#6-활동-핸들러-phase-패턴)
7. [새 캐릭터 유형 추가 시 고려사항](#7-새-캐릭터-유형-추가-시-고려사항)

---

## 1. 캐릭터 유형 분류

| 유형 | Agent 클래스 | UnitType | think() | survival/needs | 스케줄 | 소멸 |
|------|------------|----------|---------|---------------|--------|------|
| 일반 캐릭터 | `BaseAgent` | Character | 5-tier 우선순위 | O | 시간대별 복합 활동 | 영구 |
| 크리처 | `CreatureAgent` | Creature | 7-tier 단순화 | X | 순찰/휴식/수면/복귀 | 수명 기반 |
| 특수 캐릭터 | 커스텀 Agent | Character | 완전 커스텀 | X (선택) | 커스텀 로직 | 영구 |

### 파일 위치

| 구분 | 경로 |
|------|------|
| BaseAgent | `think/__init__.py` |
| CreatureAgent | `think/creature_agent.py` |
| 활동 핸들러 | `think/activities/` |
| 인터럽트 핸들러 | `think/handlers/` |
| 캐릭터 정의 | `assets/characters/*.py` |
| 몬스터 정의 | `assets/characters/monster.py` |
| 스포너 | `spawner.py` |

---

## 2. 일반 캐릭터 (BaseAgent)

세라, 밀라, 리나, 엘라, 유키 등 모든 거주 NPC가 사용하는 Agent.

### 2.1 think() 5-tier 우선순위

```
FSM 스택 디스패치: 최상위 State.update() → True이면 하위 차단
  - GateTransitState(lv=30): cross-location 이동 중 think 차단
  - CombatState: 전투 중 think 차단
  - LifeState(lv=0): 항상 False → 아래 5-tier 진행

Tier -1: 운반 중 (Limbo 대기)
Tier  0: 결박 (행동불능이면 탈출 시도 없이 대기)
Tier  1 (Involuntary): 기절 / 탈진 / 수면 (추위 기상: 체온 <= 35.0 → tier 3)
Tier  2 (Reactive): 피격 반응 / 간호 / 구출
Tier  3 (Survival): 배고픔 → 추위 → 더위
Tier  4 (Comfort): 착의 → 배변 → 피로 → 성욕 → 목욕 → 세탁 → 출산 → 모성 → 사회 → 선물 → 수면
Tier  5 (Routine): 스케줄 기반 일반 활동
```

각 tier는 **상위 tier가 행동을 결정하면 하위 tier를 건너뜁니다**.
예: 배고픔(tier 3)이 발동하면 스케줄(tier 5)은 실행되지 않습니다.

### 2.2 스케줄 시스템

NPC 일과는 캐릭터 파일의 `SCHEDULE` 또는 `SCHEDULES` dict에 정의됩니다.

```python
SCHEDULE = [
    {"name": "아침식사", "start": 420*_M, "end": 480*_M,
     "region_id": 0, "location_id": 3, "x": 90, "activity": "식사"},
    {"name": "물자점검", "start": 540*_M, "end": 570*_M,
     "activity": "점검", "region_id": 0, "location_id": 16, "x": 90},
    {"name": "오전활동", "start": 570*_M, "end": 720*_M,
     "activity": "취미낚시"},  # location_id 생략 → 동적 탐색
]
```

- `location_id` 있으면 → 고정 위치 이동
- `location_id` 없으면 → `activity_resolver.resolve_activity_location()` 동적 탐색
- `dynamic: True` + `candidates` → 조건 기반 활동 선택 (동적 스케줄)

### 2.3 활동 핸들러 디스패치

Tier 5에서 `_check_tier5_routine()`이 현재 스케줄 entry의 `activity`를 확인하고
`ACTIVITY_HANDLERS` dict에서 핸들러를 찾아 호출합니다.

```python
# think/activities/__init__.py
ACTIVITY_HANDLERS = {
    "소등": handle_lights_off,  "점등": handle_lights_on,
    "벌목": handle_chop,        "낚시": handle_fish,
    "채집": handle_gather_store, "요리": handle_cook,
    "청소": handle_clean,       "물자수집": handle_scavenge,
    "정원": handle_garden,      "연료수집": handle_fuel,
    "난방 연료 수집": handle_branch_collect,
    "제작": handle_craft,       "연료장전": handle_fuel_load,
    "건축": handle_build,       "점검": handle_inspect,
    "취미낚시": handle_fish_hobby,
    "취미벌목": handle_chop_hobby,
    "취미채집": handle_gather_hobby,
}
```

핸들러가 없는 활동은 `_handle_default_activity()`로 처리됩니다.
순찰/산책은 `_WANDER_ACTIVITIES`에 등록되어 wandering 동작을 합니다.

### 2.4 동적 스케줄

```python
{"name": "아침준비", "start": 380*_M, "end": 420*_M,
 "dynamic": True, "candidates": [
     {"activity": "요리", "condition": "can_cook"},
     {"activity": "청소", "condition": "should_clean"},
     {"activity": "휴식", "condition": None},  # fallback
 ]}
```

조건 평가 (`_evaluate_condition`):

| 조건 | 의미 |
|------|------|
| `can_cook` | `food_ingredient` 컨테이너에 재료 >= 2 |
| `should_clean` | 거처 내 오염도 > 0인 방 존재 |
| `need_social` | 최대 그리움 >= 50 |
| `need_fuel` | 거처 내 열원에 연료 부족 |

> v0.2.4에서 `need_fish`, `need_logs` 등 자원 부족 조건은 **점검 활동**으로 대체됨.

### 2.5 점검 활동 (v0.2.4)

NPC가 보관소 위치를 방문 → 같은 세력 오브젝트의 `need:{item_uid}` prop 스캔 →
`_responsibility` 확률로 수집 결정 → 수집 → trigger 오브젝트에 반납.

| NPC 속성 | 설명 |
|----------|------|
| `_responsibility` | 수집 확률 (0.0~1.0, 기본 0.7) |
| `_collectible_items` | 수집 가능 item_uid 집합 (None=제한 없음) |

### 2.6 취미 활동 (v0.2.4)

기존 도구/자원 활동의 `mode="hobby"` 변형. 수확물을 **인벤토리에 보관** (보관소 반납 안 함).

```python
# 예: 취미낚시
_FISH_HOBBY_CONFIG = {**_FISH_CONFIG, "mode": "hobby"}
def handle_fish_hobby(agent, entry):
    handle_tool_activity(agent, entry, _FISH_HOBBY_CONFIG)
```

### 2.7 인터럽트 핸들러

Tier 3~4의 욕구/생존 인터럽트는 `think/handlers/` 패키지에 모듈화:

| 모듈 | 핸들러 |
|------|--------|
| `eat.py` | `_handle_eat`, `_handle_excretion` |
| `thermal.py` | `_handle_cold`, `_handle_hot`, `_handle_clothing` |
| `self_comfort.py` | `_handle_self_comfort`, `_handle_seek_player` |
| `social.py` | `_handle_socialize`, `_handle_gift` |
| `laundry.py` | `_handle_laundry` |

인터럽트는 `_memory` dict에 phase를 저장하여 다단계 행동을 관리합니다.
활동 변경 시 리셋되는 `_activity_state`와 달리, `_memory`는 유지됩니다.

### 2.8 등록 과정

```python
# think/agents/sera_agent.py  (캐릭터 표준 ③ — U4b에서 캐릭터 파일과 분리)
@register_agent_class("sera")
class SeraAgent(BaseAgent):
    owner_unique_id = "sera"
    _responsibility = 0.9
    _collectible_items = {"food_fish", "log", "wood_chip"}
    SCHEDULE = [...]
```

1. `Character` 서브클래스 정의 (`assets/characters/{이름}.py` — Asset 데이터)
2. `BaseAgent` 서브클래스 정의 (`think/agents/{이름}_agent.py` — AI 행동)
3. `@register_agent_class` 데코레이터로 자동 등록 (`think/agents/__init__.py`가 import)
4. `chapters/chapter_N.py`에서 `instantiate()` 호출 시 Agent 자동 생성

---

## 3. 크리처 (CreatureAgent)

늑대, 박쥐, 거미 등 야생 생물용 Agent. BaseAgent를 상속하되 대폭 단순화.

### 3.1 NPC와의 핵심 차이

| 항목 | NPC (BaseAgent) | 크리처 (CreatureAgent) |
|------|----------------|---------------------|
| survival 등록 | O (포만감/기절) | X (HP는 전투로만 관리) |
| needs 등록 | O (5개 욕구) | X |
| 전투 감지 | 세력 적대 + 관계 적대 | 동일 |
| 세력 | "주민" (기본) | 종별 ("늑대"/"거미"/"박쥐") |
| home region | `bed_owner` prop 기반 | `전투:홈리전` prop |
| 스케줄 | 시간대별 복합 활동 | 순찰/휴식/수면/복귀 |
| 소멸 | 영구 | 수명 기반 자연 소멸 |

### 3.2 think() 7-tier 흐름

```
Tier 0: 운반 중        → idle 60s
Tier 1: 사망           → idle 1h (spawner 디스폰 대기)
Tier 2: 기절           → idle (잔여 시간)
Tier 3: 전투 위협      → _check_combat_threat()
Tier 3.5: 겁탈 기회    → bestiality ON + 유성 + 무력화 대상
Tier 3.6: 성추행 기회  → harassment ON + 유성 + 무력화 대상
Tier 3.7: 기생 기회    → is_parasitic + 무력화 대상
Tier 4: 스케줄         → 순찰/휴식/수면/복귀
Safety net: 할 일 없음 → idle 60s
```

### 3.3 스케줄 활동

CreatureAgent의 스케줄은 4가지 활동만 지원:

| 활동 | 처리 |
|------|------|
| 순찰 | `_do_wander(entry)` — home_region 내 랜덤 이동 + 10~30분 휴식 |
| 휴식 | `_insert_idle_job("휴식", remaining_ms)` — 제자리 대기 |
| 수면 | `_insert_idle_job("수면", remaining_ms)` — lair에서 대기 |
| 복귀 | `_do_return_to_lair(entry)` — spawn location으로 이동 |

예시 (늑대 스케줄):
```
00:00-05:00  수면 (늑대굴)
05:00-12:00  순찰 (숲 내 배회)
12:00-15:00  휴식
15:00-21:00  순찰
21:00-23:00  복귀 (늑대굴로)
23:00-24:00  수면
```

### 3.4 스포너 (Spawner) 시스템

크리처는 스포너가 생성/소멸을 관리합니다.

```python
register_spawn_source(
    source_id="forest_wolves",
    monster_class=Wolf,
    max_count=2,
    interval_hours=6,
    region_id=3, location_id=4,
    lifespan_hours=72,
)
```

**라이프사이클:**
```
register_spawn_source() → 매 1시간 체크
  ├─ 사망/수명만료 정리
  ├─ 조건 충족 시 새 생물 스폰
  └─ 시체 4h 후 디스폰
```

### 3.5 세력 시스템

`전투:세력` prop 기반 적대/중립/우호 판별:

| 세력 | 종류 |
|------|------|
| 주민 | NPC 기본 |
| 늑대/거미/박쥐/야생/유적/기생 | 크리처 종별 |
| 행상 | 상인 페이 (중립) |

동일 세력 = 우호, `FACTION_RELATIONS` 테이블에 정의된 관계 적용.

### 3.6 등록 과정

1. `Monster` 서브클래스 정의 (`assets/characters/monster.py`)
2. `chapters/chapter_N.py`에서 `spawner.register_spawn_source()` 호출
3. 스포너가 `CreatureAgent` 자동 생성 + 스케줄 할당

---

## 4. 특수 캐릭터 — 상인 페이 (FayeAgent)

떠돌이 상인 페이는 BaseAgent를 상속하되 **think()를 완전히 재정의**합니다.

### 4.1 핵심 특징

| 항목 | 값 |
|------|---|
| Agent | `FayeAgent(BaseAgent)` |
| UnitType | Character (크리처 아님) |
| survival/needs | **미등록** (포만감/욕구 없음) |
| 세력 | "행상" (독립 중립) |
| 스케줄 | 커스텀 로직 (요일+시간 기반 텔레포트) |
| 거래 시스템 | 구매/판매/재구매 UI |

### 4.2 스케줄 로직

일반 NPC의 `SCHEDULE` 배열 대신 **모듈 레벨 함수**로 스케줄을 관리:

```
월/화/수 08:00~20:00 → 도시 입구 (R2, L0)
목/금   08:00~20:00 → 숲 오두막 (R3, L5)
야간 / 토/일        → 대기소 (Region 10) — 사라짐
```

### 4.3 think() 흐름

```python
def think(self):
    schedule = _get_active_schedule(time_info)

    # 비활성 시간 (야간/주말) → 텔레포트로 사라짐
    if schedule is None:
        _teleport_to_limbo(self.unit_id, my_loc)
        self._insert_idle_job("대기", 60분)
        return

    # 날짜 변경 → 거래 아이템 리셋 + HP 회복
    if current_day != self._last_trade_day:
        _reset_trade_items(self.unit_id, keep_item_ids=buyback)
        self._last_trade_day = current_day

    # 위치 다르면 즉시 텔레포트 (출근)
    if not at_target:
        morld.set_unit_location(unit_id, target_region, target_location)

    # 영업 대기 (30분 idle)
    self._insert_idle_job("영업", 30분)
```

**일반 NPC와의 핵심 차이:**
- **5-tier 우선순위 없음** — 배고픔/추위/욕구 인터럽트 전혀 없음
- **이동 시스템 미사용** — `_move_to()` 대신 `set_unit_location()` 텔레포트
- **스케줄 시스템 미사용** — `SCHEDULE` 배열 없이 직접 시간 판정
- **거래 시스템 전용** — `buy_items()`, `sell_items()`, `buyback_items()` 구현

### 4.4 거래 시스템

| 기능 | 설명 |
|------|------|
| 구매 | `TRADE_STOCK` 목록에서 아이템 판매 |
| 판매 | 플레이어 아이템을 정가 50%에 매입 |
| 재구매 | 매입한 아이템을 다시 판매 (정가 50%) |
| 일일 리셋 | 매일 아침 거래 아이템 + HP 복원 |
| buyback 한도 | 일반 10개, 퀘스트 아이템은 영구 보관 |

### 4.5 새 특수 캐릭터 추가 시 참고

페이 패턴을 참고하여 특수 캐릭터를 만들 때:

1. `BaseAgent`를 상속하되 `think()`를 완전히 재정의
2. `__init__`에서 `survival.register_npc()` / `needs.register_character()` 호출 안 함
3. 커스텀 스케줄 로직 구현 (텔레포트, 조건부 등장 등)
4. `@register_agent_class` 데코레이터로 등록
5. **반드시 모든 think() 경로에서 job 삽입** (`_action_taken` 규칙 준수)

---

## 5. 공통 규칙: _action_taken 패턴

**모든 Agent 유형에 적용되는 가장 중요한 규칙입니다.**

### 5.1 핵심 원칙

```
모든 think() 호출은 반드시 job을 삽입해야 합니다 (duration > 0).
job 삽입 후 _action_taken = True를 설정해야 합니다.
```

이 규칙을 어기면:
- DES 루프가 무한 반복 (step = 0)
- Safety net이 WARNING 출력 + "할 일 없음" 삽입

### 5.2 올바른 패턴

```python
# 이동 → _move_to는 내부에서 job 삽입 + action_taken 설정
agent._move_to(target, "설명")

# 대기 → _insert_idle_job + action_taken 수동 설정
agent._insert_idle_job("이름", 밀리초)
agent._action_taken = True

# 고정 시간 행동 → _do_instant_action이 한 번에 처리
agent._do_instant_action("이름", "duration_key")
# 내부적으로: _insert_idle_job + _action_taken = True
```

### 5.3 Phase 전환 시 주의사항 (v0.2.4 Fix)

**idle → 다른 phase 전환 시 반드시 `_do_instant_action` 호출 필요:**

```python
# BAD: phase 전환만 하고 action 없음 → _action_taken = False
agent._activity_phase = "going_to_storage"
# → 다음 think()에서 이 phase가 실행되지 않을 수 있음

# GOOD: phase 전환 + instant action
agent._activity_phase = "going_to_storage"
agent._do_instant_action("연료장전", "brief")  # 1분 대기 + action_taken
```

이유: `_check_tier5_routine()`의 while 루프에서:
- **dynamic entry**: `_action_taken=False` → `_skip_dynamic_activity()` → 다음 candidate로 넘어감
- **non-dynamic entry**: `_action_taken=False` → 잔여 시간 전체를 "할 일 없음"으로 채움

### 5.4 handler 복귀 패턴

| 상황 | 올바른 패턴 |
|------|------------|
| 할 일 없으면 대기 | `_insert_idle_job("이름", remaining)` + `_action_taken = True` |
| 할 일 없으면 폴백 | `return` (디스패치 루프가 자동 처리) |
| 이동 | `_move_to(target, "설명")` |
| 고정 행동 | `_do_instant_action("이름", "key")` |
| dynamic 건너뛰기 | `_skip_dynamic_activity(entry)` + `return` |

---

## 6. 활동 핸들러 Phase 패턴

### 6.1 기본 구조

```python
def handle_X(agent, entry):
    phase = agent._activity_phase

    if phase == "idle":
        # 탐색 → 다음 phase 전환
        target = find_target(agent)
        if not target:
            return  # 폴백
        agent._activity_state["target"] = target
        agent._activity_phase = "going"
        agent._do_instant_action("활동명", "brief")  # 필수!

    elif phase == "going":
        target = agent._activity_state.get("target")
        if agent._is_at(target):
            do_work()
            agent._activity_phase = "idle"
            agent._do_instant_action("작업명", "action_key")
        else:
            agent._move_to(target, "이동 설명")
```

### 6.2 공통 핸들러 (재사용 가능)

| 핸들러 | 파일 | Phase 흐름 | 용도 |
|--------|------|-----------|------|
| `handle_tool_activity` | `tool_activity.py` | idle→getting_tool→going_to_work→storing→returning_tool | 도구 기반 활동 |
| `handle_resource_activity` | `resource_activity.py` | idle→going_to_work→storing | 자원 수집 활동 |
| `phase_getting_tool` | `tool_activity.py` | 도구 획득 공용 phase | import하여 사용 |
| `phase_returning_tool` | `tool_activity.py` | 도구 반납 공용 phase | import하여 사용 |
| `phase_storing` | `tool_activity.py` | 보관소 저장 공용 phase | import하여 사용 |

### 6.3 새 활동 추가 체크리스트

1. `think/activities/`에 핸들러 모듈 생성
2. `think/activities/__init__.py`에 등록
3. NPC 스케줄에 `"activity": "활동명"` 추가
4. **모든 phase 전환에 `_do_instant_action` 확인**
5. (선택) 동적 스케줄 조건 추가
6. (선택) 도구 필요 시 getting_tool/returning_tool phase 추가

> 상세 가이드: [make_activity.md](make_activity.md)

---

## 7. 새 캐릭터 유형 추가 시 고려사항

### 7.1 유형 선택 기준

| 조건 | 추천 유형 |
|------|----------|
| 거주 NPC, 욕구/일과 필요 | BaseAgent 상속 |
| 야생 생물, 단순 AI, 스폰/소멸 | CreatureAgent 사용 |
| 독자적 동작 패턴 (상인, 여행자 등) | BaseAgent 상속 + think() 재정의 |

### 7.2 BaseAgent 상속 시

```python
class MyAgent(BaseAgent):
    def __init__(self, unit_id):
        super().__init__(unit_id)
        # survival.register_npc() — 호출하면 포만감 추적
        # needs.register_character() — 호출하면 5개 욕구 추적
        # 호출 안 하면 해당 시스템 비활성

    # think()를 재정의하지 않으면 기본 5-tier 동작
    # 재정의하면 완전 커스텀 (페이 패턴)
```

### 7.3 시나리오03 호환성

- 새 prop은 없어도 동작하도록 설계 (`getattr(agent, 'attr', default)`)
- `_responsibility` 없는 NPC → `getattr(agent, '_responsibility', 0.7)` 기본값
- `_collectible_items` 없는 NPC → `None` → 제한 없음
- C# 변경 없이 Python만으로 새 유형 추가 가능

---

## 참고 문서

| 문서 | 내용 |
|------|------|
| [schedule.md](schedule.md) | 스케줄/Job 시스템, DES, Phase 시스템 상세 |
| [life.md](life.md) | 욕구 시스템, 인터럽트, 시설 탐색 |
| [make_activity.md](make_activity.md) | 활동 핸들러 제작 가이드 |
| [make_character.md](make_character.md) | 캐릭터 Asset + Agent 정의 가이드 |
| [creature.md](creature.md) | 크리처 시스템 전체 (세력/스포너/AI/겁탈/기생) |
| [party-design-notes.md](party-design-notes.md) | 파티 시스템 (FSM 스택 + 분대 지시) |
