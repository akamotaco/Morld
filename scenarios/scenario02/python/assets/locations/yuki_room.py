# assets/locations/yuki_room.py - 유키의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden


class YukiRoom(Location):
    unique_id = "yuki_room"
    name = "유키의 방"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "조용하고 깔끔한 방. 책이 가지런히 정리되어 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """유키의 방 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
