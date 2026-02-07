# assets/locations/bathroom.py - 욕실

from assets.base import Location
from assets.objects.grounds import GroundTile
from assets.objects.furniture import Mirror, Bathtub, Washbasin, WallLamp


class Bathroom(Location):
    unique_id = "bathroom"
    name = "욕실"
    is_indoor = True
    stay_duration = 0
    length = 180  # Pi-World: 욕실 길이
    describe_text = {
        "default": "낡지만 깨끗하게 관리된 욕실. 큰 나무 욕조가 놓여 있다."
    }

    # life.md 연동용 (미래 구현)
    activities = ["목욕", "세수"]
    activity_capacity = {"목욕": 1, "세수": 1}  # 1명씩만

    def instantiate(self, location_id: int, region_id: int):
        """욕실 생성 + 타일 바닥 + 거울 + 욕조 + 세면대 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundTile())
        self.add_object(Mirror(), x=5)      # 문 옆
        self.add_object(Bathtub(), x=15)    # 중앙
        self.add_object(Washbasin(), x=25)  # 안쪽
        self.add_object(WallLamp(), x=90)
