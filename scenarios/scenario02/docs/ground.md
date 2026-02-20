# 바닥(Ground) 시스템

## 개요

Location은 inventory를 갖지 않음. "바닥" Object가 떨어진 아이템을 저장.

아이템 드롭 시에만 바닥 오브젝트를 동적 생성. Location의 `ground_type` 속성에 따라 적절한 종류로 생성. 인벤토리가 비면 자동 소멸.

---

## 바닥 종류 (assets/objects/grounds.py)

```python
class Ground(Object):
    item_visible = True  # 아이템 개수 표시
    actions = ["putinobject", "call:rough_sleep:노숙하기", ...]
```

| 실내 | 실외 | 도시 |
|------|------|------|
| GroundWooden | GroundDirt | GroundAsphalt |
| GroundStone | GroundGrass | GroundConcrete |
| GroundMarble | GroundForest | |
| GroundTile | GroundRocky | |

### Location별 바닥 종류 (ground_type)

각 Location 클래스에 `ground_type` 속성이 정의되어 있음. 동적 바닥 생성 시 참조.

| 실내 | 실외 | 도시 |
|------|------|------|
| `GroundWooden` (거실, 침실, 복도) | `GroundGrass` (마당) | `GroundAsphalt` (주유소, 주차장) |
| `GroundStone` (현관, 주방) | `GroundForest` (숲, 사냥터) | `GroundConcrete` (편의점, 은신처) |
| `GroundTile` (욕실, 화장실) | `GroundRocky` (강가) | |

```python
class Kitchen(Location):
    ground_type = "GroundStone"  # 동적 바닥 생성 시 이 종류로 생성
```

`ground_type` 미설정 → 범용 `DynamicGround("바닥")` fallback.

---

## 동적 바닥 관리 (ground.py)

> `ground.py` -- 순수 Python

### 병합 규칙

같은 Location 내 X좌표 거리 <= `MERGE_THRESHOLD`(3.0) -> 기존 바닥에 추가.
이를 초과하면 새 바닥 오브젝트 생성.

### 동작 흐름

```
아이템 드롭 요청
  -> ensure_ground_at(region, location, x)
     -> 거리 <= 3.0인 기존 바닥? -> 해당 바닥에 give_item
     -> 없으면 -> _create_ground() -> 새 DynamicGround 유닛 생성
  -> give_item(ground_id, item_id, count)

아이템 꺼내기 후
  -> check_empty_ground(ground_unit_id)
     -> 인벤토리 비었으면 -> _remove_ground() -> morld.remove_unit()
```

### DynamicGround 클래스

```python
class DynamicGround(Object):
    item_visible = True
    name = "바닥"
    actions = ["putinobject", ...]
    focus_text = {"default": "아이템이 놓여 있다."}
```

- `unique_id`는 런타임에 `"dynamic_ground:{unit_id}"` 형태로 설정
- 정적 `Ground`와 달리 노숙하기 액션 없음

### 환경 시스템 연동

동적 바닥도 일반 오브젝트로 생성되므로 `get_objects_at_location()`에 자동 포함.

- **초기 복사**: 생성 시 `_copy_env_props()`로 오염도/젖음 즉시 복사
- **이후 동기화**: 매시간 hourly 업데이트에서 자동 적용 (pollution, humidity)

### Python API

```python
import ground

ground.ensure_ground_at(region_id, location_id, x)   # 바닥 확보 (생성 or 기존) -> unit_id
ground.drop_item_at(unit_id, item_id, count, x=None)  # 유닛 위치에 아이템 드롭 -> ground_unit_id
ground.check_empty_ground(ground_unit_id)              # 비었으면 제거 -> bool
ground.get_grounds_at(region_id, location_id)          # 동적 바닥 목록 -> [{"unit_id", "x"}, ...]
ground.is_dynamic_ground(unit_id)                      # 동적 바닥 여부 -> bool
ground.register_ground(region_id, location_id, uid, x) # 챕터 초기화용 등록
ground.reset()                                         # 챕터 전환 초기화
```

### morld API

```python
morld.set_location_ground_id(region_id, location_id, ground_unit_id)
morld.get_location_ground_id(region_id, location_id)
```

### 챕터 전환 대응

`ground.reset()` -- `chapters/__init__.py`의 `load_chapter()`에서 자동 호출.
레지스트리 초기화 후 챕터 코드에서 `register_ground()`로 재등록.
