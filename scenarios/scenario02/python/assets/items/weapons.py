# assets/items/weapons.py — 전투 무기
#
# 장비 인스턴스 시스템 사용:
#   item_id = morld.create_id()
#   weapon = Revolver()
#   weapon.instantiate_as_item(item_id)
#   morld.give_item(owner, item_id, 1)
#   morld.set_unit_prop(item_id, "내구도", 100)
#   morld.set_unit_prop(item_id, "내구도:최대", 100)

import morld
import ui
from assets.base import Item
from assets.registry import register_item


# ========================================
# 근접 무기
# ========================================

@register_item
class Baton(Item):
    """삼단봉 — 경찰서 루팅"""
    unique_id = "baton"
    name = "삼단봉"
    category = "weapon"
    equip_props = {
        "전투:공격력": 5,
        "전투:사거리": 60,
        "전투:명중": 10,       # 보너스
        "장착:손": 1,
    }
    value = 40
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "경찰용 삼단봉이다.",
            "가볍고 다루기 쉽다."
        ])


@register_item
class IronSword(Item):
    """철검 — 광석 제작"""
    unique_id = "iron_sword"
    name = "철검"
    category = "weapon"
    equip_props = {
        "전투:공격력": 7,
        "전투:사거리": 80,
        "장착:손": 1,
    }
    value = 80
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "단단한 철로 만든 검이다.",
            "묵직하지만 위력이 대단하다."
        ])


@register_item
class Pickaxe(Item):
    """곡괭이 — 채광용 도구겸 무기"""
    unique_id = "pickaxe"
    name = "곡괭이"
    category = "tool"
    passive_props = {"can:mine": 1}
    equip_props = {
        "전투:공격력": 4,
        "전투:사거리": 60,
        "장착:손": 1,
    }
    value = 50
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "무거운 곡괭이다.",
            "광석을 캘 수 있다."
        ])


# ========================================
# 원거리 무기
# ========================================

@register_item
class Revolver(Item):
    """리볼버 — 경찰서 루팅, 희소"""
    unique_id = "revolver"
    name = "리볼버"
    category = "weapon"
    equip_props = {
        "전투:공격력": 12,
        "전투:사거리": 200,
        "전투:명중": -10,      # 패널티
        "전투:치명타": 10,     # 보너스
        "전투:탄약": "pistol_ammo",
        "전투:장탄수": 6,
        "can:reload": 1,
        "장착:손": 1,
    }
    value = 200
    actions = [
        "take@container", "equip@inventory",
        "call:reload:재장전#",
        "call:look:살펴보기@inventory",
    ]

    def reload(self):
        """재장전"""
        import combat
        player_id = morld.get_player_id()
        if combat.reload_weapon(player_id):
            morld.advance_time_des(combat.RELOAD_DURATION)

    def look(self):
        yield ui.dialog([
            "오래된 리볼버다.",
            "탄약이 희소하니 아껴 써야 한다."
        ])
