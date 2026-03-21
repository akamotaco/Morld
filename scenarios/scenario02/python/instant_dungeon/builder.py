# builder.py — Room/Corridor/Bridge → morld Region/Location/Gate 변환
"""
generator.py가 만든 Room/Corridor/Bridge를 morld API로 실제 게임 지형에 등록.
"""

import random

import morld
from .generator import Room, Corridor, Bridge

# 방 타입별 이름/묘사 (특수 방 — 고정)
ROOM_NAMES = {
    "start":       "던전 입구",
    "boss":        "심층",
    "treasure":    "보물방",
    "stairs_down": "하층 계단",
    "stairs_up":   "상층 계단",
}

ROOM_DESCRIPTIONS = {
    "start":       "던전의 입구다. 돌아갈 수 있는 출구가 보인다.",
    "boss":        "깊은 곳에서 강한 기운이 느껴진다.",
    "treasure":    "뭔가 반짝이는 것이 보인다.",
    "normal":      "어둡고 습한 통로다.",
    "stairs_down": "아래층으로 내려가는 계단이 보인다.",
    "stairs_up":   "위층으로 올라가는 계단이 보인다.",
}

# 분위기 수식어 (seed 기반 랜덤)
_ATMOSPHERE = [
    "으슥한", "습한", "이끼 낀", "어두운", "차가운",
    "바람 부는", "고요한", "먼지 쌓인", "금 간", "축축한",
]

# 크기 → 공간 명칭
_SIZE_NAMES = [
    (150, "넓은 ", "방"),
    (80,  "",      "통로"),
    (0,   "좁은 ", "골목"),
]


def _get_direction(room, all_rooms):
    """방의 2D 중심 좌표 기반 방향 (맵 중심 대비)"""
    if not all_rooms:
        return ""
    # 맵 중심 계산
    cx = sum(r.x + r.w // 2 for r in all_rooms) // len(all_rooms)
    cy = sum(r.y + r.h // 2 for r in all_rooms) // len(all_rooms)
    rx, ry = room.center()
    dx = rx - cx
    dy = ry - cy

    # 거리가 너무 가까우면 방향 생략
    if abs(dx) < 30 and abs(dy) < 30:
        return ""

    if abs(dx) > abs(dy) * 2:
        return "동쪽 " if dx > 0 else "서쪽 "
    elif abs(dy) > abs(dx) * 2:
        return "남쪽 " if dy > 0 else "북쪽 "
    elif dx > 0:
        return "남동쪽 " if dy > 0 else "북동쪽 "
    else:
        return "남서쪽 " if dy > 0 else "북서쪽 "


def _generate_room_name(room, all_rooms, seed):
    """normal 방의 고유 이름 생성 (크기 + 방향 + 분위기)"""
    # 크기 판정
    size_prefix = ""
    space_name = "통로"
    for threshold, prefix, name in _SIZE_NAMES:
        if room.w >= threshold:
            size_prefix = prefix
            space_name = name
            break

    # 방향
    direction = _get_direction(room, all_rooms)

    # 분위기 (seed + room.id 기반 결정론)
    rng = random.Random(seed + room.id * 7)
    atmosphere = rng.choice(_ATMOSPHERE)

    return f"{atmosphere} {size_prefix}{direction}{space_name}"


def _generate_room_description(room, name):
    """분위기 기반 묘사 텍스트"""
    if room.w >= 150:
        return f"{name}. 넓은 공간이 펼쳐져 있다."
    elif room.w < 80:
        return f"{name}. 좁아서 조심스럽게 움직여야 한다."
    else:
        return f"{name}. 어둡고 습한 공기가 감돈다."


def build_floor_interior(rooms, corridors, bridges, region_id, floor_label,
                         skip_start=False, skip_stairs_up=False, seed=0):
    """
    한 층의 내부를 morld에 등록 (Lazy Generation Phase 2).

    이미 존재하는 Location은 skip:
    - skip_start=True: start(id=0) Location은 Phase 1에서 생성됨
    - skip_stairs_up=True: stairs_up(id=0) Location은 stub에서 생성됨

    Args:
        rooms: 방 목록
        corridors: corridor 목록
        bridges: bridge 목록
        region_id: 이 층의 Region ID
        floor_label: Region 이름 (로그용)
        skip_start: start room skip 여부
        skip_stairs_up: stairs_up room skip 여부
        seed: 이름 생성용 시드

    Returns:
        {"region_id": int, "locations": {room_id: loc_id}}
    """
    locations = {}

    for room in rooms:
        loc_id = room.id

        if room.room_type == "normal":
            name = _generate_room_name(room, rooms, seed)
            desc = _generate_room_description(room, name)
        else:
            name = ROOM_NAMES.get(room.room_type, f"방 {room.id}")
            desc = ROOM_DESCRIPTIONS.get(room.room_type, "어두운 공간이다.")
        describe_dict = {"default": desc}

        # 이미 생성된 Location skip
        if skip_start and room.room_type == "start" and room.id == 0:
            locations[room.id] = loc_id
            continue
        if skip_stairs_up and room.room_type == "stairs_up" and room.id == 0:
            locations[room.id] = loc_id
            continue

        # add_location: positional args (kwargs 미지원 — PyBuiltinFunction 제약)
        morld.add_location(region_id, loc_id, name,
                           0, False, None,
                           describe_dict, None,
                           "line", room.w)
        locations[room.id] = loc_id

    # Corridor → Gate (양방향)
    gate_counter = 0
    room_map = {r.id: r for r in rooms}
    for corr in corridors:
        gate_counter = _add_gate_pair(
            region_id, room_map, locations, corr.room_a, corr.room_b, gate_counter
        )

    # Bridge → Gate (양방향, 동일 처리)
    for br in bridges:
        gate_counter = _add_gate_pair(
            region_id, room_map, locations, br.room_a, br.room_b, gate_counter
        )

    return {
        "region_id": region_id,
        "locations": locations,
    }


def _add_gate_pair(region_id, room_map, locations, room_a_id, room_b_id, gate_counter):
    """두 방 사이에 양방향 Gate 추가. gate_counter 반환."""
    room_a = room_map[room_a_id]
    room_b = room_map[room_b_id]
    loc_a = locations[room_a_id]
    loc_b = locations[room_b_id]

    gate_x_a = room_a.w - 10
    gate_x_b = 10

    morld.add_gate(region_id, loc_a, gate_counter, gate_x_a,
                   region_id, loc_b, gate_x_b)
    morld.add_gate(region_id, loc_b, gate_counter + 1, gate_x_b,
                   region_id, loc_a, gate_x_a)

    return gate_counter + 2
