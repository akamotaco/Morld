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

        morld.add_location(region_id, loc_id, name, length=room.w)

        # 2D 좌표 저장 (지도 표시용)
        morld.set_location_prop(region_id, loc_id, "던전:x", room.x)
        morld.set_location_prop(region_id, loc_id, "던전:y", room.y)
        morld.set_location_prop(region_id, loc_id, "던전:w", room.w)
        morld.set_location_prop(region_id, loc_id, "던전:h", room.h)
        morld.set_location_prop(region_id, loc_id, "던전:타입", room.room_type)
        morld.set_location_prop(region_id, loc_id, "describe_text", desc)

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

    # 외부 입구 연결
    entrance_loc = locations.get(0, 0)  # start room
    if entrance_gate:
        ext_r = entrance_gate["region_id"]
        ext_l = entrance_gate["location_id"]
        ext_gx = entrance_gate.get("gate_x", 400)
        arr_x = entrance_gate.get("arrival_x", 0)

        # 외부 → 던전 입구
        morld.add_gate(ext_r, ext_l, 900 + region_id, ext_gx,
                       region_id, entrance_loc, 10)
        # 던전 입구 → 외부
        morld.add_gate(region_id, entrance_loc, 999, 0,
                       ext_r, ext_l, arr_x)

    return {
        "region_id": region_id,
        "locations": locations,
        "entrance_location": entrance_loc,
    }
