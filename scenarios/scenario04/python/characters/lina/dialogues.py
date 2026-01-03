# characters/lina/dialogues.py - 리나 대화

DIALOGUES = {
    "default": {
        "pages": [
            "안녕! 나는 리나야.",
            "숲에서 열매 따는 일을 맡고 있어.",
            "뭔가 필요한 거 있어?"
        ]
    },
    "휴식": {
        "pages": [
            "후~ 오늘도 열심히 했다!",
            "좀 쉬어야겠어."
        ]
    },
    "식사": {
        "pages": [
            "(맛있게 먹고 있다)",
            "음~ 밀라 언니 요리 최고야!"
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "...zzZ"
        ]
    },
    "채집": {
        "pages": [
            "오늘 열매가 많이 열렸어!",
            "같이 따볼래? 재밌어!"
        ]
    },
    "준비": {
        "pages": [
            "(기지개를 켠다)",
            "음~ 오늘도 화이팅!"
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
