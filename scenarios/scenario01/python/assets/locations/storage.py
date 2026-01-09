# assets/locations/storage.py - 창고 (Location 1)
#
# 선반에서 쪽지1, 캐비닛에서 은열쇠 획득

from assets.base import Location


class Storage(Location):
    unique_id = "storage"
    name = "창고"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "먼지가 자욱한 창고다. 오래된 가구와 상자들이 어지럽게 쌓여있다. 거미줄이 곳곳에 드리워져 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.storage import Shelf, OldCabinet

        self.add_object(Shelf(), 102)
        self.add_object(OldCabinet(), 103)
