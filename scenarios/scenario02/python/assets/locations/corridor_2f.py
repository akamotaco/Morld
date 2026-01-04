# assets/locations/corridor_2f.py - 2층 복도

from assets.base import Location
from assets.objects.grounds import GroundWooden


class Corridor2F(Location):
    unique_id = "corridor_2f"
    name = "2층 복도"
    is_indoor = True
    stay_duration = 0
    appearance = {
        "default": "2층으로 올라오면 나오는 넓은 복도. 창문으로 저택 앞마당이 내려다보인다.",
        "아침": "아침 햇살이 창문을 통해 복도를 비춘다.",
        "밤": "복도 양쪽에 걸린 촛불이 희미하게 길을 밝힌다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """2층 복도 생성 + 나무 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
