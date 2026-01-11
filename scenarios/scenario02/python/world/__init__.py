# world/__init__.py - 월드 모듈
#
# 역할:
# - 지형 데이터 정의 및 초기화
# - 시간 설정
# - 아이템/오브젝트/캐릭터 인스턴스화
# - Region 간 연결 (RegionEdge) 관리
#
# 챕터별 Region 선택적 로드:
# - 챕터 파일에서 필요한 Region만 initialize_terrain() 호출
# - RegionEdge는 양쪽 Region이 존재할 때만 등록 (없으면 무시)
# - 예: 챕터 2에서 mansion + forest만 로드하면, city 연결 Edge는 무시됨

import morld

from . import mansion   # Region 0: 숲속 저택
from . import vehicle   # Region 1: 차량 전용
from . import city      # Region 2: 황폐화된 도시
from . import forest    # Region 3: 숲

# ========================================
# Region 간 연결 (RegionEdge)
# ========================================
# (edge_id, region_a, location_a, region_b, location_b, travel_time)
#
# 모든 Edge 데이터를 미리 정의하고, 실제 등록 시 Region 존재 여부 체크

REGION_EDGES = [
    # 숲 입구(R0:20) ↔ 도시 입구(R2:0) - 2시간 도보
    (0, mansion.REGION_ID, 20, city.REGION_ID, 0, 120),

    # 주차장(R2:4) ↔ 낡은 자동차(R1:0) - 1분 탑승
    (1, city.REGION_ID, 4, vehicle.REGION_ID, 0, 1),

    # 숲 입구(R0:20) ↔ 숲 입구(R3:0) - 30분 도보
    (2, mansion.REGION_ID, 20, forest.REGION_ID, 0, 30),
]


# ========================================
# 안전한 RegionEdge 등록
# ========================================

def _safe_add_region_edge(region_a, loc_a, region_b, loc_b, travel_time):
    """
    Region이 존재할 때만 RegionEdge 등록 (존재하지 않으면 무시)

    챕터별로 Region을 선택적으로 로드할 때,
    존재하지 않는 Region에 대한 Edge 등록 시도를 조용히 무시합니다.

    Returns:
        bool: 등록 성공 여부
    """
    if morld.region_exists(region_a) and morld.region_exists(region_b):
        morld.add_region_edge(region_a, loc_a, region_b, loc_b, travel_time)
        return True
    # 존재하지 않는 Region은 조용히 무시 (의도된 동작)
    return False


def initialize_region_edges():
    """
    모든 RegionEdge를 안전하게 등록

    이미 로드된 Region들 사이의 Edge만 등록됩니다.
    챕터 파일에서 Region들을 먼저 초기화한 후 이 함수를 호출하세요.
    """
    registered = 0
    for edge_id, region_a, loc_a, region_b, loc_b, travel_time in REGION_EDGES:
        if _safe_add_region_edge(region_a, loc_a, region_b, loc_b, travel_time):
            registered += 1
    print(f"[world] RegionEdges registered: {registered}/{len(REGION_EDGES)}")


# ========================================
# 초기화 함수들
# ========================================

def initialize_world():
    """월드 초기화 (지형 + 시간 + RegionEdge)"""
    # 각 Region 초기화
    mansion.initialize_terrain()
    vehicle.initialize_terrain()
    city.initialize_terrain()
    forest.initialize_terrain()

    # 시간 설정 (mansion에서 관리)
    mansion.initialize_time()

    # Region 간 연결 (RegionEdge) - 안전한 등록
    initialize_region_edges()


def instantiate_player():
    """플레이어만 인스턴스화 (챕터 0용)"""
    mansion.instantiate_player()


def instantiate_npcs():
    """NPC들만 인스턴스화 (챕터 1 전환 시)"""
    mansion.instantiate_npcs()


def instantiate_all():
    """모든 유닛 인스턴스화 (플레이어 + NPC + 오브젝트 + 아이템)"""
    mansion.instantiate()
