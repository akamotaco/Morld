# world/forest.py - 숲 Region
#
# Region 3: 숲
# - 0: 숲 입구 (저택과 연결)
# - 1: 소나무 숲
# - 2: 참나무 숲
# - 3: 토끼굴
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

# Region 내 Edge
EDGES = [
    # (from_location, to_location, travel_time)
    (0, 1, 10),   # 숲 입구 - 소나무 숲
    (0, 2, 10),   # 숲 입구 - 참나무 숲
    (1, 3, 15),   # 소나무 숲 - 토끼굴
    (2, 4, 20),   # 참나무 숲 - 늑대굴
    (2, 5, 15),   # 참나무 숲 - 오두막
    (1, 2, 10),   # 소나무 숲 - 참나무 숲
]


# ========================================
# 초기화 함수들
# ========================================

def initialize_terrain():
    """숲 Region 초기화"""
    from assets.locations.forest import (
        ForestEntrance, PineForest, OakForest,
        RabbitBurrow, WolfDen, ForestCabin
    )

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 인스턴스 생성 및 등록
    locations = {
        0: ForestEntrance(),
        1: PineForest(),
        2: OakForest(),
        3: RabbitBurrow(),
        4: WolfDen(),
        5: ForestCabin(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Edge 등록 (Region 내 연결)
    for from_id, to_id, travel_time in EDGES:
        morld.add_edge(REGION_ID, from_id, to_id, travel_time)

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
