# assets/locations/sera_room.py - 세라의 방

import morld
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Bed, Wardrobe


class SeraRoom(Location):
    unique_id = "sera_room"
    name = "방"
    owner = "sera"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Bed())

        # 옷장 추가 + 옷 배치
        wardrobe = Wardrobe()
        wardrobe_id = self.add_object(wardrobe)

        from assets.items.clothes import (
            LinenShirt, LinenPants, HuntingVest, HuntingCap, LeatherBoots,
            SportsBra, CottonPanties, SimpleSocks, TankTop
        )

        # 겉옷
        item = LinenShirt(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = LinenPants(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = TankTop(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = HuntingVest(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 속옷
        item = SportsBra(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = CottonPanties(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 악세서리
        item = HuntingCap(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = SimpleSocks(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = LeatherBoots(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
