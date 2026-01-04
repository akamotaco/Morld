# assets/locations/storage.py - 창고

from assets.base import Location
from assets.objects.grounds import GroundWooden


class Storage(Location):
    unique_id = "storage"
    name = "창고"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "선반에 식량과 도구가 정리되어 있다. 약간 먼지 냄새가 난다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """창고 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
