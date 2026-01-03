# characters/younghee/dialogues.py - 영희 대화

# activity별 대사 오버라이드
DIALOGUES = {
    "default": {
        "pages": [
            "어서오세요, 손님.",
            "필요한 물건이 있으시면 말씀해주세요."
        ]
    },
    "영업": {
        "pages": [
            "환영합니다!",
            "오늘 신상품이 들어왔어요.",
            "천천히 구경하세요."
        ]
    },
    "식사": {
        "pages": [
            "(식사 중이다)",
            "잠시 쉬는 중이에요."
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "...zzZ"
        ]
    },
    "준비": {
        "pages": [
            "(준비 중이다)",
            "곧 문을 열 거예요."
        ]
    },
    "정리": {
        "pages": [
            "(정리 중이다)",
            "오늘 장사는 마감이에요."
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
