# world/mansion.py - 숲속 저택 Region
#
# Region 0: 숲속 저택
# - 저택 내부 (1층, 2층)
# - 마당 (앞마당, 뒷마당)
# - 야외/숲 (숲 입구, 깊은 숲, 강가, 채집터, 사냥터)

import morld

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

# Region 내 Edge
EDGES = [
    # === 저택 1층 연결 ===
    (0, 1, 1),   # 현관 - 거실
    (1, 2, 1),   # 거실 - 주방
    (1, 3, 1),   # 거실 - 식당
    (1, 4, 2),   # 거실 - 욕실
    (1, 6, 1),   # 거실 - 주인공 방 (1층)
    (1, 7, 1),   # 거실 - 리나 방 (1층)
    (1, 9, 1),   # 거실 - 밀라 방 (1층)
    (2, 3, 1),   # 주방 - 식당

    # === 저택 2층 연결 ===
    (1, 14, 1),  # 거실 - 2층 복도 (계단)
    (14, 8, 1),  # 2층 복도 - 세라 방
    (14, 10, 1), # 2층 복도 - 빈 방 1 (guest_room1)
    (14, 11, 1), # 2층 복도 - 빈 방 2 (guest_room2)
    (14, 5, 1),  # 2층 복도 - 창고

    # === 마당 연결 ===
    (0, 12, 1),  # 현관 - 앞마당
    (0, 13, 2),  # 현관 - 뒷마당

    # === 야외/숲 연결 ===
    (12, 20, 3),  # 앞마당 - 숲 입구
    (20, 21, 15), # 숲 입구 - 숲 깊은 곳
    (20, 22, 10), # 숲 입구 - 강가
    (20, 23, 10), # 숲 입구 - 채집터
    (21, 24, 10), # 숲 깊은 곳 - 사냥터
    (23, 22, 5),  # 채집터 - 강가
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
    from assets.locations.yuki_room import GuestRoom1
    from assets.locations.ella_room import GuestRoom2
    from assets.locations.corridor_2f import Corridor2F
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
        10: GuestRoom1(),   # 빈 방 1 (나중에 도심에서 데려올 캐릭터용)
        11: GuestRoom2(),   # 빈 방 2 (나중에 도심에서 데려올 캐릭터용)
        # === 저택 2층 (실내) ===
        14: Corridor2F(),
        5: Storage(),       # 창고 (2층)
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

    # Edge 등록 (Region 내 연결)
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

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
        SeraHuntingOutfit, HuntingVest,
        MaidDress, MilaApron,
        Sundress
    )

    # 세라: 사냥복 + 사냥용 조끼
    if "sera" in npcs:
        sera_id = npcs["sera"].instance_id
        outfit = SeraHuntingOutfit()
        outfit_id = morld.create_id("item")
        outfit.instantiate(outfit_id)
        morld.give_item(sera_id, outfit_id, 1)
        morld.equip_item(sera_id, outfit_id)

        vest = HuntingVest()
        vest_id = morld.create_id("item")
        vest.instantiate(vest_id)
        morld.give_item(sera_id, vest_id, 1)
        morld.equip_item(sera_id, vest_id)

    # 밀라: 메이드복 + 앞치마
    if "mila" in npcs:
        mila_id = npcs["mila"].instance_id
        dress = MaidDress()
        dress_id = morld.create_id("item")
        dress.instantiate(dress_id)
        morld.give_item(mila_id, dress_id, 1)
        morld.equip_item(mila_id, dress_id)

        apron = MilaApron()
        apron_id = morld.create_id("item")
        apron.instantiate(apron_id)
        morld.give_item(mila_id, apron_id, 1)
        morld.equip_item(mila_id, apron_id)

    # 리나: 선드레스
    if "lina" in npcs:
        lina_id = npcs["lina"].instance_id
        sundress = Sundress()
        sundress_id = morld.create_id("item")
        sundress.instantiate(sundress_id)
        morld.give_item(lina_id, sundress_id, 1)
        morld.equip_item(lina_id, sundress_id)


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
