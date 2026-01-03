# items.py - 아이템 정의

import morld

ITEMS = [
    # === 기본 자원 (0~9) ===
    {
        "id": 0,
        "name": "밀가루",
        "passiveTags": {},
        "equipTags": {},
        "value": 5,
        "actions": ["take@container"]
    },
    {
        "id": 1,
        "name": "쌀",
        "passiveTags": {},
        "equipTags": {},
        "value": 5,
        "actions": ["take@container"]
    },
    {
        "id": 2,
        "name": "물",
        "passiveTags": {},
        "equipTags": {},
        "value": 1,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 3,
        "name": "빵",
        "passiveTags": {},
        "equipTags": {},
        "value": 10,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 4,
        "name": "나무",
        "passiveTags": {},
        "equipTags": {},
        "value": 3,
        "actions": ["take@container"]
    },
    {
        "id": 5,
        "name": "열매",
        "passiveTags": {},
        "equipTags": {},
        "value": 3,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 6,
        "name": "약초",
        "passiveTags": {"치료": 1},
        "equipTags": {},
        "value": 8,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 7,
        "name": "고기",
        "passiveTags": {},
        "equipTags": {},
        "value": 15,
        "actions": ["take@container"]
    },

    # === 초기 장비 - 사냥꾼 (10~19) ===
    {
        "id": 10,
        "name": "낡은 칼",
        "passiveTags": {},
        "equipTags": {"공격": 2, "사냥": 1},
        "value": 20,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 11,
        "name": "가죽 주머니",
        "passiveTags": {"수납": 5},
        "equipTags": {},
        "value": 10,
        "actions": ["take@container", "equip@inventory"]
    },

    # === 초기 장비 - 학자 (20~29) ===
    {
        "id": 20,
        "name": "필기구",
        "passiveTags": {},
        "equipTags": {"지능": 1},
        "value": 5,
        "actions": ["take@container"]
    },
    {
        "id": 21,
        "name": "낡은 책",
        "passiveTags": {"지식": 1},
        "equipTags": {},
        "value": 15,
        "actions": ["take@container", "script:read_book:읽기@inventory"]
    },

    # === 초기 장비 - 장인 (30~39) ===
    {
        "id": 30,
        "name": "작은 도구함",
        "passiveTags": {"수리": 1},
        "equipTags": {"손재주": 2},
        "value": 25,
        "actions": ["take@container"]
    },

    # === 기타 아이템 (40~) ===
    {
        "id": 40,
        "name": "횃불",
        "passiveTags": {},
        "equipTags": {"밝기": 3},
        "value": 5,
        "actions": ["take@container", "use@inventory", "equip@inventory"]
    },
    {
        "id": 41,
        "name": "밧줄",
        "passiveTags": {},
        "equipTags": {},
        "value": 8,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 42,
        "name": "천 조각",
        "passiveTags": {},
        "equipTags": {},
        "value": 2,
        "actions": ["take@container"]
    },
]


def initialize_items():
    """morld API를 사용하여 아이템 데이터 등록"""
    for item in ITEMS:
        morld.add_item_def(
            item["id"],
            item["name"],
            item.get("passiveTags"),
            item.get("equipTags"),
            item.get("value", 0),
            item.get("actions")
        )
    print(f"[items.py] {len(ITEMS)} items initialized via morld API")


def get_item(item_id):
    """특정 아이템 조회 (Python 내부용)"""
    for item in ITEMS:
        if item["id"] == item_id:
            return item
    return None
