# world/mansion.py - 저택 Region
#
# 이 파일에서 저택 Region의 모든 데이터를 정의합니다:
# - 지형 (Region, Location, Edge)
# - 시간 설정
# - 캐릭터/오브젝트/아이템 인스턴스화

import morld
from assets import registry

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
# 지형 데이터
# ========================================

REGION = {
    "id": REGION_ID,
    "name": "저택",
    "appearance": {"default": "으스스한 분위기의 오래된 저택이다."},
    "weather": "흐림"
}

LOCATIONS = [
    (0, "지하실", {
        "default": "어둡고 습한 지하실이다. 먼지 냄새가 코를 찌른다.",
        "불켜짐": "희미한 전등불이 지하실을 비추고 있다."
    }),
    (1, "창고", {
        "default": "오래된 물건들이 여기저기 쌓여 있는 창고다. 거미줄이 가득하다."
    }),
    (2, "거실", {
        "default": "낡은 소파와 먼지 쌓인 벽난로가 있다. 한때 화려했을 흔적이 보인다."
    }),
    (3, "주방", {
        "default": "먼지 쌓인 주방이다. 녹슨 조리도구들이 선반에 놓여 있다."
    }),
    (4, "복도 1층", {
        "default": "긴 복도가 여러 방으로 연결되어 있다. 바닥이 삐걱거린다."
    }),
    (5, "계단", {
        "default": "2층으로 올라가는 나무 계단이다. 일부 계단이 부서져 있다."
    }),
    (6, "침실", {
        "default": "먼지 덮인 침대와 낡은 화장대가 있다. 커튼이 찢어져 있다."
    }),
    (7, "서재", {
        "default": "책장에 오래된 책들이 가득하다. 책상 위에 촛대가 놓여 있다."
    }),
    (8, "복도 2층", {
        "default": "2층 복도다. 벽에 낡은 그림들이 걸려 있다."
    }),
    (9, "정문 홀", {
        "default": "저택의 정문이 있는 넓은 홀이다. 탈출구가 바로 눈앞에 있다!"
    }),
]


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
# 오브젝트 배치 (instance_id, region_id, location_id, unique_id)
# ========================================

OBJECTS = [
    # 지하실 (location: 0)
    (100, REGION_ID, 0, "old_box"),         # 낡은 상자
    (101, REGION_ID, 0, "power_panel"),     # 배전함

    # 창고 (location: 1)
    (102, REGION_ID, 1, "shelf"),           # 선반
    (103, REGION_ID, 1, "old_cabinet"),     # 낡은 캐비닛

    # 거실 (location: 2)
    (104, REGION_ID, 2, "fireplace"),       # 벽난로
    (105, REGION_ID, 2, "sofa_cushion"),    # 소파 쿠션

    # 주방 (location: 3)
    (106, REGION_ID, 3, "refrigerator"),    # 냉장고
    (107, REGION_ID, 3, "cupboard"),        # 찬장

    # 복도 1층 (location: 4)
    (115, REGION_ID, 4, "grandfather_clock"),  # 괘종시계
    (116, REGION_ID, 4, "umbrella_stand"),     # 우산꽂이

    # 계단 (location: 5)
    (117, REGION_ID, 5, "broken_step"),     # 부서진 계단
    (118, REGION_ID, 5, "stair_window"),    # 창문

    # 침실 (location: 6)
    (108, REGION_ID, 6, "bed_under"),       # 침대 밑
    (109, REGION_ID, 6, "vanity_drawer"),   # 화장대 서랍

    # 서재 (location: 7)
    (111, REGION_ID, 7, "safe"),            # 금고
    (112, REGION_ID, 7, "desk_drawer"),     # 책상 서랍

    # 복도 2층 (location: 8)
    (110, REGION_ID, 8, "picture_frame"),   # 그림 액자
    (114, REGION_ID, 8, "study_door"),      # 서재 문

    # 정문 홀 (location: 9)
    (113, REGION_ID, 9, "front_door"),      # 정문
]


# ========================================
# 초기화 함수들
# ========================================

def initialize_terrain():
    """지형 데이터 초기화"""
    r = REGION

    # Region 등록
    morld.add_region(r["id"], r["name"], r["appearance"], r["weather"])

    # Location 등록
    for loc_id, name, appearance in LOCATIONS:
        morld.add_location(
            REGION_ID,    # region_id
            loc_id,       # local_id
            name,         # name
            appearance,   # appearance
            0,            # stay_duration
            True          # is_indoor
        )

    # Edge 등록

    # 지하실-창고 (배전함 스위치 필요)
    morld.add_edge_with_conditions(
        REGION_ID, 0, 1,   # region_id, from_id, to_id
        1, 1,              # time_a_to_b, time_b_to_a
        {"power": 1},      # conditions_a_to_b (지하실→창고)
        {}                 # conditions_b_to_a (창고→지하실) - 무조건
    )

    # 일반 연결
    morld.add_edge(REGION_ID, 1, 4, 1)  # 창고-복도1층
    morld.add_edge(REGION_ID, 2, 4, 1)  # 거실-복도1층
    morld.add_edge(REGION_ID, 3, 4, 1)  # 주방-복도1층
    morld.add_edge(REGION_ID, 4, 5, 1)  # 복도1층-계단
    morld.add_edge(REGION_ID, 5, 8, 1)  # 계단-복도2층
    morld.add_edge(REGION_ID, 6, 8, 1)  # 침실-복도2층

    # 서재-복도2층 (비밀번호로 잠금 해제 필요)
    morld.add_edge_with_conditions(
        REGION_ID, 7, 8,           # region_id, from_id, to_id
        1, 1,                      # time_a_to_b, time_b_to_a
        {},                        # conditions_a_to_b (서재→복도2층) - 무조건
        {"study_unlocked": 1}      # conditions_b_to_a (복도2층→서재) - 잠금
    )

    # 복도2층-정문홀
    morld.add_edge(REGION_ID, 8, 9, 1)

    print(f"[world.mansion] Terrain initialized: {len(LOCATIONS)} locations")


def initialize_time():
    """게임 시간 초기화"""
    # 방 탈출은 시간이 중요하지 않으므로 임의의 시간 설정
    morld.set_time(1842, 10, 31, 18, 0)  # 저택이 지어진 해, 18시
    print("[world.mansion] Time set to 1842-10-31 18:00")


def instantiate():
    """저택 Region의 모든 인스턴스 생성"""

    # 캐릭터 인스턴스화
    for instance_id, unique_id, region_id, location_id in CHARACTERS:
        registry.instantiate_character(unique_id, instance_id, region_id, location_id)

    print(f"[world.mansion] Instantiated {len(CHARACTERS)} characters")

    # 아이템 인스턴스화
    for instance_id, unique_id in ITEMS.items():
        registry.instantiate_item(unique_id, instance_id)

    print(f"[world.mansion] Instantiated {len(ITEMS)} items")

    # 오브젝트 인스턴스화
    for instance_id, region_id, location_id, unique_id in OBJECTS:
        registry.instantiate_object(unique_id, instance_id, region_id, location_id)

    print(f"[world.mansion] Instantiated {len(OBJECTS)} objects")
