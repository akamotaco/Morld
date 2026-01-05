# world/vehicle.py - 차량 전용 Region
#
# Region 1: 차량 관리 전용
# - 밀폐형 탈것 (자동차 등)은 별도 Region에서 관리
# - RegionEdge로 외부 Location과 연결
# - 운전 시 RegionEdge의 LocationA가 변경됨

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 1

REGION = {
    "id": REGION_ID,
    "name": "차량",
    "describe_text": {"default": "탈것들이 관리되는 공간."},
    "weather": "맑음"
}

# ========================================
# 초기화 함수
# ========================================

def initialize_terrain():
    """차량 Region 초기화"""
    from assets.locations.vehicles import OldCar

    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # 차량 Location
    locations = {
        0: OldCar(),  # 낡은 자동차 (Region 1, Location 0)
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    print(f"[world.vehicle] Region {REGION_ID} initialized: {len(locations)} locations")
    return locations
