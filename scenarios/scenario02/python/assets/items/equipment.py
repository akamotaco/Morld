# assets/items/equipment.py - 장비 아이템
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명@context"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
#
# 사용법:
#   from assets.items.equipment import OldKnife, LeatherPouch
#   knife = OldKnife()
#   knife.instantiate(item_id)

import morld
from assets.base import Item
from assets.registry import register_item


# ========================================
# 사냥꾼 장비
# ========================================

@register_item
class OldKnife(Item):
    unique_id = "old_knife"
    name = "낡은 칼"
    passive_props = {}
    equip_props = {"공격": 2, "사냥": 1}
    action_props = {"put": 1}  # 장착 시 0으로 변경되어 놓기 비활성화
    value = 20
    actions = ["take@container", "equip@inventory"]


@register_item
class LeatherPouch(Item):
    unique_id = "leather_pouch"
    name = "가죽 주머니"
    passive_props = {"수납": 5}
    equip_props = {}
    action_props = {"put": 1}  # 장착 시 0으로 변경되어 놓기 비활성화
    value = 10
    actions = ["take@container", "equip@inventory"]


# ========================================
# 학자 장비
# ========================================

@register_item
class WritingTool(Item):
    unique_id = "writing_tool"
    name = "필기구"
    passive_props = {}
    equip_props = {"지능": 1}
    value = 5
    actions = ["take@container"]


@register_item
class OldBook(Item):
    unique_id = "old_book"
    name = "낡은 책"
    passive_props = {"지식": 1}
    equip_props = {}
    value = 15
    actions = ["take@container", "call:read:읽기@inventory"]

    def read(self):
        """낡은 책 읽기"""
        yield morld.dialog([
            "오래된 책을 펼쳐본다.",
            "손때 묻은 페이지에는 이 저택의 역사가 적혀 있다.",
            "흥미로운 내용이지만, 대부분의 글자는 바래져 읽기 어렵다."
        ], autofill="book")
        morld.advance_time(10)


# ========================================
# 장인 장비
# ========================================

@register_item
class SmallToolbox(Item):
    unique_id = "small_toolbox"
    name = "작은 도구함"
    passive_props = {"수리": 1}
    equip_props = {"손재주": 2}
    value = 25
    actions = ["take@container"]
