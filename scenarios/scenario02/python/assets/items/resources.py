# assets/items/resources.py - 기본 자원 아이템

from assets import registry

# ========================================
# 식량 자원
# ========================================

FLOUR = {
    "unique_id": "flour",
    "name": "밀가루",
    "passiveTags": {},
    "equipTags": {},
    "value": 5,
    "actions": ["take@container"]
}

RICE = {
    "unique_id": "rice",
    "name": "쌀",
    "passiveTags": {},
    "equipTags": {},
    "value": 5,
    "actions": ["take@container"]
}

WATER = {
    "unique_id": "water",
    "name": "물",
    "passiveTags": {},
    "equipTags": {},
    "value": 1,
    "actions": ["take@container", "use@inventory"]
}

BREAD = {
    "unique_id": "bread",
    "name": "빵",
    "passiveTags": {},
    "equipTags": {},
    "value": 10,
    "actions": ["take@container", "use@inventory"]
}

BERRY = {
    "unique_id": "berry",
    "name": "열매",
    "passiveTags": {},
    "equipTags": {},
    "value": 3,
    "actions": ["take@container", "use@inventory"]
}

MEAT = {
    "unique_id": "meat",
    "name": "고기",
    "passiveTags": {},
    "equipTags": {},
    "value": 15,
    "actions": ["take@container"]
}

# ========================================
# 기타 자원
# ========================================

WOOD = {
    "unique_id": "wood",
    "name": "나무",
    "passiveTags": {},
    "equipTags": {},
    "value": 3,
    "actions": ["take@container"]
}

HERB = {
    "unique_id": "herb",
    "name": "약초",
    "passiveTags": {"치료": 1},
    "equipTags": {},
    "value": 8,
    "actions": ["take@container", "use@inventory"]
}

CLOTH = {
    "unique_id": "cloth",
    "name": "천 조각",
    "passiveTags": {},
    "equipTags": {},
    "value": 2,
    "actions": ["take@container"]
}


def register():
    """자원 아이템 Asset 등록"""
    registry.register_item(FLOUR)
    registry.register_item(RICE)
    registry.register_item(WATER)
    registry.register_item(BREAD)
    registry.register_item(BERRY)
    registry.register_item(MEAT)
    registry.register_item(WOOD)
    registry.register_item(HERB)
    registry.register_item(CLOTH)
