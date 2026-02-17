# 신규 활동(Activity) 제작 가이드

## 개요

Activity Handler는 NPC가 스케줄 시간대에 수행하는 **다단계 행동**을 정의합니다.
핸들러는 `think/activities/` 패키지에 모듈화되어 있으며, 스케줄에 activity 이름만 지정하면 자동으로 호출됩니다.

이 문서는 신규 activity를 처음부터 만드는 과정을 단계별로 안내합니다.

---

## 파일 구조

```
think/activities/
├── __init__.py          # ACTIVITY_HANDLERS dict (핸들러 등록)
├── helpers.py           # 공용 헬퍼 (resolve_storage_container, store_npc_items, resolve_branch_tree 등)
├── lights.py            # 소등/점등
├── chop.py              # 벌목
├── fish.py              # 낚시
├── gather.py            # 채집→저장
├── cook.py              # 요리
├── clean.py             # 청소
├── scavenge.py          # 물자수집
├── garden_activity.py   # 정원 (텃밭 관리)
├── fuel.py              # 연료수집
└── branch_collect.py    # 난방 연료 수집
```

---

## 핵심 개념

### Phase 시스템

모든 활동은 **Phase(단계)**로 나뉩니다. `think()`가 호출될 때마다 현재 phase를 확인하고, 해당 단계의 로직을 실행합니다.

```python
agent._activity_phase   # 현재 단계 ("idle", "going_to_X", "returning_tool" 등)
agent._activity_state   # 활동별 임시 데이터 dict (activity 변경 시 자동 리셋)
agent._action_taken     # True로 설정하면 이번 think()에서 행동 완료 표시
```

- `_activity_phase`는 activity가 변경되면 자동으로 `"idle"`로 리셋됩니다.
- `_activity_state`는 activity가 변경되면 `{}`로 리셋됩니다.
- `_action_taken`은 매 `think()` 호출 시 `False`로 초기화됩니다.

### DES 규칙

**반드시 지켜야 할 규칙:**

