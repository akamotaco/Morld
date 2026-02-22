# world/test_dungeon.py — 잊혀진 유적 Region (테스트 던전)
#
# Region 5: 잊혀진 유적
# - 깊은 숲(R3:3)에서 접근 (~15분 도보)
# - 5 Location: 입구, 1층 회랑, 2층 거미굴, 3층 기생실, 유적 심층
# - 몬스터: 거미(1층), 아라크네+기생(2층), 기생(3층), 서큐버스(심층)

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 5

REGION = {
    "id": REGION_ID,
    "name": "잊혀진 유적",
    "describe_text": {"default": "깊은 숲 너머에 숨겨진 고대 유적."},
    "weather": "맑음"
}

# Pi-World Gates (양방향 연결)
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
GATES = [
    # === 유적 입구(0) → 1층 회랑(1) ===
    (REGION_ID, 0, 0, 400, REGION_ID, 1, 0),
    (REGION_ID, 1, 0, 0, REGION_ID, 0, 400),

    # === 1층 회랑(1) → 2층 거미굴(2) ===
    (REGION_ID, 1, 1, 500, REGION_ID, 2, 0),
    (REGION_ID, 2, 0, 0, REGION_ID, 1, 500),

    # === 2층 거미굴(2) → 3층 기생실(3) ===
    (REGION_ID, 2, 1, 400, REGION_ID, 3, 0),
    (REGION_ID, 3, 0, 0, REGION_ID, 2, 400),

    # === 3층 기생실(3) → 유적 심층(4) ===
    (REGION_ID, 3, 1, 300, REGION_ID, 4, 0),
    (REGION_ID, 4, 0, 0, REGION_ID, 3, 300),
]


# ========================================
# 초기화 함수
# ========================================

def initialize_terrain():
    """유적 Region 초기화"""
    from assets.locations.test_dungeon import (
        RuinEntrance, RuinCorridor, RuinNest, RuinParasiteRoom, RuinBossRoom
    )

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스
    locations = {
        0: RuinEntrance(),
        1: RuinCorridor(),
        2: RuinNest(),
        3: RuinParasiteRoom(),
        4: RuinBossRoom(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Gate 등록
    for region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x in GATES:
        morld.add_gate(region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x)

    print(f"[world.test_dungeon] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def register_spawn_sources():
    """유적 몬스터 스폰 소스 등록"""
    from spawner import register_spawn_source
    from assets.characters.monster import Spider, Arachne, Succubus
    from assets.characters.monster import BreastParasiteCreature, GenitalParasiteCreature

    # 1층 회랑: 거미 (일반)
    register_spawn_source(
        source_id="ruin_spiders_1f",
        monster_class=Spider,
        max_count=2,
        interval_hours=4,
        region_id=REGION_ID,
        location_id=1,
    )

    # 2층 거미굴: 아라크네 (인간형) + 기생형
    register_spawn_source(
        source_id="ruin_arachne",
        monster_class=Arachne,
        max_count=1,
        interval_hours=6,
        region_id=REGION_ID,
        location_id=2,
    )
    register_spawn_source(
        source_id="ruin_parasites_2f",
        monster_class=BreastParasiteCreature,
        max_count=1,
        interval_hours=8,
        region_id=REGION_ID,
        location_id=2,
    )

    # 3층 기생실: 기생형 전용
    register_spawn_source(
        source_id="ruin_parasites_3f",
        monster_class=GenitalParasiteCreature,
        max_count=2,
        interval_hours=6,
        region_id=REGION_ID,
        location_id=3,
    )

    # 유적 심층: 서큐버스 (보스)
    register_spawn_source(
        source_id="ruin_boss",
        monster_class=Succubus,
        max_count=1,
        interval_hours=12,
        region_id=REGION_ID,
        location_id=4,
    )

    print("[world.test_dungeon] Spawn sources registered: spiders + arachne + parasites + succubus")
