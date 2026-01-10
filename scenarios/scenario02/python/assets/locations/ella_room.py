# assets/locations/ella_room.py - 빈 방 2 (guest_room2)
#
# 원래 엘라의 방이었으나, 엘라가 도심에 있으므로 빈 방으로 사용
# 나중에 도심에서 데려온 캐릭터에게 배정될 예정

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror, Bed


class GuestRoom2(Location):
    unique_id = "guest_room2"
    name = "방6"
    owner = None  # 빈 방 (아직 소유자 없음)
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "깨끗하지만 비어있는 방. 언젠가 누군가 사용할 것 같다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror())
        self.add_object(Bed())
