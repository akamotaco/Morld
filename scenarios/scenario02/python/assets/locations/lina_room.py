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

        from assets.items.clothes import (
            Sundress, WhiteBlouse, Shorts, PleatedSkirt, Ribbon,
            SimpleBra, SimplePanties, ThighHighSocks, Sandals, Pajamas
        )

        # 겉옷
        item = Sundress(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = WhiteBlouse(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = Shorts(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = PleatedSkirt(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = Pajamas(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 속옷
        item = SimpleBra(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = SimplePanties(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 악세서리
        item = Ribbon(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = ThighHighSocks(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = Sandals(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
