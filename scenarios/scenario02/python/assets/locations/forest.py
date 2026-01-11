# assets/locations/forest.py - 숲 Region 전용 Location들
#
# 숲 Region (Region ID 3) 내부 Location들
# - 0: 숲 입구 (저택과 연결)
# - 1: 소나무 숲
# - 2: 참나무 숲
# - 3: 토끼굴
# - 4: 늑대굴
# - 5: 오두막

from assets.base import Location
from assets.objects.grounds import GroundForest, GroundWooden


class ForestEntrance(Location):
    """숲 입구 - 저택에서 숲으로 들어가는 곳"""
    unique_id = "forest_entrance_region"
    name = "숲 입구"
    is_indoor = False
    stay_duration = 5
    describe_text = {
        "default": "울창한 숲으로 들어가는 입구. 나무들 사이로 길이 나 있다.",
        "아침": "아침 안개가 숲 입구를 감싸고 있다.",
        "낮": "햇살이 나뭇잎 사이로 흩뿌린다.",
        "저녁": "노을이 나무 사이로 비친다.",
        "밤": "어둠 속에 숲의 소리만 들린다.",
        "날씨:비": "빗물이 나뭇잎에서 떨어진다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())


class PineForest(Location):
    """소나무 숲 - 소나무가 밀집한 구역"""
    unique_id = "pine_forest"
    name = "소나무 숲"
    is_indoor = False
    stay_duration = 5
    describe_text = {
        "default": "키 큰 소나무들이 하늘을 가리고 있다. 솔향기가 은은하다.",
        "아침": "이슬 맺힌 솔잎이 빛난다.",
        "낮": "소나무 사이로 햇빛이 내리쬔다.",
        "밤": "소나무 숲이 바람에 흔들리며 스산한 소리를 낸다.",
        "날씨:눈": "소나무 가지에 눈이 쌓여 휘어져 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())

        # 소나무 배치
        from assets.objects.trees import PineTree
        pine1 = PineTree()
        self.add_object(pine1)


class OakForest(Location):
    """참나무 숲 - 참나무가 밀집한 구역"""
    unique_id = "oak_forest"
    name = "참나무 숲"
    is_indoor = False
    stay_duration = 5
    describe_text = {
        "default": "굵직한 참나무들이 숲을 이루고 있다. 튼튼한 목재를 얻을 수 있을 것 같다.",
        "아침": "참나무 잎에 이슬이 맺혀 있다.",
        "낮": "참나무 그늘이 시원하다.",
        "저녁": "참나무 숲이 노을빛에 물든다.",
        "밤": "거대한 참나무들의 실루엣이 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())

        # 참나무 배치
        from assets.objects.trees import OakTree
        oak1 = OakTree()
        self.add_object(oak1)


class RabbitBurrow(Location):
    """토끼굴 - 토끼가 서식하는 곳 (빈 Location)"""
    unique_id = "rabbit_burrow"
    name = "토끼굴"
    is_indoor = False
    stay_duration = 5
    describe_text = {
        "default": "땅에 여러 개의 구멍이 뚫려 있다. 토끼가 사는 것 같다.",
        "아침": "토끼들이 풀을 뜯고 있다.",
        "낮": "토끼들이 굴 근처에서 어슬렁거린다.",
        "저녁": "토끼들이 하나둘 굴로 들어간다.",
        "밤": "조용하다. 토끼들은 굴 안에 있는 것 같다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())


class WolfDen(Location):
    """늑대굴 - 늑대가 서식하는 곳 (빈 Location)"""
    unique_id = "wolf_den"
    name = "늑대굴"
    is_indoor = False
    stay_duration = 5
    describe_text = {
        "default": "바위틈에 굴이 있다. 동물 냄새가 진하다. 조심해야 할 것 같다.",
        "아침": "굴 안에서 인기척이 느껴진다.",
        "낮": "굴 앞에 발자국들이 보인다.",
        "저녁": "어디선가 늑대 울음소리가 들린다.",
        "밤": "굴 안에서 눈빛이 반짝인다. 위험하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundForest())


class ForestCabin(Location):
    """오두막 - 숲 속의 작은 오두막 (실내)"""
    unique_id = "forest_cabin"
    name = "오두막"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "숲 속에 있는 낡은 오두막. 오래 전에 누군가 살았던 흔적이 있다.",
        "낮": "창으로 들어오는 빛에 먼지가 춤을 춘다.",
        "밤": "어두운 오두막 안. 밖에서 동물 소리가 들린다."
    }

    def instantiate(self, location_id: int, region_id: int):
        import morld
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())

        # 낡은 옷장 추가 - 이전 주인이 남긴 옷들
        from assets.objects.furniture import Wardrobe
        wardrobe = Wardrobe()
        wardrobe_id = self.add_object(wardrobe)

        from assets.items.clothes import (
            HoodedCloak, TravelCloak, WoolSocks, WarmBoots,
            MensHoodie, MensCargoPants, WornOutJacket, DirtyShirt
        )

        # 숲에서 활동하기 좋은 옷들
        item = HoodedCloak(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = TravelCloak(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = WoolSocks(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = WarmBoots(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensHoodie(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensCargoPants(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 낡은 옷들
        item = WornOutJacket(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = DirtyShirt(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
