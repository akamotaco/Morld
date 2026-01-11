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

        # 중첩 함수 패턴 - SharpPy v0.4.1 버그 수정 테스트
        def add_to_wardrobe(item_class):
            item = item_class()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            morld.give_item(wardrobe_id, item_id, 1)

        # 겉옷
        add_to_wardrobe(Sundress)
        add_to_wardrobe(WhiteBlouse)
        add_to_wardrobe(Shorts)
        add_to_wardrobe(PleatedSkirt)
        add_to_wardrobe(Pajamas)
        # 속옷
        add_to_wardrobe(SimpleBra)
        add_to_wardrobe(SimplePanties)
        # 악세서리
        add_to_wardrobe(Ribbon)
        add_to_wardrobe(ThighHighSocks)
        add_to_wardrobe(Sandals)
