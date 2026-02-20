# assets/locations/guest_room.py - 빈 방 (Guest Room)
#
# 도심에서 데려온 캐릭터에게 배정될 예정인 빈 방
# 인스턴스 생성 시 unique_id와 description 지정

from assets.base import Location
from assets.objects.furniture import Mirror, Bed, WallLamp, Window


class GuestRoom(Location):
    """빈 방 Location - 인스턴스 생성 시 unique_id와 describe_text 지정"""
    name = "방"
    owner = None  # 빈 방 (아직 소유자 없음)
    is_indoor = True
    ground_type = "GroundWooden"
    stay_duration = 0
    length = 150  # Pi-World: 침실 (개인 공간)

    def __init__(self, unique_id: str, description: str):
        super().__init__()
        self.unique_id = unique_id
        self.describe_text = {"default": description}

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_object(Mirror(), x=5)   # 문 옆
        self.add_object(Bed(), x=20)     # 방 안쪽
        self.add_object(WallLamp(), x=90)
        self.add_object(Window(), x=120)
