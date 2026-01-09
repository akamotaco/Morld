# assets/locations/mila_room.py - 밀라의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror, Bed


class MilaRoom(Location):
    unique_id = "mila_room"
    name = "방4"
    owner = "mila"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "따뜻한 느낌의 방. 손수 만든 쿠션과 담요가 곳곳에 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror(), 203)
        self.add_object(Bed(), 214)
