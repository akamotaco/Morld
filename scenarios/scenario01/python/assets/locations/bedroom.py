# assets/locations/bedroom.py - 침실 (Location 6)
#
# 침대 밑에서 일기장+편지, 화장대 서랍(비밀번호 3749)에서 서재 메모

from assets.base import Location


class Bedroom(Location):
    unique_id = "bedroom"
    name = "침실"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "낡은 침실이다. 헤진 시트가 덮인 침대와 먼지 쌓인 화장대가 있다. 희미한 향수 냄새가 공기 중에 맴돈다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.bedroom import BedUnder, VanityDrawer

        self.add_object(BedUnder())
        self.add_object(VanityDrawer())
