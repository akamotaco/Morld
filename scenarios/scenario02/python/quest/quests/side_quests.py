# quest/quests/side_quests.py
"""
범용 사이드 퀘스트 정의

캐릭터 개인 퀘스트는 각 캐릭터 파일의 CHARACTER_QUESTS에 정의됨.
여기는 특정 캐릭터에 종속되지 않는 범용 퀘스트만 정의.
"""

from quest import Quest, register_quest


# =============================================================================
# 탐험 퀘스트
# =============================================================================

@register_quest
class SideExploreBasement(Quest):
    """지하실 탐험 - 숨겨진 장소 발견"""

    unique_id = "side_explore_basement"
    name = "지하실의 비밀"
    description = "저택 지하실에 뭔가 있는 것 같다. 탐험해보자."
    category = "side"

    prerequisites = []  # 초반부터 가능
    giver = None  # 자동 해금
    reporter = None  # 자동 완료

    conditions = [
        {"type": "reach", "region": 0, "location": "basement"},
    ]

    rewards = [
        {"type": "item", "item": "old_key", "count": 1},
        {"type": "prop", "target": "player", "prop": "탐험:지하실", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(저택 어딘가에 지하실이 있는 것 같다)",
            "(한 번 가보는 것이 좋을 것 같다)",
        ],
        "complete": [
            "(지하실에서 오래된 열쇠를 발견했다)",
            "(이 열쇠는 어디에 쓰이는 것일까?)",
        ],
    }


@register_quest
class SideExploreAttic(Quest):
    """다락방 탐험"""

    unique_id = "side_explore_attic"
    name = "다락방"
    description = "저택 다락방에는 무엇이 있을까?"
    category = "side"

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "reach", "region": 0, "location": "attic"},
    ]

    rewards = [
        {"type": "item", "item": "old_diary", "count": 1},
        {"type": "prop", "target": "player", "prop": "탐험:다락방", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(다락방이 있다는 얘기를 들었다)",
            "(올라가 볼까?)",
        ],
        "complete": [
            "(다락방에서 오래된 일기장을 발견했다)",
            "(누군가의 기록이 남아있다...)",
        ],
    }


@register_quest
class SideExploreForest(Quest):
    """숲 깊은 곳 탐험"""

    unique_id = "side_explore_forest"
    name = "숲의 심연"
    description = "숲 깊은 곳에는 무엇이 있을까?"
    category = "side"

    prerequisites = ["sub_meet_sera"]  # 세라 만남 이후
    giver = None
    reporter = None

    conditions = [
        {"type": "reach", "region": 0, "location": "deep_forest"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "탐험:깊은숲", "value": 1},
        {"type": "unlock_quest", "quest": "side_find_herb_patch"},
    ]

    dialogs = {
        "offer": [
            "(세라가 숲 깊은 곳에 대해 경고했다)",
            "(하지만... 호기심이 이긴다)",
        ],
        "complete": [
            "(숲 깊은 곳까지 도달했다)",
            "(이 주변에 희귀한 약초가 자란다는 소문이 있다...)",
        ],
    }


# =============================================================================
# 수집 퀘스트
# =============================================================================

@register_quest
class SideCollectFirewood(Quest):
    """땔감 수집 - 겨울 대비"""

    unique_id = "side_collect_firewood"
    name = "땔감 모으기"
    description = "저택의 겨울을 대비해 땔감을 모으자."
    category = "side"

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "collect", "item": "firewood", "count": 10},
    ]

    rewards = [
        {"type": "prop", "target": "global", "prop": "저택:땔감비축", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(겨울이 오기 전에 땔감을 모아두는 것이 좋겠다)",
        ],
        "complete": [
            "(충분한 땔감을 확보했다)",
            "(이 정도면 겨울을 날 수 있을 것이다)",
        ],
    }


@register_quest
class SideCollectMushrooms(Quest):
    """버섯 수집"""

    unique_id = "side_collect_mushrooms"
    name = "버섯 채집"
    description = "숲에서 버섯을 채집하자. 요리 재료로 쓸 수 있다."
    category = "side"

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "collect", "item": "mushroom", "count": 5},
    ]

    rewards = [
        {"type": "item", "item": "mushroom_soup", "count": 1},
    ]

    dialogs = {
        "offer": [
            "(숲에 버섯이 자라는 곳이 있다고 한다)",
            "(몇 개 채집해볼까?)",
        ],
        "complete": [
            "(버섯을 충분히 모았다)",
            "(이것으로 수프를 만들 수 있겠다)",
        ],
    }


