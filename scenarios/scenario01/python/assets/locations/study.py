# assets/locations/study.py - 서재 (Location 7)
#
# 금고(비밀번호 1842)에서 황금열쇠 몸통, 책상 서랍에서 쪽지3

from assets.base import Location


class Study(Location):
    unique_id = "study"
    name = "서재"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "오래된 책들이 가득한 서재다. 가죽 장정된 고서들과 먼지 냄새가 학구적인 분위기를 자아낸다. 책상 옆에 금고가 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.study import Safe, DeskDrawer

        self.add_object(Safe(), 111)
        self.add_object(DeskDrawer(), 112)
