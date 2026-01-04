# assets/items/keys.py - 열쇠류 (녹슨 열쇠, 은열쇠)

from assets import registry

# ========================================
# Asset 정의
# ========================================

RUSTY_KEY = {
    "unique_id": "rusty_key",
    "name": "녹슨 열쇠",
    "passiveTags": {"녹슨열쇠": 1},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container"]
}

SILVER_KEY = {
    "unique_id": "silver_key",
    "name": "은열쇠",
    "passiveTags": {"은열쇠": 1},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container"]
}


def register():
    """열쇠류 Asset 등록"""
    registry.register_item(RUSTY_KEY)
    registry.register_item(SILVER_KEY)