1. **모든 think() 호출은 job을 삽입해야 합니다** (duration > 0)
2. 이동: `agent._move_to(target, "설명")` → duration=0 move job (C#이 자동 계산)
3. 대기: `agent._insert_idle_job("이름", 밀리초)` → stay job
4. `_action_taken = True`를 설정하여 행동 완료를 표시

> handler가 `_action_taken`을 설정하지 않으면, `_handle_schedule()`이 "할 일 없음" idle job을 자동 삽입합니다 (폴백).

### 행동 시간 시스템 (ACTION_DURATION)

고정 시간이 소요되는 모든 행동은 `think/activities/helpers.py`의 **ACTION_DURATION** 테이블에 정의됩니다.

#### 고정 시간 행동 — `_do_instant_action()`

```python
# 도구 집기 (1분)
agent._do_instant_action("도구 준비", "take_item")

# 벌목 (30분)
agent._do_instant_action("벌목", "chop")

# 중단/오류 (5분)
agent._do_instant_action("대기", "abort")
```

`_do_instant_action(job_name, duration_key)`는 내부적으로:
1. `_get_action_duration(key)` → ACTION_DURATION 테이블에서 밀리초 조회
2. `_insert_idle_job(job_name, duration)` → DES job 삽입
3. `_action_taken = True` → 행동 완료 표시

#### 주요 duration_key 목록

| key | 시간 | 용도 |
|-----|------|------|
| `take_item` | 1분 | 컨테이너에서 아이템 꺼내기 |
| `store_item` | 1분 | 컨테이너에 아이템 넣기 |
| `abort` | 5분 | 중단/오류 시 대기 |
| `brief` | 1분 | 짧은 전환 |

> 전체 목록은 `think/activities/helpers.py`의 ACTION_DURATION dict 참조.

#### 비고정 시간 행동 — 테이블 대상 아님

| 패턴 | 설명 |
|------|------|
| `max(remaining, 1)` | 스케줄 잔여 시간 연동 — 스케줄 종료까지 대기 |
| `_move_to()` | C#이 거리/속도 기반으로 동적 계산 |

#### 캐릭터 오버라이드

서브클래스에서 `_action_duration_overrides` dict를 정의하면 해당 NPC만 시간이 변경됩니다:

```python
class SeraAgent(BaseAgent):
    _action_duration_overrides = {
        "chop": 20 * 60_000,   # 세라는 벌목이 빠름 (20분)
    }
```

### Agent 헬퍼 메서드

| 메서드 | 설명 |
|--------|------|
| `agent._is_at(target)` | NPC가 target 위치에 도착했는지 확인 |
| `agent._move_to(target, "설명")` | target으로 이동 job 삽입 (매번 새 job, C# 동적 duration) |
| `agent._insert_idle_job("이름", ms)` | 대기 job 삽입 (duration=ms) |
| `agent._do_instant_action("이름", "key")` | 고정 시간 행동 (ACTION_DURATION 조회 + job 삽입 + action_taken) |
| `agent._get_action_duration("key")` | ACTION_DURATION 테이블에서 밀리초 조회 (오버라이드 우선) |
| `agent._remaining_millis_in_entry(entry)` | 현재 스케줄 entry의 남은 시간(ms) |
| `agent._get_home_region()` | NPC 거처 region_id 반환 |
| `agent._find_tool_by_capability("can:X")` | 도구 탐색 (인벤토리 → 도구함) |
| `agent._skip_dynamic_activity(entry)` | dynamic entry에서 다음 candidate로 건너뛰기 |
| `agent._do_wander(entry)` | 순찰/산책용 wandering (랜덤 location → 이동 → 10~30분 휴식) |
| `agent._pick_wander_location()` | 같은 region 내 랜덤 location 선택 |

### target dict 형식

이동/위치 관련 dict의 공통 형식:

```python
target = {
    "region_id": int,      # Region ID
    "location_id": int,    # Location ID
    "x": int,              # X 좌표
    "object_id": int,      # (선택) 대상 오브젝트 ID
}
```

---

## 튜토리얼: 연료수집 핸들러 따라 만들기

`fuel.py`를 예시로 활동 핸들러를 만드는 전체 과정을 설명합니다.

### Step 1: 핸들러 함수 작성

파일: `think/activities/fuel.py`

```python
"""연료 수집 활동 핸들러

NPC가 나뭇가지를 주워 모아서 열원에 장전하는 활동.
Phase flow: idle → going_to_tree → going_to_heat_source
"""
import morld
from .helpers import get_object_x_from_info


def handle_fuel(agent, entry):
    """연료수집: 나뭇가지 있는 나무 → 줍기 → 열원으로 이동 → 장전"""
    phase = agent._activity_phase

    if phase == "idle":
        # 1. 연료 필요한 열원 찾기
        target_source = find_heat_source_needing_fuel(agent)
        if not target_source:
            # 연료 충분 → 나머지 시간 대기
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("연료수집", max(remaining, 1))
            agent._action_taken = True
            return

        # 2. 나뭇가지 있는 나무 찾기
        tree_target = _resolve_branch_tree(agent)
        if not tree_target:
            return  # 나무 없음 → 디스패치 루프가 "할 일 없음" 폴백

        agent._activity_state["fuel_target"] = target_source
        agent._activity_state["tree_target"] = tree_target
        agent._activity_phase = "going_to_tree"

    elif phase == "going_to_tree":
        target = agent._activity_state.get("tree_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 나뭇가지 줍기 (최대 3개)
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_gather_branch"):
                    for _ in range(3):
                        if not obj.npc_gather_branch(agent.unit_id):
                            break
            agent._activity_phase = "going_to_heat_source"
            agent._action_taken = True
        else:
            agent._move_to(target, "나뭇가지 줍기")

    elif phase == "going_to_heat_source":
        target = agent._activity_state.get("fuel_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 인벤토리의 branch/log를 열원에 장전
            _load_all_fuel(agent, target["object_id"])
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "연료 장전")
```

#### 핵심 패턴 해설

**패턴 1: idle → 탐색 → 다음 phase 전환**
```python
if phase == "idle":
    target = find_something(agent)
    if not target:
        return  # 또는 idle job 삽입
    agent._activity_state["target"] = target
    agent._activity_phase = "going_to_somewhere"
```

**패턴 2: 이동 → 도착 시 행동 → 다음 phase**
```python
elif phase == "going_to_somewhere":
    target = agent._activity_state.get("target")
    if agent._is_at(target):
        # 도착 → 행동 실행
        do_something()
        agent._activity_phase = "next_phase"
        agent._action_taken = True
    else:
        agent._move_to(target, "이동 설명")
```

**패턴 3: 할 일 없으면 대기 or return**
```python
# 방법 A: 직접 idle job 삽입 (나머지 시간 대기)
remaining = agent._remaining_millis_in_entry(entry)
agent._insert_idle_job("활동명", max(remaining, 1))
agent._action_taken = True

# 방법 B: return (디스패치 루프가 자동으로 "할 일 없음" 폴백)
return
```

### Step 2: 헬퍼 함수 작성

핸들러 하단에 탐색/실행 헬퍼를 추가합니다.

```python
def find_heat_source_needing_fuel(agent):
    """거처 내 연료 필요한 열원 찾기"""
    import fuel
    from assets.objects import _location_objects, get_instance
    from assets.objects.furniture import PortableStove, DrumBath

    home_region = agent._get_home_region()
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            if fuel.is_fuel_source(obj_id) and fuel.needs_fuel(obj_id):
                obj = get_instance(obj_id)
                if isinstance(obj, (PortableStove, DrumBath)):
                    return {
                        "region_id": r,
                        "location_id": l,
                        "x": get_object_x_from_info(obj_id),
                        "object_id": obj_id,
                    }
    return None
```

**탐색 패턴:**
1. `agent._get_home_region()`으로 거처 region 필터링
2. `_location_objects`에서 오브젝트 순회
3. 조건 만족하면 target dict 반환 (`region_id`, `location_id`, `x`, `object_id`)

### Step 3: `__init__.py`에 등록

```python
# think/activities/__init__.py
from .fuel import handle_fuel  # ← 추가

ACTIVITY_HANDLERS = {
    ...
    "연료수집": handle_fuel,       # ← 추가
}
```

### Step 4: NPC 스케줄에 활동 추가

```python
# 캐릭터 파일의 SCHEDULE 또는 SCHEDULES에 추가
{"name": "연료수집", "start": 840*_M, "end": 900*_M, "activity": "연료수집"},
```

이것만으로 NPC는 해당 시간대에 자동으로 연료수집을 시작합니다.

---

## 보관 시스템 (Storage System)

활동 핸들러가 아이템을 저장/탐색할 때 사용하는 prop 기반 시스템입니다.

### 컨테이너 prop

오브젝트에 `storage:{category}` prop을 부여하면 해당 카테고리의 보관소로 인식됩니다.

```python
class KitchenFridge(Object):
    props = {
        "storage:food": 1,              # 음식 보관
        "storage:food_ingredient": 1,   # 식재료 보관
        "storage:drink_ingredient": 1,  # 음료 재료 보관
    }

class Toolbox(Object):
    props = {
        "storage:tool": 1,          # 도구 보관
        "storage:garden_tool": 1,   # 정원 도구 보관
        "storage:material": 1,      # 재료 (나뭇가지, 통나무 등) 보관
    }
```

### 기준치 prop (`need:{item_uid}`)

컨테이너에 `need:{item_uid}` prop을 설정하면, NPC의 동적 스케줄 조건 판정 시 **부족 기준치**로 사용됩니다.

```python
class Toolbox(Object):
    props = {
        "storage:tool": 1,
        "storage:material": 1,
        "need:branch": 6,    # 나뭇가지 6개 미만이면 "부족"
        "need:log": 3,       # 통나무 3개 미만이면 "부족"
    }
```

**동작 원리:**

`_check_storage_need(category, item_uid, threshold)` 함수가 호출될 때:

1. `resolve_storage_container(agent, category)`로 컨테이너 탐색
2. 컨테이너에 `need:{item_uid}` prop이 있으면 → **prop 값을 기준치로 사용**
3. prop이 없으면 → **파라미터 threshold를 fallback으로 사용**

```python
# 예시: 나뭇가지 부족 확인
# Toolbox에 "need:branch": 6 prop 설정
agent._check_storage_need("material", "branch", 10)
# → Toolbox에서 need:branch=6 읽음 → branch < 6이면 True
# → prop이 없었다면 fallback threshold=10 사용
```

### 아이템 카테고리 (category)

아이템 클래스의 `category` 속성으로 분류됩니다. 컨테이너의 `storage:{category}` prop과 매칭됩니다.

| category | 아이템 예시 |
|----------|-------------|
| `tool` | FishingRod, Axe, Saw, Broom, Torch, Lantern, HuntingBow, RusticDagger, KitchenKnife |
| `garden_tool` | WateringCan, WaterBucket |
| `food` | 요리 완성품 |
| `food_ingredient` | 생선, 열매, 약초 |
| `drink_ingredient` | 음료 재료 |
| `material` | branch, log |
| `seed` | 씨앗류 |
| `garden_supply` | 비료 |
| `clothing` | 의류/장비 |

### 보관소 탐색 API

```python
from think.activities.helpers import resolve_storage_container, store_npc_items

# 카테고리별 보관소 찾기 (NPC 거처 내)
target = resolve_storage_container(agent, "food_ingredient")
# → {"region_id", "location_id", "x", "object_id"} 또는 None

# NPC 인벤토리 → 현재 위치 컨테이너에 저장
store_npc_items(agent, categories=["food", "food_ingredient"])
# → 컨테이너가 같은 location에 있어야 함 (이동은 caller 책임)
```

### 활동에서 보관소 사용 예시

물자수집 핸들러(`scavenge.py`)의 보관 phase:

```python
elif phase == "going_to_storage":
    target = agent._activity_state.get("storage_target")
    if not target:
        # 보관소 탐색
        target = resolve_storage_container(agent, "food_ingredient")
        if not target:
            target = resolve_storage_container(agent, "food")
        if not target:
            agent._activity_phase = "idle"
            agent._action_taken = True
            return
        agent._activity_state["storage_target"] = target

    if agent._is_at(target):
        # 도착 → 인벤토리를 컨테이너에 저장
        store_npc_items(agent, categories=["food", "food_ingredient", "drink_ingredient"])
        agent._activity_phase = "idle"
        agent._action_taken = True
    else:
        agent._move_to(target, "물자 저장")
```

---

## 동적 스케줄 (Dynamic Schedule)

스케줄 entry에 `"dynamic": True`와 `"candidates"` 리스트를 추가하면, 조건에 따라 활동을 자동 선택합니다.

### 형식

```python
{"name": "오전활동", "start": 540*_M, "end": 720*_M,
 "dynamic": True, "candidates": [
     {"activity": "낚시", "condition": "need_fish"},
     {"activity": "벌목", "condition": "need_logs"},
     {"activity": "순찰", "condition": None},     # fallback (항상 True)
 ]}
```

candidates는 **순서대로** 평가됩니다. 첫 번째로 조건이 True인 후보가 선택됩니다.
마지막 후보의 `condition`을 `None`으로 설정하면 fallback으로 사용됩니다.

### 기존 조건 목록

| 조건 | 의미 | 판정 방법 |
|------|------|----------|
| `need_fish` | 물고기 부족 | `food_ingredient` 컨테이너에서 food_fish < 기준치 |
| `need_logs` | 통나무 부족 | `material` 컨테이너에서 log < 기준치 |
| `need_food` | 식재료 부족 | `food_ingredient` 컨테이너에 food_ingredient 카테고리 아이템 < 기준치 |
| `can_cook` | 요리 가능 | `food_ingredient` 컨테이너에 food_ingredient 카테고리 재료 ≥ 2 |
| `need_supplies` | 물자 부족 | `food` 컨테이너에 food 카테고리 아이템 < 기준치 |
| `should_clean` | 청소 필요 | 거처 내 오염도 > 0인 방 존재 |
| `need_social` | 사교 필요 | `needs.get_social() >= 50` |
| `need_fuel` | 연료 부족 | 거처 내 열원에 연료 부족 |
| `need_fuel_material` | 연료 재료 부족 | `material` 컨테이너에서 branch < 6 또는 log < 3 |

> 기준치는 컨테이너의 `need:{item_uid}` prop 값을 우선 사용하며, 없으면 코드의 fallback 값을 사용합니다.

### 신규 조건 추가하기

`think/__init__.py`의 `_evaluate_condition()` 메서드에 조건을 추가합니다:

```python
def _evaluate_condition(self, condition):
    """동적 스케줄 조건 평가 (True=활동 필요)"""
    if condition == "need_fish":
        return self._check_storage_need("food_ingredient", "food_fish", 3)
    # ...기존 조건들...
    elif condition == "my_new_condition":
        return self._check_storage_need("category", "item_uid", fallback_threshold)
    return False
```

---

## 도구 관리 패턴

벌목, 낚시, 청소 등 **도구가 필요한 활동**의 공통 패턴입니다.

### Phase 흐름

```
idle → getting_tool → [작업 phase] → returning_tool → idle
```

### 코드 패턴

```python
def handle_my_activity(agent, entry):
    phase = agent._activity_phase

    if phase == "idle":
        # 1. 도구 탐색 (capability 기반)
        tool = agent._find_tool_by_capability("can:my_cap")
        if not tool:
            agent._set_tool_missing_flag("can:my_cap")
            agent._skip_dynamic_activity(entry)
            return

        agent._clear_tool_missing_flag("can:my_cap")
        agent._activity_state["tool"] = tool

        # 2. 작업 대상 탐색
        target = find_work_target(agent)
        if not target:
            return  # "할 일 없음" 폴백

        agent._activity_state["work_target"] = target

        if tool["source"] == "inventory":
            agent._activity_phase = "going_to_work"  # 이미 소지
        else:
            agent._activity_phase = "getting_tool"    # 가져와야 함

    elif phase == "getting_tool":
        tool = agent._activity_state.get("tool")
        target = tool.get("location")
        if not target:
            from .helpers import resolve_storage_container
            target = resolve_storage_container(agent, "tool")

        if agent._is_at(target):
            # 도구 픽업
            container_id = tool.get("container_id") or target.get("object_id")
            morld.remove_item(container_id, tool["item_id"], 1)
            morld.give_item(agent.unit_id, tool["item_id"], 1)
            agent._activity_phase = "going_to_work"
            agent._action_taken = True
        else:
            agent._move_to(target, "도구 찾기")

    elif phase == "going_to_work":
        # ... 이동 → 도착 시 작업 → returning_tool ...

    elif phase == "returning_tool":
        tool = agent._activity_state.get("tool")
        item_id = tool["item_id"] if tool else None

        from .helpers import resolve_storage_container
        target = resolve_storage_container(agent, "tool")
        if not target:
            agent._activity_phase = "idle"
            agent._action_taken = True
            return

        if agent._is_at(target):
            if item_id:
                morld.remove_item(agent.unit_id, item_id, 1)
                morld.give_item(target["object_id"], item_id, 1)
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "도구 반납")
```

---

## 체크리스트: 신규 활동 추가

1. **`think/activities/` 에 핸들러 모듈 생성**
   - `handle_X(agent, entry)` 시그니처
   - Phase별 분기 + 헬퍼 함수

2. **`think/activities/__init__.py`에 등록**
   ```python
   from .my_module import handle_my_activity
   ACTIVITY_HANDLERS["활동명"] = handle_my_activity
   ```

3. **NPC 스케줄에 추가**
   ```python
   {"name": "활동명", "start": N*_M, "end": M*_M, "activity": "활동명"}
   ```

4. **(선택) 동적 스케줄 조건 추가**
   - `_evaluate_condition()`에 조건 추가
   - 스케줄에 `"dynamic": True, "candidates": [...]` 사용

5. **(선택) 보관 기준치 설정**
   - 컨테이너 오브젝트에 `need:{item_uid}` prop 추가
   - `_check_storage_need()` 호출 시 자동 적용

6. **(선택) 도구 필요 시**
   - `_find_tool_by_capability("can:X")` 사용
   - getting_tool / returning_tool phase 추가

---

## 기존 핸들러 레퍼런스

| 활동 | 파일 | Phase 흐름 | 특징 |
|------|------|-----------|------|
| 소등/점등 | `lights.py` | idle → going → idle (반복) | 방 순회, 열원 제외 |
| 벌목 | `chop.py` | idle → getting_tool → going_to_tree → returning_tool → idle | 도구 관리 (can:chop) |
| 낚시 | `fish.py` | idle → getting_tool → going_to_spot → going_to_storage → returning_tool → idle | 도구 + 보관 |
| 채집 | `gather.py` | idle → going_to_bush → going_to_storage → idle | 보관소 저장 |
| 요리 | `cook.py` | idle → going_to_storage → going_to_stove → idle | 재료 가져오기 → 조리 |
| 청소 | `clean.py` | idle → getting_tool → going_to_room (반복) → returning_tool → idle | 도구 + 오염 방 순회 |
| 물자수집 | `scavenge.py` | idle → going_to_resource → going_to_storage → idle | ScavengeableObject 탐색 |
| 정원 | `garden_activity.py` | idle → getting_tool → going_to_garden → working → storing_harvest → returning_tool → idle | 7-phase, 도구+보관 |
| 연료수집 | `fuel.py` | idle → going_to_tree → going_to_heat_source → idle | 나뭇가지 줍기 → 열원 장전 |

---

## FAQ

### Q: 순찰/산책처럼 돌아다니는 활동을 만들려면?
`_WANDER_ACTIVITIES` frozenset에 활동 이름을 추가하면, `_handle_default_activity()`가 자동으로 `_do_wander()`를 사용합니다. 별도 핸들러 작성 불필요.

### Q: handler가 action을 만들지 못하면?
`_handle_schedule()`의 디스패치 루프가 자동으로 "할 일 없음" idle job을 삽입합니다. handler 안에서 명시적으로 `return`만 해도 안전합니다.

### Q: dynamic entry에서 handler가 실패하면?
`agent._skip_dynamic_activity(entry)`를 호출하면 다음 candidate로 넘어갑니다. 모든 candidate가 실패하면 "할 일 없음" 폴백.

### Q: 다른 region의 보관소를 사용하려면?
`resolve_storage_container()`는 현재 `agent._get_home_region()` 내에서만 탐색합니다. cross-region 탐색이 필요하면 직접 `_location_objects`를 순회해야 합니다.

### Q: 새 아이템 카테고리를 추가하려면?
1. 아이템 클래스에 `category = "my_category"` 설정
2. 컨테이너 오브젝트에 `"storage:my_category": 1` prop 추가
3. `store_npc_items(agent, categories=["my_category"])` 호출
