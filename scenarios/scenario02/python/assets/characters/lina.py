# assets/characters/lina.py - 리나 캐릭터 Asset

from assets import registry

CHARACTER_ID = 1

PRESENCE_TEXT = {
    "activity:채집": "{name}가 채집 준비를 하고 있다.",
    "activity:식사": "{name}가 맛있게 밥을 먹고 있다.",
    "activity:수면": "{name}가 새근새근 잠들어 있다.",
    "activity:휴식": "{name}가 기지개를 켜며 쉬고 있다.",
    "0:23": "{name}가 열매를 따고 있다.",
    "0:1": "{name}가 소파에 앉아 발을 흔들고 있다.",
    "default": "{name}가 밝은 표정으로 주변을 둘러본다."
}

LINA = {
    "unique_id": "lina",
    "name": "리나",
    "type": "female",
    "tags": {
        "외모:금발": 1, "외모:단발": 1, "외모:녹색눈": 1,
        "성격:명랑함": 1, "성격:활발함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 7,
    },
    "actions": ["script:npc_talk:대화"],
    "appearance": {
        "default": "밝은 금발 단발머리의 활기찬 소녀. 녹색 눈이 반짝인다.",
        "기쁨": "환하게 웃고 있다. 에너지가 넘쳐 보인다.",
        "슬픔": "평소와 달리 기운이 없어 보인다.",
        "식사": "맛있게 음식을 먹고 있다.",
        "수면": "새근새근 잠들어 있다. 평화로운 얼굴이다.",
        "채집": "바구니를 들고 열심히 열매를 따고 있다."
    },
    "mood": [],
    "scheduleStack": [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 7, "start": 360, "end": 390, "activity": "준비"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 480, "activity": "식사"},
                {"name": "채집", "regionId": 0, "locationId": 23, "start": 540, "end": 720, "activity": "채집"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "채집", "regionId": 0, "locationId": 23, "start": 840, "end": 1020, "activity": "채집"},
                {"name": "귀가", "regionId": 0, "locationId": 1, "start": 1080, "end": 1110, "activity": "휴식"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "자유시간", "regionId": 0, "locationId": 1, "start": 1170, "end": 1320, "activity": "휴식"},
                {"name": "수면", "regionId": 0, "locationId": 7, "start": 1320, "end": 360, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}


def register():
    """리나 Asset 등록"""
    registry.register_character(LINA)


# ========================================
# 이벤트 모듈
# ========================================

class events:
    @staticmethod
    def on_meet_player(player_id):
        """플레이어와 만남"""
        return {
            "type": "monologue",
            "pages": ["[리나]", "안녕! 넌 누구야?", "처음 보는 얼굴인데... 혹시 밖에서 온 거야?"],
            "time_consumed": 2,
            "button_type": "ok",
            "freeze_others": True
        }

    @staticmethod
    def npc_talk(context_unit_id):
        """대화"""
        return {
            "type": "monologue",
            "pages": ["[리나]", "응? 뭐야뭐야?", "...심심한 거야? 나도 좀 심심했는데!"],
            "time_consumed": 3,
            "button_type": "ok"
        }
