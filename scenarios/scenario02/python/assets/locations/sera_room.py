# assets/locations/sera_room.py - 세라의 방

from assets.base import Location
from assets.objects.grounds import GroundWooden


class SeraRoom(Location):
    unique_id = "sera_room"
    name = "세라의 방"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """세라의 방 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
