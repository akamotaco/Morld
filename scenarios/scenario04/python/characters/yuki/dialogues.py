# characters/yuki/dialogues.py - 유키 대화

DIALOGUES = {
    "default": {
        "pages": [
            "......",
            "...유키... 입니다.",
            "...청소와 빨래를... 맡고 있어요."
        ]
    },
    "휴식": {
        "pages": [
            "(책을 읽고 있다)",
            "...아, 네...?",
            "...괜찮아요..."
        ]
    },
    "식사": {
        "pages": [
            "(조용히 먹고 있다)",
            "......",
            "...맛있어요."
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "......"
        ]
    },
    "청소": {
        "pages": [
            "(청소에 집중하고 있다)",
            "...아, 죄송해요. 좀 비켜주실래요...?"
        ]
    },
    "빨래": {
        "pages": [
            "(빨래를 널고 있다)",
            "...오늘은 날씨가 좋아서... 빨래가 잘 마를 것 같아요."
        ]
    },
    "준비": {
        "pages": [
            "...좋은 아침이에요.",
            "......",
            "(살짝 고개를 숙인다)"
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
