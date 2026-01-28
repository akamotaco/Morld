# world/mansion.py - 숲속 저택 Region
#
# Region 0: 숲속 저택
# - 저택 내부 (1층, 2층)
# - 마당 (앞마당, 뒷마당)
# - 야외/숲 (숲 입구, 깊은 숲, 강가, 채집터, 사냥터)

import morld
import equipment

# ========================================
# Instance ID 생성
# ========================================
#
# morld.create_id(category)를 사용하여 동적 생성
# - "unit": 캐릭터 + 오브젝트
# - "item": 아이템
# - "location": 장소 (필요 시)
#
# 바닥 유닛: 1000 + location_id (예: location_id=3 → ground_id=1003)

# ========================================
# Region 설정
# ========================================

REGION_ID = 0

REGION = {
    "id": REGION_ID,
    "name": "숲속 저택",
    "describe_text": {"default": "깊은 숲 속에 자리한 저택과 그 주변이다."},
    "weather": "맑음"
}

# ========================================
# Pi-World Gate 정의
# ========================================
#
# Gate는 Location 간 연결점 (통과 시간 = 0)
# 이동 시간 = Location 내에서 Gate까지의 거리 / 속도
#
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
#
# - x: Gate의 위치 (이 Location 내)
# - arrival_x: Gate 통과 시 도착 위치 (연결된 Location 내)
#
# Location 길이 설정:
# - 실내 (방): 30 단위
# - 복도/거실: 50~60 단위
# - 마당: 100 단위
# - 숲: 200~300 단위

