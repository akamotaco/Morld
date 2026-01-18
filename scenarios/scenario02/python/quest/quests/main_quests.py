# quest/quests/main_quests.py
"""
메인 퀘스트 정의

주요 퀘스트:
0. 현재 상황을 파악하자 - 챕터1 시작 퀘스트 (아무 NPC와 만남)
1. 저택 식구들 - 5명의 캐릭터를 모두 만나는 다중 서브퀘스트
2. 도시로의 여정 - 도시 이동 후 엘라/유키 만나기
"""

from quest import Quest, register_quest


# ============================================
# 챕터1 시작 퀘스트
# ============================================

@register_quest
class MainUnderstandSituation(Quest):
    """현재 상황을 파악하자 - 챕터1 시작 퀘스트"""

    unique_id = "main_understand_situation"
    name = "현재 상황을 파악하자"
    description = "주변을 둘러보고 누군가를 만나 이야기를 들어보자."
    category = "main"

    prerequisites = []
    giver = None  # 챕터1 시작 시 자동 지급
    reporter = None  # 자동 완료

    # 아무 NPC와 만나면 완료 (관계:*:진척도 합산 >= 1)
    conditions = [
        {"type": "meet_anyone"},
    ]

    rewards = [
        {"type": "unlock_quest", "quest": "main_meet_everyone"},
    ]

    dialogs = {
        "offer": [
            "...머리가 아프다.",
            "기억이 잘 나지 않는다.",
            "일단 주변을 둘러보고, 누군가 있다면 말을 걸어보자.",
        ],
        "complete": [
            "이곳의 사정을 조금은 알게 되었다.",
            "더 많은 사람을 만나볼 필요가 있을 것 같다.",
        ],
    }


# ============================================
# 저택 식구들 (다중 서브퀘스트)
# ============================================

@register_quest
class MainMeetEveryone(Quest):
    """저택 식구들 - 5명 모두 만나기 (메인 퀘스트 컨테이너)"""

    unique_id = "main_meet_everyone"
    name = "저택 식구들"
    description = "저택에 사는 사람들을 모두 만나보자."
    category = "main"

    prerequisites = []
    giver = None  # 이벤트로 자동 지급
    reporter = None  # 자동 완료

    # 모든 서브퀘스트가 완료되면 이 퀘스트도 완료
    conditions = [
        {"type": "all", "conditions": [
            {"type": "quest_completed", "quest": "sub_meet_mila"},
            {"type": "quest_completed", "quest": "sub_meet_sera"},
            {"type": "quest_completed", "quest": "sub_meet_lina"},
            {"type": "quest_completed", "quest": "sub_meet_yuki"},
            {"type": "quest_completed", "quest": "sub_meet_ella"},
        ]},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "저택:친밀도", "value": 10},
    ]

    dialogs = {
        "offer": [
            "이 저택에는 여러 사람이 살고 있는 것 같다.",
            "한 명씩 만나보는 것이 좋겠다.",
        ],
        "complete": [
            "저택에 사는 모든 사람을 만났다.",
            "이제 이곳이 조금은 익숙해진 것 같다.",
        ],
    }


@register_quest
class SubMeetMila(Quest):
    """밀라 만나기 - 서브퀘스트"""

    unique_id = "sub_meet_mila"
    name = "밀라 만나기"
    description = "부엌을 관리하는 밀라를 만나보자."
    category = "main"

    prerequisites = ["main_meet_everyone"]
    giver = None
    reporter = None

    conditions = [
        {"type": "meet", "target": "mila"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 5},
    ]

    dialogs = {
        "complete": [
            "부엌을 관리하는 밀라를 만났다.",
            "따뜻하고 친절한 사람 같다.",
        ],
    }


@register_quest
class SubMeetSera(Quest):
    """세라 만나기 - 서브퀘스트"""

    unique_id = "sub_meet_sera"
    name = "세라 만나기"
    description = "숲에서 사냥을 하는 세라를 찾아보자."
    category = "main"

    prerequisites = ["main_meet_everyone"]
    giver = None
    reporter = None

    conditions = [
        {"type": "meet", "target": "sera"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:세라:호감", "value": 5},
    ]

    dialogs = {
        "complete": [
            "사냥꾼 세라를 만났다.",
            "과묵하지만 믿음직한 느낌이다.",
        ],
    }


@register_quest
class SubMeetLina(Quest):
    """리나 만나기 - 서브퀘스트"""

    unique_id = "sub_meet_lina"
    name = "리나 만나기"
    description = "저택 어딘가에 있는 리나를 찾아보자."
    category = "main"

    prerequisites = ["main_meet_everyone"]
    giver = None
    reporter = None

    conditions = [
        {"type": "meet", "target": "lina"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:리나:호감", "value": 5},
    ]

    dialogs = {
        "complete": [
            "활발한 소녀 리나를 만났다.",
            "호기심이 많고 에너지가 넘친다.",
        ],
    }


# ============================================
# 도시로의 여정 (순차 퀘스트)
# ============================================

@register_quest
class MainJourneyToCity(Quest):
    """도시로의 여정 - 도시 이동 퀘스트"""

    unique_id = "main_journey_to_city"
    name = "도시로의 여정"
    description = "저택 너머에 있다는 도시를 찾아가보자."
    category = "main"

    prerequisites = []  # 챕터 1 시작 시 해금
    giver = "mila"
    reporter = None

    conditions = [
        {"type": "reach", "region_id": 1, "location_id": 0},  # 도시 입구
    ]

    rewards = [
        {"type": "unlock_quest", "quest": "sub_meet_yuki"},
        {"type": "unlock_quest", "quest": "sub_meet_ella"},
    ]

    dialogs = {
        "offer": [
            "[밀라]",
            "저택에서 조금 더 가면 도시가 있어요.",
            "필요한 물건이 있으면 그곳에서 구할 수 있을 거예요.",
            "유키와 엘라라는 분들이 가게를 운영하고 있어요.",
        ],
        "accept": [
            "[밀라]",
            "조심해서 다녀오세요!",
            "길을 잃으면 안 되니까, 잘 기억해 두세요.",
        ],
        "decline": [
            "[밀라]",
            "...그래요. 나중에 가도 괜찮아요.",
        ],
        "complete": [
            "도시에 도착했다.",
            "생각보다 활기찬 곳이다.",
        ],
    }


@register_quest
class SubMeetYuki(Quest):
    """유키 만나기 - 도시 도착 후 해금"""

    unique_id = "sub_meet_yuki"
    name = "유키 만나기"
    description = "도시에서 가게를 운영하는 유키를 찾아보자."
    category = "main"

    prerequisites = ["main_journey_to_city"]
    giver = None
    reporter = None

    conditions = [
        {"type": "meet", "target": "yuki"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:유키:호감", "value": 5},
    ]

    dialogs = {
        "complete": [
            "잡화점 주인 유키를 만났다.",
            "차분하고 신비로운 분위기의 여성이다.",
        ],
    }


@register_quest
class SubMeetElla(Quest):
    """엘라 만나기 - 도시 도착 후 해금"""

    unique_id = "sub_meet_ella"
    name = "엘라 만나기"
    description = "도시에서 카페를 운영하는 엘라를 찾아보자."
    category = "main"

    prerequisites = ["main_journey_to_city"]
    giver = None
    reporter = None

    conditions = [
        {"type": "meet", "target": "ella"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:엘라:호감", "value": 5},
    ]

    dialogs = {
        "complete": [
            "카페 주인 엘라를 만났다.",
            "쾌활하고 사교적인 성격이다.",
        ],
    }
