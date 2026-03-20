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


def create_dungeon(name="던전", width=400, height=400, min_size=60,
                   max_depth=4, seed=None, entrance_gate=None):
    """
    인스턴트 던전 생성.

    Args:
        name: 던전 이름
        width, height: BSP 공간 크기
        min_size: 최소 방 크기
        max_depth: BSP 분할 깊이 (깊을수록 방 많음)
        seed: 랜덤 시드
        entrance_gate: 외부 연결 {"region_id", "location_id", "gate_x", "arrival_x"}

    Returns:
        str: dungeon_id
    """
    global _next_region_id, _dungeon_counter

    region_id = _next_region_id
    _next_region_id += 1
    _dungeon_counter += 1
    dungeon_id = f"dungeon_{_dungeon_counter}"

    # BSP 생성
    rooms, corridors = generate_dungeon(
        width=width, height=height,
        min_size=min_size, max_depth=max_depth,
        seed=seed
    )

    # morld에 등록
    info = build_dungeon(rooms, corridors, region_id, name,
                         entrance_gate=entrance_gate)

    info["dungeon_id"] = dungeon_id
    info["rooms"] = rooms
    info["corridors"] = corridors
    _active_dungeons[dungeon_id] = info

    print(f"[instant_dungeon] Created '{name}' (id={dungeon_id}, "
          f"region={region_id}, rooms={len(rooms)})")

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

    del _active_dungeons[dungeon_id]
    print(f"[instant_dungeon] Destroyed '{dungeon_id}'")


def get_dungeon_info(dungeon_id):
    """던전 정보 조회"""
    return _active_dungeons.get(dungeon_id)


def get_active_dungeons():
    """활성 던전 목록"""
    return dict(_active_dungeons)


def get_dungeon_for_region(region_id):
    """Region ID로 던전 조회"""
    for did, info in _active_dungeons.items():
        if info["region_id"] == region_id:
            return did, info
    return None, None
