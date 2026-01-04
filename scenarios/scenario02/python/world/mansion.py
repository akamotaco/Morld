# world/mansion.py - 숲속 저택 Region
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
# NPC: 1 ~ 99
# 아이템: 100 ~ 199
# 오브젝트: 200 ~ 299
# 바닥 유닛: 1000 + location_id

REGION_ID = 0


# ========================================
# 지형 데이터
# ========================================

REGION = {
    "id": REGION_ID,
    "name": "숲속 저택",
    "appearance": {"default": "깊은 숲 속에 자리한 저택과 그 주변이다."},
    "weather": "맑음"
}

LOCATIONS = [
    # === 저택 1층 (실내) ===
    (0, "현관", True, 0, {
        "default": "저택의 입구. 무거운 나무 문이 달려 있다.",
        "아침": "아침 햇살이 문틈으로 스며든다.",
        "밤": "어둠 속에 문의 윤곽만 희미하게 보인다."
    }),
    (1, "거실", True, 0, {
        "default": "넓은 거실. 벽난로와 낡은 소파가 놓여 있다. 이곳에서 매일 아침 조회가 열린다.",
        "아침": "창문으로 들어오는 햇살이 먼지 입자를 비춘다.",
        "저녁": "벽난로에 불이 피워져 따뜻한 분위기다.",
        "밤": "벽난로의 불씨가 은은하게 타오른다."
    }),
    (2, "주방", True, 0, {
        "default": "각종 조리도구가 걸려 있는 주방. 아궁이에서 연기가 피어오른다.",
        "아침": "아침 식사를 준비하는 냄새가 난다.",
        "낮": "점심 준비로 분주하다.",
        "저녁": "저녁 식사 준비로 맛있는 냄새가 가득하다."
    }),
    (3, "식당", True, 0, {
        "default": "긴 나무 테이블이 놓인 식당. 여섯 개의 의자가 가지런히 놓여 있다.",
        "아침": "아침 식사 시간. 테이블에 음식이 차려져 있다.",
        "낮": "점심 시간. 따뜻한 음식 냄새가 풍긴다.",
        "저녁": "저녁 식사 시간. 촛불이 테이블을 밝힌다."
    }),
    (4, "욕실", True, 0, {
        "default": "낡지만 깨끗하게 관리된 욕실. 큰 나무 욕조가 놓여 있다."
    }),
    (5, "창고", True, 0, {
        "default": "선반에 식량과 도구가 정리되어 있다. 약간 먼지 냄새가 난다."
    }),
    (6, "주인공 방", True, 0, {
        "default": "작지만 아늑한 방. 침대와 작은 책상이 놓여 있다.",
        "아침": "창문으로 아침 햇살이 들어온다.",
        "밤": "촛불 하나가 방을 희미하게 밝힌다."
    }),
    (7, "리나의 방", True, 0, {
        "default": "밝고 활기찬 분위기의 방. 창가에 작은 화분이 놓여 있다."
    }),
    (8, "세라의 방", True, 0, {
        "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다."
    }),
    (9, "밀라의 방", True, 0, {
        "default": "따뜻한 느낌의 방. 손수 만든 쿠션과 담요가 곳곳에 있다."
    }),
    (10, "유키의 방", True, 0, {
        "default": "조용하고 깔끔한 방. 책이 가지런히 정리되어 있다."
    }),
    (11, "엘라의 방", True, 0, {
        "default": "단정하고 권위있는 분위기의 방. 책상 위에 서류가 놓여 있다."
    }),
    (14, "2층 복도", True, 0, {
        "default": "2층으로 올라오면 나오는 넓은 복도. 창문으로 저택 앞마당이 내려다보인다.",
        "아침": "아침 햇살이 창문을 통해 복도를 비춘다.",
        "밤": "복도 양쪽에 걸린 촛불이 희미하게 길을 밝힌다."
    }),

    # === 마당 (실외) ===
    (12, "앞마당", False, 0, {
        "default": "저택 앞에 펼쳐진 넓은 마당. 잘 가꿔진 정원이 있다.",
        "아침": "아침 이슬이 풀잎에 맺혀 반짝인다.",
        "낮": "햇살이 정원을 환하게 비춘다.",
        "저녁": "석양빛이 정원을 황금빛으로 물들인다.",
        "밤": "달빛 아래 정원이 고요하다.",
        "날씨:비": "빗줄기가 정원을 적시고 있다.",
        "날씨:눈": "눈이 정원을 하얗게 덮고 있다."
    }),
    (13, "뒷마당", False, 0, {
        "default": "저택 뒤편의 넓은 공터. 텃밭을 가꿀 수 있을 것 같다.",
        "아침": "아침 안개가 뒷마당을 감싸고 있다.",
        "낮": "햇살이 따스하게 내리쬔다.",
        "저녁": "저녁 노을이 아름답다.",
        "밤": "고요한 밤. 풀벌레 소리가 들린다.",
        "날씨:비": "빗방울이 텃밭을 적시고 있다.",
        "날씨:눈": "눈이 소복이 쌓여 있다."
    }),

    # === 야외/숲 (실외) ===
    (20, "숲 입구", False, 5, {
        "default": "저택으로 이어지는 숲길. 오래된 나무들이 늘어서 있다.",
        "아침": "아침 안개가 숲 입구를 감싸고 있다.",
        "낮": "햇살이 나뭇잎 사이로 쏟아진다.",
        "저녁": "석양빛이 나무 사이로 비친다.",
        "밤": "어둠 속에 나무들의 실루엣만 보인다.",
        "날씨:비": "빗방울이 나뭇잎을 두드린다.",
        "날씨:눈": "눈이 소복이 쌓여 발자국이 선명하다."
    }),
    (21, "숲 깊은 곳", False, 0, {
        "default": "울창한 나무들 사이. 낮에도 어둑하고 길을 잃기 쉽다.",
        "낮": "나뭇잎 사이로 간간이 빛이 스며든다.",
        "밤": "칠흑같이 어둡다. 부엉이 소리가 들린다.",
        "날씨:비": "빗물이 나뭇잎을 타고 흘러내린다.",
        "날씨:눈": "눈이 쌓여 숲이 고요하다."
    }),
    (22, "강가", False, 0, {
        "default": "맑은 물이 흐르는 작은 강. 물소리가 청량하게 들린다.",
        "아침": "아침 햇살에 수면이 반짝인다.",
        "낮": "햇빛에 물이 눈부시게 빛난다.",
        "저녁": "노을빛이 수면에 비친다.",
        "날씨:비": "빗방울이 수면에 파문을 만든다.",
        "날씨:눈": "강가에 눈이 쌓여 있다."
    }),
    (23, "채집터", False, 0, {
        "default": "야생 열매와 약초가 자라는 곳. 숲의 은혜를 느낄 수 있다.",
        "봄": "새싹이 돋아나고 있다.",
        "여름": "무성한 풀과 열매가 가득하다.",
        "가을": "익은 열매가 주렁주렁 달려 있다.",
        "겨울": "말라버린 풀만 남아 있다.",
        "날씨:비": "비에 젖은 풀잎이 반짝인다.",
        "날씨:눈": "눈 아래 겨울잠을 자는 듯하다."
    }),
    (24, "사냥터", False, 0, {
        "default": "야생 동물의 흔적이 보이는 곳. 조심스럽게 움직여야 한다.",
        "아침": "이슬 맺힌 풀 위에 동물 발자국이 보인다.",
        "낮": "숲 속에서 동물 울음소리가 들린다.",
        "밤": "어둠 속에서 눈빛이 반짝인다.",
        "날씨:비": "비 오는 날은 사냥하기 어렵다.",
        "날씨:눈": "눈 위에 선명한 발자국이 보인다."
    }),
]

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

