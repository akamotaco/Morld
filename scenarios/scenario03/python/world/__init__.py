# world/__init__.py - 월드 모듈 (시나리오03)
#
# 역할:
# - Region 초기화 (플랫폼 + 지저철)
# - Region 간 연결 (cross-region Gate)

import morld

from . import platform  # Region 0: 플랫폼
from . import train     # Region 1: 지저철 내부


# ========================================
# cross-region Gate 정의
# ========================================
# (region_a, location_a, region_b, location_b, distance)

CROSS_REGION_GATES = [
    # 승강장(R0:L0) ↔ 지저철 내부(R1:L0) — 즉시 (탑승/하차)
    (platform.REGION_ID, 0, train.REGION_ID, 0, 0),
]

_CROSS_GATE_ID_BASE = 100


def _safe_add_cross_region_gate(region_a, loc_a, region_b, loc_b, distance, gate_idx):
    """Region이 존재할 때만 양방향 Gate 등록"""
    if not (morld.region_exists(region_a) and morld.region_exists(region_b)):
        return False

    info_a = morld.get_location_info(region_a, loc_a)
    info_b = morld.get_location_info(region_b, loc_b)
    length_a = info_a.get("length", 100) if info_a else 100

    gate_id_a = _CROSS_GATE_ID_BASE + gate_idx * 2
    gate_id_b = _CROSS_GATE_ID_BASE + gate_idx * 2 + 1

    morld.add_gate(region_a, loc_a, gate_id_a, max(0, length_a - 10),
                   region_b, loc_b, 10)
    morld.add_gate(region_b, loc_b, gate_id_b, 10,
                   region_a, loc_a, max(0, length_a - 10))
    return True


def initialize_cross_region_gates():
    """cross-region Gate 양방향 등록"""
    registered = 0
    for idx, entry in enumerate(CROSS_REGION_GATES):
        region_a, loc_a, region_b, loc_b, distance = entry
        if _safe_add_cross_region_gate(region_a, loc_a, region_b, loc_b, distance, idx):
            registered += 1
    print(f"[world] Cross-region gates registered: {registered}/{len(CROSS_REGION_GATES)}")


def initialize_world():
    """월드 초기화 (지형 + cross-region Gate)"""
    platform.initialize_terrain()
    train.initialize_terrain()
    initialize_cross_region_gates()