GATES = [
    # === 저택 1층 연결 ===
    # 현관(0) <-> 거실(1)
    (REGION_ID, 0, 0, 30, REGION_ID, 1, 0),   # 현관 끝(x=30) -> 거실 입구(x=0)
    (REGION_ID, 1, 0, 0, REGION_ID, 0, 30),   # 거실 입구(x=0) -> 현관 끝(x=30)

    # 거실(1) <-> 주방(2)
    (REGION_ID, 1, 1, 50, REGION_ID, 2, 0),   # 거실 오른쪽(x=50) -> 주방 입구(x=0)
    (REGION_ID, 2, 0, 0, REGION_ID, 1, 50),   # 주방 입구(x=0) -> 거실 오른쪽(x=50)

    # 거실(1) <-> 식당(3)
    (REGION_ID, 1, 2, 25, REGION_ID, 3, 0),   # 거실 중앙(x=25) -> 식당 입구(x=0)
    (REGION_ID, 3, 0, 0, REGION_ID, 1, 25),   # 식당 입구(x=0) -> 거실 중앙(x=25)

    # 거실(1) <-> 욕실(4)
    (REGION_ID, 1, 3, 40, REGION_ID, 4, 0),   # 거실(x=40) -> 욕실 입구(x=0)
    (REGION_ID, 4, 0, 0, REGION_ID, 1, 40),   # 욕실 입구(x=0) -> 거실(x=40)

    # 거실(1) <-> 주인공 방(6)
    (REGION_ID, 1, 4, 10, REGION_ID, 6, 0),   # 거실 왼쪽(x=10) -> 주인공 방(x=0)
    (REGION_ID, 6, 0, 0, REGION_ID, 1, 10),   # 주인공 방(x=0) -> 거실(x=10)

    # 거실(1) <-> 리나 방(7)
    (REGION_ID, 1, 5, 15, REGION_ID, 7, 0),   # 거실(x=15) -> 리나 방(x=0)
    (REGION_ID, 7, 0, 0, REGION_ID, 1, 15),   # 리나 방(x=0) -> 거실(x=15)

    # 거실(1) <-> 밀라 방(9)
    (REGION_ID, 1, 6, 20, REGION_ID, 9, 0),   # 거실(x=20) -> 밀라 방(x=0)
    (REGION_ID, 9, 0, 0, REGION_ID, 1, 20),   # 밀라 방(x=0) -> 거실(x=20)

    # 거실(1) <-> 1층 화장실(15)
    (REGION_ID, 1, 7, 45, REGION_ID, 15, 0),  # 거실(x=45) -> 1층 화장실(x=0)
    (REGION_ID, 15, 0, 0, REGION_ID, 1, 45),  # 1층 화장실(x=0) -> 거실(x=45)

    # 주방(2) <-> 식당(3)
    (REGION_ID, 2, 1, 30, REGION_ID, 3, 30),  # 주방 끝(x=30) -> 식당(x=30)
    (REGION_ID, 3, 1, 30, REGION_ID, 2, 30),  # 식당(x=30) -> 주방 끝(x=30)

    # === 저택 2층 연결 ===
    # 거실(1) <-> 2층 복도(14) - 계단
    (REGION_ID, 1, 8, 30, REGION_ID, 14, 0),  # 거실 계단(x=30) -> 2층 복도(x=0)
    (REGION_ID, 14, 0, 0, REGION_ID, 1, 30),  # 2층 복도(x=0) -> 거실 계단(x=30)

    # 2층 복도(14) <-> 세라 방(8)
    (REGION_ID, 14, 1, 10, REGION_ID, 8, 0),  # 2층 복도(x=10) -> 세라 방(x=0)
    (REGION_ID, 8, 0, 0, REGION_ID, 14, 10),  # 세라 방(x=0) -> 2층 복도(x=10)

    # 2층 복도(14) <-> 빈 방 1(10)
    (REGION_ID, 14, 2, 20, REGION_ID, 10, 0), # 2층 복도(x=20) -> 빈 방 1(x=0)
    (REGION_ID, 10, 0, 0, REGION_ID, 14, 20), # 빈 방 1(x=0) -> 2층 복도(x=20)

    # 2층 복도(14) <-> 빈 방 2(11)
    (REGION_ID, 14, 3, 30, REGION_ID, 11, 0), # 2층 복도(x=30) -> 빈 방 2(x=0)
    (REGION_ID, 11, 0, 0, REGION_ID, 14, 30), # 빈 방 2(x=0) -> 2층 복도(x=30)

    # 2층 복도(14) <-> 창고(5)
    (REGION_ID, 14, 4, 40, REGION_ID, 5, 0),  # 2층 복도(x=40) -> 창고(x=0)
    (REGION_ID, 5, 0, 0, REGION_ID, 14, 40),  # 창고(x=0) -> 2층 복도(x=40)

    # 2층 복도(14) <-> 2층 화장실(16)
    (REGION_ID, 14, 5, 50, REGION_ID, 16, 0), # 2층 복도(x=50) -> 2층 화장실(x=0)
    (REGION_ID, 16, 0, 0, REGION_ID, 14, 50), # 2층 화장실(x=0) -> 2층 복도(x=50)

    # === 마당 연결 ===
    # 현관(0) <-> 앞마당(12)
    (REGION_ID, 0, 1, 0, REGION_ID, 12, 0),   # 현관 앞(x=0) -> 앞마당(x=0)
    (REGION_ID, 12, 0, 0, REGION_ID, 0, 0),   # 앞마당(x=0) -> 현관 앞(x=0)

    # 현관(0) <-> 뒷마당(13)
    (REGION_ID, 0, 2, 15, REGION_ID, 13, 0),  # 현관 옆(x=15) -> 뒷마당(x=0)
    (REGION_ID, 13, 0, 0, REGION_ID, 0, 15),  # 뒷마당(x=0) -> 현관 옆(x=15)

    # === 야외/숲 연결 ===
    # 앞마당(12) <-> 숲 입구(20)
    (REGION_ID, 12, 1, 100, REGION_ID, 20, 0),  # 앞마당 끝(x=100) -> 숲 입구(x=0)
    (REGION_ID, 20, 0, 0, REGION_ID, 12, 100),  # 숲 입구(x=0) -> 앞마당 끝(x=100)

    # 숲 입구(20) <-> 숲 깊은 곳(21)
    (REGION_ID, 20, 1, 300, REGION_ID, 21, 0),  # 숲 입구 깊이(x=300) -> 숲 깊은 곳(x=0)
    (REGION_ID, 21, 0, 0, REGION_ID, 20, 300),  # 숲 깊은 곳(x=0) -> 숲 입구(x=300)

    # 숲 입구(20) <-> 강가(22)
    (REGION_ID, 20, 2, 200, REGION_ID, 22, 0),  # 숲 입구 옆(x=200) -> 강가(x=0)
    (REGION_ID, 22, 0, 0, REGION_ID, 20, 200),  # 강가(x=0) -> 숲 입구(x=200)

    # 숲 입구(20) <-> 채집터(23)
    (REGION_ID, 20, 3, 150, REGION_ID, 23, 0),  # 숲 입구(x=150) -> 채집터(x=0)
    (REGION_ID, 23, 0, 0, REGION_ID, 20, 150),  # 채집터(x=0) -> 숲 입구(x=150)

    # 숲 깊은 곳(21) <-> 사냥터(24)
    (REGION_ID, 21, 1, 300, REGION_ID, 24, 0),  # 숲 깊은 곳(x=300) -> 사냥터(x=0)
    (REGION_ID, 24, 0, 0, REGION_ID, 21, 300),  # 사냥터(x=0) -> 숲 깊은 곳(x=300)

    # 채집터(23) <-> 강가(22)
    (REGION_ID, 23, 1, 150, REGION_ID, 22, 200), # 채집터(x=150) -> 강가(x=200)
    (REGION_ID, 22, 1, 200, REGION_ID, 23, 150), # 강가(x=200) -> 채집터(x=150)
]

