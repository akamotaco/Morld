# assets/items/shields.py — 방어 장비 (방패)

import ui
from assets.base import Item
from assets.registry import register_item


@register_item
class WoodenShield(Item):
    """나무 방패 — 크래프팅 제작"""
    unique_id = "wooden_shield"
    name = "나무 방패"
    category = "weapon"
    equip_props = {
        "전투:방어력": 3,
        "전투:회피": -5,       # 회피 패널티
        "장착:손": 1,
    }
    value = 25
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "나무로 만든 방패다.",
            "가볍지만 방어력이 있다."
        ])


@register_item
class CopperShield(Item):
    """구리 방패 — 구리광석 제작, 하위 등급"""
    unique_id = "copper_shield"
    name = "구리 방패"
    category = "weapon"
    equip_props = {
        "전투:방어력": 3,
        "전투:회피": -5,
        "장착:손": 1,
    }
    value = 35
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "구리로 만든 방패다.",
            "나무 방패보다 튼튼하다."
        ])


@register_item
class IronShield(Item):
    """철제 방패 — 광석 제작"""
    unique_id = "iron_shield"
    name = "철제 방패"
    category = "weapon"
    equip_props = {
        "전투:방어력": 5,
        "전투:회피": -10,      # 회피 패널티
        "장착:손": 1,
    }
    value = 60
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "단단한 철로 만든 방패다.",
            "무겁지만 방어력이 높다."
        ])
