# world/platform.py - 플랫폼 Region (시나리오03)
#
# Region 0: 플랫폼 (베이스캠프)
# - 승강장 (L0): 지저철 정차/탑승, len=200
# - 중앙 통로 (L1): 이동 허브, 건축 분기점, len=100
# - 통신실 (L2): 플레이어 CRT 시점, len=40
# - L3+: 건축으로 동적 생성

import morld

REGION_ID = 0

REGION = {
    "id": REGION_ID,
    "name": "플랫폼",
    "describe_text": {"default": "지저 세계의 오래된 역사(驛舍). 콘크리트 벽이 습기로 검게 물들어 있다."},
    "weather": "맑음",
}

# Pi-World Gate 정의
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
GATES = [
    # 승강장(0) ↔ 중앙 통로(1)
    (REGION_ID, 0, 0, 200, REGION_ID, 1, 0),     # 승강장 우측 → 통로 좌측
    (REGION_ID, 1, 0, 0,   REGION_ID, 0, 200),   # 통로 좌측 → 승강장 우측

    # 중앙 통로(1) ↔ 통신실(2)
    (REGION_ID, 1, 1, 50,  REGION_ID, 2, 0),     # 통로 x=50 → 통신실 좌측
    (REGION_ID, 2, 0, 40,  REGION_ID, 1, 50),    # 통신실 우측 → 통로 x=50

    # 승강장(0) ↔ 지저철 내부(R1, L0) — 동적 재연결 대상
    (REGION_ID, 0, 2, 100, 1, 0, 0),             # 승강장 중앙 → 객차 입구
    (1, 0, 0, 0,           REGION_ID, 0, 100),   # 객차 입구 → 승강장 중앙
]


def initialize_terrain():
    """플랫폼 Region 지형 초기화"""
    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    # Location 등록
    _initialize_locations()

    # Gate 등록
    for region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x in GATES:
        morld.add_gate(region_id, location_id, gate_id, x, conn_region, conn_location, arrival_x)

    print(f"[platform] Region {REGION_ID} initialized: 3 locations, {len(GATES)} gates")


def _initialize_locations():
    """플랫폼 Location 초기화"""
    from assets.locations.platform_locations import Station, PlatformCorridor, CommRoom

    locations = {
        0: Station(),
        1: PlatformCorridor(),
        2: CommRoom(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)


def instantiate_npcs():
    """플랫폼 NPC 인스턴스화 (demo.py에서 직접 처리)"""
    # 데모에서는 chapters/demo.py가 NPC를 직접 배치
    pass
