# assets/locations/living_room.py - 거실

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import LivingSofa


class LivingRoom(Location):
    unique_id = "living_room"
    name = "거실"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "넓은 거실. 벽난로와 낡은 소파가 놓여 있다. 이곳에서 매일 아침 조회가 열린다.",
        "아침": "창문으로 들어오는 햇살이 먼지 입자를 비춘다.",
        "저녁": "벽난로에 불이 피워져 따뜻한 분위기다.",
        "밤": "벽난로의 불씨가 은은하게 타오른다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """거실 생성 + 나무 바닥 + 소파 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())

        # 거실 소파 배치
        self.add_object(LivingSofa())
