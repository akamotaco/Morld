# assets/items/resources.py - 기본 자원 아이템
#
# 사용법:
#   from assets.items.resources import Flour, Bread
#   flour = Flour()
#   flour.instantiate(item_id)

from assets.base import Item


# ========================================
# 식량 자원
# ========================================

class Flour(Item):
    unique_id = "flour"
    name = "밀가루"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container"]


class Rice(Item):
    unique_id = "rice"
    name = "쌀"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container"]


class Water(Item):
    unique_id = "water"
    name = "물"
    passive_props = {}
    equip_props = {}
    value = 1
    actions = ["take@container", "use@inventory"]


class Bread(Item):
    unique_id = "bread"
    name = "빵"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "use@inventory"]


class Berry(Item):
    unique_id = "berry"
    name = "열매"
    passive_props = {}
    equip_props = {}
    value = 3
    actions = ["take@container", "use@inventory"]


class Meat(Item):
    unique_id = "meat"
    name = "고기"
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
    passive_props = {}
    equip_props = {}
    value = 3
    actions = ["take@container"]


class Herb(Item):
    unique_id = "herb"
    name = "약초"
    passive_props = {"치료": 1}
    equip_props = {}
    value = 8
    actions = ["take@container", "use@inventory"]


class Cloth(Item):
    unique_id = "cloth"
    name = "천 조각"
    passive_props = {}
    equip_props = {}
    value = 2
    actions = ["take@container"]
