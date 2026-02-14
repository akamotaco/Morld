# assets/items/collectibles.py - 수집 아이템 (꽃, 장식품)
#
# 선물용 소품 아이템
# - category: "flower" 또는 "trinket"
# - 지형 곳곳에 배치되어 수집 가능
#
# 사용법:
#   from assets.items.collectibles import WildFlower, PrettyStone
#   flower = WildFlower()
#   flower.instantiate(item_id)

import morld
import ui
from assets.base import Item
from assets.registry import register_item


# ========================================
# 꽃
# ========================================

@register_item
class WildFlower(Item):
    unique_id = "flower_wild"
    name = "들꽃"
    category = "flower"
    value = 1
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "수수한 들꽃이다. 누군가 좋아할지도."


@register_item
class DriedFlower(Item):
    unique_id = "flower_dried"
    name = "말린 꽃"
    category = "flower"
    value = 3
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "잘 말린 꽃이다. 은은한 향기가 남아있다."


# ========================================
# 장식품
# ========================================

@register_item
class PrettyStone(Item):
    unique_id = "trinket_pretty_stone"
    name = "예쁜 돌멩이"
    category = "trinket"
    value = 2
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "반짝이는 돌멩이다. 소장 가치가 있어 보인다."


@register_item
class OldPendant(Item):
    unique_id = "trinket_old_pendant"
    name = "낡은 펜던트"
    category = "trinket"
    value = 15
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "녹슨 금속 펜던트다. 누구의 것이었을까."


@register_item
class WoodCarving(Item):
    unique_id = "trinket_wood_carving"
    name = "나무 조각"
    category = "trinket"
    value = 5
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "누군가 정성들여 깎은 나무 인형이다."


@register_item
class BrokenWatch(Item):
    unique_id = "trinket_broken_watch"
    name = "고장난 시계"
    category = "trinket"
    value = 8
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "바늘이 멈춘 시계다. 수리할 수 있을지도."


@register_item
class OldTeddyBear(Item):
    unique_id = "trinket_teddy_bear"
    name = "낡은 곰 인형"
    category = "trinket"
    value = 10
    actions = ["take@ground", "take@container"]

    def get_focus_text(self):
        return "헤진 곰 인형이다. 누군가 매우 아꼈던 것 같다."
