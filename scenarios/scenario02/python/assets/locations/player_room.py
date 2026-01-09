# assets/locations/player_room.py - 주인공 방

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror, Bed


class PlayerRoom(Location):
    unique_id = "player_room"
    name = "방1"
    owner = "player"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "작지만 아늑한 방. 침대와 작은 책상이 놓여 있다.",
        "아침": "창문으로 아침 햇살이 들어온다.",
        "밤": "촛불 하나가 방을 희미하게 밝힌다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror(), 201)
        self.add_object(Bed(), 211)
