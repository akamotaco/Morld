# chapters/chapter_0.py - 마을과 던전 시작 챕터
#
# 마을 (Region 0): 트리스트럼 컨셉, 안전 거점
# 자원 채취 필드 (Region 1): 마을 외곽
# 던전은 마을 내 입구에서 동적 생성 (별도 시스템)

import morld

# --- Region 정의 ---

VILLAGE_REGION_ID = 0
FIELD_REGION_ID = 1

VILLAGE_REGION = {
    "id": VILLAGE_REGION_ID,
    "name": "마을",
    "describe_text": {"default": "던전 옆에 세워진 작은 마을이다. 모험가들로 북적인다."},
    "weather": "맑음"
}

FIELD_REGION = {
    "id": FIELD_REGION_ID,
    "name": "마을 외곽",
    "describe_text": {"default": "마을 바깥의 자연 지대. 자원을 채취할 수 있다."},
    "weather": "맑음"
}

# --- Location 정의 ---
# 마을 (Region 0)
# 2D 좌표는 map_coords.rebuild()로 Gate 그래프 기반 자동 계산

VILLAGE_LOCATIONS = [
    # (loc_id, name, length, indoor)
    (0,  "마을 광장",   300, False),
    (1,  "여관",        200, True),
    (2,  "대장간",      150, True),
    (3,  "잡화점",      150, True),
    (4,  "술집",        200, True),
    (5,  "구호소",      150, True),
    (6,  "정화소",      100, True),
    (7,  "던전 입구",   100, False),
    (8,  "마을 출구",   100, False),
]

# 자원 채취 필드 (Region 1)
FIELD_LOCATIONS = [
    # (loc_id, name, length, indoor)
    (0,  "숲길",        500, False),
    (1,  "벌목장",      400, False),
    (2,  "강가",        300, False),
    (3,  "야생 채집지", 400, False),
]

# --- Gate 정의 ---
# (region, loc, gate_id, x, conn_region, conn_loc, arrival_x)

VILLAGE_GATES = [
    # 광장(0) ↔ 여관(1)
    (0, 0, 0, 0,   0, 1, 190),
    (0, 1, 0, 190, 0, 0, 0),
    # 광장(0) ↔ 대장간(2)
    (0, 0, 1, 100, 0, 2, 0),
    (0, 2, 0, 0,   0, 0, 100),
    # 광장(0) ↔ 잡화점(3)
    (0, 0, 2, 200, 0, 3, 0),
    (0, 3, 0, 0,   0, 0, 200),
    # 광장(0) ↔ 술집(4)
    (0, 0, 3, 50,  0, 4, 190),
    (0, 4, 0, 190, 0, 0, 50),
    # 광장(0) ↔ 구호소(5)
    (0, 0, 4, 250, 0, 5, 0),
    (0, 5, 0, 0,   0, 0, 250),
    # 광장(0) ↔ 정화소(6)
    (0, 0, 5, 290, 0, 6, 0),
    (0, 6, 0, 0,   0, 0, 290),
    # 광장(0) ↔ 던전 입구(7)
    (0, 0, 6, 150, 0, 7, 0),
    (0, 7, 0, 0,   0, 0, 150),
    # 광장(0) ↔ 마을 출구(8)
    (0, 0, 7, 10,  0, 8, 90),
    (0, 8, 0, 90,  0, 0, 10),
    # 마을 출구(8) ↔ 필드 숲길(R1,0)
    (0, 8, 1, 0,   1, 0, 490),
    (1, 0, 0, 490, 0, 8, 0),
]

FIELD_GATES = [
    # 숲길(0) ↔ 벌목장(1)
    (1, 0, 1, 0,   1, 1, 390),
    (1, 1, 0, 390, 1, 0, 0),
    # 숲길(0) ↔ 강가(2)
    (1, 0, 2, 200, 1, 2, 290),
    (1, 2, 0, 290, 1, 0, 200),
    # 숲길(0) ↔ 야생 채집지(3)
    (1, 0, 3, 100, 1, 3, 390),
    (1, 3, 0, 390, 1, 0, 100),
]

# --- 시간 설정 ---

TIME_SETTINGS = {
    "year": 1,
    "month": 4,
    "day": 1,
    "hour": 8,
    "minute": 0
}


def initialize():
    """챕터 0 초기화: 마을 + 자원 필드"""
    print("[chapter_0] Initializing village and field...")

    # 1. Region 등록
    for r in [VILLAGE_REGION, FIELD_REGION]:
        morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # 2. Location 등록
    import map_coords
    for loc_id, name, length, indoor in VILLAGE_LOCATIONS:
        morld.add_location(VILLAGE_REGION_ID, loc_id, name, length=length, indoor=indoor)
        map_coords.register(VILLAGE_REGION_ID, loc_id)

    for loc_id, name, length, indoor in FIELD_LOCATIONS:
        morld.add_location(FIELD_REGION_ID, loc_id, name, length=length, indoor=indoor)
        map_coords.register(FIELD_REGION_ID, loc_id)

    # 3. Gate 등록
    for gate_data in VILLAGE_GATES + FIELD_GATES:
        region_id, loc_id, gate_id, x, conn_region, conn_loc, arrival_x = gate_data
        morld.add_gate(region_id, loc_id, gate_id, x, conn_region, conn_loc, arrival_x)

    # 4. 지도 좌표 자동 계산 (Gate 완성 후)
    map_coords.rebuild(VILLAGE_REGION_ID)
    map_coords.rebuild(FIELD_REGION_ID)

    # 4. 시간 설정
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))

    # 5. 플레이어 생성
    _instantiate_player()

    # 6. 마을 NPC 스케줄 초기화
    import village_schedule
    village_schedule.initialize()

    print(f"[chapter_0] Initialized: {len(VILLAGE_LOCATIONS)} village + {len(FIELD_LOCATIONS)} field locations")


def _instantiate_player():
    """플레이어 캐릭터 생성"""
    from assets.registry import instantiate_character
    import survival
    import economy
    import party

    player_id = instantiate_character("player", VILLAGE_REGION_ID, 0, x=150)
    morld.set_player(player_id)

    # 생존 시스템 등록
    survival.register_character(player_id)

    # 경제 초기화
    economy.init_money(player_id)

    # 파티 초기화 (플레이어만)
    party.initialize_party(player_id)

    print(f"[chapter_0] Player spawned at village square (id={player_id})")
