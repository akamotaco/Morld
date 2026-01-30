# assets/locations/entrance.py - 현관

from assets.base import Location
from assets.objects.grounds import GroundStone
from assets.objects.errand_board import ErrandBoard


class Entrance(Location):
    unique_id = "entrance"
    name = "현관"
    is_indoor = True
    stay_duration = 0
    length = 180  # Pi-World: 현관 길이
    describe_text = {
        "default": "저택의 입구. 무거운 나무 문이 달려 있다.",
        "아침": "아침 햇살이 문틈으로 스며든다.",
        "밤": "어둠 속에 문의 윤곽만 희미하게 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """현관 생성 + 돌바닥 + 심부름 게시판 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundStone())
        # 심부름 게시판 (문 옆, x=5)
        self.add_object(ErrandBoard(), x=5)
