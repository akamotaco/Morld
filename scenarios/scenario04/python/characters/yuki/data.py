# characters/yuki/data.py - 유키 캐릭터 정의

CHARACTER_ID = 4

PRESENCE_TEXT = {
    # activity 기반
    "activity:청소": "{name}가 조용히 청소하고 있다.",
    "activity:빨래": "{name}가 빨래를 널고 있다.",
    "activity:식사": "{name}가 조용히 식사 중이다.",
    "activity:수면": "{name}가 새근새근 잠들어 있다.",
    "activity:휴식": "{name}가 책을 읽고 있다.",

    # 애정도 기반
    "애정:낮음": "{name}가 멀찍이 서서 이쪽을 힐끗 본다.",
    "애정:중간": "{name}가 자꾸 플레이어 쪽을 흘깃흘깃 쳐다본다.",
    "애정:높음": "{name}와 눈이 마주치자 얼굴을 붉히며 눈을 피한다.",
    "애정:최고": "{name}가 수줍게 웃으며 옆에 다가와 선다.",

    # 장소 기반
    "0:4": "{name}가 욕실을 청소하고 있다.",  # 욕실
    "0:1": "{name}가 소파 구석에 앉아 책을 읽고 있다.",  # 거실

    # 기본값
    "default": "{name}가 조용히 서 있다."
}

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "유키",
    "comment": "npc_yuki",
    "type": "female",
    "regionId": 0,
    "locationId": 10,  # 유키의 방
    "tags": {
        # 외모
        "외모:은발": 1,
        "외모:장발": 1,
        "외모:붉은눈": 1,
        # 성격
        "성격:수줍음": 1,
        "성격:얌전함": 1,
        # 관계
        "애정": 0,
        "성욕": 0,
        "질투": 0,
        # 상태
        "피로": 0,
        "기분": 5,
    },
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "은빛 긴 머리의 조용한 소녀. 붉은 눈이 신비로운 느낌을 준다.",
        "기쁨": "살짝 볼이 붉어지며 희미하게 웃는다.",
        "슬픔": "고개를 숙이고 있다. 말을 걸기 어려워 보인다.",
        "식사": "조용히 음식을 먹고 있다.",
        "수면": "새근새근 잠들어 있다. 인형 같다.",
        "청소": "열심히 청소하고 있다.",
        "빨래": "빨래를 정성스럽게 널고 있다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 10, "start": 360, "end": 420, "activity": "준비"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 480, "activity": "식사"},
                {"name": "청소", "regionId": 0, "locationId": 1, "start": 540, "end": 660, "activity": "청소"},
                {"name": "빨래", "regionId": 0, "locationId": 4, "start": 660, "end": 720, "activity": "빨래"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "청소", "regionId": 0, "locationId": 5, "start": 840, "end": 960, "activity": "청소"},
                {"name": "휴식", "regionId": 0, "locationId": 10, "start": 960, "end": 1080, "activity": "휴식"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "독서", "regionId": 0, "locationId": 1, "start": 1200, "end": 1320, "activity": "휴식"},
                {"name": "수면", "regionId": 0, "locationId": 10, "start": 1320, "end": 360, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
