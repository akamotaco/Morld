# manager.py — 인스턴트 던전 라이프사이클 관리 (v2)
"""
Spec + seed 기반 동적 던전.
층별 Lazy Generation: 입구만 생성 → 진입 시 BSP 확장.
"""

import morld
from .generator import generate_floor

# 동적 Region 시작 ID (고정 지형과 충돌 방지)
_REGION_START = 100
_next_region_id = _REGION_START

# 활성 던전 목록
_active_dungeons = {}  # {dungeon_id: dungeon_info}
_dungeon_counter = 0


def reset():
    """챕터 전환 시 리셋"""
    global _next_region_id, _dungeon_counter, _active_dungeons
    _next_region_id = _REGION_START
    _dungeon_counter = 0
    _active_dungeons.clear()
    from . import fog
    fog.reset()


def _alloc_region_id():
    """Region ID 할당"""
    global _next_region_id
    rid = _next_region_id
    _next_region_id += 1
    return rid


# ========================================
# Phase 1: 입구만 생성 (스케줄러 호출)
# ========================================

def create_dungeon_entrance(spec, seed, entrance_gate=None):
    """
    Phase 1: 입구만 생성 (가벼움).

    Region + 입구 Location 1개 + 외부 Gate만 등록.
    내부는 expand_floor()에서 생성.

    Args:
        spec: 던전 Spec dict
        seed: base seed
        entrance_gate: {"region_id", "location_id", "distance"}

    Returns:
        str: dungeon_id
    """
    global _dungeon_counter

    region_id = _alloc_region_id()
    _dungeon_counter += 1
    dungeon_id = f"dungeon_{_dungeon_counter}"

    name = spec.get("name", "던전")

    # 입구 Region + Location 등록
    from .builder import ROOM_DESCRIPTIONS
    morld.add_region(region_id, f"{name} 1F",
                     {"default": f"{name} — 동적 생성된 던전"},
                     "맑음")
    entrance_loc = 0
    env_indoor = spec.get("environment", {}).get("indoor", True)
    morld.add_location(region_id, entrance_loc, "던전 입구",
                       0, env_indoor, None,
                       {"default": ROOM_DESCRIPTIONS["start"]}, None,
                       "line", 100)

    # 온도 시스템에 입구 등록
    try:
        import temperature
        temp_mod = spec.get("environment", {}).get("temperature_mod", 0)
        temperature.register_dynamic_location(region_id, entrance_loc, env_indoor, temp_mod)
    except ImportError:
        pass

    # 외부 ↔ 입구 Gate
    if entrance_gate:
        ext_r = entrance_gate["region_id"]
        ext_l = entrance_gate["location_id"]
        distance = entrance_gate.get("distance", 60)
        morld.add_region_gate(ext_r, ext_l, region_id, entrance_loc, distance)

    # dungeon_info 초기화
    info = {
        "dungeon_id": dungeon_id,
        "base_region_id": region_id,
        "entrance_location": entrance_loc,
        "spec": spec,
        "base_seed": seed,

        # 층별 생성 상태
        "floors_generated": {},
        # {floor_num: {
        #     "region_id": int, "rooms": [], "corridors": [], "bridges": [],
        #     "locations": {room_id: loc_id}, "has_stairs_down": bool
        # }}

        # 다음 층 stub
        "floor_stubs": {},
        # {floor_num: {"region_id": int, "stub_location": int}}

        # 외부 연결
        "_entrance_ext_region": entrance_gate["region_id"] if entrance_gate else None,
        "_entrance_ext_location": entrance_gate["location_id"] if entrance_gate else None,
    }
    _active_dungeons[dungeon_id] = info

    print(f"[instant_dungeon] Entrance created '{name}' (id={dungeon_id}, region={region_id})")
    return dungeon_id


# ========================================
# Phase 2: 층 확장 (on_reach 트리거)
# ========================================

