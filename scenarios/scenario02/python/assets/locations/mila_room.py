# assets/locations/mila_room.py - 밀라의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden


class MilaRoom(Location):
    unique_id = "mila_room"
    name = "밀라의 방"
    is_indoor = True
    stay_duration = 0
    appearance = {
        "default": "따뜻한 느낌의 방. 손수 만든 쿠션과 담요가 곳곳에 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """밀라의 방 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
