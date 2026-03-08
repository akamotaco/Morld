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
all_recipes = build.get_all_recipes()  # {unique_id: BuildRecipe}
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
success, region_id, location_id, site_id, msg = build.build_location_frame(
    builder_id,                      # 건축자 unit_id (None이면 원격 지정)
    source_region, source_location,  # 출입구가 생기는 위치
    gate_x,                          # gate X 좌표
    recipe_id="cabin",               # 레시피 (선택)
    room_name="오두막",               # 방 이름 (선택)
)

# 원격 건축 지정 (builder_id=None) — 시나리오03 공유 패턴
success, r, l, site_id, msg = build.designate_build(
    "cabin", source_region, source_location, gate_x
)
```

**처리 흐름:**
1. 새 location 생성 (`base_length`, `indoor`, `geometry="line"`)
2. 양방향 gate 생성 (source ↔ new)
3. ConstructionSite 오브젝트 자동 배치
4. Props 설정: `건설:진척도=0`, `건설:소유자`, `건설:레시피`
5. `builder_id=None`이면 소유자를 "operator"로 설정

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
- `get_focus_text()`: 4단계 묘사 (미착공/초반/절반 이상/완료)

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
build.get_all_recipes()                   # 전체 레시피 dict
build.designate_build(recipe_id, ...)     # 원격 건축 지정
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

---

## 11. 방 명명 (Location Naming)

건축 시 또는 플레이어 소유 location에 이름을 지정/변경하는 기능.

> **Phase 1:** 프리셋 선택 방식
> **Phase 2 (미래):** 자유 텍스트 입력 (C# InputField 연동)

### 11-1. 프리셋 이름 목록

```python
# build.py — 명명 프리셋

ROOM_NAME_PRESETS = {
    # 주거
    "residential": [
        "침실", "거실", "작업실", "서재", "창고",
        "다락방", "지하실", "비밀 방",
    ],
    # 기능
    "functional": [
        "부엌", "욕실", "화장실", "세탁실", "건조실",
        "작업장", "대장간", "제련소", "양조장",
    ],
    # 야외 건축
    "outdoor": [
        "오두막", "헛간", "마구간", "우물", "망루",
        "초소", "울타리", "텃밭", "온실",
    ],
    # 커스텀 접두/접미 (Phase 2에서 조합)
    "prefix": [
        "{owner}의 ", "작은 ", "큰 ", "낡은 ", "새 ",
    ],
}

def get_name_presets(recipe_id=None):
    """레시피에 맞는 프리셋 목록 반환

    Args:
        recipe_id: 건축 레시피 ID (None이면 전체)

    Returns:
        list[str]: 선택 가능한 이름 리스트
    """
    recipe = get_recipe(recipe_id) if recipe_id else None

    if recipe and recipe.recipe_type == "location":
        # 레시피에 연결된 카테고리가 있으면 해당 카테고리만
        category = getattr(recipe, 'name_category', None)
        if category and category in ROOM_NAME_PRESETS:
            return list(ROOM_NAME_PRESETS[category])

    # 기본: 모든 카테고리 합침 (prefix 제외)
    result = []
    for key, names in ROOM_NAME_PRESETS.items():
        if key != "prefix":
            result.extend(names)
    return result
```

### 11-2. 건축 시 명명

`build_location_frame()` 호출 전에 이름 선택 UI를 표시:

```python
# assets/objects/construction.py 또는 player 건축 액션

def _select_room_name(builder_id, recipe_id=None):
    """방 이름 선택 UI (프리셋)

    Yields:
        선택된 이름 (str) 또는 None (취소)
    """
    presets = build.get_name_presets(recipe_id)

    # 소유자 이름으로 prefix 조합
    builder_info = morld.get_unit_info(builder_id)
    owner_name = builder_info.get("name", "") if builder_info else ""
    if owner_name:
        presets.insert(0, f"{owner_name}의 방")

    # 프리셋 선택 UI (call: 액션 목록)
    options = []
    for name in presets:
        options.append(f"call:select_name_{name}:{name}")

    yield ui.action_menu("방 이름 선택", options)
    # → 플레이어가 선택하면 해당 이름으로 건축 진행