@register_quest
class SideFindHerbPatch(Quest):
    """희귀 약초 발견"""

    unique_id = "side_find_herb_patch"
    name = "희귀 약초"
    description = "숲 깊은 곳에서 희귀한 약초를 찾자."
    category = "side"

    prerequisites = ["side_explore_forest"]  # 숲 깊은 곳 탐험 이후 해금
    giver = None
    reporter = None

    conditions = [
        {"type": "collect", "item": "rare_herb", "count": 3},
    ]

    rewards = [
        {"type": "item", "item": "healing_potion", "count": 2},
        {"type": "prop", "target": "player", "prop": "지식:약초학", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(숲 깊은 곳에 희귀한 약초가 자란다는 소문이 있다)",
            "(찾아볼 가치가 있을 것이다)",
        ],
        "complete": [
            "(희귀 약초를 수집했다)",
            "(이것으로 회복 물약을 만들 수 있다)",
        ],
    }


# =============================================================================
# 일일/반복 퀘스트
# =============================================================================

@register_quest
class DailyPatrol(Quest):
    """저택 순찰 - 일일 퀘스트"""

    unique_id = "daily_patrol"
    name = "저택 순찰"
    description = "저택 주변을 순찰하며 이상이 없는지 확인하자."
    category = "daily"
    repeatable = True  # 일일 반복

    prerequisites = ["sub_meet_sera"]  # 세라 만남 이후
    giver = None
    reporter = "sera"

    conditions = [
        {"type": "all", "conditions": [
            {"type": "reach", "region": 0, "location": "front_yard"},
            {"type": "reach", "region": 0, "location": "back_yard"},
            {"type": "reach", "region": 0, "location": "forest_entrance"},
        ]},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:세라:신뢰", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(저택 주변을 순찰하는 것이 좋겠다)",
            "(앞마당, 뒷마당, 숲 입구를 돌아보자)",
        ],
        "progress": [
            "[세라]",
            "...순찰 중이냐?",
            "...좋은 습관이다.",
        ],
        "complete": [
            "[세라]",
            "...순찰 보고다.",
            "이상 없나?",
            "...수고했다.",
        ],
    }


@register_quest
class DailyFishing(Quest):
    """낚시하기 - 일일 퀘스트"""

    unique_id = "daily_fishing"
    name = "오늘의 낚시"
    description = "호수에서 물고기를 잡아보자."
    category = "daily"
    repeatable = True  # 일일 반복

    prerequisites = []  # 낚시대가 있어야 진행 가능 (조건에서 체크)
    giver = None
    reporter = None

    conditions = [
        {"type": "collect", "item": "fish", "count": 1},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "포만감", "value": 20},
    ]

    dialogs = {
        "offer": [
            "(호수에서 낚시를 해볼까?)",
            "(낚시대가 필요하다)",
        ],
        "complete": [
            "(물고기를 잡았다!)",
            "(신선한 생선으로 배를 채울 수 있겠다)",
        ],
    }


# =============================================================================
# 특수 퀘스트
# =============================================================================

@register_quest
class SideRepairFence(Quest):
    """울타리 수리"""

    unique_id = "side_repair_fence"
    name = "울타리 수리"
    description = "저택 울타리가 망가졌다. 재료를 모아 수리하자."
    category = "side"

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "all", "conditions": [
            {"type": "collect", "item": "wood_plank", "count": 5},
            {"type": "collect", "item": "nail", "count": 10},
        ]},
    ]

    rewards = [
        {"type": "prop", "target": "global", "prop": "저택:울타리수리", "value": 1},
        {"type": "prop", "target": "player", "prop": "기술:목공", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(저택 울타리가 낡아서 부서진 곳이 있다)",
            "(나무판과 못을 구해 수리해야겠다)",
        ],
        "complete": [
            "(울타리를 수리했다)",
            "(이제 야생동물이 함부로 들어오지 못할 것이다)",
        ],
    }


@register_quest
class SideCleanWell(Quest):
    """우물 청소"""

    unique_id = "side_clean_well"
    name = "우물 청소"
    description = "우물이 더러워졌다. 청소하면 깨끗한 물을 얻을 수 있다."
    category = "side"

    prerequisites = []
    giver = None
    reporter = None

    conditions = [
        {"type": "all", "conditions": [
            {"type": "reach", "region": 0, "location": "well"},
            {"type": "prop", "prop": "우물청소중", "value": 1},  # 청소 액션 실행 후
        ]},
    ]

    rewards = [
        {"type": "prop", "target": "global", "prop": "저택:우물청소", "value": 1},
    ]

    dialogs = {
        "offer": [
            "(우물물이 탁해 보인다)",
            "(청소하면 깨끗한 물을 마실 수 있을 것이다)",
        ],
        "complete": [
            "(우물을 깨끗이 청소했다)",
            "(이제 맑은 물을 마실 수 있다)",
        ],
    }