TIME_SETTINGS = {
    "year": 1,
    "month": 4,  # 봄
    "day": 1,
    "hour": 14,  # 오후 2시 시작 (숲에서 방황 중)
    "minute": 0
}


# ========================================
# 캐릭터 배치
# ========================================

NPC_SPAWNS = [
    # (unique_id, instance_id, region_id, location_id)
    ("lina", 1, REGION_ID, 7),   # 리나 - 리나 방
    ("sera", 2, REGION_ID, 8),   # 세라 - 세라 방
    ("mila", 3, REGION_ID, 9),   # 밀라 - 밀라 방
    # 유키(4)와 엘라(5)는 도심 Region에 배치됨 (world/city.py)
]


# ========================================
# 초기화 함수들
# ========================================

def initialize_terrain():
    """저택 Region 초기화"""
    # Location 클래스 import
    from assets.locations.entrance import Entrance
    from assets.locations.living_room import LivingRoom
    from assets.locations.kitchen import Kitchen
    from assets.locations.dining_room import DiningRoom
    from assets.locations.bathroom import Bathroom
    from assets.locations.storage import Storage
    from assets.locations.player_room import PlayerRoom
    from assets.locations.lina_room import LinaRoom
    from assets.locations.sera_room import SeraRoom
    from assets.locations.mila_room import MilaRoom
    from assets.locations.guest_room import GuestRoom
    from assets.locations.corridor_2f import Corridor2F
    from assets.locations.toilet import ToiletRoom
    from assets.locations.front_yard import FrontYard
    from assets.locations.back_yard import BackYard
    from assets.locations.forest_entrance import ForestEntrance
    from assets.locations.deep_forest import DeepForest
    from assets.locations.riverside import Riverside
    from assets.locations.gathering_spot import GatheringSpot
    from assets.locations.hunting_ground import HuntingGround

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스 생성 및 등록
    locations = {
        # === 저택 1층 (실내) ===
        0: Entrance(),
        1: LivingRoom(),
        2: Kitchen(),
        3: DiningRoom(),
        4: Bathroom(),
        6: PlayerRoom(),
        7: LinaRoom(),
        8: SeraRoom(),
        9: MilaRoom(),
        10: GuestRoom("guest_room1", "정리되어 있지만 사람 냄새가 나지 않는 방. 아무도 사용하지 않는 듯하다."),
        11: GuestRoom("guest_room2", "깨끗하지만 비어있는 방. 언젠가 누군가 사용할 것 같다."),
        15: ToiletRoom("toilet_1f", "저택 1층에 있는 작은 화장실. 깔끔하게 정돈되어 있다."),
        # === 저택 2층 (실내) ===
        14: Corridor2F(),
        5: Storage(),       # 창고 (2층)
        16: ToiletRoom("toilet_2f", "저택 2층에 있는 작은 화장실. 창문으로 숲이 보인다."),
        # === 마당 (실외) ===
        12: FrontYard(),
        13: BackYard(),
        # === 야외/숲 (실외) ===
        20: ForestEntrance(),
        21: DeepForest(),
        22: Riverside(),
        23: GatheringSpot(),
        24: HuntingGround(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Gate 등록 (Pi-World 연결)
    for region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x in GATES:
        morld.add_gate(region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x)

    print(f"[world.mansion] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def initialize_time():
    """게임 시간 초기화"""
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))
    print(f"[world.mansion] Time set to {t['year']}/{t['month']}/{t['day']} {t['hour']}:{t.get('minute', 0):02d}")


def instantiate_player():
    """플레이어만 인스턴스화"""
    from assets.characters.player import Player

    player = Player()
    player_id = morld.create_id("unit")
    player.instantiate(player_id, REGION_ID, 21)  # 숲 깊은 곳에서 시작
    print(f"[world.mansion] Player instantiated (id={player_id})")
    return player


def instantiate_npcs():
    """저택 NPC들만 인스턴스화 + Agent 등록 + 옷 장착 (유키/엘라는 도심에 배치)"""
    from think import register_agent, create_agent_for
    from assets.characters.lina import Lina
    from assets.characters.sera import Sera
    from assets.characters.mila import Mila

    # (cls, location_id)
    npc_classes = {
        "lina": (Lina, 7),
        "sera": (Sera, 8),
        "mila": (Mila, 9),
    }

    npcs = {}
    for unique_id, (cls, location_id) in npc_classes.items():
        npc = cls()
        instance_id = morld.create_id("unit")
        npc.instantiate(instance_id, REGION_ID, location_id)
        npcs[unique_id] = npc

        # Agent 등록
        agent = create_agent_for(unique_id, instance_id)
        if agent:
            register_agent(instance_id, agent)

    # NPC들에게 옷 착용
    _dress_npcs(npcs)

    print(f"[world.mansion] {len(npcs)} NPCs instantiated with agents")
    return npcs


def _dress_npcs(npcs):
    """NPC들에게 기본 옷 착용"""
    from assets.items.clothes import (
        # 세라용
        SeraHuntingOutfit, HuntingVest, LeatherBoots, SportsBra, CottonPanties,
        # 밀라용
        MaidDress, MilaApron, MaidHeadband, SimpleShoes, Stockings, SimpleBra, SimplePanties,
        # 리나용
        Sundress, Sandals, Ribbon, ThighHighSocks, CuteBra, CutePanties
    )

    def equip_clothes(unit_id, clothes_list):
        """의류 리스트를 유닛에게 장착"""
        for clothes_class in clothes_list:
            item = clothes_class()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            morld.give_item(unit_id, item_id, 1)
            equipment.equip_item(unit_id, item_id)

    # 세라: 사냥복 + 사냥용 조끼 + 가죽 부츠 + 스포츠 브라 + 면 팬티
    if "sera" in npcs:
        sera_id = npcs["sera"].instance_id
        equip_clothes(sera_id, [
            SeraHuntingOutfit,  # 상의+하의 일체형
            HuntingVest,        # 외투
            LeatherBoots,       # 신발
            SportsBra,          # 속옷상의
            CottonPanties,      # 속옷하의
        ])

    # 밀라: 메이드복 + 앞치마 + 머리띠 + 신발 + 스타킹 + 속옷
    if "mila" in npcs:
        mila_id = npcs["mila"].instance_id
        equip_clothes(mila_id, [
            MaidDress,          # 상의+하의 일체형
            MilaApron,          # 외투
            MaidHeadband,       # 모자
            SimpleShoes,        # 신발
            Stockings,          # 양말
            SimpleBra,          # 속옷상의
            SimplePanties,      # 속옷하의
        ])

    # 리나: 선드레스 + 샌들 + 리본 + 사이하이삭스 + 귀여운 속옷
    if "lina" in npcs:
        lina_id = npcs["lina"].instance_id
        equip_clothes(lina_id, [
            Sundress,           # 상의+하의 일체형
            Sandals,            # 신발
            Ribbon,             # 모자
            ThighHighSocks,     # 양말
            CuteBra,            # 속옷상의
            CutePanties,        # 속옷하의
        ])


def instantiate():
    """모든 유닛 인스턴스화 (플레이어 + NPC)"""
    player = instantiate_player()
    npcs = instantiate_npcs()

    return {
        "player": player,
        "npcs": npcs,
    }


# ========================================
# 자연 오브젝트 배치
# ========================================

# 오브젝트 배치 정보
# (unique_id, region_id, location_id, initial_resources)
NATURE_OBJECTS = [
    # 채집터 (location 23)
    ("berry_bush", REGION_ID, 23, 3),      # 산딸기 덤불
    ("mushroom_patch", REGION_ID, 23, 2),  # 버섯 군락

    # 숲 깊은 곳 (location 21)
    ("apple_tree", REGION_ID, 21, 2),      # 사과나무

    # 강가 (location 22)
    ("berry_bush", REGION_ID, 22, 2),      # 산딸기 덤불

    # 뒷마당 (location 13)
    ("herb_garden", REGION_ID, 13, 3),     # 약초밭
]


# 음식 아이템 unique_id 목록
FOOD_ITEM_UNIQUE_IDS = [
    "food_wild_berry",
    "food_apple",
    "food_mushroom",
    "food_cooked_meat",
    "food_cooked_fish",
    "food_fish",
    "food_herb",
    "drink_herb_tea",
    "food_fruit_salad",
    "food_mushroom_stew",
]


def instantiate_food_items():
    """음식 아이템들을 ItemSystem에 등록"""
    from assets.items.food import (
        WildBerry, Apple, Mushroom, CookedMeat, CookedFish, Fish,
        Herb, HerbTea, FruitSalad, MushroomStew
    )

    item_classes = {
        "food_wild_berry": WildBerry,
        "food_apple": Apple,
        "food_mushroom": Mushroom,
        "food_cooked_meat": CookedMeat,
        "food_cooked_fish": CookedFish,
        "food_fish": Fish,
        "food_herb": Herb,
        "drink_herb_tea": HerbTea,
        "food_fruit_salad": FruitSalad,
        "food_mushroom_stew": MushroomStew,
    }

    count = 0
    for unique_id in FOOD_ITEM_UNIQUE_IDS:
        cls = item_classes.get(unique_id)
        if cls:
            item = cls()
            instance_id = morld.create_id("item")
            item.instantiate(instance_id)
            count += 1

    print(f"[world.mansion] {count} food items registered")


def instantiate_nature_objects():
    """자연 오브젝트 인스턴스화 + 이벤트 기반 자원 생성 등록 + 초기 자원 생성"""
    from think.resource_agent import register_resource_object
    from assets.objects.nature import AppleTree, BerryBush, MushroomPatch, HerbGarden

    object_classes = {
        "apple_tree": AppleTree,
        "berry_bush": BerryBush,
        "mushroom_patch": MushroomPatch,
        "herb_garden": HerbGarden,
    }

    objects = []
    for unique_id, region_id, location_id, initial_resources in NATURE_OBJECTS:
        cls = object_classes.get(unique_id)
        if not cls:
            print(f"[world.mansion] Unknown object: {unique_id}")
            continue

        obj = cls()
        instance_id = morld.create_id("unit")  # 오브젝트도 unit 카테고리
        obj.instantiate(instance_id, region_id, location_id)
        objects.append(obj)

        # 이벤트 기반 자원 생성 등록
        register_resource_object(instance_id, unique_id)

        # 초기 자원 생성
        for _ in range(initial_resources):
            obj.spawn_resource()

    print(f"[world.mansion] {len(objects)} nature objects instantiated")
    return objects
