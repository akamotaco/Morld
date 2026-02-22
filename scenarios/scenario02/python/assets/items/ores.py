# assets/items/ores.py — 광석 아이템 (채광 산출물)

import ui
from assets.base import Item
from assets.registry import register_item


@register_item
class CopperOre(Item):
    """구리광석 — 폐광산 1층/2층, 구리 무기 재료"""
    unique_id = "copper_ore"
    name = "구리광석"
    category = "material"
    value = 8
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "녹청이 낀 구리광석이다.",
            "제작대에서 무기나 방패를 만들 수 있다."
        ])


@register_item
class IronOre(Item):
    """철광석 — 폐광산 2층/깊은 갱도, 철 무기 재료"""
    unique_id = "iron_ore"
    name = "철광석"
    category = "material"
    value = 12
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "무거운 철광석이다.",
            "제작대에서 강한 무기를 만들 수 있다."
        ])
