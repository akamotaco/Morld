# NPC 생활 시스템 (Life System)

> **이 문서는 설계/계획 문서입니다.** 대부분의 내용은 아직 구현되지 않았습니다.
>
> **v0.2.1에서 부분 구현된 항목:**
> - 동적 Activity 탐색 → `activity_resolver.py` (채집/사냥/순찰/벌목)
> - 도구 기반 Activity → 벌목 시 도끼 가져오기/반납 (`_handle_chop`)
> - Activity 결과물 → 채집(`_do_gather`), 벌목(`npc_chop`)
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

## 1. 동적 Activity 탐색 — 부분 구현됨 (v0.2.1)

> `activity_resolver.py`에서 채집/사냥/순찰/벌목 구현. 아래 설계와 다른 점:
> - `Location.activities` 속성 없이, resolver 함수가 직접 오브젝트 탐색
> - `terrain.find_activity()` 대신 `resolve_activity_location(unit_id, activity, region_id)` 사용
> - 수면은 C# `resolve_sleep_target` API 사용

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
| 1b | 동적 Activity 탐색 | 1a | 중간 | **부분 구현** (resolver 4종) |
| 2a | 욕구 props 정의 | 없음 | 낮음 | 미구현 |
| 2b | 욕구 증가/감소 로직 | 2a | 중간 | 미구현 |
| 2c | 긴급 행동 트리거 | 2b, 1b | 중간 | 미구현 |
| 3a | 소유물 검색 API | 없음 | 중간 | 미구현 |
| 3b | 도구 기반 Activity | 3a | 중간 | **벌목 도끼만 구현** |
| 3c | 결과물 저장소 이동 | 3a, 1b | 높음 | 미구현 |
| 4a | 상호작용 조건 체크 | 2a | 중간 | 미구현 |
| 4b | NPC 주도 대화 | 4a | 중간 | 미구현 |
| 5 | think() 통합 | 전체 | 높음 | 미구현 |

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
