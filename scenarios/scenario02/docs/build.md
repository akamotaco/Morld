# 건축/파괴 시스템

## 개요

플레이어와 NPC가 오브젝트를 건축하고, 방(location)을 건설/확장/파괴할 수 있는 시스템.

**핵심 모듈:**
- `build.py` — 건축/파괴 로직 (레시피, 재료 확인, 생성/제거)
- `assets/objects/construction.py` — 건설현장 오브젝트 (ConstructionSite)

**관련 시스템:**
- [craft.md](craft.md) — 크래프팅 (아이템 제작)
- [terrain.md](terrain.md) — 지형 시스템 (Region/Location/Gate)
- [ground.md](ground.md) — 바닥 오브젝트 (파괴 시 아이템 drop)

---

## 1. 건축 레시피

### BuildRecipe 클래스

```python
class BuildRecipe:
    unique_id: str           # 레시피 고유 ID
    name: str                # 표시 이름
    type: str                # "object" | "location" | "expand"
    tool_category: str       # 필요 도구 카테고리
    materials: list          # [(item_uid, count), ...]
    result_class: type       # Object 서브클래스 (type="object"일 때)
    base_length: int         # 방 기본 크기 or 확장량
    progress_per_build: int  # 1회 작업당 진척도 증가량 (기본 10)
    indoor: bool             # 실내 여부 (기본 True)
```

### 레시피 등록/조회

```python
import build

# 레시피 등록 (챕터 init에서)
build.register_recipe(BuildRecipe(
    unique_id="cabin",
    name="오두막",
    recipe_type="location",
    tool_category="construction",
    materials=[("plank", 10), ("branch", 5)],
    base_length=50,
    progress_per_build=20,
))

# 조회
recipe = build.get_recipe("cabin")
recipes = build.get_recipes_for_tool("construction")
```

---

## 2. 오브젝트 건축

재료를 소비하여 오브젝트를 즉시 생성.

```python
success, obj_id, msg = build.build_object(
    builder_id,              # 건축자 unit_id
    recipe_id,               # 레시피 unique_id
    region_id, location_id,  # 배치 위치
    x                        # X 좌표
)
```

**처리 흐름:**
1. 레시피 검증 (`type == "object"`, `result_class` 존재)
2. 재료 확인 (`morld.has_item`)
3. 재료 소비 (`morld.remove_item`)
4. 오브젝트 생성 (`result_class().instantiate()`)
5. `건축:소유자` prop 설정

---

## 3. 방 건설

2단계 프로세스: **뼈대 건설** → **재료 투입 (진척도)**

### 3-1. 뼈대 건설

```python
success, region_id, location_id, msg = build.build_location_frame(
    builder_id,
    source_region, source_location,  # 출입구가 생기는 위치
    gate_x,                          # gate X 좌표
    recipe_id="cabin",               # 레시피 (선택)
    room_name="오두막",               # 방 이름 (선택)
)
```

**처리 흐름:**
1. 새 location 생성 (`base_length`, `indoor`, `geometry="line"`)
2. 양방향 gate 생성 (source ↔ new)
3. ConstructionSite 오브젝트 자동 배치
4. Props 설정: `건설:진척도=0`, `건설:소유자`, `건설:레시피`

### 3-2. 재료 투입 (진척도 상승)

```python
success, new_progress, msg = build.build_location_progress(
    builder_id,
    site_id,                         # ConstructionSite의 unit_id
    materials_used                   # [(item_uid, count), ...]
)
```

**처리 흐름:**
1. 현재 진척도 확인 (이미 100이면 거부)
2. 재료 확인 → 소비
3. 진척도 += `recipe.progress_per_build` (기본 10)
4. 100 도달 시 건설 완료

### 3-3. ConstructionSite 오브젝트

```python
class ConstructionSite(Object):
    unique_id = "construction_site"
    name = "건설현장"
    actions = [
        "call:build_progress:건설",       # 재료 투입
        "call:check_progress:진척도 확인", # 상태 확인
    ]
```

- `build_progress()`: 재료 목록 표시 → 확인 → `build.build_location_progress()` 호출
- `check_progress()`: 현재 진척도/소유자/필요 재료 표시

---

## 4. 방 확장

