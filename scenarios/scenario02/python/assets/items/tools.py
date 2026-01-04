# assets/items/tools.py - 도구 아이템

from assets import registry

# ========================================
# 기타 도구
# ========================================

TORCH = {
    "unique_id": "torch",
    "name": "횃불",
    "passiveTags": {},
    "equipTags": {"밝기": 3},
    "value": 5,
    "actions": ["take@container", "use@inventory", "equip@inventory"]
}

ROPE = {
    "unique_id": "rope",
    "name": "밧줄",
    "passiveTags": {},
    "equipTags": {},
    "value": 8,
    "actions": ["take@container", "use@inventory"]
}


def register():
    """도구 아이템 Asset 등록"""
    registry.register_item(TORCH)
    registry.register_item(ROPE)
