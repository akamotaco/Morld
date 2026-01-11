# assets/locations/mila_room.py - 밀라의 방

import morld
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Mirror, Bed, Wardrobe


class MilaRoom(Location):
    unique_id = "mila_room"
    name = "방"
    owner = "mila"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "따뜻한 느낌의 방. 손수 만든 쿠션과 담요가 곳곳에 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Mirror())
        self.add_object(Bed())

        # 옷장 추가 + 옷 배치
        wardrobe = Wardrobe()
        wardrobe_id = self.add_object(wardrobe)

        from assets.items.clothes import Blouse, LongSkirt, Apron
        # 블라우스
        blouse = Blouse()
        blouse_id = morld.create_id("item")
        blouse.instantiate(blouse_id)
        morld.give_item(wardrobe_id, blouse_id, 1)
        # 긴 치마
        skirt = LongSkirt()
        skirt_id = morld.create_id("item")
        skirt.instantiate(skirt_id)
        morld.give_item(wardrobe_id, skirt_id, 1)
        # 앞치마
        apron = Apron()
        apron_id = morld.create_id("item")
        apron.instantiate(apron_id)
        morld.give_item(wardrobe_id, apron_id, 1)