완성된 방의 length를 증가.

```python
success, new_length, msg = build.expand_location(
    builder_id,
    region_id, location_id,
    amount,                 # 증가량
    materials               # [(item_uid, count), ...]
)
```

---

## 5. 파괴

### 5-1. 오브젝트 파괴

```python
success, msg = build.destroy_object(destroyer_id, object_id)
```

**조건:** 소유자만 파괴 가능 (`건축:소유자` prop)

**처리:**
1. 소유권 확인
2. 오브젝트 인벤토리 → 바닥 drop (`ground.drop_item_at`)
3. Python 레지스트리 정리 (`_instances`, `_location_objects`)
4. C# 유닛 제거 (`morld.remove_unit`)

### 5-2. 방 파괴

```python
success, msg = build.destroy_location(destroyer_id, region_id, location_id)
```

**조건:**
- 소유자만 파괴 가능 (`location.owner`)
- 방 안에 유닛 없어야 함
- gate가 정확히 1개여야 함 (막다른 방만 파괴 가능)
- 파괴자는 방 밖에 있어야 함

**처리:**
1. 조건 검증
2. Python 레지스트리 정리 (`_location_objects`)
3. `morld.remove_location()` — location + 양방향 gate 제거

---

## 6. 위치 이동 (move_x)

플레이어가 location 내 X 좌표를 변경하는 기능. 건설 위치 지정 등에 사용.

### UI (Python)

`get_action_text()`에서 "위치 이동" 토글 메뉴 생성:

```
행동:
  ▶위치 이동 (X=50)
   [hidden=move_x]
     -1  +1
     -5  +5
     -10  +10
     -50  +50
   [/hidden=move_x]
```

- **Line geometry** (직선): `clamp(0, length)` — 경계에서 멈춤
- **Ring geometry** (원형): `% loc_length` — 경계 순환
- 앉기/눕기 상태에서 숨김 (`can_move` 체크)

### C# 핸들러

`MetaActionHandler.Navigation.cs`의 `HandleMoveXAction()`:

```
move_x:{targetX} → player.PositionX = targetX (즉시, 시간 소비 없음)
```

- 앉은 상태 체크 (`seated_on` prop)
- `CurrentMovement` 초기화
- UI 갱신 (`RequestUpdateDisplay`)

---

## 7. Props 정리

| Prop | 대상 | 값 | 용도 |
|------|------|---|------|
| `건축:소유자` | 오브젝트 | 건축자 이름 | 파괴 권한 |
| `건설:진척도` | ConstructionSite | 0-100 | 건설 진행도 |
| `건설:소유자` | ConstructionSite | 건축자 이름 | 표시용 |
| `건설:레시피` | ConstructionSite | recipe unique_id | 재료/진척도 참조 |

---

## 8. 조회 API

```python
build.get_construction_progress(site_id)  # 진척도 (0-100)
build.is_construction_complete(site_id)   # 완료 여부 (bool)
```

---

## 9. 챕터 전환

`build.reset()` — `_recipes` 딕셔너리 초기화.
`chapters/__init__.py`의 `load_chapter()`에서 호출.

---

## 10. 테스트

`tests/test_build.py` — mock_morld 기반 27개 테스트 케이스:

| 테스트 그룹 | 케이스 수 | 내용 |
|------------|----------|------|
| TestRecipe | 3 | 레시피 등록/조회/도구 필터 |
| TestBuildObject | 3 | 오브젝트 건축 성공/재료부족/소유자 |
| TestBuildLocationFrame | 3 | 뼈대 생성/건설현장/ID 자동배정 |
| TestBuildLocationProgress | 4 | 진척도 상승/완료/중복완료/재료부족 |
| TestExpandLocation | 2 | 확장 성공/재료부족 |
| TestDestroyObject | 4 | 파괴 성공/비소유자/인벤토리drop/레지스트리정리 |
| TestDestroyLocation | 5 | 방파괴 성공/비소유자/유닛있음/gate복수/내부파괴 |
| TestHelpers | 2 | 진척도 조회/완료 판정 |
| TestReset | 1 | 챕터 전환 리셋 |

```bash
cd scenarios/scenario02/python/tests
python -m pytest test_build.py -v
```
