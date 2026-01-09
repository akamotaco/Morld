# assets/locations/entrance_hall.py - 정문 홀 (Location 9)
#
# 정문 - 황금열쇠로 탈출!

from assets.base import Location


class EntranceHall(Location):
    unique_id = "entrance_hall"
    name = "정문 홀"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "저택의 정문 홀이다. 높은 천장과 대리석 바닥이 한때의 위엄을 보여준다. 거대한 정문이 자유로의 탈출구처럼 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.entrance import FrontDoor

        self.add_object(FrontDoor(), 113)
