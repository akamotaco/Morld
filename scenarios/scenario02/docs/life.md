# NPC 생활 시스템 (Life System)

> **v0.2.1에서 핵심 기능 구현 완료.**
>
> **구현된 항목:**
> - 동적 Activity 탐색 → `activity_resolver.py` (채집/사냥/순찰/벌목/낚시/독서/물자수집)
> - 도구 기반 Activity → 벌목 도끼, 낚시대, 빗자루 가져오기/반납
> - Activity 결과물 → 채집→저장, 낚시→저장, 벌목, 요리, 청소(오염도 감소), 물자수집
> - NPC 만복도 시스템 → `survival.py` (register_npc, is_npc_hungry, npc_eat)
> - 배고픔 인터럽트 → think()에서 스케줄보다 우선 처리
> - 추위/더위 인터럽트 → 방한/방수 의류 자동 착탈 (v0.2.2)
> - 동적 스케줄 → 조건 기반 활동 선택 (`dynamic: True`, `candidates`)
> - 자원 순환 → 채집→저장→요리→식사 파이프라인
> - 컨테이너 헬퍼 → `npc_store_item`, `npc_take_item`, `get_item_count`
> - 텃밭 활동 → 정원 4-phase (idle/going/working/storing_harvest)
> - 시설 탐색 리졸버 → `facility_resolver.py` (목욕 예약 + 옷장 우선순위 탐색) (v0.2.2)
>
> **미구현 항목:** 배변욕, 수면욕, 사회욕, NPC 주도 상호작용
>
> 현재 구현 상태는 [schedule.md#8](schedule.md#8-v021-phase-시스템) 참조.

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

## 1. 동적 Activity 탐색 — 구현됨 (v0.2.1)

> `activity_resolver.py`에서 7종 구현. 아래 설계와 다른 점:
> - `Location.activities` 속성 없이, resolver 함수가 직접 오브젝트 탐색
> - `terrain.find_activity()` 대신 `resolve_activity_location(unit_id, activity, region_id)` 사용
> - 수면은 C# `resolve_sleep_target` API 사용
>
> **구현된 resolver:** 채집, 사냥, 순찰, 벌목, 낚시, 독서, 물자수집

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

## 2. 욕구 시스템 (Needs System)

### 욕구 타입

| 욕구 | prop 키 | 범위 | 증가 조건 | 해소 방법 |
|------|---------|------|-----------|-----------|
| 배고픔 | `욕구:배고픔` | 0~100 | 시간 경과 | 식사 |
| 배변욕 | `욕구:배변` | 0~100 | 시간 경과, 식사 후 | 화장실/야외 |
| 수면욕 | `욕구:수면` | 0~100 | 시간 경과 | 수면 |
| 사회욕 | `욕구:사회` | 0~100 | 혼자 있을 때 | 대화 |

### 욕구 증가율

```python
NEED_RATES = {
    "배고픔": {
        "base_rate": 4,      # 시간당 기본 증가
        "activity_mod": {    # 활동별 보정
            "사냥": 2,       # 사냥 중 +2/시간
            "수면": -2,      # 수면 중 -2/시간
        }
    },
    "배변": {
        "base_rate": 2,
        "after_meal": 20,    # 식사 후 +20
    },
    "수면": {
        "base_rate": 4,
        "night_mod": 2,      # 밤에 추가 증가
    },
    "사회": {
        "base_rate": 1,
        "alone_mod": 3,      # 혼자 있을 때 추가
    }
}
```

### 욕구 임계값

| 욕구 | 경고 | 긴급 | 위험 |
|------|------|------|------|
| 배고픔 | 50 | 70 | 90 |
| 배변 | 60 | 80 | 95 |
| 수면 | 50 | 70 | 90 |
| 사회 | 40 | 60 | 80 |

### 긴급 행동 트리거

```python
def think(self):
    """욕구 기반 행동 우선순위"""

    needs = self.get_all_needs()

    # 1. 위험 수준 욕구 (즉시 처리)
    for need, value in needs.items():
        if value >= CRITICAL_THRESHOLD[need]:
            return self._handle_critical_need(need)

    # 2. 긴급 수준 욕구 (스케줄 중단)
    for need, value in needs.items():
        if value >= URGENT_THRESHOLD[need]:
            return self._handle_urgent_need(need)

    # 3. 경고 수준 욕구 (스케줄 빈 시간에 처리)
    pending_needs = [n for n, v in needs.items()
                    if v >= WARNING_THRESHOLD[n]]

    # 4. 기본 스케줄
    return self.fill_schedule_jobs(pending_needs)

def _handle_critical_need(self, need):
    """위험 수준 욕구 처리"""
    if need == "배변":
        # 가장 가까운 곳에서 즉시 해결 (야외도 가능)
        location = terrain.find_activity(self.unit_id, "배변")
        if not location:
            location = terrain.find_activity(self.unit_id, "야외배변")
        return self.set_urgent_job("배변", location, priority="critical")

    elif need == "수면":
        # 쓰러지기 직전 - 그 자리에서 잠들 수도
        location = terrain.find_sleep_location(self.unit_id)
        return self.set_urgent_job("수면", location, priority="critical")
```

### 욕구 해소 효과

```python
NEED_RELIEF = {
    "배고픔": {
        "식사": -50,          # 식사 시 -50
        "간식": -20,          # 간식 시 -20
    },
    "배변": {
        "배변": -100,         # 완전 해소
    },
    "수면": {
        "수면": -10,          # 시간당 -10 (8시간 = -80)
        "낮잠": -5,           # 시간당 -5
    },
    "사회": {
        "대화": -30,          # 대화 시 -30
        "함께있기": -5,       # 같은 공간에 있을 때 시간당
    }
}
```

### 배변 시스템 상세

```python
class ToiletBehavior:
    """배변 행동 처리"""

    def process(self, unit_id):
        need = morld.get_unit_prop(unit_id, "욕구:배변")

        if need >= 95:
            # 위험: 즉시 해결 (실수 가능성)
            return self._emergency_relief(unit_id)

        elif need >= 80:
            # 긴급: 가장 가까운 화장실
            location = terrain.find_activity(unit_id, "배변")
            return self._go_to_toilet(unit_id, location)

        elif need >= 60:
            # 경고: 스케줄 빈 시간에 처리
            return self._schedule_toilet(unit_id)

    def _emergency_relief(self, unit_id):
        """긴급 배변 - 야외 포함"""
        toilet = terrain.find_activity(unit_id, "배변")
        if toilet and self._is_close(unit_id, toilet):
            return self._go_to_toilet(unit_id, toilet)

        # 화장실이 멀면 야외에서
        outdoor = terrain.find_activity(unit_id, "야외배변")
        if outdoor:
            return self._outdoor_relief(unit_id, outdoor)

        # 최악의 경우: 그 자리에서... (이벤트 발생)
        return self._accident(unit_id)
```

---

## 2-B. 추위/더위 인터럽트 — 구현됨 (v0.2.2)

> `think/__init__.py` — 배고픔 인터럽트와 같은 계층에서 동작

### think() 우선순위

```
기절(최우선) > 목욕/수면 > 배고픔 > 추위 > 더위 > 일반 활동
```

### 추위 인터럽트 (`_check_cold` → `_handle_cold`)

**트리거 조건** (모두 충족):
1. 체온 ≤ 35.5 AND 보온 < 2, **OR** 비 + 젖음 > 30 + 방수 < 1
2. `wardrobe_location` 설정됨 (옷장 접근 가능)
3. 1시간 쿨다운 경과 (`_memory["cold_last_attempt"]`)

**페이즈 흐름** (`_memory["cold_phase"]`):
```
None → idle → going → taking → equipping → None
```

| 페이즈 | 동작 |
|--------|------|
| `idle` | 인벤토리에 보온 아이템 있으면 → `equipping`, 없으면 → `going` |
| `going` | `wardrobe_location`으로 이동 (move job) |
| `taking` | 옷장에서 보온/방수 아이템 꺼내기 (`npc_take_item`) |
| `equipping` | 인벤토리의 보온/방수 아이템 장착 (`equipment.equip_item`) → 완료 |

### 더위 인터럽트 (`_check_hot` → `_handle_hot`)

**트리거 조건** (모두 충족):
1. 체온 ≥ 37.5
2. 보온 합계 > 0 (보온 의류 착용 중)
3. `wardrobe_location` 설정됨

**페이즈 흐름** (`_memory["hot_phase"]`):
```
None → idle → unequipping → storing → None
```

| 페이즈 | 동작 |
|--------|------|
| `idle` | → `unequipping` |
| `unequipping` | 보온 아이템 벗기 (`equipment.unequip_item`), 이동 불필요 |
| `storing` | 옷장 location이면 옷장에 넣기, 아니면 인벤토리 보관 → 완료 |

### wardrobe_location 설정

각 NPC 에이전트에 `wardrobe_location` dict 설정:

| NPC | wardrobe_location | 위치 |
|-----|-------------------|------|
| 세라 | `{"region_id": 0, "location_id": 8, "x": 25}` | 세라방 옷장 |
| 밀라 | `{"region_id": 0, "location_id": 9, "x": 25}` | 밀라방 옷장 |
| 리나 | `{"region_id": 0, "location_id": 7, "x": 25}` | 리나방 옷장 |
| 유키 | `{"region_id": 2, "location_id": 6, "x": 120}` | 의류점 |
| 엘라 | `{"region_id": 2, "location_id": 6, "x": 120}` | 의류점 |

`BaseAgent`에 `wardrobe_location = None` (기본: 비활성). `wardrobe_unique_id = "wardrobe"`.

### _memory 키

```python
self._memory = {
    "cold_phase": None,         # None/idle/going/taking/equipping
    "cold_last_attempt": None,  # 실패 시 쿨다운 타임스탬프
    "hot_phase": None,          # None/idle/unequipping/storing
}
```

---

## 2-C. 시설 탐색 리졸버 — 구현됨 (v0.2.2)

> `think/facility_resolver.py` — 목욕/옷장 등 시설의 우선순위 탐색 + 예약

### 개요

NPC가 시설(욕조, 옷장 등)을 사용할 때 하드코딩 좌표 대신 **우선순위 기반 동적 탐색**을 수행합니다.
`activity_resolver.py`와 동일한 stateless 패턴 (lazy init 불필요, 챕터 전환 이슈 없음).

### 탐색 우선순위

```
1. agent.bath_location / wardrobe_location (선호 위치)
2. 같은 region의 다른 시설
3. (cross_region=True일 때만) 다른 region의 시설
4. 모두 점유/없음 → None
```

### 목욕 시설 탐색 (`resolve_bath`)

```python
from think.facility_resolver import resolve_bath, release_bath

target = resolve_bath(agent)                    # 탐색 + 예약
target = resolve_bath(agent, cross_region=True) # 다른 region도 탐색
release_bath(agent)                             # 예약 해제
```

**예약 시스템**: 욕조 오브젝트에 `예약:사용자` prop을 설정하여 점유 표시.
침대의 `seated_by` 패턴과 동일. 챕터 전환 시 오브젝트 재생성으로 자동 초기화.

| 동작 | 설명 |
|------|------|
| `resolve_bath()` | 가용 욕조 탐색 → `예약:사용자` prop 설정 → dict 반환 |
| `release_bath()` | 해당 NPC의 예약 prop 해제 |
| stale 정리 | 예약자의 `_is_bath_time()`이 False면 자동 해제 |

**대기 로직** (`_handle_bath`에서):
- 모든 욕실 점유 + 목욕 시간 10분+ 남음 → 5분 대기 후 재탐색
- 모든 욕실 점유 + 목욕 시간 10분 미만 → 목욕 포기
- 예: 밀라가 5분 대기 → 세라가 5:30에 완료 → 밀라 5:05에 입욕

### 옷장 탐색 (`resolve_wardrobe`)

```python
from think.facility_resolver import resolve_wardrobe

target = resolve_wardrobe(agent)  # 탐색 (예약 불필요)
```

점유 감지 없음 (동시 사용 충돌 불가).
추위/더위 인터럽트의 `_handle_cold`/`_handle_hot`에서 옷장 위치 탐색에 사용.

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

def _find_storage(self, storage_type):
    """저장소 찾기"""
    # 1순위: 자기 소유 저장소
    owned = find_owned_objects(self.unit_id, f"storage_{storage_type}")
    if owned:
        return owned[0]

    # 2순위: 공용 저장소
    return terrain.find_activity(self.unit_id, f"{storage_type}보관")
```

---

## 4. NPC 주도 상호작용

### 상호작용 조건

```python
class NPCInteraction:
    """NPC 주도 상호작용"""

    # 대화 발동 조건
    TALK_CONDITIONS = {
        "min_affection": 30,      # 최소 호감도
        "min_social_need": 40,    # 최소 사회욕
        "cooldown": 60,           # 쿨다운 (분)
        "same_location": True,    # 같은 위치 필요
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

    # 같은 위치인지
    my_loc = morld.get_unit_location(self.unit_id)
    target_loc = morld.get_unit_location(target_id)
    if my_loc != target_loc:
        return None

    # 호감도
    affection = self.get_affection_to(target_id)

    # 사회욕
    social_need = morld.get_unit_prop(self.unit_id, "욕구:사회")

    # 쿨다운
    last_interaction = self.get_last_interaction_time(target_id)
    if last_interaction and (now - last_interaction) < COOLDOWN:
        return None

    # 대화 조건 체크
    if (affection >= 30 and social_need >= 40):
        return "talk"

    # 선물 조건 체크 (더 높은 호감도)
    if (affection >= 50 and self._has_gift_item()):
        return "gift"

    return None

def initiate_interaction(self, target_id, interaction_type):
    """상호작용 시작"""

    if interaction_type == "talk":
        # NPC가 먼저 말 걸기
        yield morld.dialog(self._get_greeting(target_id))

        # 사회욕 해소
        morld.add_unit_prop(self.unit_id, "욕구:사회", -30)

    elif interaction_type == "gift":
        gift = self._select_gift_item()
        yield morld.dialog(f"[{self.name}]\n이거... 받아줘.")
        morld.transfer_item(self.unit_id, target_id, gift)
```

### 캐릭터별 상호작용 성향

```python
class Character:
    # 상호작용 설정
    INTERACTION_CONFIG = {
        "talk_threshold": 30,      # 대화 호감도 임계값
        "social_need_weight": 1.0, # 사회욕 가중치
        "proactive": 0.5,          # 적극성 (0~1)
    }

class Sera(Character):
    INTERACTION_CONFIG = {
        "talk_threshold": 50,      # 높은 임계값 (과묵)
        "social_need_weight": 0.5, # 사회욕 영향 적음
        "proactive": 0.2,          # 소극적
    }

class Lina(Character):
    INTERACTION_CONFIG = {
        "talk_threshold": 20,      # 낮은 임계값 (친근)
        "social_need_weight": 1.5, # 사회욕 영향 큼
        "proactive": 0.8,          # 적극적
    }
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
| 2e | 배변/수면/사회욕 | 2a | 중간 | 미구현 |
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
18:00 [사회욕 60 + 호감도] 플레이어 발견 → NPC 주도 대화
      "...오늘 사냥은 어땠어?"
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
11:30 [사회욕 70] 밀라 발견 → 대화
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
