# assets/locations/ella_room.py - 엘라의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden


class EllaRoom(Location):
    unique_id = "ella_room"
    name = "엘라의 방"
    is_indoor = True
    stay_duration = 0
    appearance = {
        "default": "단정하고 권위있는 분위기의 방. 책상 위에 서류가 놓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """엘라의 방 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
