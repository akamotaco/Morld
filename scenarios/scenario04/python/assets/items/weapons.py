# assets/items/weapons.py - 무기 아이템
#
# 임시 목록. 밸런싱 추후.

from assets.base import Item
from assets.registry import register_item


@register_item
class RustyKnife(Item):
    unique_id = "rusty_knife"
    name = "녹슨 칼"
    weight = 1.5
    value = 500
    category = "weapon"
    props = {"장비:유형": "무기", "장비:슬롯": "주무기", "장비:공격력": 5, "내구도": 60}


@register_item
class ShortSword(Item):
    unique_id = "short_sword"
    name = "단검"
    weight = 2.0
    value = 3000
    category = "weapon"
    props = {"장비:유형": "무기", "장비:슬롯": "주무기", "장비:공격력": 10, "내구도": 100}


@register_item
class LongSword(Item):
    unique_id = "long_sword"
    name = "장검"
    weight = 4.0
    value = 8000
    category = "weapon"
    props = {"장비:유형": "무기", "장비:슬롯": "주무기", "장비:공격력": 18, "내구도": 100}


@register_item
class Bow(Item):
    unique_id = "bow"
    name = "활"
    weight = 2.5
    value = 5000
    category = "weapon"
    props = {"장비:유형": "무기", "장비:슬롯": "주무기", "장비:공격력": 12, "장비:사거리": 1, "내구도": 80}


@register_item
class WoodenShield(Item):
    unique_id = "wooden_shield"
    name = "나무 방패"
    weight = 3.0
    value = 2000
    category = "weapon"
    props = {"장비:유형": "방패", "장비:슬롯": "보조", "장비:방어력": 5, "내구도": 80}
