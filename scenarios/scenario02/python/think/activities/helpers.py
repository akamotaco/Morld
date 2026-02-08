"""활동 핸들러 공통 유틸

find_npc_food / find_food_in_container — 음식 탐색 (eat, gather, cook 공용)
store_food_items — NPC 인벤토리 → 저장소 일괄 이동
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
    """NPC 인벤토리의 모든 음식 아이템을 저장소에 보관"""
    from assets.registry import get_instance_id, get_unique_id, get_item_class
    from assets.objects import get_instance

    storage_id = get_instance_id(agent.food_storage_unique_id)
    if not storage_id:
        return
    obj = get_instance(storage_id)
    if not obj:
        return

    inventory = morld.get_unit_inventory(agent.unit_id)
    if not inventory:
        return

    for item_id, count in list(inventory.items()):
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        if uid:
            cls = get_item_class(uid)
            if cls and getattr(cls, 'food_satiety', 0) > 0:
                obj.npc_store_item(agent.unit_id, uid, count)


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
    sleep = getattr(agent, "sleep_location", None)
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


def find_polluted_room(agent):
    """오염도가 있는 거처 내 방 찾기 (아직 청소하지 않은 방)"""
    import pollution

    cleaned = agent._activity_state.get("cleaned", set())
    home_region = agent._get_home_region()
    sleep = getattr(agent, "sleep_location", None)
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
