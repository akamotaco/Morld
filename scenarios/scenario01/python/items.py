# items.py - 시나리오01 아이템 정의

import morld


def initialize_items():
    """아이템 정의 등록"""

    items = [
        # 열쇠류
        {
            "id": 1,
            "name": "녹슨 열쇠",
            "passiveTags": {"녹슨열쇠": 1},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container"]
        },
        {
            "id": 2,
            "name": "은열쇠",
            "passiveTags": {"은열쇠": 1},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container"]
        },
        {
            "id": 3,
            "name": "황금열쇠",
            "passiveTags": {"황금열쇠": 1},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container"]
        },

        # 황금열쇠 파츠
        {
            "id": 10,
            "name": "황금열쇠 머리",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:combine_key:조합@inventory"]
        },
        {
            "id": 11,
            "name": "황금열쇠 몸통",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:combine_key:조합@inventory"]
        },

        # 읽을 수 있는 아이템
        {
            "id": 4,
            "name": "쪽지 1",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:read_note:읽기@inventory"]
        },
        {
            "id": 5,
            "name": "쪽지 2",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:read_note:읽기@inventory"]
        },
        {
            "id": 6,
            "name": "쪽지 3",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:read_note:읽기@inventory"]
        },
        {
            "id": 7,
            "name": "일기장",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:read_diary:읽기@inventory"]
        },
        {
            "id": 8,
            "name": "금고 메모",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:read_note:읽기@inventory"]
        },
        {
            "id": 9,
            "name": "서재 메모",
            "passiveTags": {},
            "equipTags": {},
            "value": 0,
            "actions": ["take@container", "script:read_note:읽기@inventory"]
        },
    ]

    for item in items:
        morld.add_item(
            item["id"],
            item["name"],
            item["passiveTags"],
            item["equipTags"],
            item["value"],
            item["actions"]
        )

    print(f"[items] Registered {len(items)} items")
