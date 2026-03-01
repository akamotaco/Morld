# assets/locations/merchant_limbo.py — 상인 대기소 Location
#
# Region 10: 상인 대기소
# - Gate 없음 → 플레이어 접근 불가
# - 페이(Faye)가 야간/주말에 머무는 숨겨진 공간

from assets.base import Location


class MerchantWaiting(Location):
    """대기 공간 — NPC 전용, 플레이어 접근 불가"""
    unique_id = "merchant_waiting"
    name = "대기 공간"
    is_indoor = True
    ground_type = None
    stay_duration = 0
    length = 10
    describe_text = {"default": "알 수 없는 공간이다."}

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
