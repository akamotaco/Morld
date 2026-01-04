# assets/locations/lina_room.py - 리나의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden


class LinaRoom(Location):
    unique_id = "lina_room"
    name = "리나의 방"
    is_indoor = True
    stay_duration = 0
    appearance = {
        "default": "밝고 활기찬 분위기의 방. 창가에 작은 화분이 놓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """리나의 방 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
