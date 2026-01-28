# assets/locations/mila_room.py - 밀라의 방
#
# 따뜻하고 가정적인 밀라지만, 방은 의외로 텅 비어 있다.
# 개인 물건이 거의 없는 건조한 공간. 어두운 과거를 암시.

import morld
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import Bed, Wardrobe


class MilaRoom(Location):
    unique_id = "mila_room"
    name = "방"
    owner = "mila"
    is_indoor = True
    stay_duration = 0
    length = 30  # Pi-World: 방 길이
    describe_text = {
        "default": "깨끗하지만 텅 빈 방. 개인 물건이라곤 거의 보이지 않는다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(Bed(), x=20)  # 방 안쪽

        # 옷장 추가 + 옷 배치
        wardrobe = Wardrobe()
        wardrobe_id = self.add_object(wardrobe, x=25)  # 침대 옆

        from assets.items.clothes import (
            Blouse, LongSkirt, Apron, MaidHeadband, SimpleShoes,
            SimpleBra, SimplePanties, Stockings, Sweater, Pajamas
        )

        def add_to_wardrobe(item_class):
            item = item_class()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            morld.give_item(wardrobe_id, item_id, 1)

        # 겉옷
        add_to_wardrobe(Blouse)
        add_to_wardrobe(LongSkirt)
        add_to_wardrobe(Sweater)
        add_to_wardrobe(Apron)
        add_to_wardrobe(Pajamas)
        # 속옷
        add_to_wardrobe(SimpleBra)
        add_to_wardrobe(SimplePanties)
        # 악세서리
        add_to_wardrobe(MaidHeadband)
        add_to_wardrobe(Stockings)
        add_to_wardrobe(SimpleShoes)
