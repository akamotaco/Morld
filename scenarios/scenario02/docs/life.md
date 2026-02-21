# NPC 생활 시스템 (Life System)

> **v0.2.2에서 욕구 수치화 시스템 구현 완료.**
>
> **구현된 항목:**
> - 동적 Activity 탐색 → `activity_resolver.py` (채집/사냥/순찰/벌목/낚시/독서/물자수집)
> - 도구 기반 Activity → 벌목 도끼, 낚시대, 빗자루 가져오기/반납
> - Activity 결과물 → 채집→저장, 낚시→저장, 벌목→저장, 요리, 청소(오염도 감소), 물자수집
> - NPC 만복도 시스템 → `survival.py` (register_npc, is_npc_hungry, npc_eat)
> - 배고픔 인터럽트 → think()에서 스케줄보다 우선 처리
> - 추위/더위 인터럽트 → 방한/방수 의류 자동 착탈 (v0.2.2)
> - 동적 스케줄 → 조건 기반 활동 선택 (`dynamic: True`, `candidates`)
> - 자원 순환 → 채집→저장→요리→식사 파이프라인
> - 컨테이너 헬퍼 → `npc_store_item`, `npc_take_item`, `get_item_count`
> - **Prop 기반 보관 기준치** → `need:{item_uid}` prop으로 컨테이너별 부족 기준 커스터마이징 (v0.2.2)
> - **난방 연료 수집** → `need_fuel_material` 조건, `storage:material` 컨테이너에 나뭇가지/통나무 비축 (v0.2.2)
> - 텃밭 활동 → 정원 7-phase (idle/getting_tool/going_to_garden/working/working_wait/storing_harvest/returning_tool)
> - 시설 탐색 리졸버 → `facility_resolver.py` (목욕/화장실 선착순 + 옷장 소유권 탐색) (v0.2.2)
> - **욕구 수치화** → `needs.py` (배변/피로/청결/사회/성욕) 매시간 추적 (v0.2.2)
> - **배변 인터럽트** → `resolve_toilet()` 동적 탐색 + 화장실 이동 (v0.2.2)
> - **피로 인터럽트** → 비스케줄 수면 자동 시작 (v0.2.2)
> - **청결 인터럽트** → 비스케줄 목욕 자동 시작 (v0.2.2)
>
> **미구현 항목:** NPC 주도 상호작용
>
> 현재 구현 상태는 [schedule.md#8](schedule.md#8-v021-phase-시스템) 참조.
> 활동 핸들러 제작 가이드: [make_activity.md](make_activity.md)

## 개요

NPC가 자연스러운 생활 패턴을 보이도록 하는 자율 행동 시스템입니다.
단순한 스케줄 기반 이동을 넘어서, 욕구와 상황에 따라 동적으로 행동을 결정합니다.

**핵심 목표:**
- 하드코딩된 location_id 대신 Activity 기반 동적 탐색
- 욕구(식욕, 배변욕, 수면욕) 기반 긴급 행동
- 소유물 인식 및 도구 사용
- NPC 주도 상호작용

---

## 시스템 계층

```
┌─────────────────────────────────────────────────────────────┐
│ NPC 생활 시스템 (Life System)                                │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 욕구 시스템  │  │ Activity    │  │ 소유물      │         │
│  │ (Needs)     │  │ 탐색        │  │ 관리        │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│                 ┌─────────────────┐                         │
│                 │ Agent.think()   │                         │
│                 └────────┬────────┘                         │
│                          ▼                                  │
│                 ┌─────────────────┐                         │
│                 │ JobList         │ ← schedule.md           │
│                 └─────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

### 행동 시간 시스템

고정 시간 행동은 `think/activities/helpers.py`의 **ACTION_DURATION** 테이블에 중앙 관리됩니다.
활동 핸들러에서는 `agent._do_instant_action("이름", "duration_key")`로 통일하여 DES job 삽입 + `_action_taken` 설정을 한 번에 처리합니다.
캐릭터별 `_action_duration_overrides` dict로 NPC별 행동 시간 오버라이드가 가능합니다.

> 상세: [make_activity.md#행동-시간-시스템-action_duration](make_activity.md#행동-시간-시스템-action_duration)

---

## 1. 동적 Activity 탐색 — 구현됨 (v0.2.1)

> `activity_resolver.py`에서 7종 구현. 아래 설계와 다른 점:
> - `Location.activities` 속성 없이, resolver 함수가 직접 오브젝트 탐색
> - `terrain.find_activity()` 대신 `resolve_activity_location(unit_id, activity, region_id)` 사용
> - 수면은 C# `resolve_sleep_target` API 사용
>
> **구현된 resolver:** 채집, 사냥, 순찰, 벌목, 낚시, 독서, 물자수집
>
> **순찰/산책 wandering** (v0.2.2): 순찰/산책 활동은 도착 후 제자리 대기가 아닌 실제로 근처를 돌아다닙니다.
> `_WANDER_ACTIVITIES = frozenset({"순찰", "산책"})` — `_do_wander()`로 랜덤 location 선택 → 이동 → 10~30분 휴식 → 반복.
> target이 없는 경우에도 wandering. 그 외 활동에서 target=None이면 현재 위치에서 대기.

### 현재 문제

```python
# 현재: location_id 하드코딩
SCHEDULE = [
    {"activity": "낚시", "location_id": 23, ...}  # 23번이 뭔지 알아야 함
]
```

### 목표

```python
# 목표: Activity만 지정, 위치는 동적 탐색
SCHEDULE = [
    {"activity": "낚시", ...}  # 위치 없음
]

def think(self):
    activity = self.get_current_activity()
    location = terrain.find_activity(self.unit_id, activity)
    self.move_to(location)
```

### Location Activity 속성

```python
class Location:
    # 이 장소에서 가능한 활동들
    activities: list[str] = []

    # 활동별 용량 (선택적)
    activity_capacity: dict = {}  # {"낚시": 2, "채집": 5}

class RiverBank(Location):
    unique_id = "river_bank"
    name = "강가"
    activities = ["낚시", "세탁", "물긷기", "수영"]
    activity_capacity = {"낚시": 3}  # 동시에 3명까지 낚시 가능

class Bedroom(Location):
    unique_id = "sera_room"
    name = "세라의 방"
    owner = "sera"
    activities = ["수면", "휴식", "옷갈아입기"]

class Toilet(Location):
    unique_id = "mansion_toilet"
    name = "화장실"
    activities = ["배변", "세면", "목욕"]
    activity_capacity = {"배변": 1, "목욕": 1}  # 1명씩만
```

### terrain.find_activity() API

```python
def find_activity(unit_id, activity, **options):
    """
    Activity를 수행할 수 있는 최적의 Location 탐색

    Args:
        unit_id: NPC ID
        activity: 활동 이름 ("낚시", "수면", "배변" 등)
        **options:
            prefer_owned: 소유 장소 우선 (기본: True)
            max_distance: 최대 거리 제한
            check_capacity: 용량 체크 (기본: True)

    Returns:
        LocationRef 또는 None
    """
    unit_loc = morld.get_unit_location(unit_id)
    unit_info = morld.get_unit_info(unit_id)
    owner_id = unit_info.get("unique_id")

    candidates = []

    for location in get_all_locations():
        if activity not in location.activities:
            continue

        # 용량 체크
        if options.get("check_capacity", True):
            if not _has_capacity(location, activity):
                continue

        # 거리 계산
        distance = calculate_distance(unit_loc, location)

        # 점수 계산
        score = -distance  # 가까울수록 좋음

        # 소유 장소 보너스
        if options.get("prefer_owned", True):
            if location.owner == owner_id:
                score += 1000  # 큰 보너스

        candidates.append((location, score))

    if not candidates:
        return None

    # 최고 점수 Location 반환
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]
```

### 특수 Activity 탐색

```python
# 수면: 자기 소유 방 우선, 없으면 공용 공간
def find_sleep_location(unit_id):
    # 1순위: 자기 방
    owned = find_activity(unit_id, "수면", prefer_owned=True)
    if owned and owned.owner == get_unique_id(unit_id):
        return owned

    # 2순위: 공용 침실
    shared = find_activity(unit_id, "수면", prefer_owned=False)
    if shared:
        return shared

    # 3순위: 아무 실내 (노숙 방지)
    return find_any_indoor(unit_id)

