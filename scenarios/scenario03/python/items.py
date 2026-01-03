# items.py - 아이템 정의
# morld 모듈을 사용하여 직접 게임 시스템에 데이터 등록

import morld

ITEMS = [
    # 기본 아이템
    {
        "id": 0,
        "name": "녹슨 열쇠",
        "passiveTags": {"열쇠": 1},
        "equipTags": {},
        "value": 5,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 1,
        "name": "체력 포션",
        "passiveTags": {},
        "equipTags": {},
        "value": 50,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 2,
        "name": "망원경",
        "passiveTags": {},
        "equipTags": {"관찰": 2},
        "value": 200,
        "actions": ["take@container", "use@inventory", "equip@inventory"]
    },
    {
        "id": 3,
        "name": "가죽 장갑",
        "passiveTags": {},
        "equipTags": {"방어": 1},
        "value": 30,
        "actions": ["take@container", "use@inventory", "equip@inventory"]
    },
    {
        "id": 4,
        "name": "돌멩이",
        "passiveTags": {},
        "equipTags": {},
        "value": 1,
        "actions": ["take@container", "throw@inventory"]
    },

    # 검사 장비 (10~19)
    {
        "id": 10,
        "name": "철검",
        "passiveTags": {},
        "equipTags": {"공격": 5, "검술": 1},
        "value": 150,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 11,
        "name": "나무 방패",
        "passiveTags": {},
        "equipTags": {"방어": 3, "막기": 1},
        "value": 80,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 12,
        "name": "가죽 갑옷",
        "passiveTags": {},
        "equipTags": {"방어": 4},
        "value": 120,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 13,
        "name": "철 투구",
        "passiveTags": {},
        "equipTags": {"방어": 2},
        "value": 60,
        "actions": ["take@container", "equip@inventory"]
    },

    # 마법사 장비 (20~29)
    {
        "id": 20,
        "name": "참나무 지팡이",
        "passiveTags": {},
        "equipTags": {"마력": 3, "집중": 1},
        "value": 100,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 21,
        "name": "마법사 로브",
        "passiveTags": {},
        "equipTags": {"마력": 2, "방어": 1},
        "value": 90,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 22,
        "name": "마나 포션",
        "passiveTags": {},
        "equipTags": {},
        "value": 60,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 23,
        "name": "마법서: 불꽃",
        "passiveTags": {"화염마법": 1},
        "equipTags": {},
        "value": 200,
        "actions": ["take@container", "use@inventory"]
    },

    # 도적 장비 (30~39)
    {
        "id": 30,
        "name": "단검",
        "passiveTags": {},
        "equipTags": {"공격": 3, "민첩": 2},
        "value": 70,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 31,
        "name": "투척용 나이프",
        "passiveTags": {},
        "equipTags": {},
        "value": 15,
        "actions": ["take@container", "throw@inventory"]
    },
    {
        "id": 32,
        "name": "경장갑",
        "passiveTags": {},
        "equipTags": {"방어": 2, "민첩": 1},
        "value": 100,
        "actions": ["take@container", "equip@inventory"]
    },
    {
        "id": 33,
        "name": "자물쇠 따개",
        "passiveTags": {"열쇠": 1, "자물쇠따기": 1},
        "equipTags": {},
        "value": 40,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 34,
        "name": "그림자 망토",
        "passiveTags": {},
        "equipTags": {"은신": 3},
        "value": 180,
        "actions": ["take@container", "equip@inventory"]
    },

    # 소모품 (40~49)
    {
        "id": 40,
        "name": "마른 빵",
        "passiveTags": {},
        "equipTags": {},
        "value": 5,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 41,
        "name": "물통",
        "passiveTags": {},
        "equipTags": {},
        "value": 10,
        "actions": ["take@container", "use@inventory"]
    },
    {
        "id": 42,
        "name": "동전 주머니",
        "passiveTags": {"금화": 50},
        "equipTags": {},
        "value": 50,
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
