# assets/items/equipment.py - 장비 아이템

from assets import registry

# ========================================
# 사냥꾼 장비
# ========================================

OLD_KNIFE = {
    "unique_id": "old_knife",
    "name": "낡은 칼",
    "passiveTags": {},
    "equipTags": {"공격": 2, "사냥": 1},
    "value": 20,
    "actions": ["take@container", "equip@inventory"]
}

LEATHER_POUCH = {
    "unique_id": "leather_pouch",
    "name": "가죽 주머니",
    "passiveTags": {"수납": 5},
    "equipTags": {},
    "value": 10,
    "actions": ["take@container", "equip@inventory"]
}

# ========================================
# 학자 장비
# ========================================

WRITING_TOOL = {
    "unique_id": "writing_tool",
    "name": "필기구",
    "passiveTags": {},
    "equipTags": {"지능": 1},
    "value": 5,
    "actions": ["take@container"]
}

OLD_BOOK = {
    "unique_id": "old_book",
    "name": "낡은 책",
    "passiveTags": {"지식": 1},
    "equipTags": {},
    "value": 15,
    "actions": ["take@container", "script:read_book:읽기@inventory"]
}

# ========================================
# 장인 장비
# ========================================

SMALL_TOOLBOX = {
    "unique_id": "small_toolbox",
    "name": "작은 도구함",
    "passiveTags": {"수리": 1},
    "equipTags": {"손재주": 2},
    "value": 25,
    "actions": ["take@container"]
}


def register():
    """장비 아이템 Asset 등록"""
    registry.register_item(OLD_KNIFE)
    registry.register_item(LEATHER_POUCH)
    registry.register_item(WRITING_TOOL)
    registry.register_item(OLD_BOOK)
    registry.register_item(SMALL_TOOLBOX)
