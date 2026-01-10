# assets/locations/stairs.py - 계단 (Location 5)
#
# 부서진 계단, 창문은 플레이버 텍스트 (탈출 불가 확인)

from assets.base import Location


class Stairs(Location):
    unique_id = "stairs"
    name = "계단"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "삐걱거리는 나무 계단이다. 일부 단은 썩어서 주의해서 밟아야 한다. 벽에 걸린 창문 너머로 어둠만이 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.stairs import BrokenStep, StairWindow

        self.add_object(BrokenStep())
        self.add_object(StairWindow())
