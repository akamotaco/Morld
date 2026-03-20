# builder.py — Room/Corridor → morld Region/Location/Gate 변환
"""
generator.py가 만든 Room/Corridor를 morld API로 실제 게임 지형에 등록.
"""

import morld
from .generator import Room, Corridor

# 방 타입별 이름/묘사
ROOM_NAMES = {
    "start":       "던전 입구",
    "boss":        "심층",
    "treasure":    "보물방",
    "normal":      "통로",
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


def build_multi_floor(floor_data, base_region_id, dungeon_name="던전",
                      entrance_gate=None):
    """
    다층 던전 빌드 — 층별 Region + 계단 RegionGate.

    Args:
        floor_data: generate_multi_floor() 결과 (list[dict])
        base_region_id: 첫 층 Region ID (이후 +1씩)
        dungeon_name: 던전 이름
        entrance_gate: 외부 연결 정보

    Returns:
        dict: {
            "floors": [{
                "floor": int,
                "region_id": int,
                "locations": {room_id: loc_id},
                "rooms": list[Room],
                "corridors": list[Corridor],
            }],
            "entrance_region_id": int,
            "entrance_location": int,
        }
    """
    floors_info = []

    for i, fd in enumerate(floor_data):
        floor_num = fd["floor"]
        rooms = fd["rooms"]
        corridors = fd["corridors"]
        region_id = base_region_id + i
        floor_label = f"{dungeon_name} {floor_num + 1}F"

        # 이 층의 Region + Location + Gate 등록
        info = build_dungeon(rooms, corridors, region_id, floor_label,
                             entrance_gate=entrance_gate if i == 0 else None)
        info["floor"] = floor_num
        info["rooms"] = rooms
        info["corridors"] = corridors
        floors_info.append(info)

    # 층간 계단 연결 (RegionGate)
    for i in range(len(floors_info) - 1):
        upper = floors_info[i]
        lower = floors_info[i + 1]

        # stairs_down 방 찾기 (upper층)
        stairs_down_loc = None
        for room in upper["rooms"]:
            if room.room_type == "stairs_down":
                stairs_down_loc = upper["locations"].get(room.id)
                break

        # stairs_up 방 찾기 (lower층)
        stairs_up_loc = None
        for room in lower["rooms"]:
            if room.room_type == "stairs_up":
                stairs_up_loc = lower["locations"].get(room.id)
                break

        if stairs_down_loc is not None and stairs_up_loc is not None:
            morld.add_region_gate(
                upper["region_id"], stairs_down_loc,
                lower["region_id"], stairs_up_loc,
                30  # 계단 이동 30초
            )
            print(f"[builder] Stairs: {upper['region_id']}:L{stairs_down_loc} "
                  f"↔ {lower['region_id']}:L{stairs_up_loc}")

    entrance_info = floors_info[0] if floors_info else {}
    return {
        "floors": floors_info,
        "entrance_region_id": entrance_info.get("region_id", base_region_id),
        "entrance_location": entrance_info.get("entrance_location", 0),
    }
