# world/vehicle.py - 대형 차량 내부 Region
#
# Region 1: 대형 차량 내부
# - OldBus의 interior Location (R1:L0)
# - RegionGate로 외부 Location과 연결 (초기: 주차장 R2:L4)

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 1

REGION = {
    "id": REGION_ID,
    "name": "차량 내부",
    "describe_text": {"default": "대형 차량의 내부 공간."},
    "weather": "맑음"
}

# ========================================
# 초기화 함수
# ========================================

def initialize_terrain():
    """대형 차량 내부 Region 초기화"""
    from assets.locations.vehicles import BusInterior

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # 내부 Location
    locations = {
        0: BusInterior(),  # 버스 내부 (Region 1, Location 0)
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    print(f"[world.vehicle] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations
