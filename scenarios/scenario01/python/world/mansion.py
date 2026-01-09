# world/mansion.py - 저택 Region
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
# 아이템: 1 ~ 99
# 오브젝트: 100 ~ 199
# NPC: 200 ~ 299
# 바닥 유닛: 1000 + location_id

REGION_ID = 0

# ========================================
# Region 설정
# ========================================

REGION = {
    "id": REGION_ID,
    "name": "저택",
    "describe_text": {"default": "미스터리한 저택이다. 어디선가 삐걱거리는 소리가 들린다."},
    "weather": "흐림"
}

# Region 내 Edge
EDGES = [
    # (from_id, to_id, travel_time)
    # 지하실-창고는 조건부이므로 별도 처리
    (1, 4, 1),   # 창고-복도1층
    (2, 4, 1),   # 거실-복도1층
    (3, 4, 1),   # 주방-복도1층
    (2, 3, 1),   # 거실-주방
    (4, 5, 1),   # 복도1층-계단
    (5, 8, 1),   # 계단-복도2층
    (6, 8, 1),   # 침실-복도2층
    (8, 9, 1),   # 복도2층-정문홀
    # 서재-복도2층은 조건부이므로 별도 처리
]

TIME_SETTINGS = {
    "year": 1842,
    "month": 10,
    "day": 31,
    "hour": 18,
    "minute": 0
}


# ========================================
# 캐릭터 배치
# ========================================

CHARACTERS = [
    # (instance_id, unique_id, region_id, location_id)
    (0, "player", REGION_ID, 0),  # 플레이어 - 지하실에서 시작
]


# ========================================
# 아이템 배치 (instance_id → unique_id)
# ========================================

ITEMS = {
    # 열쇠류
    1: "rusty_key",       # 녹슨 열쇠 (낡은 상자에서 획득)
    2: "silver_key",      # 은열쇠 (캐비닛에서 획득)
    3: "golden_key",      # 황금열쇠 (조합으로 획득)

    # 황금열쇠 파츠
    10: "golden_key_head",  # 황금열쇠 머리 (찬장에서 획득)
    11: "golden_key_body",  # 황금열쇠 몸통 (금고에서 획득)

    # 쪽지류
    4: "note1",           # 쪽지 1 (선반에서 획득)
    5: "note2",           # 쪽지 2 (소파에서 획득)
    6: "note3",           # 쪽지 3 (책상 서랍에서 획득)

    # 문서류
    7: "diary",           # 일기장 (침대 밑에서 획득)
    8: "old_letter",      # 오래된 편지 (침대 밑에서 획득)
    9: "study_memo",      # 서재 메모 (화장대에서 획득)
}


# ========================================
# 초기화 함수들
# ========================================

def initialize_terrain():
    """지형 데이터 초기화 - Location 클래스 방식"""
    # Location 클래스 import
    from assets.locations.basement import Basement
    from assets.locations.storage import Storage
    from assets.locations.living_room import LivingRoom
    from assets.locations.kitchen import Kitchen
    from assets.locations.corridor_1f import Corridor1F
    from assets.locations.stairs import Stairs
    from assets.locations.bedroom import Bedroom
    from assets.locations.study import Study
    from assets.locations.corridor_2f import Corridor2F
    from assets.locations.entrance_hall import EntranceHall

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스 생성 및 등록 (오브젝트도 함께 배치됨)
    locations = {
        0: Basement(),
        1: Storage(),
        2: LivingRoom(),
        3: Kitchen(),
        4: Corridor1F(),
        5: Stairs(),
        6: Bedroom(),
        7: Study(),
        8: Corridor2F(),
        9: EntranceHall(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Edge 등록

    # 지하실-창고 (배전함 스위치 필요)
    morld.add_edge_with_conditions(
        REGION_ID, 0, 1,   # region_id, from_id, to_id
        1, 1,              # time_a_to_b, time_b_to_a
        {"flag:power": 1},      # conditions_a_to_b (지하실→창고)
        {}                 # conditions_b_to_a (창고→지하실) - 무조건
    )

    # 일반 연결
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

    # 서재-복도2층 (비밀번호로 잠금 해제 필요)
    morld.add_edge_with_conditions(
        REGION_ID, 7, 8,           # region_id, from_id, to_id
        1, 1,                      # time_a_to_b, time_b_to_a
        {},                        # conditions_a_to_b (서재→복도2층) - 무조건
        {"flag:study_unlocked": 1}      # conditions_b_to_a (복도2층→서재) - 잠금
    )

    print(f"[world.mansion] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def initialize_time():
    """게임 시간 초기화"""
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))
    print(f"[world.mansion] Time set to {t['year']}-{t['month']}-{t['day']} {t['hour']}:{t.get('minute', 0):02d}")


def instantiate():
    """저택 Region의 모든 인스턴스 생성"""
    # 클래스 import
    from assets.characters.player import Player
    from assets.items.keys import RustyKey, SilverKey
    from assets.items.golden_key import GoldenKeyHead, GoldenKeyBody, GoldenKey
    from assets.items.notes import Note1, Note2, Note3
    from assets.items.documents import Diary, OldLetter, StudyMemo

    # 아이템 레지스트리 등록 (스크립트에서 조회용)
    from assets.items import golden_key as gk_module

    # 아이템 클래스 매핑 (unique_id → class)
    item_classes = {
        "rusty_key": RustyKey,
        "silver_key": SilverKey,
        "golden_key": GoldenKey,
        "golden_key_head": GoldenKeyHead,
        "golden_key_body": GoldenKeyBody,
        "note1": Note1,
        "note2": Note2,
        "note3": Note3,
        "diary": Diary,
        "old_letter": OldLetter,
        "study_memo": StudyMemo,
    }

    # 캐릭터 인스턴스화
    for instance_id, unique_id, region_id, location_id in CHARACTERS:
        if unique_id == "player":
            player = Player()
            player.instantiate(instance_id, region_id, location_id)

    print(f"[world.mansion] Instantiated {len(CHARACTERS)} characters")

    # 아이템 인스턴스화
    for instance_id, unique_id in ITEMS.items():
        if unique_id in item_classes:
            item_cls = item_classes[unique_id]
            item = item_cls()
            item.instantiate(instance_id)
            # 스크립트 조회용 레지스트리 등록
            gk_module.register_item_instance(unique_id, item)

    print(f"[world.mansion] Instantiated {len(ITEMS)} items")

    # 오브젝트는 Location.instantiate()에서 이미 배치됨
    print("[world.mansion] Objects instantiated via Location classes")
