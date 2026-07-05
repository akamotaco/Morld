# build.py — 건축/파괴 시스템
#
# 오브젝트 건축: 재료 소비 → 오브젝트 생성
# 방 건설: 뼈대 세우기 → 재료 투입 → 진척도 상승 → 완성
# 방 확장: 완성된 방의 length 증가
# 오브젝트 파괴: 소유 확인 → 인벤토리 바닥 drop → 제거
# 방 파괴: 소유 확인 → 유닛 없음 + gate 1개 → gate + location 제거

import morld
import map_coords


def get_or_create_item_id(item_uid):
    """assets.registry 위임 (lazy import).

    Why lazy: 엔진 → 시나리오(assets) 의존은 pi-world 의존성 규칙 위반.
    톱레벨 import면 시나리오 없는 환경(엔진 단독 테스트)에서 모듈 로드 자체가
    실패한다. 구조적 해소(주입/레지스트리 역전)는 restructure-plan P5 참조.
    """
    from assets.registry import get_or_create_item_id as _impl
    return _impl(item_uid)


# ========================================
# 건축 레시피
# ========================================

class BuildRecipe:
    """건축 레시피 데이터"""

    __slots__ = (
        "unique_id", "name", "type", "tool_category",
        "materials", "result_class", "base_length",
        "progress_per_build", "indoor",
    )

    def __init__(self, unique_id, name, recipe_type, tool_category,
                 materials=None, result_class=None, base_length=1,
                 progress_per_build=10, indoor=True):
        self.unique_id = unique_id
        self.name = name
        self.type = recipe_type          # "object" | "location" | "expand"
        self.tool_category = tool_category
        self.materials = materials or []  # [(item_uid, count), ...]
        self.result_class = result_class  # Object subclass (type=object)
        self.base_length = base_length    # 방 기본 크기 or 확장량
        self.progress_per_build = progress_per_build
        self.indoor = indoor


_recipes = {}  # unique_id → BuildRecipe


def register_recipe(recipe):
    """레시피 등록 (시나리오/챕터 init에서 호출)"""
    _recipes[recipe.unique_id] = recipe


def get_recipe(unique_id):
    """레시피 조회"""
    return _recipes.get(unique_id)


def get_recipes_for_tool(tool_category):
    """도구 카테고리에 맞는 레시피 목록"""
    return [r for r in _recipes.values() if r.tool_category == tool_category]


def get_all_recipes():
    """등록된 전체 레시피 반환"""
    return dict(_recipes)


# ========================================
# 오브젝트 건축
# ========================================

def build_object(builder_id, recipe_id, region_id, location_id, x):
    """재료 확인 → 소비 → 오브젝트 생성

    Returns: (success, object_id or None, message)
    """
    recipe = get_recipe(recipe_id)
    if recipe is None:
        return False, None, "알 수 없는 레시피"
    if recipe.type != "object":
        return False, None, "오브젝트 건축 레시피가 아님"
    if recipe.result_class is None:
        return False, None, "결과 오브젝트 미정의"

    # 재료 확인
    for item_uid, count in recipe.materials:
        item_id = get_or_create_item_id(item_uid)
        if item_id is None or not morld.has_item(builder_id, item_id, count):
            return False, None, f"재료 부족: {item_uid}"

    # 재료 소비
    for item_uid, count in recipe.materials:
        item_id = get_or_create_item_id(item_uid)
        morld.remove_item(builder_id, item_id, count)

    # 오브젝트 생성
    obj = recipe.result_class()
    obj_id = morld.create_id("unit")
    obj.instantiate(obj_id, region_id, location_id, x)

    from assets.objects import register_location_object
    register_location_object(region_id, location_id, obj_id)

    # 소유자 설정
    builder_info = morld.get_unit_info(builder_id)
    if builder_info:
        morld.set_unit_prop(obj_id, "건축:소유자",
                            builder_info.get("name", ""))

    return True, obj_id, "건축 완료"


# ========================================
# 방 건설 (뼈대)
# ========================================

