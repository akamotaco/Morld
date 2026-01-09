# world/city.py - 황폐화된 도시 Region
#
# Region 2: 황폐화된 도시
# - 도시 입구, 주유소, 편의점, 약국, 주차장, 은신처
# - 유키(4)와 엘라(5)가 이 Region에 배치됨

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 2

REGION = {
    "id": REGION_ID,
    "name": "황폐화된 도시",
    "describe_text": {"default": "문명이 붕괴된 후 버려진 도시. 건물들이 황폐해져 있다."},
    "weather": "맑음"
}

# Region 내 Edge
EDGES = [
    # (from_id, to_id, travel_time)
    (0, 1, 10),  # 도시 입구 - 주유소
    (0, 2, 5),   # 도시 입구 - 편의점
    (0, 3, 8),   # 도시 입구 - 약국
    (1, 4, 3),   # 주유소 - 주차장
    (3, 5, 5),   # 약국 - 은신처 (숨겨진 길)
]

# NPC 배치
NPC_SPAWNS = [
    # (unique_id, instance_id, region_id, location_id)
    ("yuki", 4, REGION_ID, 5),   # 유키 - 은신처
    ("ella", 5, REGION_ID, 5),   # 엘라 - 은신처
]


# ========================================
# 초기화 함수
# ========================================

def initialize_terrain():
    """도시 Region 초기화"""
    from assets.locations.city import (
        CityEntrance, GasStation, ConvenienceStore, Pharmacy, ParkingLot, Hideout
    )

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스
    locations = {
        0: CityEntrance(),    # 도시 입구
        1: GasStation(),      # 주유소
        2: ConvenienceStore(),# 편의점
        3: Pharmacy(),        # 약국
        4: ParkingLot(),      # 주차장
        5: Hideout(),         # 은신처 (유키/엘라)
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Edge 등록
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

    print(f"[world.city] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def instantiate_npcs():
    """도심 NPC들 인스턴스화 + Agent 등록"""
    from think import register_agent, create_agent_for
    from assets.characters.yuki import Yuki
    from assets.characters.ella import Ella

    npc_classes = {
        "yuki": (Yuki, 4, 5),   # 유키 - 은신처
        "ella": (Ella, 5, 5),   # 엘라 - 은신처
    }

    npcs = {}
    for unique_id, (cls, instance_id, location_id) in npc_classes.items():
        npc = cls()
        npc.instantiate(instance_id, REGION_ID, location_id)
        npcs[unique_id] = npc

        # Agent 등록
        agent = create_agent_for(unique_id, instance_id)
        if agent:
            register_agent(instance_id, agent)

    print(f"[world.city] {len(npcs)} NPCs instantiated with agents")
    return npcs
