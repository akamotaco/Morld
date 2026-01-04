# assets/locations/hunting_ground.py - 사냥터

from assets.base import Location
from assets.objects.grounds import GroundForest


class HuntingGround(Location):
    unique_id = "hunting_ground"
    name = "사냥터"
    is_indoor = False
    stay_duration = 0
    describe_text = {
        "default": "야생 동물의 흔적이 보이는 곳. 조심스럽게 움직여야 한다.",
        "아침": "이슬 맺힌 풀 위에 동물 발자국이 보인다.",
        "낮": "숲 속에서 동물 울음소리가 들린다.",
        "밤": "어둠 속에서 눈빛이 반짝인다.",
        "날씨:비": "비 오는 날은 사냥하기 어렵다.",
        "날씨:눈": "눈 위에 선명한 발자국이 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """사냥터 생성 + 숲 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())
