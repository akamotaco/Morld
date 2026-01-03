# characters/minsu/data.py - 민수 캐릭터 정의

CHARACTER_ID = 3  # 고유 ID

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "민수",
    "comment": "npc_003",
    "type": "male",
    "regionId": 0,
    "locationId": 2,
    "tags": {
        "열쇠": 1
    },
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "수수한 차림의 청년이다. 무표정한 얼굴이다.",
        "식사": "묵묵히 음식을 먹고 있다.",
        "수면": "깊이 잠들어 있다.",
        "휴식": "조용히 앉아 있다.",
        "작업": "무언가 작업에 몰두하고 있다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "수면", "regionId": 0, "locationId": 2, "start": 1380, "end": 480, "activity": "수면"},
                {"name": "아침식사", "regionId": 1, "locationId": 0, "start": 480, "end": 540, "activity": "식사"},
                {"name": "우물에서 물긷기", "regionId": 0, "locationId": 4, "start": 600, "end": 660, "activity": "작업"},
                {"name": "점심식사", "regionId": 1, "locationId": 0, "start": 720, "end": 780, "activity": "식사"},
                {"name": "광장에서 휴식", "regionId": 0, "locationId": 1, "start": 840, "end": 1020, "activity": "휴식"},
                {"name": "저녁식사", "regionId": 1, "locationId": 0, "start": 1080, "end": 1140, "activity": "식사"},
                {"name": "귀가", "regionId": 0, "locationId": 2, "start": 1200, "end": 1380, "activity": "휴식"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