```

**기존 흐름과의 통합:**

```
플레이어 "건축" 액션
  → 레시피 선택 (기존)
  → 재료 확인 (기존)
  → ★ 방 이름 선택 (프리셋 목록)
  → build_location_frame(room_name=선택된 이름)
  → 건설 시작
```

### 11-3. 소유 방 이름 변경

플레이어가 **자신이 소유한 location**의 이름을 변경:

```python
# build.py — 이름 변경 API

def rename_location(renamer_id, region_id, location_id, new_name):
    """소유 방 이름 변경

    Args:
        renamer_id: 변경 요청자 unit_id
        region_id: 대상 region
        location_id: 대상 location
        new_name: 새 이름

    Returns:
        (success: bool, msg: str)
    """
    # 1. location 정보 조회
    loc_info = morld.get_location_info(region_id, location_id)
    if not loc_info:
        return False, "해당 방을 찾을 수 없다."

    # 2. 소유권 확인
    owner = loc_info.get("owner", "")
    renamer_info = morld.get_unit_info(renamer_id)
    renamer_name = renamer_info.get("name", "") if renamer_info else ""

    if not owner or owner != renamer_name:
        return False, "소유자만 이름을 변경할 수 있다."

    # 3. 이름 변경 (C# API 호출)
    morld.set_location_name(region_id, location_id, new_name)

    morld.add_action_log(f"방 이름을 '{new_name}'(으)로 변경했다.")
    return True, new_name
```

**플레이어 액션:**

```python
# player.py 또는 location 액션 — 이름 변경
# 소유 location에 있을 때만 표시
"call:rename_location:방 이름 변경"

# 표시 조건:
#   1. 플레이어가 현재 있는 location의 owner == 플레이어 이름
#   2. can:rename_location == 1 (기본 ON)
```

**이름 변경 UI 흐름:**

```
플레이어 "방 이름 변경" 선택
  → 프리셋 목록 표시 (get_name_presets)
  → 플레이어 선택
  → rename_location() 호출
  → 성공 시 action_log에 표시
```

### 11-4. 필요한 C# API 추가

현재 Python에서 location 이름을 변경하는 API가 없으므로 추가 필요:

```csharp
// script_system_data_api.cs — 추가

morldModule.ModuleDict["set_location_name"] = new PyBuiltinFunction(
    "set_location_name", (args) =>
{
    int regionId = args[0].ToInt();
    int locationId = args[1].ToInt();
    string newName = args[2].ToString();

    var location = terrain.GetLocation(new LocationRef(regionId, locationId));
    if (location == null)
        return PyBool.False;

    location.Name = newName;
    return PyBool.True;
});
```

**API 시그니처:**

```python
# Python에서 호출
morld.set_location_name(region_id: int, location_id: int, name: str) -> bool
```

### 11-5. Props 추가

| Prop | 대상 | 값 | 용도 |
|------|------|---|------|
| `건축:원래이름` | — (location은 prop 미사용) | — | 불필요: Location.Name 직접 변경 |

> **주의:** Location은 Unit이 아니므로 `set_unit_prop()`을 사용할 수 없다.
> 이름 변경 이력이 필요하면 별도 Python dict로 관리.

### 11-6. Phase 2 — 자유 텍스트 입력 (미래)

```
Phase 2 구현 시:
  - C# InputField UI 추가 (TextUI에 텍스트 입력 필드)
  - Python API: morld.request_text_input(prompt) → 입력값 반환
  - 프리셋 목록 + "직접 입력" 옵션 추가
  - 금칙어 필터 (선택적)
  - 글자 수 제한 (최대 20자)
```
