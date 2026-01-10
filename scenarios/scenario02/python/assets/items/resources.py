# assets/items/resources.py - 기본 자원 아이템
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명@context"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
#
# 사용법:
#   from assets.items.resources import Flour, Bread
#   flour = Flour()
#   flour.instantiate(item_id)

import morld
from assets.base import Item


# ========================================
# 식량 자원 (조리 재료)
# ========================================

class Flour(Item):
    unique_id = "flour"
    name = "밀가루"
    category = "food_ingredient"  # 음식 재료
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container"]


class Rice(Item):
    unique_id = "rice"
    name = "쌀"
    category = "food_ingredient"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container"]


class Water(Item):
    unique_id = "water"
    name = "물"
    category = "food_ingredient"
    passive_props = {}
    equip_props = {}
    value = 1
    food_satiety = 5  # 약간의 포만감
    actions = ["take@container", "call:use:마시기@inventory"]

    def use(self):
        """물 마시기"""
        player_id = morld.get_player_id()

        # 포만감 회복
        import survival
        survival.add_satiety(player_id, self.food_satiety)

        # 아이템 소비
        morld.lost_item(player_id, self.instance_id)

        yield morld.dialog([
            "시원한 물을 마셨다.",
            "목이 축축해졌다."
        ])
        morld.advance_time(1)


class Bread(Item):
    unique_id = "bread"
    name = "빵"
    category = "food"  # 완성된 음식
    passive_props = {}
    equip_props = {}
    value = 10
    food_satiety = 30
    actions = ["take@container", "call:eat:먹기@inventory"]

    def eat(self):
        """빵 먹기"""
        player_id = morld.get_player_id()

        import survival
        survival.add_satiety(player_id, self.food_satiety)
        morld.lost_item(player_id, self.instance_id)

        yield morld.dialog([
            "빵을 먹었다.",
            "배가 조금 불러졌다."
        ])
        morld.advance_time(5)


class Berry(Item):
    unique_id = "berry"
    name = "열매"
    category = "food_ingredient"  # 음식 재료
    passive_props = {}
    equip_props = {}
    value = 3
    food_satiety = 10
    actions = ["take@container", "call:eat:먹기@inventory"]

    def eat(self):
        """열매 먹기"""
        player_id = morld.get_player_id()

        import survival
        survival.add_satiety(player_id, self.food_satiety)
        morld.lost_item(player_id, self.instance_id)

        yield morld.dialog([
            "열매를 먹었다.",
            "새콤달콤한 맛이 난다."
        ])
        morld.advance_time(1)


class Meat(Item):
    unique_id = "meat"
    name = "고기"
    category = "food_ingredient"  # 음식 재료
    passive_props = {}
    equip_props = {}
    value = 15
    actions = ["take@container"]


# ========================================
# 기타 자원
# ========================================

class Wood(Item):
    unique_id = "wood"
    name = "나무"
    category = "material"  # 재료/자원
    passive_props = {}
    equip_props = {}
    value = 3
    actions = ["take@container"]


class Herb(Item):
    unique_id = "herb"
    name = "약초"
    category = "food_ingredient"  # 음식 재료 (조리용)
    passive_props = {"치료": 1}
    equip_props = {}
    value = 8
    actions = ["take@container", "call:use:사용하기@inventory"]

    def use(self):
        """약초 사용 - 치료"""
        yield morld.dialog([
            "약초를 사용했다.",
            "상처가 조금 나아진 것 같다."
        ])
        morld.advance_time(5)


class Cloth(Item):
    unique_id = "cloth"
    name = "천 조각"
    category = "material"  # 재료/자원
    passive_props = {}
    equip_props = {}
    value = 2
    actions = ["take@container"]
