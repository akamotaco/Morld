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

        def add_to_wardrobe(item_class):
            item = item_class()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            morld.give_item(wardrobe_id, item_id, 1)

        # 겉옷
        add_to_wardrobe(LinenShirt)
        add_to_wardrobe(LinenPants)
        add_to_wardrobe(TankTop)
        add_to_wardrobe(HuntingVest)
        # 속옷
        add_to_wardrobe(SportsBra)
        add_to_wardrobe(CottonPanties)
        # 악세서리
        add_to_wardrobe(HuntingCap)
        add_to_wardrobe(SimpleSocks)
        add_to_wardrobe(LeatherBoots)
