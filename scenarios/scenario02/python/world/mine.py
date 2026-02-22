# world/mine.py — 폐광산 Region
#
# Region 4: 폐광산
# - 도시 주차장(R2:4)에서 접근 (~30분 도보)
# - 4 Location: 입구, 1층, 2층, 깊은 갱도
# - 몬스터: 박쥐(1층), 거미(2층/깊은)

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 4

REGION = {
    "id": REGION_ID,
    "name": "폐광산",
    "describe_text": {"default": "도시 외곽에 버려진 광산. 깊은 갱도에서 소리가 들린다."},
    "weather": "맑음"
}

# Pi-World Gates (양방향 연결)
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
GATES = [
    # === 광산 입구(0) → 1층 갱도(1) ===
    (REGION_ID, 0, 0, 300, REGION_ID, 1, 0),    # 입구 끝 → 1층 입구
    (REGION_ID, 1, 0, 0, REGION_ID, 0, 300),     # 1층 입구 → 입구 끝

    # === 1층 갱도(1) → 2층 갱도(2) ===
    (REGION_ID, 1, 1, 500, REGION_ID, 2, 0),     # 1층 끝 → 2층 입구
    (REGION_ID, 2, 0, 0, REGION_ID, 1, 500),     # 2층 입구 → 1층 끝

    # === 2층 갱도(2) → 깊은 갱도(3) ===
    (REGION_ID, 2, 1, 400, REGION_ID, 3, 0),     # 2층 끝 → 깊은 입구
    (REGION_ID, 3, 0, 0, REGION_ID, 2, 400),     # 깊은 입구 → 2층 끝
]


# ========================================
# 초기화 함수
# ========================================

def initialize_terrain():
    """광산 Region 초기화"""
    from assets.locations.mine import (
        MineEntrance, MineFloor1, MineFloor2, MineDeep
    )

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스
    locations = {
        0: MineEntrance(),   # 광산 입구
        1: MineFloor1(),     # 1층 갱도
        2: MineFloor2(),     # 2층 갱도
        3: MineDeep(),       # 깊은 갱도
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Gate 등록
    for region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x in GATES:
        morld.add_gate(region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x)

    print(f"[world.mine] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def register_spawn_sources():
    """광산 몬스터 스폰 소스 등록"""
    from spawner import register_spawn_source
    from assets.characters.monster import Bat, Spider

    # 1층 갱도 — 박쥐 (약한 몬스터, 최대 2마리, 4시간 간격)
    register_spawn_source(
        source_id="mine_bats",
        monster_class=Bat,
        max_count=2,
        interval_hours=4,
        region_id=REGION_ID,
        location_id=1,
    )

    # 2층 갱도 — 거미 (중간 몬스터, 최대 1마리, 6시간 간격)
    register_spawn_source(
        source_id="mine_spiders_2f",
        monster_class=Spider,
        max_count=1,
        interval_hours=6,
        region_id=REGION_ID,
        location_id=2,
    )

    # 깊은 갱도 — 거미 (최대 2마리, 8시간 간격)
    register_spawn_source(
        source_id="mine_spiders_deep",
        monster_class=Spider,
        max_count=2,
        interval_hours=8,
        region_id=REGION_ID,
        location_id=3,
    )

    print("[world.mine] Spawn sources registered: bats(2) + spiders(3)")
