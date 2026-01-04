# assets/locations/player_room.py - 주인공 방

from assets.base import Location
from assets.objects.grounds import GroundWooden


class PlayerRoom(Location):
    unique_id = "player_room"
    name = "주인공 방"
    is_indoor = True
    stay_duration = 0
    appearance = {
        "default": "작지만 아늑한 방. 침대와 작은 책상이 놓여 있다.",
        "아침": "창문으로 아침 햇살이 들어온다.",
        "밤": "촛불 하나가 방을 희미하게 밝힌다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """주인공 방 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
