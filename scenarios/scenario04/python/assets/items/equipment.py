# assets/items/equipment.py - 방어구/장비 아이템
#
# S02 clothes.py 기반 슬롯 구조. 임시 목록.

from assets.base import Item
from assets.registry import register_item


@register_item
class LeatherArmor(Item):
    unique_id = "leather_armor"
    name = "가죽 갑옷"
    weight = 5.0
    value = 5000
    category = "armor"
    props = {"장비:유형": "방어구", "장비:슬롯": "상의", "장비:방어력": 8, "내구도": 100}


@register_item
class ChainMail(Item):
    unique_id = "chain_mail"
    name = "사슬 갑옷"
    weight = 12.0
    value = 15000
    category = "armor"
    props = {"장비:유형": "방어구", "장비:슬롯": "상의", "장비:방어력": 15, "내구도": 100}


@register_item
class LeatherBoots(Item):
    unique_id = "leather_boots"
    name = "가죽 장화"
    weight = 1.5
    value = 2000
    category = "armor"
    props = {"장비:유형": "방어구", "장비:슬롯": "신발", "장비:방어력": 3, "내구도": 80}


@register_item
class LeatherGloves(Item):
    unique_id = "leather_gloves"
    name = "가죽 장갑"
    weight = 0.5
    value = 1500
    category = "armor"
    props = {"장비:유형": "방어구", "장비:슬롯": "장갑", "장비:방어력": 2, "내구도": 80}


@register_item
class AntiCorrosionAmulet(Item):
    unique_id = "anti_corrosion_amulet"
    name = "항오염 부적"
    weight = 0.2
    value = 20000
    category = "accessory"
    props = {"장비:유형": "악세서리", "장비:슬롯": "악세서리", "내오성": 10, "내구도": 50}