# 배변: 화장실 우선, 없으면 야외
def find_toilet_location(unit_id):
    # 1순위: 화장실
    toilet = find_activity(unit_id, "배변")
    if toilet:
        return toilet

    # 2순위: 야외 (수풀 등)
    outdoor = find_activity(unit_id, "야외배변")
    return outdoor
```

---

## 2. 욕구 시스템 (Needs System) — 구현됨 (v0.2.2)

> `needs.py` — 순수 Python, subscribe_time_elapsed 1시간 간격.
> 플레이어 자동 추적, NPC는 `register_character(unit_id)`.

### 욕구 타입

| 욕구 | Prop | 범위 | 시간당 증가 | 해소 | NPC 임계치 |
|------|------|------|------------|------|-----------|
| 배변 | `욕구:배변` | 0-100 | 식사 시 `max(5, 포만감/2)` | 화장실 → 0 | 70 |
| 피로 | `욕구:피로` | 0-100 | +4/h (각성 중) | 수면 중 -12/h | 80 |
| 청결 | `욕구:청결` | 0-100 | +1 + 오염×0.1 + 젖음×0.05 | 목욕 → 0 | 70 |
| 그리움 | `그리움:{name}` | 0-100 | 호감 기반 (대상별) | 대화/만남 시 해소 | 70 (찾아감) |
| 성욕 | `상태:성욕` | 0-100 | +0.5/h (동적 cap) | 절정 → 0 | — |

### 매시간 업데이트

```python
def _process_hourly(unit_id):
    # 피로: 수면 중이면 감소, 아니면 증가
    if _is_sleeping(unit_id):
        reduce_fatigue(unit_id, FATIGUE_SLEEP_RECOVERY)  # -12/h
    else:
        add_fatigue(unit_id, FATIGUE_RATE)  # +4/h

    # 청결: 오염 + 젖음 기반 증가
    cleanliness_increase = (1 + pollution × 0.1 + wetness × 0.05)

    # 그리움: 호감 30+ 대상별 축적/감소 (대상과 떨어져 있으면 증가)
    _update_longing(unit_id)

    # 성욕: 자연 증가 (욕망 기반 동적 상한)
    arousal_cap = _get_arousal_cap(unit_id)  # min(100, 50 + max_desire * 0.5)
    if current < arousal_cap:
        arousal += 0.5

    # 절정 상시 관리 (성인용품 삽입물/착용형)
    _update_climax(unit_id)  # 삽입물 효과 - 자연감소(3/h), ≥100 → 비로맨스 절정

    # 약물 타이머 (배란유도제, 정력제)
    # 매시간 남은시간 -1, 소진 시 상태 해제
