# assets/locations/yuki_room.py - 빈 방 1 (guest_room1)
#
# 원래 유키의 방이었으나, 유키가 도심에 있으므로 빈 방으로 사용
# 나중에 도심에서 데려온 캐릭터에게 배정될 예정

from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror


class GuestRoom1(Location):
    unique_id = "guest_room1"
    name = "방5"
    owner = None  # 빈 방 (아직 소유자 없음)
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "정리되어 있지만 사람 냄새가 나지 않는 방. 아무도 사용하지 않는 듯하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror(), 204)
