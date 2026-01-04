# world/mansion.py - 숲속 저택 Region
#
# 이 파일에서 저택 Region의 모든 데이터를 정의합니다:
# - 지형 (Region, Location, Edge)
# - 시간 설정
# - 캐릭터/오브젝트/아이템 인스턴스화

import morld

# ========================================
# Instance ID 할당 규칙
# ========================================
#
# 플레이어: 0
# NPC: 1 ~ 99
# 아이템: 100 ~ 199
# 오브젝트: 200 ~ 299
# 바닥 유닛: 1000 + location_id (예: location_id=3 → ground_id=1003)

REGION_ID = 0


# ========================================
# 지형 데이터
# ========================================

REGION = {
    "id": REGION_ID,
    "name": "숲속 저택",
    "describe_text": {"default": "깊은 숲 속에 자리한 저택과 그 주변이다."},
    "weather": "맑음"
}

EDGES = [
    # === 저택 1층 연결 ===
    (0, 1, 1),   # 현관 - 거실
    (1, 2, 1),   # 거실 - 주방
    (1, 3, 1),   # 거실 - 식당
    (1, 4, 2),   # 거실 - 욕실
    (1, 5, 2),   # 거실 - 창고
    (1, 6, 1),   # 거실 - 주인공 방 (1층)
    (1, 7, 1),   # 거실 - 리나 방 (1층)
    (1, 9, 1),   # 거실 - 밀라 방 (1층)
    (2, 3, 1),   # 주방 - 식당

    # === 저택 2층 연결 ===
    (1, 14, 1),  # 거실 - 2층 복도 (계단)
    (14, 8, 1),  # 2층 복도 - 세라 방
    (14, 10, 1), # 2층 복도 - 유키 방
    (14, 11, 1), # 2층 복도 - 엘라 방

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
    ("lina", 1, REGION_ID, 7),   # 리나 - 리나의 방
    ("sera", 2, REGION_ID, 8),   # 세라 - 세라의 방
    ("mila", 3, REGION_ID, 9),   # 밀라 - 밀라의 방
    ("yuki", 4, REGION_ID, 10),  # 유키 - 유키의 방
    ("ella", 5, REGION_ID, 11),  # 엘라 - 엘라의 방
]


# ========================================
# 초기화 함수들
# ========================================

def initialize_terrain():
    """지형 데이터 초기화 (Location 클래스 인스턴스 사용)"""
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
    from assets.locations.yuki_room import YukiRoom
    from assets.locations.ella_room import EllaRoom
    from assets.locations.corridor_2f import Corridor2F
    from assets.locations.front_yard import FrontYard
    from assets.locations.back_yard import BackYard
    from assets.locations.forest_entrance import ForestEntrance
    from assets.locations.deep_forest import DeepForest
    from assets.locations.riverside import Riverside
    from assets.locations.gathering_spot import GatheringSpot
    from assets.locations.hunting_ground import HuntingGround

    r = REGION

    # Region 등록
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스 생성 및 등록
    locations = {
        # === 저택 1층 (실내) ===
        0: Entrance(),
        1: LivingRoom(),
        2: Kitchen(),
        3: DiningRoom(),
        4: Bathroom(),
        5: Storage(),
        6: PlayerRoom(),
        7: LinaRoom(),
        8: SeraRoom(),
        9: MilaRoom(),
        10: YukiRoom(),
        11: EllaRoom(),
        14: Corridor2F(),
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

    # Edge 등록 (연결성 정보는 World에서 관리)
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

    print(f"[world.mansion] Terrain initialized: {len(locations)} locations")

    # 인스턴스 반환 (이후 아이템 배치 등에 사용 가능)
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
    player.instantiate(0, REGION_ID, 21)  # 숲 깊은 곳에서 시작
    print("[world.mansion] Player instantiated")
    return player


def instantiate_npcs():
    """NPC들만 인스턴스화 + Agent 등록"""
    from think import register_agent, create_agent_for
    from assets.characters.lina import Lina
    from assets.characters.sera import Sera
    from assets.characters.mila import Mila
    from assets.characters.yuki import Yuki
    from assets.characters.ella import Ella

    npc_classes = {
        "lina": (Lina, 1, 7),
        "sera": (Sera, 2, 8),
        "mila": (Mila, 3, 9),
        "yuki": (Yuki, 4, 10),
        "ella": (Ella, 5, 11),
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

    print(f"[world.mansion] {len(npcs)} NPCs instantiated with agents")
    return npcs


def instantiate():
    """모든 유닛 인스턴스화 (플레이어 + NPC)"""
    player = instantiate_player()
    npcs = instantiate_npcs()

    return {
        "player": player,
        "npcs": npcs,
    }