```

> 절정 상시 관리 + 성인용품 상세: [adult-toys.md](adult-toys.md) 참조

### 연동 시스템

| 이벤트 | 호출 | 효과 |
|--------|------|------|
| 식사 | `survival.add_satiety()` | `needs.add_excretion(max(5, amount//2))` |
| 화장실 | `Toilet.use()` / NPC `_handle_excretion()` | `needs.set_excretion(0)` |
| 목욕 | `_handle_bath()` 도착 시 | `needs.set_cleanliness(0)` |
| 수면 중 | `needs._on_time_elapsed()` | `needs.reduce_fatigue(12)` |

### NPC 인터럽트 (Tier 4)

```
4a. 착의 (_check_clothing): 상의/하의 미착용 → _handle_clothing()
4b. 배변 (_check_excretion): 욕구:배변 ≥ 70 → _handle_excretion()
4c. 피로 (_check_fatigue): 욕구:피로 ≥ 80 → _handle_sleep() (2시간 fallback)
4d. 성욕 (_check_arousal): 성욕 임계값 → _handle_self_comfort() (성인용품 자동 사용) / _handle_seek_player()
4e. 목욕 (스케줄 OR 청결): 욕구:청결 ≥ 70 → _handle_bath() (30분 fallback)
4e-2. 세탁 (_check_laundry): 착용 의류 오염 > 5 → _handle_laundry() (비차단 대기)
4f. 취침: 스케줄 수면 시간 → _handle_sleep()
```

### 배변 인터럽트 (`_check_excretion` → `_handle_excretion`)

**조건**: `욕구:배변 ≥ 70` + `resolve_toilet()` 성공 (화장실 탐색 가능)

**페이즈 흐름** (`_memory["excretion_phase"]`):
```
None → idle → going → using → None
```

| 페이즈 | 동작 |
|--------|------|
| `idle` | → `going` |
| `going` | `_memory["excretion_target"]` (동적 탐색 결과)로 이동 |
| `using` | `needs.set_excretion(0)` + 5분 대기 → 완료 |

화장실은 `resolve_toilet(agent)` (prop `action:toilet` 기반)으로 동적 탐색.
`_memory["excretion_target"]`에 캐시, 완료 시 자동 정리.

### 비스케줄 fallback duration

| 인터럽트 | fallback | 비고 |
|----------|----------|------|
| 피로 수면 | 2시간 | `_is_sleep_time()` 반환값이 None일 때 |
| 청결 목욕 | 30분 | `_is_bath_time()` 반환값이 None일 때 |

### Python API

```python
import needs

# 등록 (NPC Agent.__init__에서)
needs.register_character(unit_id)

# 조회
needs.get_excretion(unit_id)     # → float
needs.get_fatigue(unit_id)       # → float
needs.get_cleanliness(unit_id)   # → float
needs.get_longing(unit_id, name)  # → float (대상별 그리움)
needs.get_max_longing(unit_id)    # → float (최대 그리움)

# 수정
needs.add_excretion(unit_id, amount)
needs.set_excretion(unit_id, 0)     # 화장실 사용 시
needs.set_cleanliness(unit_id, 0)   # 목욕 시
needs.reduce_fatigue(unit_id, amount)
needs.reduce_longing(unit_id, name) # 대화/만남 시 그리움 해소

# NPC 체크
needs.is_npc_need_excretion(unit_id)  # → bool (≥ 70)
needs.is_npc_need_sleep(unit_id)      # → bool (≥ 80)
needs.is_npc_need_bath(unit_id)       # → bool (≥ 70)

# 챕터 전환
needs.reset()
```

### UI 표시

Footer에 임계치 근처일 때만 표시:
```
체온 36.5℃ | 젖음 20% | 오염 15 | 배변 72 | 피로 45 | 불결 30
```
- 50 이상: 노란색
- 임계치 이상: 빨간색 (배변 70, 피로 80, 청결 70)

### 챕터 전환 대응

`reset()` 함수로 상태 초기화. `chapters/__init__.py`의 `load_chapter()`에서 자동 호출.

---

## 2-B. 추위/더위 인터럽트 — 구현됨 (v0.2.2)

> `think/__init__.py` — 배고픔 인터럽트와 같은 계층에서 동작

### think() 5-tier 우선순위

```
Tier -1: 운반 중 (Limbo 대기)
Tier  0: 결박 (행동불능이면 탈출 시도 없이 대기)
Tier  1 (Involuntary): 기절 / 탈진 / 수면 (추위 기상: 체온 ≤ 35.0 → tier 3으로 이관)
Tier  2 (Reactive): 피격 반응 (미래)
Tier  3 (Survival): 배고픔 → 추위 → 더위
Tier  4 (Comfort): 착의 → 배변 → 피로 → 성욕 → 목욕/청결 → 세탁 → 출산 → 모성 → 사회 → 선물 → 수면
Tier  5 (Routine): 스케줄 기반 일반 활동 (순찰/산책은 wandering)
```

> **결박 + 행동불능**: 결박(Tier 0)이 기절/탈진/수면(Tier 1)보다 우선이지만, 행동불능 상태(`is_npc_incapacitated()` 또는 수면)이면 결박 탈출 시도 없이 해당 상태 job만 삽입. 상태 해제 후 탈출 재개.

**Safety net**: 모든 tier를 통과했는데 `_action_taken=False`이면 WARNING 출력 (도달한 tier + 활성 phase 정보 포함) 후 "할 일 없음" job 삽입. 이는 알고리즘 약점을 식별하기 위한 진단 시스템입니다.

**추위 기상** (v0.2.2): 수면 중 체온이 위험 수준(≤ 35.0)이면 tier 1에서 수면을 중단하고 `return False` → `_ensure_standing()` → tier 3 cold 인터럽트로 방한 처리. 미세한 추위(35.0 < 체온 ≤ 35.5)에서는 수면 유지. 연료 소진으로 열원이 꺼지면 체온이 하락하여 기상 트리거.

### 추위 인터럽트 (`_check_cold` → `_handle_cold`)

**트리거 조건** (모두 충족):
1. 체온 ≤ 35.5 AND 보온 < 2, **OR** 비 + 젖음 > 30 + 방수 < 1
2. `resolve_wardrobe()` 성공 (옷장 접근 가능)
3. 1시간 쿨다운 경과 (`_memory["cold_last_attempt"]`)

**페이즈 흐름** (`_memory["cold_phase"]`):
```
None → idle → going → taking → equipping → None
```

| 페이즈 | 동작 |
|--------|------|
| `idle` | 인벤토리에 보온 아이템 있으면 → `equipping`, 없으면 → `going` |
| `going` | `resolve_wardrobe()` 결과 위치로 이동 (move job) |
| `taking` | 옷장에서 보온/방수 아이템 꺼내기 (`npc_take_item`) |
| `equipping` | 인벤토리의 보온/방수 아이템 장착 (`equipment.equip_item`) → 완료 |

### 더위 인터럽트 (`_check_hot` → `_handle_hot`)

**트리거 조건** (모두 충족):
1. 체온 ≥ 37.5
2. 보온 합계 > 0 (보온 의류 착용 중)
3. `resolve_wardrobe()` 성공

**페이즈 흐름** (`_memory["hot_phase"]`):
```
None → idle → unequipping → storing → None
```

| 페이즈 | 동작 |
|--------|------|
| `idle` | → `unequipping` |
| `unequipping` | 보온 아이템 벗기 (`equipment.unequip_item`), 이동 불필요 |
| `storing` | 옷장 location이면 옷장에 넣기, 아니면 인벤토리 보관 → 완료 |

### 옷장 탐색 (동적)

`resolve_wardrobe(agent)` — prop 기반 동적 탐색 (하드코딩 제거):
1. 소유 옷장: `wardrobe_owner:{owner_unique_id}` prop 매칭
2. 아무 옷장: `unique_id == "wardrobe"` (모브 fallback)
3. home_region 우선, `cross_region=True`일 때 다른 region도 탐색

옷장 소유권은 Location 파일에서 `wardrobe.wardrobe_owner = "sera"` 등으로 설정.
`Wardrobe.instantiate()`에서 `wardrobe_owner:{name}` prop 자동 추가.

### _memory 키

```python
self._memory = {
    "cold_phase": None,          # None/idle/going/taking/equipping
    "cold_last_attempt": None,   # 실패 시 쿨다운 타임스탬프
    "hot_phase": None,           # None/idle/unequipping/storing
    "clothing_phase": None,      # None/idle/going/taking/equipping
    "clothing_last_attempt": None,  # 실패 시 쿨다운 타임스탬프
    "excretion_phase": None,     # None/idle/going/using
    "excretion_target": None,    # resolve_toilet() 결과 캐시
    "laundry_phase": None,       # None/going_to_washer/loading/waiting_wash/collecting_wash/going_to_dryer/loading_dry/waiting_dry/collecting_dry
    "laundry_washer": None,      # resolve_washer() 결과 캐시
    "laundry_dryer": None,       # resolve_dryer() 결과 캐시
    "laundry_items": None,       # 세탁 중인 아이템 item_id 목록
    "laundry_cooldown": None,    # 세탁 완료 후 3시간 쿨다운
}
```

### 착의 인터럽트 (`_check_clothing` → `_handle_clothing`)

**트리거 조건** (모두 충족):
1. `착용:상의` 또는 `착용:하의` 슬롯 미착용 (나체/반나체)
2. `resolve_wardrobe()` 성공 (옷장 접근 가능)
3. `cold_phase`/`hot_phase` 비활성 (의류 핸들러 충돌 방지)
4. 1시간 쿨다운 경과 (`_memory["clothing_last_attempt"]`)

**페이즈 흐름** (`_memory["clothing_phase"]`):
```
None → idle → going → taking → equipping → None
```

| 페이즈 | 동작 |
|--------|------|
| `idle` | 인벤토리에 상의/하의 있으면 → `equipping`, 없으면 → `going` |
| `going` | `resolve_wardrobe()` 결과 위치로 이동 |
| `taking` | 옷장에서 부족 슬롯(상의/하의) 아이템 꺼내기 |
| `equipping` | 인벤토리의 상의/하의 장착 → 완료 |

**더위 충돌 방지**: 더울 때(`temperature.is_hot()`) 보온 아이템(`보온>0`)을 제외하고 착의. hot_handler가 벗긴 보온 아이템을 다시 입는 순환 방지.

---

## 2-D. 세탁 인터럽트 — 구현됨 (v0.2.2)

> `think/handlers/laundry.py` — 오염 의류 자동 감지 + 세탁/건조 + 비차단 대기

### 트리거 조건 (`_check_laundry`)

1. 장착 중인 의류 `오염:수치 > 5` (DIRTY_THRESHOLD)
2. `resolve_washer()` 성공 (idle 세탁기 존재)
3. 3시간 쿨다운 경과 (`_memory["laundry_cooldown"]`)

### 페이즈 흐름 (`_memory["laundry_phase"]`)

```
None → going_to_washer → loading → waiting_wash → collecting_wash
     → going_to_dryer → loading_dry → waiting_dry → collecting_dry → None
```

| 페이즈 | 동작 | 비차단 |
|--------|------|--------|
| `going_to_washer` | 세탁기로 이동 | |
| `loading` | 의류 벗기 + `npc_load_laundry` + `npc_start` | |
| `waiting_wash` | 세탁 중 대기 (60분) | **O** — `_check_laundry()` → False |
| `collecting_wash` | `npc_unload_laundry` → 건조기 탐색 | |
| `going_to_dryer` | 건조기로 이동 (없으면 skip) | |
| `loading_dry` | `npc_load_laundry` + `npc_start` | |
| `waiting_dry` | 건조 중 대기 (30분) | **O** — `_check_laundry()` → False |
| `collecting_dry` | `npc_unload_laundry` → 재장착 → 완료 | |

### 비차단 대기 (Non-blocking Wait)

`waiting_wash`/`waiting_dry` 페이즈에서 `_check_laundry()` → **False** 반환.
NPC는 다른 tier 인터럽트(배고픔, 스케줄 등)에 자유롭게 응답.
`laundry.get_machine_state() == 2` (완료) 감지 시 collecting 페이즈로 자동 전환.

### 건조기 없음 처리

건조기가 없으면 `collecting_wash`에서 바로 재장착 + 완료 (건조 생략).

---

## 2-E. 시설 탐색 리졸버 — 구현됨 (v0.2.2)

> `think/facility_resolver.py` — 목욕/화장실/옷장 시설의 prop 기반 동적 탐색 + 선착순 점유

### 개요

NPC가 시설(욕조, 화장실, 옷장)을 사용할 때 **prop 기반 동적 탐색**을 수행합니다.
하드코딩 좌표(`_locations` dict) 완전 제거 — 모든 시설은 오브젝트 prop으로 탐색.
`activity_resolver.py`와 동일한 stateless 패턴 (lazy init 불필요, 챕터 전환 이슈 없음).

### 탐색 우선순위

```
1. 소유권 prop 매칭 (옷장: wardrobe_owner:{owner})
2. home_region 내 시설 (bed_owner:{owner} prop 기반 home_region 판정)
3. (cross_region=True일 때만) 다른 region의 시설
4. 모두 점유/없음 → None
```

### home_region 판정

`_get_home_region()` — `bed_owner:{owner_unique_id}` prop으로 소유 침대 위치에서 region 판정.
lazy cache (`_home_region_id`)로 한 번만 탐색, 이후 캐시 사용.

### 목욕 시설 탐색 (`resolve_bath`)

```python
from think.facility_resolver import resolve_bath

target = resolve_bath(agent)                    # 탐색 (선착순 점유)
target = resolve_bath(agent, cross_region=True) # 다른 region도 탐색
```

prop: `action:bath`. 선착순 점유 — 욕조의 location에 목욕 중인 NPC가 없으면 사용 가능.

| 동작 | 설명 |
|------|------|
| `resolve_bath()` | 가용 욕조 탐색 → 점유되지 않은 첫 번째 욕조 반환 |
| 점유 판정 | location 내 NPC가 `_is_bath_time()` 또는 `is_npc_need_bath()` → 점유 |
| 재시도 | needs 주기적 체크로 자연 재시도 (별도 대기 로직 불필요) |

### 화장실 탐색 (`resolve_toilet`)

```python
from think.facility_resolver import resolve_toilet

target = resolve_toilet(agent)                    # 탐색 (선착순 점유)
target = resolve_toilet(agent, cross_region=True) # 다른 region도 탐색
```

prop: `action:toilet`. 선착순 점유 — 화장실의 location에 배변 중(`excretion_phase` 활성) NPC가 없으면 사용 가능.

### 옷장 탐색 (`resolve_wardrobe`)

```python
from think.facility_resolver import resolve_wardrobe

target = resolve_wardrobe(agent)  # 탐색 (소유권 기반)
```

소유권 기반 탐색:
1. `wardrobe_owner:{owner_unique_id}` prop 매칭 (소유 옷장)
2. `unique_id == "wardrobe"` fallback (모브 NPC용)

점유 감지 없음 (동시 사용 충돌 불가).
추위/더위/착의 인터럽트의 `_handle_cold`/`_handle_hot`/`_handle_clothing`에서 사용.

### 세탁기/건조기 탐색 (`resolve_washer`, `resolve_dryer`)

```python
from think.facility_resolver import resolve_washer, resolve_dryer

washer = resolve_washer(agent)  # idle 세탁기 탐색
dryer = resolve_dryer(agent)    # idle 건조기 탐색
```

unique_id 기반 탐색 + `laundry.get_machine_state() == 0` (idle) 필터.
세탁 인터럽트(`_handle_laundry`)에서 사용.

### 반환값

```python
{
    "region_id": 0,
    "location_id": 4,
    "x": 15,
    "object_id": 101
}
# 또는 None (시설 없음)
```

### 시설 prop 정리

| 오브젝트 | prop | 용도 |
|----------|------|------|
| Toilet, PortableToilet | `action:toilet = 1` | 화장실 탐색 |
| DrumBath, BathroomBath | `action:bath = 1` | 목욕 시설 탐색 |
| Wardrobe | `wardrobe_owner:{name} = 1` | 소유 옷장 탐색 |
| Bed, SleepingBag 등 | `bed_owner:{name} = 1` | 소유 침대 탐색, home_region 판정 |
| WashingMachine | `unique_id == "washing_machine"` | 세탁기 탐색 (idle 상태만) |
| Dryer | `unique_id == "dryer"` | 건조기 탐색 (idle 상태만) |

---

## 3. 소유물 기반 행동

### 소유물 인식

```python
def find_owned_items(unit_id, item_type=None):
    """
    NPC 소유 아이템 찾기

    Args:
        unit_id: NPC ID
        item_type: 아이템 타입 필터 (None이면 전체)

    Returns:
        [(item_id, location)] 리스트
    """
    unique_id = morld.get_unit_unique_id(unit_id)
    results = []

    # 모든 아이템 검색
    for item in get_all_items():
        if item.owner != unique_id:
            continue
        if item_type and item.item_type != item_type:
            continue

        # 아이템 위치 찾기
        location = find_item_location(item.id)
        results.append((item.id, location))

    return results

def find_item_location(item_id):
    """아이템이 있는 위치 찾기"""
    # 1. 누군가 소지 중
    holder = morld.get_item_holder(item_id)
    if holder:
        return morld.get_unit_location(holder)

    # 2. 컨테이너(오브젝트) 안
    container = morld.get_item_container(item_id)
    if container:
        return morld.get_unit_location(container)

    # 3. 바닥
    return morld.get_item_ground_location(item_id)
```

### 도구 기반 Activity

```python
class ActivityRequirements:
    """Activity별 필요 도구/조건"""

    REQUIREMENTS = {
        "낚시": {
            "tool": "fishing_rod",       # 필요 도구
            "tool_optional": False,       # 필수 여부
            "location_activity": "낚시",  # Location activity
        },
        "사냥": {
            "tool": "weapon",             # 무기 종류 아무거나
            "tool_category": True,        # 카테고리로 검색
            "tool_optional": False,
        },
        "채집": {
            "tool": "basket",
            "tool_optional": True,        # 없어도 가능 (효율 감소)
        },
        "요리": {
            "tool": "cooking_tool",
            "location_activity": "요리",
            "requires_ingredient": True,   # 재료 필요
        },
    }
```

### 도구 수집 행동

```python
def prepare_for_activity(self, activity):
    """Activity 준비 - 필요 도구 수집"""

    req = ActivityRequirements.REQUIREMENTS.get(activity)
    if not req:
        return None  # 준비 불필요

    tool_type = req.get("tool")
    if not tool_type:
        return None

    # 이미 소지 중인지 확인
    if self.has_item_type(tool_type):
        return None  # 준비 완료

    # 소유 도구 찾기
    owned_tools = find_owned_items(self.unit_id, tool_type)
    if owned_tools:
        item_id, location = owned_tools[0]
        return self._create_fetch_job(item_id, location)

    # 공용 도구 찾기
    if req.get("tool_optional"):
        return None  # 없어도 진행

    # 도구 없음 - activity 불가
    return self._skip_activity(activity, reason="도구 없음")

def _create_fetch_job(self, item_id, location):
    """아이템 가져오기 Job 생성"""
    return [
        Job("이동", "move", location, duration=None),
        Job("줍기", "take", item_id=item_id, duration=1),
    ]
```

### Activity 결과물 처리

```python
def on_activity_complete(self, activity, location):
    """Activity 완료 시 결과물 처리"""

    if activity == "낚시":
        # 물고기 획득
        fish = self._roll_fishing_result(location)
        for item in fish:
            morld.give_item(self.unit_id, item)

        # 저장소로 이동하여 보관
        storage = self._find_storage("식품")
        if storage and fish:
            return self._create_store_job(fish, storage)

    elif activity == "채집":
        # 채집물 획득
        gathered = self._roll_gathering_result(location)
        for item in gathered:
            morld.give_item(self.unit_id, item)

        # 저장소 보관
        storage = self._find_storage("식품")
        if storage and gathered:
            return self._create_store_job(gathered, storage)

    elif activity == "사냥":
        # 사냥감 획득
        prey = self._roll_hunting_result(location)
        if prey:
            morld.give_item(self.unit_id, prey)
            # 주방으로 이동하여 손질
            kitchen = terrain.find_activity(self.unit_id, "요리")
            if kitchen:
                return self._create_process_job(prey, kitchen)

def _find_storage(self, category):
    """저장소 찾기 — storage:{category} prop 기반 동적 탐색"""
    from think.activities.helpers import resolve_storage_container
    return resolve_storage_container(self, category)
```

> **Prop 기반 보관 기준치** (v0.2.2): 컨테이너에 `need:{item_uid}` prop을 설정하면
> `_check_storage_need()` 호출 시 해당 값을 부족 기준치로 사용합니다.
> 예: `"need:branch": 6` → 나뭇가지 6개 미만이면 "부족"으로 판정.
> item_uid=None인 조건(need_food, can_cook, need_supplies)은 **카테고리별 카운팅** (`get_category_item_count`)으로
> 해당 카테고리 아이템만 정확하게 집계합니다.
> 상세: [make_activity.md#보관-시스템-storage-system](make_activity.md#보관-시스템-storage-system)

---

## 4. NPC 주도 상호작용

### 상호작용 조건

```python
class NPCInteraction:
    """NPC 주도 상호작용"""

    # 대화 발동 조건
    TALK_CONDITIONS = {
        "min_longing": 70,        # 최소 그리움 (대상별)
        "cooldown": 60,           # 쿨다운 (분)
        "cross_region": True,     # 다른 region도 찾아감
    }

    # 선물 발동 조건
    GIFT_CONDITIONS = {
        "min_affection": 50,
        "has_gift_item": True,    # 선물할 아이템 보유
        "cooldown": 1440,         # 하루 쿨다운
    }
```

### 상호작용 체크

```python
def check_interaction_opportunity(self, target_id):
    """상호작용 기회 체크"""

    # 그리움 기반 대상 탐색 (cross-region)
    from think.handlers.social import _find_most_missed
    target_id, longing = _find_most_missed(self, threshold=70)
    if target_id is None:
        return None

    # 쿨다운
    last = self._memory.get("socialize_cooldown")
    if last and (self.get_time() - last) < 3_600_000:
        return None

    return "talk"  # 대상 location으로 이동 → 대화

def initiate_interaction(self, target_id, interaction_type):
    """상호작용 시작"""

    if interaction_type == "talk":
        # NPC가 대상 위치로 이동 → 대화(30분) → 양측 그리움 해소
        import needs
        target_info = morld.get_unit_info(target_id)
        agent_info = morld.get_unit_info(self.unit_id)
        if target_info and agent_info:
            needs.reduce_longing(self.unit_id, target_info.get("name", ""))
            needs.reduce_longing(target_id, agent_info.get("name", ""))

    elif interaction_type == "gift":
        gift = self._select_gift_item()
        yield morld.dialog(f"[{self.name}]\n이거... 받아줘.")
        morld.transfer_item(self.unit_id, target_id, gift)
```

### 캐릭터별 상호작용 성향

```python
class Character:
    # 상호작용은 그리움 시스템으로 자동 결정
    # 호감 30+ 대상 → 그리움 축적 → 70+ 시 찾아감
    # rate = (호감 - 30) / 70 * 2.0/h
    # 호감 100 → +2.0/h (50시간에 100 도달)
    # 호감 65  → +1.0/h (100시간에 100 도달)
    # 호감 30  → +0.0/h (그리워하지 않음)

# 캐릭터별 차이는 호감도 축적 속도에 의해 자연 발생
# (호감이 높은 대상을 더 빨리 그리워함)
```

---

## 5. think() 통합 흐름

```python
class LifeAgent(BaseAgent):
    """생활 시스템 통합 Agent"""

    def think(self):
        # === 1단계: 위험 욕구 처리 ===
        critical = self._check_critical_needs()
        if critical:
            return critical

        # === 2단계: 도구 준비 ===
        next_activity = self._get_next_scheduled_activity()
        prep = self.prepare_for_activity(next_activity)
        if prep:
            return prep

        # === 3단계: 긴급 욕구 처리 ===
        urgent = self._check_urgent_needs()
        if urgent:
            return urgent

        # === 4단계: 상호작용 기회 ===
        interaction = self._check_interaction_opportunities()
        if interaction:
            return interaction

        # === 5단계: 이전 Activity 결과물 처리 ===
        pending = self._check_pending_results()
        if pending:
            return pending

        # === 6단계: 기본 스케줄 ===
        return self._fill_schedule_with_dynamic_locations()

    def _fill_schedule_with_dynamic_locations(self):
        """동적 위치 탐색으로 스케줄 채우기"""
        schedule = self.get_schedule()

        for entry in schedule:
            activity = entry["activity"]

            # 위치가 없으면 동적 탐색
            if "location_id" not in entry:
                location = terrain.find_activity(self.unit_id, activity)
                if location:
                    entry["region_id"] = location.region_id
                    entry["location_id"] = location.local_id

        return self.fill_schedule_jobs_from(schedule)
```

---

## 구현 우선순위

| 단계 | 내용 | 의존성 | 난이도 | 상태 |
|------|------|--------|--------|------|
| 1a | Location.activities 속성 | 없음 | 낮음 | 미구현 (대안: activity_resolver) |
| 1b | 동적 Activity 탐색 | 1a | 중간 | **구현됨** (resolver 7종) |
| 2a | 욕구 props 정의 (배고픔) | 없음 | 낮음 | **구현됨** (생존:포만감) |
| 2b | 욕구 증가/감소 로직 (배고픔) | 2a | 중간 | **구현됨** (survival.py) |
| 2c | 긴급 행동 트리거 (배고픔) | 2b, 1b | 중간 | **구현됨** (_check_hunger) |
| 2d | 추위/더위 인터럽트 | 체온 시스템 | 중간 | **구현됨** (_check_cold/_check_hot) |
| 2e | 배변/피로/청결/그리움 수치화 | 2a | 중간 | **구현됨** (needs.py, v0.2.2) |
| 3a | 소유물 검색 API | 없음 | 중간 | 미구현 |
| 3b | 도구 기반 Activity | 3a | 중간 | **구현됨** (벌목 도끼, 낚시대) |
| 3c | 결과물 저장소 이동 | 3a, 1b | 높음 | **구현됨** (채집→저장, 낚시→저장, 요리→저장) |
| 4a | 상호작용 조건 체크 | 2a | 중간 | 미구현 |
| 4b | NPC 주도 대화 | 4a | 중간 | 미구현 |
| 5 | think() 통합 | 전체 | 높음 | **부분 구현** (배고픔+동적스케줄+활동핸들러) |

---

## 예상 결과

### 세라의 하루 (시스템 완성 후)

```
05:00 [수면욕 해소] 자기 방에서 기상
05:10 [배변욕 60] 화장실로 이동, 배변
05:20 [스케줄] 아침 순찰 - terrain.find("순찰") → 앞마당
06:00 [배고픔 50] 식당으로 이동, 아침 식사
06:30 [배변욕 +20] 식사 후 배변욕 증가
06:40 [스케줄] 사냥 준비 - 무기 없음 → 무기고로 이동
06:50 [도구 획득] 자기 소유 활 장착
07:00 [스케줄] 사냥 - terrain.find("사냥") → 사냥터
      ... 사냥 중 ...
10:00 [Activity 완료] 토끼 2마리 획득
10:10 [결과물 처리] 주방으로 이동, 사냥감 보관
10:30 [배변욕 80] 화장실로 긴급 이동
10:40 [스케줄 복귀] 사냥터로 복귀
      ...
18:00 [그리움 70+] 플레이어 찾아감 → 방문 대화
      "...잠깐 보러 왔어."
```

### 리나의 하루 (시스템 완성 후)

```
06:00 [수면욕 해소] 기상
06:10 [스케줄] 옷 갈아입기 - 자기 옷장으로 이동
06:20 [배고픔 45] 아침 식사
07:00 [스케줄] 빨래 - terrain.find("세탁") → 뒷마당
08:00 [스케줄] 채집 준비 - 바구니 찾기 → 창고
08:10 [도구 획득] 바구니 획득
08:20 [스케줄] 채집 - terrain.find("채집") → 채집터
      ... 채집 중 ...
11:00 [Activity 완료] 산딸기 5개, 버섯 3개 획득
11:10 [결과물 처리] 주방 저장고로 이동, 보관
11:30 [그리움:밀라 70+] 밀라 찾아감 → 대화
      "밀라 언니~ 채집 다녀왔어요!"
12:00 [배고픔 60] 점심 식사
      ...
```

---

## 파일 구조 (예상)

```
scenarios/scenario02/python/
├─ life/
│   ├─ __init__.py          # 통합 API
│   ├─ needs.py             # 욕구 시스템
│   ├─ activity.py          # Activity 탐색
│   ├─ ownership.py         # 소유물 관리
│   └─ interaction.py       # NPC 상호작용
├─ think/
│   ├─ __init__.py          # BaseAgent
│   └─ life_agent.py        # LifeAgent (통합)
└─ assets/
    └─ locations/
        └─ *.py             # activities 속성 추가
```

---

## 참고 문서

- [schedule.md](schedule.md) - 기본 스케줄/JobList 시스템
- [romance.md](romance.md) - NPC 주도 이벤트 패턴 참고
- [battle.md](battle.md) - Location 용량 시스템 참고
