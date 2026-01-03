# characters/minsu/dialogues.py - 민수 대화

# activity별 대사 오버라이드
DIALOGUES = {
    "default": {
        "pages": [
            "....",
            "(말이 없다)"
        ]
    },
    "식사": {
        "pages": [
            "(묵묵히 먹고 있다)",
            "...(끄덕)"
        ]
    },
    "수면": {
        "pages": [
            "(깊이 잠들어 있다)",
            "...zzZ"
        ]
    },
    "휴식": {
        "pages": [
            "(조용히 앉아 있다)",
            "...하늘이 맑네."
        ]
    },
    "작업": {
        "pages": [
            "(물을 긷고 있다)",
            "...바빠."
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
