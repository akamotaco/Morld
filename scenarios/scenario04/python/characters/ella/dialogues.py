# characters/ella/dialogues.py - 엘라 대화

DIALOGUES = {
    "default": {
        "pages": [
            "나는 엘라. 이 저택의 관리를 맡고 있다.",
            "네가 기억을 잃었다는 건 들었다.",
            "당분간 여기서 지내도 좋다. 단, 규칙은 지켜라."
        ]
    },
    "휴식": {
        "pages": [
            "...무슨 일이지?",
            "급한 게 아니라면 나중에 이야기하도록."
        ]
    },
    "식사": {
        "pages": [
            "(우아하게 식사 중이다)",
            "...식사 중이다. 볼일이 있으면 나중에."
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "......"
        ]
    },
    "관리": {
        "pages": [
            "(서류를 검토하고 있다)",
            "...지금 바쁘다. 급한 일인가?"
        ]
    },
    "조회": {
        "pages": [
            "아침 조회 중이다.",
            "네 차례가 되면 말하겠다. 기다려라."
        ]
    },
    "순찰": {
        "pages": [
            "(저택을 순찰 중이다)",
            "이상은 없는가?"
        ]
    },
    "준비": {
        "pages": [
            "......",
            "...볼일이 있으면 조회 때 말하도록."
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
