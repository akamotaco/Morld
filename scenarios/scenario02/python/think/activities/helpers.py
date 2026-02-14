"""활동 핸들러 공통 유틸

find_npc_food / find_food_in_container — 음식 탐색 (eat, gather, cook 공용)
store_food_items — NPC 인벤토리 → 저장소 일괄 이동
resolve_storage_container — storage:{category} prop 기반 보관소 동적 탐색
store_npc_items — 카테고리 기반 보관 (현재 위치 컨테이너에 저장)
find_stove_location — 화로/아궁이 위치 탐색
get_object_x_from_info — 오브젝트 x 좌표 조회
find_indoor_room — 거처 실내 방 탐색
find_polluted_room — 오염된 거처 내 방 탐색
"""
import morld


def find_npc_food(unit_id):
    """NPC 인벤토리에서 음식 아이템 찾기

    Returns:
        {"item_id": int, "unique_id": str, "satiety": int} 또는 None
    """
    from assets.registry import get_unique_id, get_item_class
    inventory = morld.get_unit_inventory(unit_id)
    if not inventory:
        return None
    for item_id, count in inventory.items():
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        if uid:
            cls = get_item_class(uid)
            if cls and getattr(cls, 'food_satiety', 0) > 0:
                return {"item_id": item_id, "unique_id": uid, "satiety": cls.food_satiety}
    return None


def find_food_in_container(container_id):
    """컨테이너에서 음식 아이템 unique_id 찾기

    Returns:
        str (unique_id) 또는 None
    """
    from assets.registry import get_unique_id, get_item_class
    inventory = morld.get_unit_inventory(container_id)
    if not inventory:
        return None
    for item_id, count in inventory.items():
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        if uid:
            cls = get_item_class(uid)
            if cls and getattr(cls, 'food_satiety', 0) > 0:
                return uid
    return None


def store_food_items(agent):
    """NPC 인벤토리의 모든 음식 아이템을 저장소에 보관 (하위 호환)"""
    store_npc_items(agent, categories=["food", "food_ingredient", "drink_ingredient"])


def resolve_storage_container(agent, category):
    """storage:{category} prop을 가진 컨테이너를 거처 내에서 탐색

    Args:
        agent: NPC agent
        category: 아이템 카테고리 (예: "food_ingredient", "material", "tool")

    Returns:
        {"region_id", "location_id", "x", "object_id"} 또는 None

    탐색 순서: home_region 내 오브젝트
    """
    from assets.objects import _location_objects

    home_region = agent._get_home_region()
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            if morld.get_unit_prop(obj_id, f"storage:{category}"):
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": get_object_x_from_info(obj_id),
                    "object_id": obj_id,
                }
    return None


def store_npc_items(agent, categories=None):
    """NPC 인벤토리의 보관 가능 아이템을 현재 위치 컨테이너에 저장

    컨테이너와 같은 위치에 있어야 함 (이동은 caller 책임).
    각 아이템의 category와 컨테이너의 storage:{category} prop을 매칭.

    Args:
        agent: NPC agent
        categories: 저장할 카테고리 제한 (None=전부)

    Returns:
        int: 저장한 아이템 종류 수
    """
    from assets.registry import get_unique_id, get_item_class
    from assets.objects import get_instance, _location_objects

    loc = morld.get_unit_location(agent.unit_id)
    if not loc:
        return 0

    r, l = loc[0], loc[1]
    obj_ids = _location_objects.get((r, l), [])

    inv = morld.get_unit_inventory(agent.unit_id)
    if not inv:
        return 0

    stored = 0
    for item_id, count in list(inv.items()):
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        if not uid:
            continue
        cls = get_item_class(uid)
        if not cls:
            continue
        cat = getattr(cls, 'category', None)
        if not cat:
            continue
        if categories and cat not in categories:
            continue
        # 해당 카테고리를 받는 컨테이너 찾기
        for obj_id in obj_ids:
            if morld.get_unit_prop(obj_id, f"storage:{cat}"):
                obj = get_instance(obj_id)
                if obj:
                    obj.npc_store_item(agent.unit_id, uid, count)
                    stored += 1
                break
    return stored


def find_stove_location(agent):
    """화로/아궁이 위치 탐색 (거처 내)"""
    from assets.objects import _location_objects, get_instance
    from assets.objects.furniture import Stove

    home_region = agent._get_home_region()
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, Stove):
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": get_object_x_from_info(obj_id),
                    "object_id": obj_id,
                }
    return None


def get_object_x_from_info(obj_id):
    """오브젝트의 x 좌표 조회"""
    info = morld.get_unit_info(obj_id)
    if info:
        return info.get("x", 0)
    return 0


def find_indoor_room(agent):
    """거처 실내 방 찾기 (아직 청소하지 않은 방)"""
    from assets.objects import _location_objects

    cleaned = agent._activity_state.get("cleaned", set())
    sleep = agent._locations.get("sleep")
    home_region = agent._get_home_region()
    sleep_l = sleep["location_id"] if sleep else None

    for (r, l) in _location_objects.keys():
        if r != home_region:
            continue
        if l in cleaned:
            continue
        if sleep_l is not None and not morld.is_same_building(r, l, home_region, sleep_l):
            continue
        loc_info = morld.get_location_info(r, l)
        if loc_info and loc_info.get("is_indoor", False):
            return {"region_id": r, "location_id": l, "x": 0}
    return None


def find_garden_location(agent):
    """텃밭(GardenBed) 위치 탐색 (거처 내)"""
    from assets.objects import _location_objects, get_instance
    from assets.objects.garden import GardenBed

    home_region = agent._get_home_region()
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, GardenBed):
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": get_object_x_from_info(obj_id),
                    "object_id": obj_id,
                }
    return None


def find_polluted_room(agent):
    """오염도가 있는 거처 내 방 찾기 (아직 청소하지 않은 방)"""
    import pollution

    cleaned = agent._activity_state.get("cleaned", set())
    home_region = agent._get_home_region()
    sleep = agent._locations.get("sleep")
    sleep_l = sleep["location_id"] if sleep else None

    for key, data in pollution._location_pollution.items():
        r, l = key
        if r != home_region:
            continue
        if l in cleaned:
            continue
        if data["current"] <= 0:
            continue
        if sleep_l is not None and not morld.is_same_building(r, l, home_region, sleep_l):
            continue
        return {"region_id": r, "location_id": l, "x": 0}
    return None
