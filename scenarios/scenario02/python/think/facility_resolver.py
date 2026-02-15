# think/facility_resolver.py - 시설 탐색 리졸버
#
# NPC가 목욕/옷장/화장실 등 시설을 찾을 때 prop 기반 동적 탐색.
# activity_resolver.py와 동일한 stateless 패턴 (lazy init 불필요).
#
# 선착순 점유:
#   목욕/화장실 시설은 현재 해당 location에 사용 중인 NPC가 없으면 사용 가능.
#   주기적 체크(needs 시스템)로 점유 상태를 자연 감지.
#
# 사용법:
#   from think.facility_resolver import resolve_bath, resolve_wardrobe, resolve_toilet
#   target = resolve_bath(agent)
#   # -> {"region_id": 0, "location_id": 4, "x": 15, "object_id": 101} or None

import morld
from assets.objects import get_instance, _location_objects
from assets.registry import get_unique_id


def resolve_bath(agent, cross_region=False):
    """목욕 시설 탐색 (선착순 점유)

    우선순위:
    1. home_region 내 action:bath 오브젝트 — 비어있으면 사용
    2. (cross_region=True일 때만) 다른 region의 오브젝트
    3. 모두 점유/없음 → None

    Returns:
        {"region_id", "location_id", "x", "object_id"} or None
    """
    home_region = agent._get_home_region()

    all_baths = _find_facilities_by_prop("action:bath", 1)
    sorted_baths = _sort_by_priority(all_baths, None, home_region, cross_region)

    for bath in sorted_baths:
        obj_id = bath["object_id"]
        if _is_bath_available(obj_id, agent.unit_id):
            return bath

    return None


def resolve_wardrobe(agent, cross_region=False):
    """옷장 탐색 (소유권 기반)

    우선순위:
    1. wardrobe_owner:{owner} prop 소유 옷장 (home_region 내)
    2. 아무 wardrobe 오브젝트 (home_region 내, 모브 fallback)
    3. (cross_region=True일 때만) 다른 region의 오브젝트

    Returns:
        {"region_id", "location_id", "x", "object_id"} or None
    """
    home_region = agent._get_home_region()
    owner = getattr(agent, 'owner_unique_id', None)

    # 1순위: 소유 옷장
    if owner:
        owned = _find_facilities_by_prop(f"wardrobe_owner:{owner}", 1)
        sorted_owned = _sort_by_priority(owned, None, home_region, cross_region)
        if sorted_owned:
            return sorted_owned[0]

    # 2순위: 아무 옷장 (모브 fallback)
    all_wardrobes = _find_facilities_by_unique_id("wardrobe")
    sorted_wardrobes = _sort_by_priority(all_wardrobes, None, home_region, cross_region)

    return sorted_wardrobes[0] if sorted_wardrobes else None


def resolve_toilet(agent, cross_region=False):
    """화장실 탐색 (선착순 점유)

    우선순위:
    1. home_region 내 action:toilet 오브젝트 — 비어있으면 사용
    2. (cross_region=True일 때만) 다른 region의 오브젝트
    3. 모두 점유/없음 → None

    Returns:
        {"region_id", "location_id", "x", "object_id"} or None
    """
    home_region = agent._get_home_region()

    all_toilets = _find_facilities_by_prop("action:toilet", 1)
    sorted_toilets = _sort_by_priority(all_toilets, None, home_region, cross_region)

    for toilet in sorted_toilets:
        obj_id = toilet["object_id"]
        if _is_toilet_available(obj_id, agent.unit_id):
            return toilet

    return None


# ========================================
# 내부 헬퍼
# ========================================

def _find_facilities_by_prop(prop_name, prop_value):
    """prop 조건을 만족하는 오브젝트를 전체 location에서 탐색

    Object.props (클래스 속성) 기반 검색. C# API 호출 불필요.
    """
    results = []
    for (r, l), obj_ids in _location_objects.items():
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if obj and obj.props and obj.props.get(prop_name) == prop_value:
                results.append({
                    "region_id": r,
                    "location_id": l,
                    "x": _get_object_x(obj_id),
                    "object_id": obj_id,
                })
    return results


def _find_facilities_by_unique_id(unique_id):
    """unique_id가 일치하는 오브젝트 탐색"""
    results = []
    for (r, l), obj_ids in _location_objects.items():
        for obj_id in obj_ids:
            uid = get_unique_id(obj_id)
            if uid == unique_id:
                results.append({
                    "region_id": r,
                    "location_id": l,
                    "x": _get_object_x(obj_id),
                    "object_id": obj_id,
                })
    return results


def _get_object_x(obj_id):
    """오브젝트의 x 좌표"""
    info = morld.get_unit_info(obj_id)
    return info.get("x", 0) if info else 0


def _is_bath_available(obj_id, exclude_unit_id=None):
    """욕조가 사용 가능한지 (현재 location에 목욕 중인 NPC 없음)

    점유 판정:
    - 해당 location에 있는 NPC 중 목욕 스케줄이거나 청결 인터럽트 중이면 점유
    - exclude_unit_id (자기 자신)는 점유 판정에서 제외
    """
    obj_loc = morld.get_unit_location(obj_id)
    if not obj_loc:
        return False

    units = morld.get_characters_at_location(obj_loc[0], obj_loc[1])
    if not units:
        return True

    from think import _agents
    for uid in units:
        if uid == exclude_unit_id:
            continue
        agent = _agents.get(uid)
        if agent is None:
            continue
        # 목욕 스케줄 중인 NPC → 점유
        is_bath, _ = agent._is_bath_time()
        if is_bath:
            return False
        # 청결 인터럽트로 목욕 중인 NPC → 점유
        try:
            import needs
            if needs.is_npc_need_bath(uid):
                return False
        except ImportError:
            pass

    return True


def _is_toilet_available(obj_id, exclude_unit_id=None):
    """화장실이 사용 가능한지 (현재 location에 배변 중인 NPC 없음)

    점유 판정:
    - 해당 location에 있는 NPC 중 배변 phase가 활성이면 점유
    - exclude_unit_id (자기 자신)는 점유 판정에서 제외
    """
    obj_loc = morld.get_unit_location(obj_id)
    if not obj_loc:
        return False

    units = morld.get_characters_at_location(obj_loc[0], obj_loc[1])
    if not units:
        return True

    from think import _agents
    for uid in units:
        if uid == exclude_unit_id:
            continue
        ag = _agents.get(uid)
        if ag and ag._memory.get("excretion_phase") is not None:
            return False

    return True


def _sort_by_priority(facilities, preferred, home_region_id, cross_region=False):
    """우선순위 정렬: preferred → 같은 region → (옵션) 다른 region"""
    if not facilities:
        return []

    preferred_match = []
    same_region = []
    other_region = []

    for f in facilities:
        if (preferred
                and f["region_id"] == preferred["region_id"]
                and f["location_id"] == preferred["location_id"]):
            preferred_match.append(f)
        elif f["region_id"] == home_region_id:
            same_region.append(f)
        else:
            other_region.append(f)

    result = preferred_match + same_region
    if cross_region:
        result += other_region
    return result
