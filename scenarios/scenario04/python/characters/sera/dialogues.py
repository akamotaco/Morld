# characters/sera/dialogues.py - 세라 대화

DIALOGUES = {
    "default": {
        "pages": [
            "......",
            "...세라다.",
            "사냥을 맡고 있다."
        ]
    },
    "휴식": {
        "pages": [
            "......",
            "...좀 쉬는 중이다."
        ]
    },
    "식사": {
        "pages": [
            "(조용히 먹고 있다)",
            "......",
            "...밀라의 요리는 괜찮다."
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "......"
        ]
    },
    "사냥": {
        "pages": [
            "......조용히 해라.",
            "...사냥감이 도망간다."
        ]
    },
    "준비": {
        "pages": [
            "(활을 점검하고 있다)",
            "......"
        ]
    },
    "정비": {
        "pages": [
            "(화살을 다듬고 있다)",
            "...장비 관리는 중요하다."
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
