# world/city.py - 황폐화된 도시 Region
#
# Region 2: 황폐화된 도시
# - 도시 입구, 주유소, 편의점, 약국, 주차장, 은신처
# - 유키(4)와 엘라(5)가 이 Region에 배치됨

import morld
import equipment

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
    (0, 6, 7),   # 도시 입구 - 의류점
    (1, 4, 3),   # 주유소 - 주차장
    (3, 5, 5),   # 약국 - 은신처 (숨겨진 길)
    (2, 6, 3),   # 편의점 - 의류점
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
        CityEntrance, GasStation, ConvenienceStore, Pharmacy, ParkingLot, Hideout,
        ClothingStore
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
        6: ClothingStore(),   # 의류점
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Edge 등록
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

    print(f"[world.city] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def instantiate_npcs():
    """도심 NPC들 인스턴스화 + Agent 등록 + 옷 장착"""
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

    # NPC들에게 옷 착용
    _dress_npcs(npcs)

    print(f"[world.city] {len(npcs)} NPCs instantiated with agents")
    return npcs


def _dress_npcs(npcs):
    """도시 NPC들에게 기본 옷 착용"""
    from assets.items.clothes import (
        # 유키용 - 수줍고 신비로운 느낌
        OversizedHoodie, LeggingsClothing, WoolSocks, Slippers,
        SimpleBra, SimplePanties,
        # 엘라용 - 냉정하고 리더십 있는 느낌
        TurtleneckSweater, MensSlacks, LeatherBoots, WornOutJacket,
        LaceBra, LacePanties
    )

    def equip_clothes(unit_id, clothes_list):
        """의류 리스트를 유닛에게 장착"""
        for clothes_class in clothes_list:
            item = clothes_class()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            morld.give_item(unit_id, item_id, 1)
            equipment.equip_item(unit_id, item_id)

    # 유키: 오버사이즈 후드티 + 레깅스 + 울양말 + 슬리퍼 + 속옷
    # (수줍고 귀여운 느낌, 은신처에서 편안하게)
    if "yuki" in npcs:
        yuki_id = npcs["yuki"].instance_id
        equip_clothes(yuki_id, [
            OversizedHoodie,    # 상의 (귀여움, 따뜻함)
            LeggingsClothing,   # 하의 (활동적)
            WoolSocks,          # 양말 (따뜻함)
            Slippers,           # 신발
            SimpleBra,          # 속옷상의
            SimplePanties,      # 속옷하의
        ])

    # 엘라: 터틀넥 + 슬랙스 + 가죽 부츠 + 낡은 자켓 + 레이스 속옷
    # (냉정하고 단정한 느낌, 생존자 리더)
    if "ella" in npcs:
        ella_id = npcs["ella"].instance_id
        equip_clothes(ella_id, [
            TurtleneckSweater,  # 상의 (따뜻함, 단정함)
            MensSlacks,         # 하의 (단정함, 깔끔함) - 유니섹스로 사용
            WornOutJacket,      # 외투 (황폐한 도시 분위기)
            LeatherBoots,       # 신발 (활동적, 멋짐)
            LaceBra,            # 속옷상의 (우아함)
            LacePanties,        # 속옷하의 (우아함)
        ])
