# think/facility_resolver.py - 시설 탐색 리졸버
#
# NPC가 목욕/옷장 등 시설을 찾을 때 우선순위 기반으로 탐색.
# activity_resolver.py와 동일한 stateless 패턴 (lazy init 불필요).
#
# 예약 시스템:
#   욕조 오브젝트에 "예약:사용자" prop을 설정하여 점유 표시.
#   침대의 seated_by 패턴과 동일. 챕터 전환 시 오브젝트 재생성으로 자동 초기화.
#   stale 예약은 _is_bath_time()=False 확인 시 자동 정리 (self-cleaning).
#
# 사용법:
#   from think.facility_resolver import resolve_bath, resolve_wardrobe
#   target = resolve_bath(agent)
#   # -> {"region_id": 0, "location_id": 4, "x": 15, "object_id": 101} or None

import morld
from assets.objects import get_instance, _location_objects
from assets.registry import get_unique_id

PROP_RESERVED_BY = "예약:사용자"


def resolve_bath(agent, cross_region=False):
    """목욕 시설 탐색 (예약 기반 점유 감지)

    우선순위:
    1. agent.bath_location (선호 위치) — 비어있으면 사용
    2. 같은 region의 다른 action:bath 오브젝트
    3. (cross_region=True일 때만) 다른 region의 오브젝트
    4. 모두 점유/없음 → None

    예약: 결과 반환 시 욕조 오브젝트에 예약:사용자 prop 설정.

    Returns:
        {"region_id", "location_id", "x", "object_id"} or None
    """
    preferred = agent.bath_location
    home_region = preferred["region_id"] if preferred else None
    if home_region is None:
        loc = agent.get_location()
        home_region = loc[0] if loc else 0

    all_baths = _find_facilities_by_prop("action:bath", 1)
    sorted_baths = _sort_by_priority(all_baths, preferred, home_region, cross_region)

    for bath in sorted_baths:
        obj_id = bath["object_id"]
        if _is_bath_available(obj_id, agent.unit_id):
            # 예약 등록
            morld.set_unit_prop(obj_id, PROP_RESERVED_BY, agent.unit_id)
            return bath

    return None


def release_bath(agent):
    """NPC의 욕조 예약 해제 (목욕 포기/완료 시 호출)"""
    all_baths = _find_facilities_by_prop("action:bath", 1)
    for bath in all_baths:
        reserved = morld.get_unit_prop(bath["object_id"], PROP_RESERVED_BY)
        if reserved == agent.unit_id:
            morld.set_unit_prop(bath["object_id"], PROP_RESERVED_BY, -1)


def resolve_wardrobe(agent, cross_region=False):
    """옷장 탐색 (점유 감지 없음)

    우선순위:
    1. agent.wardrobe_location (선호 위치)
    2. 같은 region의 다른 wardrobe 오브젝트
    3. (cross_region=True일 때만) 다른 region의 오브젝트

    Returns:
        {"region_id", "location_id", "x", "object_id"} or None
    """
    preferred = agent.wardrobe_location
    home_region = preferred["region_id"] if preferred else None
    if home_region is None:
        loc = agent.get_location()
        home_region = loc[0] if loc else 0

    unique_id = getattr(agent, "wardrobe_unique_id", "wardrobe")
    all_wardrobes = _find_facilities_by_unique_id(unique_id)
    sorted_wardrobes = _sort_by_priority(all_wardrobes, preferred, home_region, cross_region)

    return sorted_wardrobes[0] if sorted_wardrobes else None


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
    """욕조 오브젝트가 사용 가능한지 확인 (예약 prop 기반)

    예약:사용자 prop 확인:
    - None/-1 → 사용 가능
    - exclude_unit_id → 자기 자신 예약 → 사용 가능
    - 다른 unit_id → 해당 NPC의 _is_bath_time() 확인
      - True → 점유 중
      - False → stale 예약 → 자동 해제 → 사용 가능
    """
    reserved = morld.get_unit_prop(obj_id, PROP_RESERVED_BY)
    if reserved is None or reserved <= 0:
        return True
    if reserved == exclude_unit_id:
        return True

    # 예약자가 아직 목욕 시간인지 확인 (stale 정리)
    from think import _agents
    reserving_agent = _agents.get(reserved)
    if reserving_agent is None:
        # 에이전트 없음 → stale
        morld.set_unit_prop(obj_id, PROP_RESERVED_BY, -1)
        return True

    is_bath, _ = reserving_agent._is_bath_time()
    if not is_bath:
        # 스케줄 목욕이 아닌 경우 — 예약자가 아직 욕조 location에 있으면 사용 중
        agent_loc = reserving_agent.get_location()
        obj_loc = morld.get_unit_location(obj_id)
        if (agent_loc and obj_loc
                and agent_loc[0] == obj_loc[0]
                and agent_loc[1] == obj_loc[1]):
            return False  # 같은 location → 사용 중
        # 목욕 시간 아니고 부재 → stale 예약 해제
        morld.set_unit_prop(obj_id, PROP_RESERVED_BY, -1)
        return True

    return False


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
