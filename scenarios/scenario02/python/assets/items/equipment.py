# assets/items/equipment.py - 장비 아이템
#
# 사용법:
#   from assets.items.equipment import OldKnife, LeatherPouch
#   knife = OldKnife()
#   knife.instantiate(item_id)

from assets.base import Item


# ========================================
# 사냥꾼 장비
# ========================================

class OldKnife(Item):
    unique_id = "old_knife"
    name = "낡은 칼"
    passive_props = {}
    equip_props = {"공격": 2, "사냥": 1}
    value = 20
    actions = ["take@container", "equip@inventory"]


class LeatherPouch(Item):
    unique_id = "leather_pouch"
    name = "가죽 주머니"
    passive_props = {"수납": 5}
    equip_props = {}
    value = 10
    actions = ["take@container", "equip@inventory"]


# ========================================
# 학자 장비
# ========================================

class WritingTool(Item):
    unique_id = "writing_tool"
    name = "필기구"
    passive_props = {}
    equip_props = {"지능": 1}
    value = 5
    actions = ["take@container"]


class OldBook(Item):
    unique_id = "old_book"
    name = "낡은 책"
    passive_props = {"지식": 1}
    equip_props = {}
    value = 15
    actions = ["take@container", "script:read_book:읽기@inventory"]


# ========================================
# 장인 장비
# ========================================

class SmallToolbox(Item):
    unique_id = "small_toolbox"
    name = "작은 도구함"
    passive_props = {"수리": 1}
    equip_props = {"손재주": 2}
    value = 25
    actions = ["take@container"]
