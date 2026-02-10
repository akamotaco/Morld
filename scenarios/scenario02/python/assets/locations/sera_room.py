# assets/locations/sera_room.py - 세라의 방
#
# 과묵하고 무뚝뚝한 세라지만, 방 한 켠에 낡은 인형이 있다.
# 은근히 귀여운 것을 좋아하는 의외의 면이 있음을 암시.

import morld
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Bed, Wardrobe, OldDoll, WallLamp, Window


class SeraRoom(Location):
    unique_id = "sera_room"
    name = "방"
    owner = "sera"
    is_indoor = True
    stay_duration = 0
    length = 180  # Pi-World: 방 길이
    describe_text = {
        "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다. 침대 곁에 작은 인형이 놓여 있는 게 의외다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        bed = Bed()
        bed.bed_owner = "sera"
        self.add_object(bed, x=20)              # 방 안쪽
        self.add_object(OldDoll(), owner="sera", x=22)  # 침대 곁
        self.add_object(WallLamp(), x=90)
        self.add_object(Window(), x=120)

        # 옷장 추가 + 옷 배치
        wardrobe = Wardrobe()
        wardrobe_id = self.add_object(wardrobe, x=25)  # 침대 옆

        from assets.items.clothes import (
            LinenShirt, LinenPants, HuntingVest, HuntingCap, LeatherBoots,
            SportsBra, CottonPanties, SimpleSocks, TankTop,
            WarmCoat, WoolHat,
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
        # 방한
        add_to_wardrobe(WarmCoat)
        add_to_wardrobe(WoolHat)
