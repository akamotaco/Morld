# characters/cheolsu/data.py - 철수 캐릭터 정의

CHARACTER_ID = 1  # 고유 ID

# 플레이어와 같은 장소에 있을 때 표시되는 텍스트
# 우선순위: activity > location > mood > default
PRESENCE_TEXT = {
    # activity 기반
    "activity:식사": "{name}가 맛있게 밥을 먹고 있다.",
    "activity:수면": "{name}가 깊이 잠들어 있다.",
    "activity:쇼핑": "{name}가 물건을 구경하고 있다.",
    "activity:산책": "{name}가 여유롭게 산책하고 있다.",
    "activity:휴식": "{name}가 편하게 쉬고 있다.",
    "activity:준비": "{name}가 무언가 준비하고 있다.",

    # 장소 기반
    "0:0": "{name}가 집에서 느긋하게 앉아 있다.",
    "0:1": "{name}가 분수대 옆에 서 있다.",
    "0:3": "{name}가 공원 벤치에 앉아 쉬고 있다.",
    "1:0": "{name}가 식당 테이블에 앉아 있다.",
    "1:1": "{name}가 진열대를 구경하고 있다.",

    # mood 기반
    "mood:기쁨": "{name}가 밝은 표정으로 주변을 둘러본다.",
    "mood:슬픔": "{name}가 고개를 숙이고 있다.",

    # 기본값
    "default": "{name}가 주변에 있다."
}

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
