# quest/quests/daily_delivery.py
"""
일일 납품 퀘스트 정의

게시판에서 확인 가능한 납품 의뢰 퀘스트들.
매일 초기화되며 보상은 돈(코인).
"""

from quest import Quest, register_quest


# =============================================================================
# 일일 납품 퀘스트 - 허브
# =============================================================================

@register_quest
class DailyDeliverHerb(Quest):
    """허브 납품 - 일일 퀘스트"""

    unique_id = "daily_deliver_herb"
    name = "허브 납품"
    description = "허브 2개를 납품하세요."
    category = "daily"
    repeatable = True

    prerequisites = []
    giver = None  # 게시판에서 수락
    reporter = None  # 자동 완료

    conditions = [
        {"type": "deliver", "target": "errand_board", "item": "food_herb", "count": 2},
    ]

    rewards = [
        {"type": "coin", "value": 10},
    ]

    dialogs = {
        "offer": [
            "[의뢰]",
            "허브 2개를 납품해주세요.",
            "보상: 10코인",
        ],
        "complete": [
            "허브 납품이 완료되었습니다.",
            "10코인을 받았습니다.",
        ],
        "result": "허브 2개를 납품하고 10코인을 받았다.",
    }


# =============================================================================
# 일일 납품 퀘스트 - 통나무
# =============================================================================

@register_quest
class DailyDeliverLog(Quest):
    """통나무 납품 - 일일 퀘스트"""

    unique_id = "daily_deliver_log"
    name = "통나무 납품"
    description = "통나무 1개를 납품하세요."
    category = "daily"
    repeatable = True

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "deliver", "target": "errand_board", "item": "log", "count": 1},
    ]

    rewards = [
        {"type": "coin", "value": 15},
    ]

    dialogs = {
        "offer": [
            "[의뢰]",
            "통나무 1개를 납품해주세요.",
            "보상: 15코인",
        ],
        "complete": [
            "통나무 납품이 완료되었습니다.",
            "15코인을 받았습니다.",
        ],
        "result": "통나무 1개를 납품하고 15코인을 받았다.",
    }


# =============================================================================
# 일일 납품 퀘스트 - 요리
# =============================================================================

@register_quest
class DailyDeliverFood(Quest):
    """요리 납품 - 일일 퀘스트"""

    unique_id = "daily_deliver_food"
    name = "요리 납품"
    description = "아무 요리 1개를 납품하세요."
    category = "daily"
    repeatable = True

    prerequisites = []
    giver = None
    reporter = None

    # 여러 아이템 중 하나만 납품하면 됨
    conditions = [
        {"type": "any", "conditions": [
            {"type": "deliver", "target": "errand_board", "item": "food_cooked_meat", "count": 1},
            {"type": "deliver", "target": "errand_board", "item": "food_cooked_fish", "count": 1},
            {"type": "deliver", "target": "errand_board", "item": "food_fruit_salad", "count": 1},
            {"type": "deliver", "target": "errand_board", "item": "food_mushroom_stew", "count": 1},
        ]},
    ]

    rewards = [
        {"type": "coin", "value": 10},
    ]

    dialogs = {
        "offer": [
            "[의뢰]",
            "아무 요리 1개를 납품해주세요.",
            "(고기구이, 생선구이, 과일샐러드, 버섯스튜 등)",
            "보상: 10코인",
        ],
        "complete": [
            "요리 납품이 완료되었습니다.",
            "10코인을 받았습니다.",
        ],
        "result": "요리를 납품하고 10코인을 받았다.",
    }


# =============================================================================
# 일일 납품 퀘스트 - 베리
# =============================================================================

@register_quest
class DailyDeliverBerry(Quest):
    """산딸기 납품 - 일일 퀘스트"""

    unique_id = "daily_deliver_berry"
    name = "산딸기 납품"
    description = "산딸기 3개를 납품하세요."
    category = "daily"
    repeatable = True

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "deliver", "target": "errand_board", "item": "food_wild_berry", "count": 3},
    ]

    rewards = [
        {"type": "coin", "value": 8},
    ]

    dialogs = {
        "offer": [
            "[의뢰]",
            "산딸기 3개를 납품해주세요.",
            "보상: 8코인",
        ],
        "complete": [
            "산딸기 납품이 완료되었습니다.",
            "8코인을 받았습니다.",
        ],
        "result": "산딸기 3개를 납품하고 8코인을 받았다.",
    }


# =============================================================================
# 일일 납품 퀘스트 - 버섯
# =============================================================================

@register_quest
class DailyDeliverMushroom(Quest):
    """버섯 납품 - 일일 퀘스트"""

    unique_id = "daily_deliver_mushroom"
    name = "버섯 납품"
    description = "버섯 2개를 납품하세요."
    category = "daily"
    repeatable = True

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "deliver", "target": "errand_board", "item": "food_mushroom", "count": 2},
    ]

    rewards = [
        {"type": "coin", "value": 12},
    ]

    dialogs = {
        "offer": [
            "[의뢰]",
            "버섯 2개를 납품해주세요.",
            "보상: 12코인",
        ],
        "complete": [
            "버섯 납품이 완료되었습니다.",
            "12코인을 받았습니다.",
        ],
        "result": "버섯 2개를 납품하고 12코인을 받았다.",
    }
