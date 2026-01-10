# assets/locations/basement.py - 지하실 (Location 0)
#
# 시작 위치. 배전함을 켜야 창고로 이동 가능.

from assets.base import Location


class Basement(Location):
    unique_id = "basement"
    name = "지하실"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "어둡고 축축한 지하실이다. 벽에서 물이 스며나오고 곰팡이 냄새가 진동한다. 희미한 빛줄기가 천장의 틈새로 새어 들어온다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.basement import OldBox, PowerPanel

        self.add_object(OldBox())
        self.add_object(PowerPanel())
