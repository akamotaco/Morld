# assets/locations/gathering_spot.py - 채집터

from assets.base import Location
from assets.objects.grounds import GroundForest


class GatheringSpot(Location):
    unique_id = "gathering_spot"
    name = "채집터"
    is_indoor = False
    stay_duration = 0
    appearance = {
        "default": "야생 열매와 약초가 자라는 곳. 숲의 은혜를 느낄 수 있다.",
        "봄": "새싹이 돋아나고 있다.",
        "여름": "무성한 풀과 열매가 가득하다.",
        "가을": "익은 열매가 주렁주렁 달려 있다.",
        "겨울": "말라버린 풀만 남아 있다.",
        "날씨:비": "비에 젖은 풀잎이 반짝인다.",
        "날씨:눈": "눈 아래 겨울잠을 자는 듯하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """채집터 생성 + 숲 바닥 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())
