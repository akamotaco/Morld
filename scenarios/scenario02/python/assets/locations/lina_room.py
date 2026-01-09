# assets/locations/lina_room.py - 리나의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror


class LinaRoom(Location):
    unique_id = "lina_room"
    name = "방2"
    owner = "lina"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "밝고 활기찬 분위기의 방. 창가에 작은 화분이 놓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror(), 202)
