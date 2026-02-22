# assets/items/ammo.py — 탄약 (소모품, 스택)

import ui
from assets.base import Item
from assets.registry import register_item


@register_item
class Arrow(Item):
    """화살 — 크래프팅 제작 가능"""
    unique_id = "arrow"
    name = "화살"
    category = "ammo"
    value = 3
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog("사냥용 활에 사용하는 화살이다.")


@register_item
class PistolAmmo(Item):
    """권총탄 — 경찰서 루팅, 희소"""
    unique_id = "pistol_ammo"
    name = "권총탄"
    category = "ammo"
    value = 15
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog("리볼버에 사용하는 탄약이다. 구하기 어렵다.")