def expand_floor(dungeon_id, floor_num):
    """
    Phase 2: 한 층 BSP 확장.

    BSP 생성 → Location/Gate 추가 → Bridge → FoW 초기화.
    이미 확장된 층이면 무시.

    Args:
        dungeon_id: 던전 ID
        floor_num: 확장할 층 번호
    """
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return
    if floor_num in info["floors_generated"]:
        return  # 이미 확장됨

    spec = info["spec"]
    seed = info["base_seed"]
    max_floors = spec.get("max_floors")
    conn = spec.get("connections", {})
    stairs_per_floor = conn.get("stairs_per_floor", 1)

    # floor_overrides 적용
    base_cfg = dict(spec.get("base", {}))
    base_cfg["connections"] = conn
    if "floor_scaling" in spec:
        base_cfg["floor_scaling"] = spec["floor_scaling"]
    overrides = spec.get("floor_overrides", {}).get(floor_num, {})
    base_cfg.update(overrides)

    # BSP 생성
    rooms, corridors, bridges = generate_floor(
        base_cfg, floor_num, seed,
        max_floors=max_floors,
        stairs_per_floor=stairs_per_floor,
    )

    # Region 결정
    if floor_num == 0:
        region_id = info["base_region_id"]
    else:
        stub = info["floor_stubs"].get(floor_num)
        if stub:
            region_id = stub["region_id"]
        else:
            region_id = _alloc_region_id()

    # Location/Gate 등록
    from .builder import build_floor_interior, ROOM_DESCRIPTIONS
    env_config = spec.get("environment", {"indoor": True})
    floor_info = build_floor_interior(
        rooms, corridors, bridges, region_id,
        f"{spec.get('name', '던전')} {floor_num + 1}F",
        skip_start=(floor_num == 0),  # 1층 입구는 이미 생성
        skip_stairs_up=(floor_num > 0 and floor_num in info["floor_stubs"]),
        seed=seed + floor_num * 100,
        floor_num=floor_num,
        env_config=env_config,
    )

    # stairs_down → 다음 층 stub 생성
    has_stairs_down = False
    for room in rooms:
        if room.room_type == "stairs_down":
            has_stairs_down = True
            next_floor = floor_num + 1
            if next_floor not in info["floor_stubs"] and next_floor not in info["floors_generated"]:
                _create_floor_stub(info, next_floor, region_id, floor_info["locations"][room.id])

    # 기록
    floor_data = {
        "region_id": region_id,
        "rooms": rooms,
        "corridors": corridors,
        "bridges": bridges,
        "locations": floor_info["locations"],
        "has_stairs_down": has_stairs_down,
        "floor": floor_num,
    }
    info["floors_generated"][floor_num] = floor_data

    # FoW 초기화
    from . import fog
    fog_id = f"{dungeon_id}_F{floor_num}"
    fog.init_fog(fog_id, rooms, corridors + [type(corridors[0])(b.room_a, b.room_b) for b in bridges] if corridors and bridges else corridors, mode="volatile")

    # 온도 시스템에 동적 등록
    try:
        import temperature
        temp_mod = env_config.get("temperature_mod", 0)
        from .builder import _resolve_indoor
        for room in rooms:
            indoor = _resolve_indoor(room, floor_num, env_config)
            temperature.register_dynamic_location(region_id, room.id, indoor, temp_mod)
    except ImportError:
        pass

    print(f"[instant_dungeon] Expanded floor {floor_num + 1}F "
          f"(id={dungeon_id}, region={region_id}, rooms={len(rooms)}, bridges={len(bridges)})")


def _create_floor_stub(info, floor_num, from_region_id, from_location_id):
    """다음 층 stub 생성: Region + stairs_up Location 1개 + 계단 Gate"""
    name = info["spec"].get("name", "던전")
    stub_region_id = _alloc_region_id()
    stub_loc = 0  # stairs_up 위치

    from .builder import ROOM_DESCRIPTIONS
    morld.add_region(stub_region_id, f"{name} {floor_num + 1}F",
                     {"default": f"{name} — 동적 생성된 던전"},
                     "맑음")
    env_config = info["spec"].get("environment", {})
    from .builder import _resolve_indoor
    from .generator import Room
    stub_room = Room(0, 0, 0, 80, 80, "stairs_up")
    stub_indoor = _resolve_indoor(stub_room, floor_num, env_config)
    morld.add_location(stub_region_id, stub_loc, "상층 계단",
                       0, stub_indoor, None,
                       {"default": ROOM_DESCRIPTIONS["stairs_up"]}, None,
                       "line", 80)

    # 온도 시스템에 stub 등록
    try:
        import temperature
        temp_mod = env_config.get("temperature_mod", 0)
        temperature.register_dynamic_location(stub_region_id, stub_loc, stub_indoor, temp_mod)
    except ImportError:
        pass

    # 계단 Gate: 이전 층 stairs_down ↔ 이 층 stub
    morld.add_region_gate(from_region_id, from_location_id,
                          stub_region_id, stub_loc, 30)

    info["floor_stubs"][floor_num] = {
        "region_id": stub_region_id,
        "stub_location": stub_loc,
    }

    print(f"[instant_dungeon] Stub created: {floor_num + 1}F (region={stub_region_id})")


