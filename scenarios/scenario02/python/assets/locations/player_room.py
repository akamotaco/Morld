# assets/locations/player_room.py - 주인공 방
#
# 플레이어가 저택에 온 지 얼마 안 되어 배정받은 방.
# 최소한의 가구만 있는 간소한 상태.

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Bed, WallLamp, Window


class PlayerRoom(Location):
    unique_id = "player_room"
    name = "방"
    owner = "player"
    is_indoor = True
    stay_duration = 0
    length = 180  # Pi-World: 방 길이
    describe_text = {
        "default": "텅 빈 방. 침대 하나만 덩그러니 놓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        # 침대 (방 안쪽, x=20)
        self.add_object(Bed(), x=20)
        self.add_object(WallLamp(), x=90)
        self.add_object(Window(), x=120)
