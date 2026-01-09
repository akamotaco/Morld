# assets/locations/living_room.py - 거실 (Location 2)
#
# 벽난로에서 숫자 힌트 "3", 소파에서 쪽지2 획득

from assets.base import Location


class LivingRoom(Location):
    unique_id = "living_room"
    name = "거실"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "한때 화려했을 거실이다. 빛바랜 벨벳 소파와 먼지 쌓인 샹들리에가 과거의 영광을 말해준다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.living_room import Fireplace, SofaCushion

        self.add_object(Fireplace(), 104)
        self.add_object(SofaCushion(), 105)
