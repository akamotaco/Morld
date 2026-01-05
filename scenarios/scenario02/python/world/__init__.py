# world/__init__.py - 월드 모듈
#
# 역할:
# - 지형 데이터 정의 및 초기화
# - 시간 설정
# - 아이템/오브젝트/캐릭터 인스턴스화
# - Region 간 연결 (RegionEdge) 관리

import morld

from . import mansion   # Region 0: 숲속 저택
from . import vehicle   # Region 1: 차량 전용
from . import city      # Region 2: 황폐화된 도시

# ========================================
# Region 간 연결 (RegionEdge)
# ========================================
# (edge_id, region_a, location_a, region_b, location_b, travel_time)

REGION_EDGES = [
    # 숲 입구(R0:20) ↔ 도시 입구(R2:0) - 30분 도보
    (0, mansion.REGION_ID, 20, city.REGION_ID, 0, 30),

    # 주차장(R2:4) ↔ 낡은 자동차(R1:0) - 1분 탑승
    (1, city.REGION_ID, 4, vehicle.REGION_ID, 0, 1),
]


# ========================================
# 초기화 함수들
# ========================================

def initialize_world():
    """월드 초기화 (지형 + 시간 + RegionEdge)"""
    # 각 Region 초기화
    mansion.initialize_terrain()
    vehicle.initialize_terrain()
    city.initialize_terrain()

    # 시간 설정 (mansion에서 관리)
    mansion.initialize_time()

    # Region 간 연결 (RegionEdge)
    for edge_id, region_a, loc_a, region_b, loc_b, travel_time in REGION_EDGES:
        morld.add_region_edge(edge_id, region_a, loc_a, region_b, loc_b, travel_time)

    print(f"[world] RegionEdges initialized: {len(REGION_EDGES)} edges")


def instantiate_player():
    """플레이어만 인스턴스화 (챕터 0용)"""
    mansion.instantiate_player()


def instantiate_npcs():
    """NPC들만 인스턴스화 (챕터 1 전환 시)"""
    mansion.instantiate_npcs()


def instantiate_all():
    """모든 유닛 인스턴스화 (플레이어 + NPC + 오브젝트 + 아이템)"""
    mansion.instantiate()
