# assets/locations/front_yard.py - 앞마당

from assets.base import Location
from assets.objects.grounds import GroundGrass


class FrontYard(Location):
    unique_id = "front_yard"
    name = "앞마당"
    is_indoor = False
    stay_duration = 0
    appearance = {
        "default": "저택 앞에 펼쳐진 넓은 마당. 잘 가꿔진 정원이 있다.",
        "아침": "아침 이슬이 풀잎에 맺혀 반짝인다.",
        "낮": "햇살이 정원을 환하게 비춘다.",
        "저녁": "석양빛이 정원을 황금빛으로 물들인다.",
        "밤": "달빛 아래 정원이 고요하다.",
        "날씨:비": "빗줄기가 정원을 적시고 있다.",
        "날씨:눈": "눈이 정원을 하얗게 덮고 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """앞마당 생성 + 잔디 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundGrass())
