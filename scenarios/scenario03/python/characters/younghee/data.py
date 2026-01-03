# characters/younghee/data.py - 영희 캐릭터 정의

CHARACTER_ID = 2  # 고유 ID

CHARACTER_DATA = {
    "id": CHARACTER_ID,
    "name": "영희",
    "comment": "npc_002",
    "type": "female",
    "regionId": 1,
    "locationId": 1,
    "tags": {},
    "actions": ["script:npc_talk:대화", "trade"],
    "appearance": {
        "default": "단정한 옷차림의 여성이다. 온화한 미소를 띠고 있다.",
        "기쁨": "활짝 웃으며 눈이 초승달처럼 휘어져 있다.",
        "피곤": "눈 밑에 다크서클이 보인다. 하품을 참고 있다.",
        "집중": "입술을 살짝 깨물고 무언가에 몰두하는 표정이다.",
        "식사": "우아하게 식사를 하고 있다.",
        "수면": "고요히 잠들어 있다.",
        "영업": "손님을 맞이할 준비가 되어 있다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 1, "locationId": 1, "start": 300, "end": 360, "activity": "준비"},
                {"name": "상점 오픈 준비", "regionId": 1, "locationId": 2, "start": 360, "end": 420, "activity": "준비"},
                {"name": "상점 근무 (오전)", "regionId": 1, "locationId": 1, "start": 420, "end": 720, "activity": "영업"},
                {"name": "점심시간", "regionId": 1, "locationId": 0, "start": 720, "end": 780, "activity": "식사"},
                {"name": "상점 근무 (오후)", "regionId": 1, "locationId": 1, "start": 780, "end": 1140, "activity": "영업"},
                {"name": "정리/마감", "regionId": 1, "locationId": 2, "start": 1140, "end": 1200, "activity": "정리"},
                {"name": "저녁식사", "regionId": 1, "locationId": 0, "start": 1200, "end": 1260, "activity": "식사"},
                {"name": "수면", "regionId": 1, "locationId": 1, "start": 1320, "end": 300, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}
