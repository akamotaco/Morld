# chapters/chapter_0.py - 프롤로그 챕터
#
# 짧은 맵: 숲 깊은 곳 → 숲 입구 → 앞마당 → 저택 현관
# 플레이어만 존재, NPC 없음
# 저택 도착 후 chapter_1로 전환

import morld

REGION_ID = 0

# 프롤로그 전용 Location 목록 (제한된 맵)
PROLOGUE_LOCATIONS = {
    # 야외/숲
    21: "deep_forest",      # 숲 깊은 곳 (시작점)
    20: "forest_entrance",  # 숲 입구
    12: "front_yard",       # 앞마당
    0: "entrance",          # 현관 (목적지)
}

# 프롤로그용 Edge (제한된 경로)
PROLOGUE_EDGES = [
    (21, 20, 15),  # 숲 깊은 곳 - 숲 입구
    (20, 12, 3),   # 숲 입구 - 앞마당
    (12, 0, 1),    # 앞마당 - 현관
]

REGION = {
    "id": REGION_ID,
    "name": "숲속 저택 (프롤로그)",
    "describe_text": {"default": "깊은 숲 속이다. 어디선가 저택의 불빛이 보인다."},
    "weather": "흐림"
}

TIME_SETTINGS = {
    "year": 1,
    "month": 4,
    "day": 1,
    "hour": 20,  # 저녁 8시 (어두운 분위기)
    "minute": 0
}


def initialize():
    """프롤로그 챕터 초기화"""
    print("[chapter_0] Initializing prologue chapter...")

    # 1. Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # 2. Location 등록 (제한된 맵)
    _initialize_locations()

    # 3. Edge 등록
    for from_id, to_id, travel_time in PROLOGUE_EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

    # 4. 시간 설정
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))

    # 5. 플레이어만 생성
    _instantiate_player()

    print("[chapter_0] Prologue initialized: 4 locations, player only")


def _initialize_locations():
    """프롤로그용 Location 초기화"""
    from assets.locations.entrance import Entrance
    from assets.locations.front_yard import FrontYard
    from assets.locations.forest_entrance import ForestEntrance
    from assets.locations.deep_forest import DeepForest

    locations = {
        0: Entrance(),
        12: FrontYard(),
        20: ForestEntrance(),
        21: DeepForest(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)


def _instantiate_player():
    """플레이어 인스턴스화"""
    from assets.characters.player import Player

    player = Player()
    player.instantiate(0, REGION_ID, 21)  # 숲 깊은 곳에서 시작
