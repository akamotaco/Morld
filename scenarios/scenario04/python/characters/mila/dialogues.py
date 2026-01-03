# characters/mila/dialogues.py - 밀라 대화

DIALOGUES = {
    "default": {
        "pages": [
            "안녕하세요. 저는 밀라예요.",
            "여기서 요리를 맡고 있어요.",
            "혹시 배고프지 않으세요? 뭐라도 만들어 드릴까요?"
        ]
    },
    "휴식": {
        "pages": [
            "잠시 쉬고 있어요.",
            "차 한 잔 하실래요?"
        ]
    },
    "식사": {
        "pages": [
            "다들 맛있게 드시고 계시네요.",
            "더 필요하신 건 없으세요?"
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "......"
        ]
    },
    "요리": {
        "pages": [
            "(요리에 집중하고 있다)",
            "조금만 기다려 주세요. 곧 완성이에요!"
        ]
    },
    "준비": {
        "pages": [
            "좋은 아침이에요!",
            "곧 아침 식사 준비할게요."
        ]
    },
    "설거지": {
        "pages": [
            "(설거지를 하고 있다)",
            "식사는 맛있으셨어요?"
        ]
    },
    "정리": {
        "pages": [
            "(주방을 정리하고 있다)",
            "오늘도 수고 많으셨어요."
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