# ========================================
# 조회 API
# ========================================

def is_floor_expanded(dungeon_id, floor_num):
    """해당 층이 BSP 확장됐는지"""
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return False
    return floor_num in info["floors_generated"]


def get_floor_num_for_region(dungeon_id, region_id):
    """region_id → floor_num (없으면 None)"""
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return None

    # 생성된 층에서 찾기
    for fnum, fdata in info["floors_generated"].items():
        if fdata["region_id"] == region_id:
            return fnum

    # stub에서 찾기
    for fnum, stub in info["floor_stubs"].items():
        if stub["region_id"] == region_id:
            return fnum

    # base_region (0층 입구)
    if info["base_region_id"] == region_id:
        return 0

    return None


def get_dungeon_info(dungeon_id):
    """던전 정보 조회"""
    return _active_dungeons.get(dungeon_id)


def get_active_dungeons():
    """활성 던전 목록"""
    return dict(_active_dungeons)


def get_dungeon_for_region(region_id):
    """
    Region ID로 던전 조회.

    Returns:
        (dungeon_id, dungeon_info) 또는 (None, None)
    """
    for did, info in _active_dungeons.items():
        if info["base_region_id"] == region_id:
            return did, info
        for fdata in info["floors_generated"].values():
            if fdata["region_id"] == region_id:
                return did, info
        for stub in info["floor_stubs"].values():
            if stub["region_id"] == region_id:
                return did, info
    return None, None


def get_floor_for_region(dungeon_id, region_id):
    """region_id → floor_info dict (없으면 None)"""
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return None

    for fdata in info["floors_generated"].values():
        if fdata["region_id"] == region_id:
            return fdata
    return None


def is_dungeon_occupied(dungeon_id):
    """던전 내에 캐릭터가 있는지"""
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return False

    # 생성된 모든 층 체크
    for fdata in info["floors_generated"].values():
        region_id = fdata["region_id"]
        for loc_id in fdata["locations"].values():
            units = morld.get_units_at_location(region_id, loc_id)
            if not units:
                continue
            for uid in units:
                unit_info = morld.get_unit_info(uid)
                if unit_info and not unit_info.get("is_object"):
                    return True
    return False


# ========================================
# 삭제
# ========================================

def destroy_dungeon(dungeon_id):
    """인스턴트 던전 삭제 — 생성된 층만 정리"""
    info = _active_dungeons.get(dungeon_id)
    if not info:
        print(f"[instant_dungeon] Dungeon '{dungeon_id}' not found")
        return

    # 플레이어 탈출 처리
    player_id = morld.get_player_id()
    if player_id:
        player_loc = morld.get_unit_location(player_id)
        if player_loc:
            _, dungeon_check = get_dungeon_for_region(player_loc[0])
            if dungeon_check and dungeon_check["dungeon_id"] == dungeon_id:
                ext_r = info.get("_entrance_ext_region", 0)
                ext_l = info.get("_entrance_ext_location", 0)
                morld.set_unit_location(player_id, ext_r or 0, ext_l or 0)
                morld.add_action_log("던전이 붕괴하여 밖으로 빠져나왔다.")

    # FoW 정리
    from . import fog
    for fnum, fdata in info["floors_generated"].items():
        fog.destroy_fog(f"{dungeon_id}_F{fnum}")
        # 온도 시스템 해제
        try:
            import temperature
            temperature.unregister_dynamic_locations(fdata["region_id"])
        except ImportError:
            pass

    # stub region 온도도 해제
    try:
        import temperature
        for stub in info["floor_stubs"].values():
            temperature.unregister_dynamic_locations(stub["region_id"])
    except ImportError:
        pass

    del _active_dungeons[dungeon_id]
    print(f"[instant_dungeon] Destroyed '{dungeon_id}'")
