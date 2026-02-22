"""활동 핸들러 공통 유틸

ACTION_DURATION — 고정 시간 행동 소요시간 테이블 (밀리초)
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

# ========================================
# 행동 소요시간 테이블 (밀리초)
# ========================================
# 이동(move)은 C#이 거리 기반 동적 계산 → 제외
# max(remaining, 1) 패턴은 스케줄 종료 시간 연동 → 제외
# BaseAgent._action_duration_overrides 로 캐릭터별 오버라이드 가능

ACTION_DURATION = {
    # 식사
    "eat":           15 * 60_000,   # 15분

    # 아이템 조작
    "take_item":      1 * 60_000,   # 1분 — 컨테이너에서 꺼내기
    "store_item":     1 * 60_000,   # 1분 — 컨테이너에 넣기

    # 의류 착탈
    "equip":          3 * 60_000,   # 3분 — 장비 착용
    "unequip":        2 * 60_000,   # 2분 — 장비 해제

    # 자원 활동
    "chop":          30 * 60_000,   # 30분 — 벌목
    "fish":          30 * 60_000,   # 30분 — 낚시
    "gather":        10 * 60_000,   # 10분 — 채집
    "scavenge":      10 * 60_000,   # 10분 — 물자 수집
    "gather_branch":  5 * 60_000,   # 5분 — 나뭇가지 줍기

    # 가사
    "cook":          20 * 60_000,   # 20분 — 요리
    "clean_room":    10 * 60_000,   # 10분 — 청소 (1개 방)
    "toggle_light":   1 * 60_000,   # 1분 — 조명 켜기/끄기
    "load_fuel":      5 * 60_000,   # 5분 — 연료 투입
    "craft":         10 * 60_000,   # 10분 — 제작

    # 생활
    "excretion":      5 * 60_000,   # 5분 — 배변
    "bath":          30 * 60_000,   # 30분 — 목욕 (비스케줄)
    "bath_wait":      5 * 60_000,   # 5분 — 목욕 대기 (욕실 점유)
    "self_comfort":  15 * 60_000,   # 15분 — 자위
    "sleep_fallback":10 * 60_000,   # 10분 — 수면 폴백
    "sleep_default":  2 * 3_600_000, # 2시간 — 비스케줄 수면

    # 사회
    "socialize":     30 * 60_000,   # 30분 — 대화
    "gift":           5 * 60_000,   # 5분 — 선물
    "npc_intimacy":  30 * 60_000,   # 30분 — NPC-NPC 성행위

    # 정원
    "water_garden":  10 * 60_000,   # 10분 — 물주기
    "harvest":       20 * 60_000,   # 20분 — 수확
    "plant_seed":    10 * 60_000,   # 10분 — 씨 심기
    "garden_tidy":    5 * 60_000,   # 5분 — 정리

    # 출산/모성
    "labor":          8 * 3_600_000, # 8시간 — 출산
    "postpartum":    24 * 3_600_000, # 24시간 — 산후조리
    "maternal":      30 * 60_000,   # 30분 — 육아

    # 세탁
    "load_laundry":   2 * 60_000,   # 2분 — 빨래 넣기
    "unload_laundry": 2 * 60_000,   # 2분 — 빨래 꺼내기
    "store_laundry":  3 * 60_000,   # 3분 — 빨래 정리/재장착

    # 성추행/유혹
    "fix_clothes":    1 * 60_000,   # 1분 — 옷매무새 정리
    "seduce":         2 * 60_000,   # 2분 — 유혹 (자발적 노출)
    "harass_player":  5 * 60_000,   # 5분 — NPC→플레이어 성추행

    # 대기/중단
    "abort":          5 * 60_000,   # 5분 — 중단/오류
    "brief":          1 * 60_000,   # 1분 — 짧은 전환
    "safety_net":    10 * 60_000,   # 10분 — think() 안전망
}


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


def resolve_branch_tree(agent, cross_region=False):
    """나뭇가지 있는 나무 탐색 (home_region 우선, cross_region=True면 다른 Region도)"""
    from assets.objects import _location_objects, get_instance
    from assets.objects.trees import Tree

    home_region = agent._get_home_region()

    # 1차: home_region
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            obj = get_instance(obj_id)
            if isinstance(obj, Tree) and obj.can_gather():
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": get_object_x_from_info(obj_id),
                    "object_id": obj_id,
                }

    # 2차: 다른 Region (cross_region=True만)
    if cross_region:
        for (r, l), obj_ids in _location_objects.items():
            if r == home_region:
                continue
            for obj_id in obj_ids:
                obj = get_instance(obj_id)
                if isinstance(obj, Tree) and obj.can_gather():
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
    home_region = agent._get_home_region()

    # 소유 침대 위치로 건물 판정
    sleep_l = None
    owner = getattr(agent, 'owner_unique_id', None)
    if owner:
        from think.facility_resolver import _find_facilities_by_prop
        beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
        if beds:
            sleep_l = beds[0]["location_id"]

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

    # 소유 침대 위치로 건물 판정
    sleep_l = None
    owner = getattr(agent, 'owner_unique_id', None)
    if owner:
        from think.facility_resolver import _find_facilities_by_prop
        beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
        if beds:
            sleep_l = beds[0]["location_id"]

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
