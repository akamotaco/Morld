# characters/cheolsu/dialogues.py - 철수 대화

# activity별 대사 오버라이드
DIALOGUES = {
    "default": {
        "pages": [
            "안녕, 나는 철수야.",
            "오늘 날씨가 좋네."
        ]
    },
    "휴식": {
        "pages": [
            "(편하게 쉬고 있다)",
            "...오늘은 좀 피곤하네."
        ]
    },
    "식사": {
        "pages": [
            "(음식을 먹고 있다)",
            "이 식당 음식은 정말 맛있어."
        ]
    },
    "수면": {
        "pages": [
            "(자고 있다)",
            "...zzZ"
        ]
    },
    "쇼핑": {
        "pages": [
            "(물건을 구경하고 있다)",
            "좋은 물건이 있나 보고 있어."
        ]
    },
    "산책": {
        "pages": [
            "(산책 중이다)",
            "날씨 좋은 날엔 산책이 최고지."
        ]
    },
    "준비": {
        "pages": [
            "(준비 중이다)",
            "곧 나갈 거야."
        ]
    }
}


def get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
