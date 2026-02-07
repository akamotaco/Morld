# think/activity_resolver.py - 활동 장소 동적 탐색
#
# sleep 시스템(_resolve_sleep_location)과 동일한 패턴.
# activity에 맞는 location을 동적으로 탐색.
#
# 사용법:
#   from think.activity_resolver import resolve_activity_location
#   target = resolve_activity_location(unit_id, "채집", home_region_id=0)
#   # -> {"region_id": 0, "location_id": 23, "x": 450, "object_id": 101}

import morld
from assets.objects import get_location_objects, get_instance


def resolve_activity_location(unit_id, activity, home_region_id):
    """
    활동에 맞는 장소를 동적 탐색

    Args:
        unit_id: NPC 유닛 ID
        activity: 활동 이름 ("채집", "사냥" 등)
        home_region_id: 탐색 대상 region ID

    Returns:
        {"region_id": int, "location_id": int, "x": int} or None
    """
    resolver = _ACTIVITY_RESOLVERS.get(activity)
    if resolver is None:
        return None
    return resolver(unit_id, home_region_id)


def _resolve_gather(unit_id, region_id):
    """채집: ResourceObject가 있는 location 탐색"""
    from assets.objects import _location_objects
    from assets.objects.nature import ResourceObject

    candidates = []
    for (r, l), obj_ids in _location_objects.items():
        if r != region_id:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, ResourceObject):
                count = obj.get_resource_count()
                if count > 0:
                    candidates.append({
                        "region_id": r,
                        "location_id": l,
                        "x": _get_object_x(obj_id),
                        "object_id": obj_id,
                        "resource_count": count,
                    })

    if not candidates:
        return None

    # 자원이 가장 많은 곳 선택
    candidates.sort(key=lambda c: -c["resource_count"])
    return candidates[0]


def _resolve_hunt(unit_id, region_id):
    """사냥: outdoor location 탐색 (forest region 우선)"""
    from assets.objects import _location_objects

    # 해당 region의 모든 location 탐색
    candidates = []
    seen_locations = set()

    for (r, l) in _location_objects.keys():
        if r != region_id:
            continue
        if l in seen_locations:
            continue
        seen_locations.add(l)

        loc_info = morld.get_location_info(r, l)
        if loc_info and not loc_info.get("is_indoor", True):
            candidates.append({
                "region_id": r,
                "location_id": l,
                "x": 0,
                "length": loc_info.get("length", 0),
            })

    if not candidates:
        return None

    # 첫 번째 outdoor location 반환
    return candidates[0]


def _resolve_patrol(unit_id, region_id):
    """순찰: outdoor location 탐색"""
    # 사냥과 동일한 탐색 (outdoor location)
    return _resolve_hunt(unit_id, region_id)


def _get_object_x(obj_id):
    """오브젝트의 x 좌표 조회"""
    info = morld.get_unit_info(obj_id)
    if info:
        return info.get("x", 0)
    return 0


def _resolve_chop(unit_id, region_id):
    """벌목: Tree 오브젝트(can_chop=True)가 있는 location 탐색"""
    from assets.objects import _location_objects
    from assets.objects.trees import Tree

    for (r, l), obj_ids in _location_objects.items():
        if r != region_id:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, Tree) and obj.can_chop():
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": _get_object_x(obj_id),
                    "object_id": obj_id,
                }
    return None


def _resolve_fish(unit_id, region_id):
    """낚시: FishingSpot + can_fish() 확인, 물고기 많은 곳 우선"""
    from assets.objects import _location_objects
    from assets.objects.outdoor import FishingSpot

    candidates = []
    for (r, l), obj_ids in _location_objects.items():
        if r != region_id:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, FishingSpot) and obj.can_fish():
                candidates.append({
                    "region_id": r,
                    "location_id": l,
                    "x": _get_object_x(obj_id),
                    "object_id": obj_id,
                    "fish_count": obj.get_fish_count(),
                })

    if not candidates:
        return None
    candidates.sort(key=lambda c: -c["fish_count"])
    return candidates[0]


def _resolve_read(unit_id, region_id):
    """독서: Bookshelf 오브젝트가 있는 location 탐색"""
    from assets.objects import _location_objects
    from assets.objects.furniture import Bookshelf

    for (r, l), obj_ids in _location_objects.items():
        if r != region_id:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, Bookshelf):
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": _get_object_x(obj_id),
                    "object_id": obj_id,
                }
    return None


def _resolve_scavenge(unit_id, region_id):
    """물자수집: ScavengeableObject 중 재고>0인 것 탐색"""
    from assets.objects import _location_objects
    from assets.objects.scavenge import ScavengeableObject

    candidates = []
    for (r, l), obj_ids in _location_objects.items():
        if r != region_id:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and isinstance(obj, ScavengeableObject):
                count = obj.get_item_count()
                if count > 0:
                    candidates.append({
                        "region_id": r,
                        "location_id": l,
                        "x": _get_object_x(obj_id),
                        "object_id": obj_id,
                        "item_count": count,
                    })

    if not candidates:
        return None
    # 아이템이 가장 많은 곳 선택
    candidates.sort(key=lambda c: -c["item_count"])
    return candidates[0]


# 활동 → resolver 함수 매핑
_ACTIVITY_RESOLVERS = {
    "채집": _resolve_gather,
    "사냥": _resolve_hunt,
    "순찰": _resolve_patrol,
    "벌목": _resolve_chop,
    "낚시": _resolve_fish,
    "독서": _resolve_read,
    "물자수집": _resolve_scavenge,
}
