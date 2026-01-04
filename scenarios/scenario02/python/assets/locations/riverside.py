# assets/locations/riverside.py - 강가

from assets.base import Location
from assets.objects.grounds import GroundRocky


class Riverside(Location):
    unique_id = "riverside"
    name = "강가"
    is_indoor = False
    stay_duration = 0
    describe_text = {
        "default": "맑은 물이 흐르는 작은 강. 물소리가 청량하게 들린다.",
        "아침": "아침 햇살에 수면이 반짝인다.",
        "낮": "햇빛에 물이 눈부시게 빛난다.",
        "저녁": "노을빛이 수면에 비친다.",
        "날씨:비": "빗방울이 수면에 파문을 만든다.",
        "날씨:눈": "강가에 눈이 쌓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """강가 생성 + 바위투성이 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundRocky())
