# build.py - 건축 시스템 (시나리오03)
#
# 시나리오02 build.py의 간소화 버전.
# Location 건설만 지원 (Object 건설/확장/파괴는 미구현).
#
# 핵심 차이점:
# - 원격 건축 지정 (CRTConsole → build:designated prop)
# - 에이전트가 실행 (오퍼레이터는 지정만)
#
# Props:
#   건설:진척도  (int 0-100)
#   건설:레시피  (str recipe unique_id)
#   건설:소유자  (str builder name or "operator")

import morld
from assets.registry import get_or_create_item_id


# === Recipe Registry ===

_recipes = {}


class BuildRecipe:
    """건축 레시피"""
    def __init__(self, unique_id, name, materials, base_length=50,
                 progress_per_build=10, indoor=True, description=""):
        self.unique_id = unique_id
        self.name = name
        self.materials = materials          # {item_uid: count}
        self.base_length = base_length
        self.progress_per_build = progress_per_build
        self.indoor = indoor
        self.description = description


def register_recipe(recipe):
    """레시피 등록"""
    _recipes[recipe.unique_id] = recipe


def get_recipe(recipe_id):
    """레시피 조회"""
    return _recipes.get(recipe_id)


def get_all_recipes():
    """전체 레시피 목록"""
    return dict(_recipes)


def reset():
    """챕터 전환 시 초기화"""
    _recipes.clear()


# === Location Building ===

def build_location_frame(builder_id, source_region, source_location,
                         gate_x, recipe_id=None, room_name=None):
    """건설 뼈대 생성

    1. 새 Location 생성 (base_length)
    2. Gate 양방향 연결
    3. ConstructionSite 오브젝트 배치
    4. 진척도 prop 설정

    Args:
        builder_id: 건설 지시자 unit_id (또는 None: 원격 지정)
        source_region: 연결 원점 Region ID
        source_location: 연결 원점 Location ID
        gate_x: 원점에서의 Gate X 좌표
        recipe_id: 레시피 unique_id (None이면 빈 방)
        room_name: 방 이름 (None이면 레시피 이름 사용)

    Returns:
        (success, region_id, location_id, site_id, msg)
    """
    recipe = _recipes.get(recipe_id) if recipe_id else None

    # 이름 결정
    if room_name is None:
        room_name = recipe.name if recipe else "건설 중인 방"

    # Location ID 할당 (Region 내 최대 ID + 1)
    new_location_id = _next_location_id(source_region)

    # 길이
    base_length = recipe.base_length if recipe else 50
    is_indoor = recipe.indoor if recipe else True

    # Location 등록
    morld.add_location(
        source_region, new_location_id,
        room_name,
        is_indoor=is_indoor,
        length=base_length,
    )

    # Gate 양방향 연결
    new_gate_id = _next_gate_id(source_region, source_location)
    return_gate_id = _next_gate_id(source_region, new_location_id)

    morld.add_gate(source_region, source_location, new_gate_id,
                   gate_x, source_region, new_location_id, 0)
    morld.add_gate(source_region, new_location_id, return_gate_id,
                   base_length, source_region, source_location, gate_x)

    # ConstructionSite 오브젝트 배치
    from assets.objects.construction import ConstructionSite
    site = ConstructionSite()
    site_id = morld.create_id("unit")
    site.instantiate(site_id, source_region, new_location_id, x=0)

    # 진척도 prop 설정
    morld.set_unit_prop(site_id, "건설:진척도", 0)
    morld.set_unit_prop(site_id, "건설:레시피", recipe_id or "")

    owner_name = "operator"
    if builder_id:
        info = morld.get_unit_info(builder_id)
        if info:
            owner_name = info.get("name", "operator")
    morld.set_unit_prop(site_id, "건설:소유자", owner_name)

    print(f"[build] Frame created: {room_name} at R{source_region}:L{new_location_id}"
          f" (site_id={site_id})")

    return True, source_region, new_location_id, site_id, f"{room_name} 뼈대 건설 완료"


def build_location_progress(builder_id, site_id, materials_used=None):
    """건설 진척도 증가

    Args:
        builder_id: 건설자 unit_id
        site_id: ConstructionSite unit_id
        materials_used: [(item_uid, count), ...] 소비할 자재 (None이면 레시피에서 계산)

    Returns:
        (success, new_progress, msg)
    """
    progress = morld.get_unit_prop(site_id, "건설:진척도")
    if progress is None:
        return False, 0, "건설현장이 아닙니다"

    if progress >= 100:
        return False, 100, "이미 건설이 완료되었습니다"

    recipe_id = morld.get_unit_prop(site_id, "건설:레시피") or ""
    recipe = _recipes.get(recipe_id)

    # 자재 소비
    if materials_used:
        for item_uid, count in materials_used:
            item_id = get_or_create_item_id(item_uid)
            if item_id and builder_id:
                if not morld.has_item(builder_id, item_id, count):
                    return False, progress, f"{item_uid} 부족"
                morld.remove_item(builder_id, item_id, count)

    # 진척도 증가
    increment = recipe.progress_per_build if recipe else 10
    new_progress = min(100, progress + increment)
    morld.set_unit_prop(site_id, "건설:진척도", new_progress)

    if new_progress >= 100:
        print(f"[build] Construction complete! site_id={site_id}")
        return True, 100, "건설 완료!"

    print(f"[build] Progress: {progress} -> {new_progress} (site_id={site_id})")
    return True, new_progress, f"건설 진행: {new_progress}%"


def is_construction_complete(site_id):
    """건설 완료 여부"""
    progress = morld.get_unit_prop(site_id, "건설:진척도")
    return progress is not None and progress >= 100


def designate_build(recipe_id, source_region, source_location, gate_x):
    """원격 건축 지정 (CRTConsole에서 호출)

    builder_id=None으로 build_location_frame 호출.
    오퍼레이터가 지정하고, 에이전트가 실행.

    Returns:
        (success, region_id, location_id, site_id, msg)
    """
    return build_location_frame(
        builder_id=None,
        source_region=source_region,
        source_location=source_location,
        gate_x=gate_x,
        recipe_id=recipe_id,
    )


# === Internal Helpers ===

def _next_location_id(region_id):
    """Region 내 사용 가능한 다음 Location ID"""
    max_id = -1
    # Check existing locations (iterate up to reasonable max)
    for loc_id in range(100):
        info = morld.get_location_info(region_id, loc_id)
        if info is not None:
            max_id = loc_id
    return max_id + 1


def _next_gate_id(region_id, location_id):
    """Location 내 사용 가능한 다음 Gate ID"""
    # Simple approach: try IDs until one doesn't exist
    for gate_id in range(20):
        # MockMorld stores gates as (region_id, location_id, gate_id)
        # Check if this gate_id is already used
        key = (region_id, location_id, gate_id)
        # Access mock's internal state if available, otherwise just return a high ID
        if hasattr(morld, '_gates'):
            if key not in morld._gates:
                return gate_id
        else:
            return gate_id
    return 20


# === Demo Recipe Registration ===

def register_demo_recipes():
    """데모용 레시피 등록"""
    from quest import BUILD_RECIPES

    for recipe_id, data in BUILD_RECIPES.items():
        recipe = BuildRecipe(
            unique_id=recipe_id,
            name=data["name"],
            materials=data["materials"],
            base_length=data.get("result_length", 50),
            progress_per_build=data.get("progress_per_input", 10),
            description=data.get("description", ""),
        )
        register_recipe(recipe)

    print(f"[build] {len(BUILD_RECIPES)} demo recipes registered")
