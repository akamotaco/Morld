# think/activity_resolver.py - 활동 장소 동적 탐색
#
# Python 인스턴스 레지스트리(_instances) 기반으로 region 내 오브젝트를 탐색합니다.
# _instances는 모든 Object.instantiate() 호출에서 등록되므로 누락이 없습니다.
# (C# get_characters_at_location은 캐릭터만 반환하여 오브젝트 탐색 불가)
#
# 사용법:
#   from think.activity_resolver import resolve_activity_location
#   target = resolve_activity_location(unit_id, "채집", home_region_id=0)
#   # -> {"region_id": 0, "location_id": 23, "x": 450, "object_id": 101}

import morld


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
        if activity not in _NO_RESOLVER_ACTIVITIES:
            print(f"[activity_resolver] No resolver for activity '{activity}' (unit={unit_id})")
        return None
    result = resolver(unit_id, home_region_id)
    if result is None:
        unit_info = morld.get_unit_info(unit_id)
        name = unit_info.get("name", "?") if unit_info else "?"
        print(f"[activity_resolver] {name}(id={unit_id}): '{activity}' target not found in region {home_region_id}")
    return result


def _iter_objects_in_region(region_id, obj_type):
    """region 내 특정 타입 오브젝트를 Python 인스턴스 레지스트리로 탐색

    _instances는 모든 Object.instantiate()에서 등록되므로 완전합니다.

    Yields: (region_id, location_id, obj_id, obj_instance)
    """
    from assets.objects import _instances

    for obj_id, obj in _instances.items():
        if isinstance(obj, obj_type) and getattr(obj, 'region_id', None) == region_id:
            yield (region_id, obj.location_id, obj_id, obj)


def _get_object_x(obj_id):
    """오브젝트의 x 좌표 조회"""
    info = morld.get_unit_info(obj_id)
    if info:
        return info.get("x", 0)
    return 0


def _resolve_gather(unit_id, region_id):
    """채집: ResourceObject가 있는 location 탐색"""
    from assets.objects.nature import ResourceObject

    candidates = []
    for r, l, obj_id, obj in _iter_objects_in_region(region_id, ResourceObject):
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
    """사냥: outdoor location 탐색"""
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return None

    for loc in region_info["locations"]:
        if not loc.get("is_indoor", True):
            return {
                "region_id": region_id,
                "location_id": loc["id"],
                "x": 0,
                "length": loc.get("length", 0),
            }

    return None


def _resolve_patrol(unit_id, region_id):
    """순찰: outdoor location 탐색"""
    return _resolve_hunt(unit_id, region_id)


def _resolve_chop(unit_id, region_id):
    """벌목: Tree 오브젝트(can_chop=True)가 있는 location 탐색"""
    from assets.objects.trees import Tree

    for r, l, obj_id, obj in _iter_objects_in_region(region_id, Tree):
        if obj.can_chop():
            return {
                "region_id": r,
                "location_id": l,
                "x": _get_object_x(obj_id),
                "object_id": obj_id,
            }
    return None


def _resolve_fish(unit_id, region_id):
    """낚시: FishingSpot + can_fish() 확인, 물고기 많은 곳 우선"""
    from assets.objects.outdoor import FishingSpot

    candidates = []
    for r, l, obj_id, obj in _iter_objects_in_region(region_id, FishingSpot):
        if obj.can_fish():
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
    from assets.objects.furniture import Bookshelf

    for r, l, obj_id, obj in _iter_objects_in_region(region_id, Bookshelf):
        return {
            "region_id": r,
            "location_id": l,
            "x": _get_object_x(obj_id),
            "object_id": obj_id,
        }
    return None


def _resolve_scavenge(unit_id, region_id):
    """물자수집: ScavengeableObject 중 재고>0인 것 탐색"""
    from assets.objects.scavenge import ScavengeableObject

    candidates = []
    for r, l, obj_id, obj in _iter_objects_in_region(region_id, ScavengeableObject):
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

# resolver가 필요 없는 활동 (경고 억제)
_NO_RESOLVER_ACTIVITIES = {"대기", "휴식", "수면", "식사"}
