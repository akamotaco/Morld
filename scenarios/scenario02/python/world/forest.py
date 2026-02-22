# world/forest.py - 숲 Region
#
# Region 3: 숲
# - 0: 숲 입구 (저택과 연결)
# - 1: 소나무 숲
# - 2: 참나무 숲
# - 3: 숲속 (토끼 굴 오브젝트 배치)
# - 4: 늑대굴
# - 5: 오두막

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 3

REGION = {
    "id": REGION_ID,
    "name": "숲",
    "describe_text": {"default": "울창한 나무들이 빽빽한 깊은 숲이다."},
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
# Location 길이:
# - 0: 숲 입구 - 200
# - 1: 소나무 숲 - 300
# - 2: 참나무 숲 - 300
# - 3: 숲속 - 400
# - 4: 늑대굴 - 600
# - 5: 오두막 - 30

GATES = [
    # 숲 입구(0) <-> 소나무 숲(1)
    (REGION_ID, 0, 0, 600, REGION_ID, 1, 0),   # 숲 입구(x=600) -> 소나무 숲(x=0)
    (REGION_ID, 1, 0, 0, REGION_ID, 0, 600),   # 소나무 숲(x=0) -> 숲 입구(x=600)

    # 숲 입구(0) <-> 참나무 숲(2)
    (REGION_ID, 0, 1, 900, REGION_ID, 2, 0),   # 숲 입구(x=900) -> 참나무 숲(x=0)
    (REGION_ID, 2, 0, 0, REGION_ID, 0, 900),   # 참나무 숲(x=0) -> 숲 입구(x=900)

    # 소나무 숲(1) <-> 숲속(3)
    (REGION_ID, 1, 1, 1800, REGION_ID, 3, 0),   # 소나무 숲(x=1800) -> 숲속(x=0)
    (REGION_ID, 3, 0, 0, REGION_ID, 1, 1800),   # 숲속(x=0) -> 소나무 숲(x=1800)

    # 참나무 숲(2) <-> 늑대굴(4)
    (REGION_ID, 2, 1, 1200, REGION_ID, 4, 0),   # 참나무 숲(x=1200) -> 늑대굴(x=0)
    (REGION_ID, 4, 0, 0, REGION_ID, 2, 1200),   # 늑대굴(x=0) -> 참나무 숲(x=1200)

    # 참나무 숲(2) <-> 오두막(5)
    (REGION_ID, 2, 2, 1500, REGION_ID, 5, 0),   # 참나무 숲(x=1500) -> 오두막(x=0)
    (REGION_ID, 5, 0, 0, REGION_ID, 2, 1500),   # 오두막(x=0) -> 참나무 숲(x=1500)

    # 소나무 숲(1) <-> 참나무 숲(2)
    (REGION_ID, 1, 2, 1200, REGION_ID, 2, 600),  # 소나무 숲(x=1200) -> 참나무 숲(x=600)
    (REGION_ID, 2, 3, 600, REGION_ID, 1, 1200),  # 참나무 숲(x=600) -> 소나무 숲(x=1200)
]


# ========================================
# 초기화 함수들
# ========================================

def initialize_terrain():
    """숲 Region 초기화"""
    from assets.locations.forest import (
        ForestEntrance, PineForest, OakForest,
        DeepForest, WolfDen, ForestCabin
    )

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스 생성 및 등록
    locations = {
        0: ForestEntrance(),
        1: PineForest(),
        2: OakForest(),
        3: DeepForest(),
        4: WolfDen(),
        5: ForestCabin(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Gate 등록 (Pi-World 연결)
    for region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x in GATES:
        morld.add_gate(region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x)

    print(f"[world.forest] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations


def instantiate_trees():
    """
    추가 나무 오브젝트 인스턴스화 (Location.instantiate에서 기본 1개씩 배치됨)

    추가 배치가 필요한 경우 이 함수에서 처리
    """
    from think.resource_agent import register_tree_object
    from assets.objects.trees import PineTree, OakTree
    from assets import registry

    # 이미 배치된 나무들 등록 (PineForest, OakForest의 instantiate에서 생성됨)
    # Location.add_object()로 생성된 나무들의 instance_id를 찾아서 등록

    # registry에서 인스턴스 찾기
    instances = registry.get_all_instances()
    for instance_id, unique_id in instances.items():
        if unique_id in ("pine_tree", "oak_tree", "apple_tree"):
            register_tree_object(instance_id, unique_id)

    print(f"[world.forest] Tree objects registered for resource regeneration")


def register_spawn_sources():
    """숲 생물 스폰 소스 등록"""
    from spawner import register_spawn_source
    from assets.characters.monster import Wolf

    # 늑대굴 — 늑대 최대 2마리, 6시간 간격, 수명 3일
    register_spawn_source(
        source_id="forest_wolves",
        monster_class=Wolf,
        max_count=2,
        interval_hours=6,
        region_id=REGION_ID,
        location_id=4,       # 늑대굴
        lifespan_hours=72,
    )

    print("[world.forest] Spawn sources registered: wolves(2)")
