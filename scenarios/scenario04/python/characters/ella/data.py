# characters/ella/data.py - 엘라 캐릭터 정의

CHARACTER_ID = 5

PRESENCE_TEXT = {
    # activity 기반
    "activity:관리": "{name}가 서류를 검토하고 있다.",
    "activity:조회": "{name}가 모두에게 지시를 내리고 있다.",
    "activity:식사": "{name}가 우아하게 식사 중이다.",
    "activity:수면": "{name}가 단정한 자세로 잠들어 있다.",
    "activity:휴식": "{name}가 창밖을 바라보고 있다.",

    # 애정도 기반
    "애정:낮음": "{name}가 날카로운 눈으로 이쪽을 본다.",
    "애정:중간": "{name}가 살짝 관심 있는 눈빛으로 바라본다.",
    "애정:높음": "{name}의 표정이 평소보다 부드럽다.",
    "애정:최고": "{name}가 희미하지만 따뜻한 미소를 짓는다.",

    # 장소 기반
    "0:1": "{name}가 거실 중앙에 서서 상황을 파악하고 있다.",  # 거실
    "0:11": "{name}가 책상에서 서류를 정리하고 있다.",  # 엘라의 방

    # 기본값
    "default": "{name}가 위엄있게 서 있다."
}

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "엘라",
    "comment": "npc_ella",
    "type": "female",
    "regionId": 0,
    "locationId": 11,  # 엘라의 방
    "tags": {
        # 외모
        "외모:흑발": 1,
        "외모:올림머리": 1,
        "외모:보라색눈": 1,
        # 성격
        "성격:냉정함": 1,
        "성격:리더십": 1,
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
        "default": "단정하게 올린 흑발의 위엄있는 여성. 보라색 눈이 냉정해 보인다.",
        "기쁨": "표정 변화는 적지만, 눈빛이 부드러워졌다.",
        "슬픔": "평소보다 더 차가워 보인다. 무언가 생각에 잠겨 있다.",
        "분노": "눈빛이 날카롭다. 함부로 다가가기 어렵다.",
        "식사": "우아하게 식사 중이다.",
        "수면": "단정한 자세로 잠들어 있다.",
        "관리": "서류를 검토하며 무언가 기록하고 있다.",
        "조회": "모두를 둘러보며 하루 일과를 지시하고 있다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 11, "start": 330, "end": 390, "activity": "준비"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 450, "activity": "식사"},
                {"name": "조회", "regionId": 0, "locationId": 1, "start": 450, "end": 510, "activity": "조회"},
                {"name": "관리", "regionId": 0, "locationId": 11, "start": 540, "end": 720, "activity": "관리"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "순찰", "regionId": 0, "locationId": 1, "start": 840, "end": 900, "activity": "순찰"},
                {"name": "관리", "regionId": 0, "locationId": 11, "start": 900, "end": 1080, "activity": "관리"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "휴식", "regionId": 0, "locationId": 11, "start": 1200, "end": 1350, "activity": "휴식"},
                {"name": "수면", "regionId": 0, "locationId": 11, "start": 1380, "end": 330, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
