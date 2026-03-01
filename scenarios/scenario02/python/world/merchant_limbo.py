# world/merchant_limbo.py — 상인 대기소 Region
#
# Region 10: 상인 대기소
# - Gate 없음 → 플레이어 접근 불가 (완전 고립)
# - 페이(Faye)가 야간/주말에 머무는 숨겨진 공간
# - props/관계 데이터 자동 유지 (unit 삭제 없음)

import morld

# ========================================
# Region 설정
# ========================================

REGION_ID = 10

REGION = {
    "id": REGION_ID,
    "name": "상인 대기소",
    "describe_text": {"default": "알 수 없는 공간."},
    "weather": "맑음"
}


# ========================================
# 초기화 함수
# ========================================

def initialize_terrain():
    """상인 대기소 Region 초기화 (Gate 없음 — 완전 고립)"""
    from assets.locations.merchant_limbo import MerchantWaiting

    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    locations = {
        0: MerchantWaiting(),
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)

    # Gate 등록 없음 → 플레이어/일반 NPC 접근 불가

    print(f"[world.merchant_limbo] Region {REGION_ID} initialized (isolated)")
    return locations
