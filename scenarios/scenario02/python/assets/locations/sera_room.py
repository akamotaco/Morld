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

        from assets.items.clothes import LinenShirt, LinenPants, HuntingVest
        # 린넨 셔츠
        shirt = LinenShirt()
        shirt_id = morld.create_id("item")
        shirt.instantiate(shirt_id)
        morld.give_item(wardrobe_id, shirt_id, 1)
        # 린넨 바지
        pants = LinenPants()
        pants_id = morld.create_id("item")
        pants.instantiate(pants_id)
        morld.give_item(wardrobe_id, pants_id, 1)
        # 사냥용 조끼
        vest = HuntingVest()
        vest_id = morld.create_id("item")
        vest.instantiate(vest_id)
        morld.give_item(wardrobe_id, vest_id, 1)
