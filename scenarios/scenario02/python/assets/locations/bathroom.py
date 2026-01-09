# assets/locations/bathroom.py - 욕실

from assets.base import Location
from assets.objects.grounds import GroundTile
from assets.objects.furniture import Mirror


class Bathroom(Location):
    unique_id = "bathroom"
    name = "욕실"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "낡지만 깨끗하게 관리된 욕실. 큰 나무 욕조가 놓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """욕실 생성 + 타일 바닥 + 거울 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundTile())
        self.add_object(Mirror(), 200)  # 욕실 거울
