# builder.py — Room/Corridor → morld Region/Location/Gate 변환
"""
generator.py가 만든 Room/Corridor를 morld API로 실제 게임 지형에 등록.
"""

import morld
from .generator import Room, Corridor

# 방 타입별 이름/묘사
ROOM_NAMES = {
    "start":    "던전 입구",
    "boss":     "심층",
    "treasure": "보물방",
    "normal":   "통로",
}

ROOM_DESCRIPTIONS = {
    "start":    "던전의 입구다. 돌아갈 수 있는 출구가 보인다.",
    "boss":     "깊은 곳에서 강한 기운이 느껴진다.",
    "treasure": "뭔가 반짝이는 것이 보인다.",
    "normal":   "어둡고 습한 통로다.",
}


def build_dungeon(rooms, corridors, region_id, dungeon_name="던전",
                  entrance_gate=None):
    """
    생성된 방/복도를 morld에 등록.

    Args:
        rooms: list[Room]
        corridors: list[Corridor]
        region_id: 사용할 Region ID
        dungeon_name: Region 이름
        entrance_gate: 외부 연결 정보 (dict) or None
            {"region_id": 3, "location_id": 5, "gate_x": 400, "arrival_x": 0}

    Returns:
        dict: {"region_id": int, "locations": {room_id: location_id}, "entrance_location": int}
    """
    # Region 등록
    morld.add_region(region_id, dungeon_name,
                     {"default": f"{dungeon_name} — 동적 생성된 던전"},
                     "맑음")

    # Room → Location
    locations = {}
    for room in rooms:
        loc_id = room.id
        name = ROOM_NAMES.get(room.room_type, f"방 {room.id}")
        desc = ROOM_DESCRIPTIONS.get(room.room_type, "어두운 공간이다.")

        # add_location: positional args (kwargs 미지원 — PyBuiltinFunction 제약)
        # (region_id, local_id, name, stay_duration, indoor, owner,
        #  describe_text, ground_id, geometry, length)
        describe_dict = {"default": desc}
        morld.add_location(region_id, loc_id, name,
                           0, False, None,        # stay=0, indoor=False(던전), owner=None
                           describe_dict, None,    # describe_text, ground_id
                           "line", room.w)         # geometry, length

        locations[room.id] = loc_id

    # Corridor → Gate (양방향)
    gate_counter = 0
    for corr in corridors:
        room_a = next(r for r in rooms if r.id == corr.room_a)
        room_b = next(r for r in rooms if r.id == corr.room_b)

        loc_a = locations[corr.room_a]
        loc_b = locations[corr.room_b]

        # Gate 위치: 방의 오른쪽 끝/왼쪽 시작
        gate_x_a = room_a.w - 10  # 방 A의 오른쪽 근처
        gate_x_b = 10             # 방 B의 왼쪽 근처

        gate_id_a = gate_counter
        gate_id_b = gate_counter + 1
        gate_counter += 2

        morld.add_gate(region_id, loc_a, gate_id_a, gate_x_a,
                       region_id, loc_b, gate_x_b)
        morld.add_gate(region_id, loc_b, gate_id_b, gate_x_b,
                       region_id, loc_a, gate_x_a)

    # 외부 입구 연결 — cross-region은 RegionGate 사용 (add_gate는 같은 region 내부 전용)
    # CPython 기존 월드: REGION_GATES → add_region_gate(region_a, loc_a, region_b, loc_b, distance)
    entrance_loc = locations.get(0, 0)  # start room
    if entrance_gate:
        ext_r = entrance_gate["region_id"]
        ext_l = entrance_gate["location_id"]
        distance = entrance_gate.get("distance", 60)  # 기본 1분 도보

        # 외부 ↔ 던전 입구 (양방향 RegionGate)
        morld.add_region_gate(ext_r, ext_l, region_id, entrance_loc, distance)

    return {
        "region_id": region_id,
        "locations": locations,
        "entrance_location": entrance_loc,
    }