def build_location_frame(builder_id, source_region, source_location, gate_x,
                         recipe_id=None, room_name=None):
    """현재 위치에 새 방 생성 (뼈대)

    1. 새 location 생성 (length=1)
    2. 양방향 gate 생성 (source ↔ new)
    3. 건설현장 오브젝트 배치

    Args:
        builder_id: 건설자 unit_id (None이면 원격 지정)

    Returns: (success, new_region_id, new_location_id, site_id, message)
    """
    recipe = get_recipe(recipe_id) if recipe_id else None

    owner_name = ""
    if builder_id:
        builder_info = morld.get_unit_info(builder_id)
        owner_name = builder_info.get("name", "") if builder_info else ""

    # 방 이름
    name = room_name or (recipe.name if recipe else None) or (
        f"{owner_name}의 방" if owner_name else "새 방"
    )

    # 다음 사용 가능한 location ID
    new_local_id = _next_location_id(source_region)

    indoor = recipe.indoor if recipe else True
    base_length = recipe.base_length if recipe else 1

    # 방 생성
    morld.add_location(
        source_region, new_local_id, name,
        indoor=indoor, length=base_length, geometry="line",
        owner=owner_name
    )

    # 양방향 gate
    src_gate_id = _next_gate_id(source_region, source_location)
    new_gate_id = 0
    morld.add_gate(source_region, source_location, src_gate_id,
                   gate_x, source_region, new_local_id, 0)
    morld.add_gate(source_region, new_local_id, new_gate_id,
                   0, source_region, source_location, gate_x)

    # 건설현장 오브젝트 배치
    from assets.objects.construction import ConstructionSite
    from assets.objects import register_location_object

    site = ConstructionSite()
    site_id = morld.create_id("unit")
    site.instantiate(site_id, source_region, new_local_id, x=0)
    register_location_object(source_region, new_local_id, site_id)

    morld.set_unit_prop(site_id, "건설:진척도", 0)
    morld.set_unit_prop(site_id, "건설:소유자", owner_name or "operator")
    if recipe_id:
        morld.set_unit_prop(site_id, "건설:레시피", recipe_id)

    # 지도 좌표 자동 배치 + 전체 재조정
    map_coords.register(source_region, new_local_id)
    map_coords.rebuild(source_region)

    return True, source_region, new_local_id, site_id, "뼈대 건설 완료"


# ========================================
# 방 건설 (진척도)
# ========================================

def build_location_progress(builder_id, site_id, materials_used):
    """건설현장에 재료 투입 → 진척도 상승

    Args:
        materials_used: [(item_uid, count), ...] 투입할 재료

    Returns: (success, new_progress, message)
    """
    progress = morld.get_unit_prop(site_id, "건설:진척도")
    if progress is None:
        return False, 0, "건설현장이 아님"
    if progress >= 100:
        return False, progress, "이미 완성됨"

    # 재료 확인
    for item_uid, count in materials_used:
        item_id = get_or_create_item_id(item_uid)
        if item_id is None or not morld.has_item(builder_id, item_id, count):
            return False, progress, f"재료 부족: {item_uid}"

    # 재료 소비
    for item_uid, count in materials_used:
        item_id = get_or_create_item_id(item_uid)
        morld.remove_item(builder_id, item_id, count)

    # 진척도 상승
    recipe_id = morld.get_unit_prop(site_id, "건설:레시피") or ""
    recipe = get_recipe(recipe_id)
    increase = recipe.progress_per_build if recipe else 10

    new_progress = min(100, progress + increase)
    morld.set_unit_prop(site_id, "건설:진척도", new_progress)

    if new_progress >= 100:
        return True, 100, "건설 완료!"
    return True, new_progress, f"진척도: {new_progress}%"


# ========================================
# 방 확장
# ========================================

def expand_location(builder_id, region_id, location_id, amount, materials):
    """방 크기(length) 증가

    Returns: (success, new_length, message)
    """
    # 재료 확인
    for item_uid, count in materials:
        item_id = get_or_create_item_id(item_uid)
        if item_id is None or not morld.has_item(builder_id, item_id, count):
            return False, 0, f"재료 부족: {item_uid}"

    # 재료 소비
    for item_uid, count in materials:
        item_id = get_or_create_item_id(item_uid)
        morld.remove_item(builder_id, item_id, count)

    # length 증가
    info = morld.get_location_info(region_id, location_id)
    cur_length = info.get("length", 0) if info else 0
    new_length = cur_length + amount
    morld.set_location_length(region_id, location_id, new_length)

    return True, new_length, f"방 확장: {cur_length} → {new_length}"


# ========================================
# 오브젝트 파괴
# ========================================

