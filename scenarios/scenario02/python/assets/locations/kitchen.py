# assets/locations/kitchen.py - 주방

from assets.base import Location
from assets.objects.grounds import GroundStone
from assets.objects.furniture import Stove, Kettle, Cupboard


class Kitchen(Location):
    unique_id = "kitchen"
    name = "주방"
    is_indoor = True
    stay_duration = 0
    length = 180  # Pi-World: 주방 길이
    describe_text = {
        "default": "각종 조리도구가 걸려 있는 주방. 아궁이에서 연기가 피어오른다.",
        "아침": "아침 식사를 준비하는 냄새가 난다.",
        "낮": "점심 준비로 분주하다.",
        "저녁": "저녁 식사 준비로 맛있는 냄새가 가득하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """주방 생성 + 바닥 + 아궁이 + 주전자 + 찬장 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundStone())
        # 오브젝트 위치 분산 (주방 길이 30)
        self.add_object(Stove(), x=10)    # 아궁이 (중앙 왼쪽)
        self.add_object(Kettle(), x=15)   # 주전자 (아궁이 옆)
        self.add_object(Cupboard(), x=25) # 찬장 (끝쪽)
