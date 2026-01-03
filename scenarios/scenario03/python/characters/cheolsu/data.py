# characters/cheolsu/data.py - 철수 캐릭터 정의

CHARACTER_ID = 1  # 고유 ID

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "철수",
    "comment": "npc_001",
    "type": "male",
    "regionId": 0,
    "locationId": 0,
    "tags": {},
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "평범한 청년이다. 차분한 표정을 짓고 있다.",
        "기쁨": "환하게 웃고 있다. 기분이 좋아 보인다.",
        "슬픔": "어깨가 축 처져 있고 눈가가 촉촉하다.",
        "분노": "눈썹이 찌푸려져 있고 주먹을 불끈 쥐고 있다.",
        "긴장": "눈동자가 불안하게 흔들린다.",
        "기쁨,긴장": "들뜬 표정이지만 어딘가 불안해 보인다.",
        "식사": "맛있게 음식을 먹고 있다.",
        "수면": "편안하게 잠들어 있다."
    },
    "mood": ["기쁨"],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상/준비", "regionId": 0, "locationId": 0, "start": 360, "end": 420, "activity": "준비"},
                {"name": "아침식사", "regionId": 1, "locationId": 0, "start": 420, "end": 480, "activity": "식사"},
                {"name": "상점 방문", "regionId": 1, "locationId": 1, "start": 540, "end": 720, "activity": "쇼핑"},
                {"name": "점심식사", "regionId": 1, "locationId": 0, "start": 720, "end": 780, "activity": "식사"},
                {"name": "공원 산책", "regionId": 0, "locationId": 3, "start": 840, "end": 1020, "activity": "산책"},
                {"name": "저녁식사", "regionId": 1, "locationId": 0, "start": 1080, "end": 1140, "activity": "식사"},
                {"name": "귀가/휴식", "regionId": 0, "locationId": 0, "start": 1200, "end": 1320, "activity": "휴식"},
                {"name": "수면", "regionId": 0, "locationId": 0, "start": 1320, "end": 360, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
