# assets/locations/sera_room.py - 세라의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Bed


class SeraRoom(Location):
    unique_id = "sera_room"
    name = "방3"
    owner = "sera"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Bed())
