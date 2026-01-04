# assets/locations/back_yard.py - 뒷마당

from assets.base import Location
from assets.objects.grounds import GroundGrass


class BackYard(Location):
    unique_id = "back_yard"
    name = "뒷마당"
    is_indoor = False
    stay_duration = 0
    describe_text = {
        "default": "저택 뒤편의 넓은 공터. 텃밭을 가꿀 수 있을 것 같다.",
        "아침": "아침 안개가 뒷마당을 감싸고 있다.",
        "낮": "햇살이 따스하게 내리쬔다.",
        "저녁": "저녁 노을이 아름답다.",
        "밤": "고요한 밤. 풀벌레 소리가 들린다.",
        "날씨:비": "빗방울이 텃밭을 적시고 있다.",
        "날씨:눈": "눈이 소복이 쌓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """뒷마당 생성 + 잔디 바닥 추가"""
        super().instantiate(location_id, region_id)

        # 바닥 오브젝트 생성
        self.add_ground(GroundGrass())
