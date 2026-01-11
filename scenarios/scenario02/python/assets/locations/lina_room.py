# assets/locations/lina_room.py - 리나의 방

import morld
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror, Bed, Wardrobe


class LinaRoom(Location):
    unique_id = "lina_room"
    name = "방"
    owner = "lina"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "밝고 활기찬 분위기의 방. 창가에 작은 화분이 놓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror())
        self.add_object(Bed())

        # 옷장 추가 + 옷 배치
        wardrobe = Wardrobe()
        wardrobe_id = self.add_object(wardrobe)

        from assets.items.clothes import Sundress, WhiteBlouse, Shorts
        # 선드레스
        sundress = Sundress()
        sundress_id = morld.create_id("item")
        sundress.instantiate(sundress_id)
        morld.give_item(wardrobe_id, sundress_id, 1)
        # 흰 블라우스
        blouse = WhiteBlouse()
        blouse_id = morld.create_id("item")
        blouse.instantiate(blouse_id)
        morld.give_item(wardrobe_id, blouse_id, 1)
        # 반바지
        shorts = Shorts()
        shorts_id = morld.create_id("item")
        shorts.instantiate(shorts_id)
        morld.give_item(wardrobe_id, shorts_id, 1)
