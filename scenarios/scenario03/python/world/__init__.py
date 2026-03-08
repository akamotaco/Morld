# world/__init__.py - 월드 모듈 (시나리오03)
#
# 역할:
# - Region 초기화 (플랫폼 + 지저철)
# - Region 간 연결 (RegionGate) 관리
# - 시나리오02와 동일 패턴

import morld

from . import platform  # Region 0: 플랫폼
from . import train     # Region 1: 지저철 내부


# ========================================
# RegionGate 정의
# ========================================
# (gate_id, region_a, location_a, region_b, location_b, distance)

REGION_GATES = [
    # 승강장(R0:L0) ↔ 지저철 내부(R1:L0) — 즉시 (탑승/하차)
    (0, platform.REGION_ID, 0, train.REGION_ID, 0, 0),
]


def _safe_add_region_gate(region_a, loc_a, region_b, loc_b, distance):
    """Region이 존재할 때만 RegionGate 등록"""
    if morld.region_exists(region_a) and morld.region_exists(region_b):
        morld.add_region_gate(region_a, loc_a, region_b, loc_b, distance)
        return True
    return False


def initialize_region_gates():
    """모든 RegionGate를 안전하게 등록"""
    registered = 0
    for gate_id, region_a, loc_a, region_b, loc_b, distance in REGION_GATES:
        if _safe_add_region_gate(region_a, loc_a, region_b, loc_b, distance):
            registered += 1
    print(f"[world] RegionGates registered: {registered}/{len(REGION_GATES)}")


def initialize_world():
    """월드 초기화 (지형 + RegionGate)"""
    # 각 Region 초기화
    platform.initialize_terrain()
    train.initialize_terrain()

    # Region 간 연결
    initialize_region_gates()