PLAYER_SPAWN = {
    "unique_id": "player",
    "instance_id": 0,
    "region_id": REGION_ID,
    "location_id": 21,  # 숲 깊은 곳에서 시작 (기억상실 상태로 방황)
}

NPC_SPAWNS = [
    # (unique_id, instance_id, region_id, location_id)
    ("lina", 1, REGION_ID, 7),   # 리나 - 리나의 방
    ("sera", 2, REGION_ID, 8),   # 세라 - 세라의 방
    ("mila", 3, REGION_ID, 9),   # 밀라 - 밀라의 방
    ("yuki", 4, REGION_ID, 10),  # 유키 - 유키의 방
    ("ella", 5, REGION_ID, 11),  # 엘라 - 엘라의 방
]


# ========================================
# 아이템 배치
# ========================================

ITEMS = [
    # (instance_id, unique_id)
    # 기본 자원류
    (100, "flour"),
    (101, "rice"),
    (102, "water"),
    (103, "bread"),
    (104, "berry"),
    (105, "meat"),
    (106, "wood"),
    (107, "herb"),
    (108, "cloth"),
    # 장비류
    (110, "old_knife"),
    (111, "leather_pouch"),
    (112, "writing_tool"),
    (113, "old_book"),
    (114, "small_toolbox"),
]


