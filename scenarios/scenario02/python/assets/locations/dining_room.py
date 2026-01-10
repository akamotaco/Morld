# assets/locations/dining_room.py - 식당

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import DiningChair


class DiningRoom(Location):
    unique_id = "dining_room"
    name = "식당"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "긴 나무 테이블이 놓인 식당. 여섯 개의 의자가 가지런히 놓여 있다.",
        "아침": "아침 식사 시간. 테이블에 음식이 차려져 있다.",
        "낮": "점심 시간. 따뜻한 음식 냄새가 풍긴다.",
        "저녁": "저녁 식사 시간. 촛불이 테이블을 밝힌다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """식당 생성 + 나무 바닥 + 의자 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())

        # 식탁 의자 배치
        self.add_object(DiningChair())
