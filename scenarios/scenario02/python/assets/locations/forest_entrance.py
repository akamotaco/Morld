# assets/locations/forest_entrance.py - 숲 입구

from assets.base import Location
from assets.objects.grounds import GroundForest


class ForestEntrance(Location):
    unique_id = "forest_entrance"
    name = "숲 입구"
    is_indoor = False
    stay_duration = 5  # 숲 진입 시 지체 시간
    describe_text = {
        "default": "저택으로 이어지는 숲길. 오래된 나무들이 늘어서 있다.",
        "아침": "아침 안개가 숲 입구를 감싸고 있다.",
        "낮": "햇살이 나뭇잎 사이로 쏟아진다.",
        "저녁": "석양빛이 나무 사이로 비친다.",
        "밤": "어둠 속에 나무들의 실루엣만 보인다.",
        "날씨:비": "빗방울이 나뭇잎을 두드린다.",
        "날씨:눈": "눈이 소복이 쌓여 발자국이 선명하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """숲 입구 생성 + 숲 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())
