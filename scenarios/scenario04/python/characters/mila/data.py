# characters/mila/data.py - 밀라 캐릭터 정의

CHARACTER_ID = 3

PRESENCE_TEXT = {
    # activity 기반
    "activity:요리": "{name}가 분주하게 요리하고 있다.",
    "activity:식사": "{name}가 다른 사람들이 먹는 모습을 흐뭇하게 바라본다.",
    "activity:수면": "{name}가 포근하게 잠들어 있다.",
    "activity:휴식": "{name}가 따뜻한 차를 마시고 있다.",

    # 애정도 기반
    "애정:낮음": "{name}가 상냥하게 미소 짓는다.",
    "애정:중간": "{name}가 걱정스러운 눈으로 이쪽을 본다.",
    "애정:높음": "{name}가 다정하게 다가와 안부를 묻는다.",
    "애정:최고": "{name}가 살짝 볼을 붉히며 곁에 선다.",

    # 장소 기반
    "0:2": "{name}가 요리에 열중하고 있다.",  # 주방
    "0:3": "{name}가 식탁을 정리하고 있다.",  # 식당

    # 기본값
    "default": "{name}가 다정한 눈으로 주변을 살핀다."
}

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "밀라",
    "comment": "npc_mila",
    "type": "female",
    "regionId": 0,
    "locationId": 9,  # 밀라의 방
    "tags": {
        # 외모
        "외모:갈색머리": 1,
        "외모:중간머리": 1,
        "외모:갈색눈": 1,
        # 성격
        "성격:다정함": 1,
        "성격:걱정많음": 1,
        # 관계
        "애정": 0,
        "성욕": 0,
        "질투": 0,
        # 상태
        "피로": 0,
        "기분": 6,
    },
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "부드러운 갈색 머리의 다정한 여성. 따뜻한 갈색 눈이 편안함을 준다.",
        "기쁨": "온화하게 웃고 있다. 보는 사람도 기분이 좋아진다.",
        "슬픔": "걱정스러운 표정이다. 무언가 마음에 걸리는 것 같다.",
        "식사": "다른 사람들이 맛있게 먹는지 살피고 있다.",
        "수면": "평화롭게 잠들어 있다.",
        "요리": "앞치마를 두르고 열심히 요리하고 있다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 9, "start": 300, "end": 360, "activity": "준비"},
                {"name": "아침준비", "regionId": 0, "locationId": 2, "start": 360, "end": 420, "activity": "요리"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 480, "activity": "식사"},
                {"name": "설거지", "regionId": 0, "locationId": 2, "start": 480, "end": 540, "activity": "설거지"},
                {"name": "점심준비", "regionId": 0, "locationId": 2, "start": 660, "end": 720, "activity": "요리"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "휴식", "regionId": 0, "locationId": 1, "start": 840, "end": 960, "activity": "휴식"},
                {"name": "저녁준비", "regionId": 0, "locationId": 2, "start": 1020, "end": 1110, "activity": "요리"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "정리", "regionId": 0, "locationId": 2, "start": 1170, "end": 1260, "activity": "정리"},
                {"name": "수면", "regionId": 0, "locationId": 9, "start": 1320, "end": 300, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
