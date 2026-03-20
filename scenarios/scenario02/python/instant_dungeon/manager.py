# manager.py — 인스턴트 던전 라이프사이클 관리
"""
던전 생성/삭제/조회.
Region ID 100번대 auto-increment.
"""

import morld
from .generator import generate_dungeon
from .builder import build_dungeon

# 동적 Region 시작 ID (고정 지형과 충돌 방지)
_REGION_START = 100
_next_region_id = _REGION_START

# 활성 던전 목록
_active_dungeons = {}  # {dungeon_id: {"region_id": int, "locations": dict, ...}}
_dungeon_counter = 0


def reset():
    """챕터 전환 시 리셋"""
    global _next_region_id, _dungeon_counter, _active_dungeons
    _next_region_id = _REGION_START
    _dungeon_counter = 0
    _active_dungeons.clear()
    from . import fog
    fog.reset()


def create_dungeon(name="던전", width=400, height=400, min_size=60,
                   max_depth=4, seed=None, entrance_gate=None, floors=1):
    """
    인스턴트 던전 생성.

    Args:
        name: 던전 이름
        width, height: BSP 공간 크기
        min_size: 최소 방 크기
        max_depth: BSP 분할 깊이 (깊을수록 방 많음)
        seed: 랜덤 시드
        entrance_gate: 외부 연결 {"region_id", "location_id", "distance"}
        floors: 층 수 (1이면 단층, 2+ 다층)

    Returns:
        str: dungeon_id
    """
    global _next_region_id, _dungeon_counter

    base_region_id = _next_region_id
    _next_region_id += floors  # 층 수만큼 region ID 예약
    _dungeon_counter += 1
    dungeon_id = f"dungeon_{_dungeon_counter}"

    from . import fog

    if floors <= 1:
        # ── 단층 (기존 로직) ──
        rooms, corridors = generate_dungeon(
            width=width, height=height,
            min_size=min_size, max_depth=max_depth,
            seed=seed
        )
        info = build_dungeon(rooms, corridors, base_region_id, name,
                             entrance_gate=entrance_gate)
        info["dungeon_id"] = dungeon_id
        info["rooms"] = rooms
        info["corridors"] = corridors
        info["floors"] = None  # 단층 표시
        info["_entrance_ext_region"] = entrance_gate["region_id"] if entrance_gate else None
        info["_entrance_ext_location"] = entrance_gate["location_id"] if entrance_gate else None
        _active_dungeons[dungeon_id] = info

        fog.init_fog(dungeon_id, rooms, corridors, mode="volatile")
        total_rooms = len(rooms)
    else:
        # ── 다층 ──
        from .generator import generate_multi_floor
        from .builder import build_multi_floor

        floor_data = generate_multi_floor(
            floors=floors, width=width, height=height,
            min_size=min_size, max_depth=max_depth,
            seed=seed
        )

        multi_info = build_multi_floor(
            floor_data, base_region_id, name,
            entrance_gate=entrance_gate
        )

        # dungeon_info 구성
        info = {
            "dungeon_id": dungeon_id,
            "region_id": multi_info["entrance_region_id"],
            "entrance_location": multi_info["entrance_location"],
            "floors": multi_info["floors"],
            # 하위 호환: 단층 필드도 유지 (첫 층 기준)
            "rooms": multi_info["floors"][0]["rooms"] if multi_info["floors"] else [],
            "corridors": multi_info["floors"][0]["corridors"] if multi_info["floors"] else [],
            "locations": multi_info["floors"][0]["locations"] if multi_info["floors"] else {},
            # 외부 나가기 링크용
            "_entrance_ext_region": entrance_gate["region_id"] if entrance_gate else None,
            "_entrance_ext_location": entrance_gate["location_id"] if entrance_gate else None,
        }
        _active_dungeons[dungeon_id] = info

        # 층별 FoW 초기화
        total_rooms = 0
        for fd in multi_info["floors"]:
            floor_fog_id = f"{dungeon_id}_F{fd['floor']}"
            fog.init_fog(floor_fog_id, fd["rooms"], fd["corridors"], mode="volatile")
            total_rooms += len(fd["rooms"])

    print(f"[instant_dungeon] Created '{name}' (id={dungeon_id}, "
          f"floors={floors}, regions={base_region_id}-{base_region_id+floors-1}, "
          f"rooms={total_rooms})")

    return dungeon_id


def destroy_dungeon(dungeon_id):
    """
    인스턴트 던전 삭제.

    내부 유닛 제거 → Location 제거 → Region 제거.
    플레이어가 내부에 있으면 입구 외부로 텔레포트.
    """
    info = _active_dungeons.get(dungeon_id)
    if not info:
        print(f"[instant_dungeon] Dungeon '{dungeon_id}' not found")
        return

    region_id = info["region_id"]

    # 플레이어 탈출 처리
    player_id = morld.get_player_id()
    if player_id:
        player_loc = morld.get_unit_location(player_id)
        if player_loc and player_loc[0] == region_id:
            # 입구 외부로 텔레포트 (gate 999의 연결 대상)
            # 간단히 Region 0, Location 0으로 이동
            morld.set_unit_location(player_id, 0, 0)
            morld.add_action_log("던전이 붕괴하여 밖으로 빠져나왔다.")

    # Location 제거 (역순)
    for loc_id in sorted(info["locations"].values(), reverse=True):
        try:
            morld.remove_location(region_id, loc_id)
        except Exception:
            pass

    # FoW 정리
    from . import fog
    fog.destroy_fog(dungeon_id)

    del _active_dungeons[dungeon_id]
    print(f"[instant_dungeon] Destroyed '{dungeon_id}'")


def get_dungeon_info(dungeon_id):
    """던전 정보 조회"""
    return _active_dungeons.get(dungeon_id)


def get_active_dungeons():
    """활성 던전 목록"""
    return dict(_active_dungeons)


def get_dungeon_for_region(region_id):
    """
    Region ID로 던전 조회 (다층 지원).

    Returns:
        (dungeon_id, dungeon_info) 또는 (None, None)
    """
    for did, info in _active_dungeons.items():
        # 단층: region_id 직접 비교
        if info["region_id"] == region_id:
            return did, info
        # 다층: 각 층의 region_id 비교
        if info.get("floors"):
            for fd in info["floors"]:
                if fd["region_id"] == region_id:
                    return did, info
    return None, None


def get_floor_for_region(dungeon_id, region_id):
    """
    Region ID로 해당 층 정보 반환 (다층 던전용).

    Returns:
        floor_info dict 또는 None
    """
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return None

    # 단층
    if not info.get("floors"):
        if info["region_id"] == region_id:
            return info
        return None

    # 다층
    for fd in info["floors"]:
        if fd["region_id"] == region_id:
            return fd
    return None


def is_dungeon_occupied(dungeon_id):
    """
    던전 내에 캐릭터(플레이어 포함)가 있는지 확인.
    1명이라도 있으면 True.
    """
    info = _active_dungeons.get(dungeon_id)
    if not info:
        return False

    region_id = info["region_id"]
    for loc_id in info["locations"].values():
        units = morld.get_units_at_location(region_id, loc_id)
        if not units:
            continue
        for uid in units:
            unit_info = morld.get_unit_info(uid)
            if unit_info and not unit_info.get("is_object"):
                return True
    return False
