# assets/items/consumables.py - 소모품 아이템

from assets.base import Item
from assets.registry import register_item


@register_item
class Bread(Item):
    unique_id = "bread"
    name = "빵"
    weight = 0.3
    value = 300
    category = "food"
    props = {"소모품:유형": "식량", "소모품:포만감": 20}


@register_item
class DriedMeat(Item):
    unique_id = "dried_meat"
    name = "건조 고기"
    weight = 0.5
    value = 800
    category = "food"
    props = {"소모품:유형": "식량", "소모품:포만감": 40}


@register_item
class HealingHerb(Item):
    unique_id = "healing_herb"
    name = "치료약초"
    weight = 0.1
    value = 1500
    category = "consumable"
    props = {"소모품:유형": "회복", "소모품:HP회복": 30}


@register_item
class Antidote(Item):
    unique_id = "antidote"
    name = "해독제"
    weight = 0.1
    value = 2000
    category = "consumable"
    props = {"소모품:유형": "해독"}


@register_item
class AntiErosionDrug(Item):
    unique_id = "anti_erosion_drug"
    name = "항침식제"
    weight = 0.2
    value = 5000
    category = "consumable"
    props = {"소모품:유형": "정화", "소모품:침식감소": 10}


@register_item
class Ration(Item):
    unique_id = "ration"
    name = "비상식량"
    weight = 1.0
    value = 1500
    category = "food"
    props = {"소모품:유형": "식량", "소모품:포만감": 60}


@register_item
class CaveMoss(Item):
    unique_id = "cave_moss"
    name = "동굴 이끼"
    weight = 0.2
    value = 200
    category = "food"
    props = {"소모품:유형": "식량", "소모품:포만감": 8}


@register_item
class MoralePill(Item):
    unique_id = "morale_pill"
    name = "진정제"
    weight = 0.1
    value = 3000
    category = "consumable"
    props = {"소모품:유형": "사기", "소모품:사기회복": 15}
