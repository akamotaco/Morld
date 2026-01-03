# characters/player/data.py - 플레이어 캐릭터 정의

CHARACTER_ID = 0  # 고유 ID

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "플레이어",
    "comment": "player",
    "type": "male",
    "regionId": 0,
    "locationId": 0,
    "tags": {
        "관찰": 3,
        "힘": 5
    },
    "actions": ["rest", "sleep", "wait"],
    "scheduleStack": [
        {
            "name": "대기",
            "schedule": [],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
