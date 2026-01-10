# assets/locations/kitchen.py - 주방 (Location 3)
#
# 냉장고에서 숫자 힌트 "7", 찬장에서 황금열쇠 머리 획득

from assets.base import Location


class Kitchen(Location):
    unique_id = "kitchen"
    name = "주방"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "오래된 주방이다. 녹슨 싱크대와 깨진 타일이 버려진 느낌을 자아낸다. 찬장에서 희미한 빛이 반사된다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.kitchen import Refrigerator, Cupboard

        self.add_object(Refrigerator())
        self.add_object(Cupboard())