# ========================================
# 오브젝트 배치
# ========================================

OBJECTS = [
    # (instance_id, region_id, location_id, unique_id)
    # 거실
    (200, REGION_ID, 1, "fireplace"),
    (201, REGION_ID, 1, "sofa"),
    (202, REGION_ID, 1, "bookshelf"),
    # 주방
    (210, REGION_ID, 2, "stove"),
    (211, REGION_ID, 2, "cupboard"),
    # 식당
    (220, REGION_ID, 3, "dining_table"),
    # 앞마당
    (230, REGION_ID, 12, "garden_bench"),
    (231, REGION_ID, 12, "well"),
    # 뒷마당
    (240, REGION_ID, 13, "garden_plot"),
    (241, REGION_ID, 13, "drying_rack"),
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
    for loc_id, name, is_indoor, stay_duration, appearance in LOCATIONS:
        morld.add_location(
            REGION_ID,
            loc_id,
            name,
            appearance,
            stay_duration,
            is_indoor
        )

    # Edge 등록
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

    print(f"[world.mansion] Terrain initialized: {len(LOCATIONS)} locations")


def initialize_time():
    """게임 시간 초기화"""
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))
    print(f"[world.mansion] Time set to {t['year']}/{t['month']}/{t['day']} {t['hour']}:{t.get('minute', 0):02d}")


def instantiate_player():
    """플레이어만 인스턴스화"""
    p = PLAYER_SPAWN
    registry.instantiate_character(p["unique_id"], p["instance_id"], p["region_id"], p["location_id"])
    print("[world.mansion] Player instantiated")


def instantiate_npcs():
    """NPC들만 인스턴스화"""
    for unique_id, instance_id, region_id, location_id in NPC_SPAWNS:
        registry.instantiate_character(unique_id, instance_id, region_id, location_id)
    print(f"[world.mansion] {len(NPC_SPAWNS)} NPCs instantiated")


def instantiate():
    """모든 유닛 인스턴스화 (플레이어 + NPC + 오브젝트 + 아이템)"""
    # 플레이어
    instantiate_player()

    # NPC
    instantiate_npcs()

    # 아이템
    for instance_id, unique_id in ITEMS:
        registry.instantiate_item(unique_id, instance_id)
    print(f"[world.mansion] {len(ITEMS)} items instantiated")

    # 오브젝트
    for instance_id, region_id, location_id, unique_id in OBJECTS:
        registry.instantiate_object(unique_id, instance_id, region_id, location_id)
    print(f"[world.mansion] {len(OBJECTS)} objects instantiated")