def destroy_object(destroyer_id, object_id):
    """소유 확인 → 인벤토리 바닥 drop → 오브젝트 제거

    Returns: (success, message)
    """
    # 소유권 확인
    owner = morld.get_unit_prop(object_id, "건축:소유자") or ""
    destroyer_info = morld.get_unit_info(destroyer_id)
    destroyer_name = destroyer_info.get("name", "") if destroyer_info else ""
    if owner and owner != destroyer_name:
        return False, "소유자만 파괴 가능"

    # 인벤토리 → 바닥 drop
    import ground as ground_module
    inventory = morld.get_unit_inventory(object_id)
    if inventory:
        for item_id_str, count in inventory.items():
            ground_module.drop_item_at(object_id, int(item_id_str), count)

    # Python 레지스트리 정리
    from assets.objects import _instances, _location_objects
    loc = morld.get_unit_location(object_id)
    if loc:
        key = (loc[0], loc[1])
        if key in _location_objects:
            _location_objects[key] = [
                x for x in _location_objects[key] if x != object_id
            ]
    _instances.pop(object_id, None)

    # C# 유닛 제거
    morld.remove_unit(object_id)

    return True, "파괴 완료"


# ========================================
# 방 파괴
# ========================================

def destroy_location(destroyer_id, region_id, location_id):
    """조건 검증 → gate + location 제거

    조건:
    - 파괴자가 소유자
    - location 내 유닛(character/object) 없음
    - gate가 정확히 1개
    - 파괴자는 해당 방 밖에 있어야 함

    Returns: (success, message)
    """
    # 소유권 확인
    loc_info = morld.get_location_info(region_id, location_id)
    if not loc_info:
        return False, "존재하지 않는 방"

    owner = loc_info.get("owner", "")
    destroyer_info = morld.get_unit_info(destroyer_id)
    destroyer_name = destroyer_info.get("name", "") if destroyer_info else ""
    if owner and owner != destroyer_name:
        return False, "소유자만 파괴 가능"

    # 파괴자가 밖에 있는지 확인
    destroyer_loc = morld.get_unit_location(destroyer_id)
    if (destroyer_loc
            and destroyer_loc[0] == region_id
            and destroyer_loc[1] == location_id):
        return False, "방 안에서는 파괴 불가"

    # 유닛 확인 (캐릭터 + 오브젝트)
    units = morld.get_units_at_location(region_id, location_id)
    if units:
        return False, "방 안에 유닛이 있어 파괴 불가"

    # gate 개수 확인
    gates = morld.get_location_gates(region_id, location_id)
    if len(gates) != 1:
        return False, f"gate가 {len(gates)}개 — 1개일 때만 파괴 가능"

    # Python 레지스트리 정리 (location에 등록된 오브젝트)
    from assets.objects import _location_objects
    key = (region_id, location_id)
    _location_objects.pop(key, None)

    # 지도 좌표 삭제 + 전체 재조정
    map_coords.remove(region_id, location_id)

    # location 제거 (C# API가 gate도 함께 정리)
    morld.remove_location(region_id, location_id)

    # 남은 좌표 재조정
    map_coords.rebuild(region_id)

    return True, "방 파괴 완료"


# ========================================
# 조회 API
# ========================================

def get_construction_progress(site_id):
    """건설현장 진척도 조회 (0-100)"""
    return morld.get_unit_prop(site_id, "건설:진척도") or 0


def is_construction_complete(site_id):
    """건설 완료 여부"""
    return get_construction_progress(site_id) >= 100


def designate_build(recipe_id, source_region, source_location, gate_x,
                    room_name=None):
    """원격 건축 지정 (builder_id=None)

    오퍼레이터/플레이어가 위치를 지정하고, NPC가 실행.

    Returns: (success, region_id, location_id, site_id, msg)
    """
    return build_location_frame(
        None, source_region, source_location, gate_x,
        recipe_id=recipe_id, room_name=room_name,
    )


# ========================================
# 헬퍼
# ========================================

def _next_location_id(region_id):
    """region 내 다음 사용 가능한 location ID"""
    info = morld.get_region_info(region_id)
    if not info:
        return 0
    used = {loc["id"] for loc in info.get("locations", [])}
    lid = 0
    while lid in used:
        lid += 1
    return lid


def _next_gate_id(region_id, location_id):
    """location 내 다음 사용 가능한 gate ID"""
    gates = morld.get_location_gates(region_id, location_id)
    if not gates:
        return 0
    used = {g["gate_id"] for g in gates}
    gid = 0
    while gid in used:
        gid += 1
    return gid


# ========================================
# 챕터 전환
# ========================================

def reset():
    """챕터 전환 시 리셋"""
    _recipes.clear()
