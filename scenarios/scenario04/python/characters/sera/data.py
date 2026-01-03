# characters/sera/data.py - 세라 캐릭터 정의

CHARACTER_ID = 2

PRESENCE_TEXT = {
    # activity 기반
    "activity:사냥": "{name}가 활을 점검하고 있다.",
    "activity:식사": "{name}가 조용히 식사 중이다.",
    "activity:수면": "{name}가 조용히 잠들어 있다.",
    "activity:휴식": "{name}가 벽에 기대어 쉬고 있다.",

    # 애정도 기반
    "애정:낮음": "{name}가 무표정하게 이쪽을 본다.",
    "애정:중간": "{name}가 살짝 고개를 끄덕인다.",
    "애정:높음": "{name}의 눈빛이 부드러워진다.",
    "애정:최고": "{name}가 희미하게 미소 짓는다.",

    # 장소 기반
    "1:4": "{name}가 사냥감을 추적하고 있다.",  # 사냥터
    "0:1": "{name}가 창가에 서서 밖을 바라본다.",  # 거실

    # 기본값
    "default": "{name}가 과묵하게 서 있다."
}

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "세라",
    "comment": "npc_sera",
    "type": "female",
    "regionId": 0,
    "locationId": 8,  # 세라의 방
    "tags": {
        # 외모
        "외모:흑발": 1,
        "외모:장발": 1,
        "외모:갈색눈": 1,
        # 성격
        "성격:과묵함": 1,
        "성격:듬직함": 1,
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
        "default": "긴 흑발을 묶은 과묵한 여성. 날카로운 갈색 눈이 인상적이다.",
        "기쁨": "표정 변화는 적지만, 눈가가 부드러워졌다.",
        "슬픔": "평소보다 더 말이 없다. 어딘가 먼 곳을 보고 있다.",
        "식사": "조용히 음식을 먹고 있다.",
        "수면": "경계심 없이 잠들어 있다.",
        "사냥": "활을 들고 날카로운 눈으로 주변을 살핀다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 8, "start": 300, "end": 360, "activity": "준비"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 450, "activity": "식사"},
                {"name": "사냥", "regionId": 1, "locationId": 4, "start": 480, "end": 720, "activity": "사냥"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "사냥", "regionId": 1, "locationId": 4, "start": 840, "end": 1080, "activity": "사냥"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "장비정비", "regionId": 0, "locationId": 8, "start": 1200, "end": 1290, "activity": "정비"},
                {"name": "수면", "regionId": 0, "locationId": 8, "start": 1290, "end": 300, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
