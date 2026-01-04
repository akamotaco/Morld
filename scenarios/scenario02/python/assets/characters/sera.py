# assets/characters/sera.py - 세라 캐릭터 Asset

from assets import registry

CHARACTER_ID = 2

PRESENCE_TEXT = {
    # activity 기반
    "activity:사냥": "{name}가 활을 점검하고 있다.",
    "activity:식사": "{name}가 조용히 식사 중이다.",
    "activity:수면": "{name}가 조용히 잠들어 있다.",
    "activity:휴식": "{name}가 벽에 기대어 쉬고 있다.",
    # 장소 기반
    "0:24": "{name}가 사냥감을 추적하고 있다.",
    "0:1": "{name}가 창가에 서서 밖을 바라본다.",
    # 기본값
    "default": "{name}가 과묵하게 서 있다."
}

SERA = {
    "unique_id": "sera",
    "name": "세라",
    "type": "female",
    "tags": {
        "외모:흑발": 1, "외모:장발": 1, "외모:갈색눈": 1,
        "성격:과묵함": 1, "성격:듬직함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 5,
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
                {"name": "사냥", "regionId": 0, "locationId": 24, "start": 480, "end": 720, "activity": "사냥"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "사냥", "regionId": 0, "locationId": 24, "start": 840, "end": 1080, "activity": "사냥"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "장비정비", "regionId": 0, "locationId": 8, "start": 1200, "end": 1290, "activity": "정비"},
                {"name": "수면", "regionId": 0, "locationId": 8, "start": 1290, "end": 300, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
}


def register():
    """세라 Asset 등록"""
    registry.register_character(SERA)


# ========================================
# 이벤트 모듈
# ========================================

class events:
    _flags = {}

    @staticmethod
    def on_meet_player(player_id):
        """플레이어와 처음 만났을 때"""
        import morld

        if events._flags.get("first_meet"):
            return None

        unit_id = registry.get_instance_id("sera")
        if unit_id is None:
            return None

        unit_info = morld.get_unit_info(unit_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        events._flags["first_meet"] = True
        return {
            "type": "monologue",
            "pages": [
                "......",
                "...일어났군.",
                "...세라다. 사냥을 맡고 있다.",
                "...무리하지 마라."
            ],
            "time_consumed": 2,
            "button_type": "ok",
            "freeze_others": True
        }

    @staticmethod
    def npc_talk(context_unit_id):
        """대화"""
        import morld

        unit_info = morld.get_unit_info(context_unit_id)
        if unit_info is None:
            return None

        activity = unit_info.get("activity")
        dialogue = _get_dialogue(activity)

        name = unit_info.get("name", "세라")
        pages = [f"[{name}]"] + dialogue["pages"]

        return {
            "type": "monologue",
            "pages": pages,
            "time_consumed": 1,
            "button_type": "ok"
        }


# ========================================
# 대화 데이터
# ========================================

DIALOGUES = {
    "default": {"pages": ["......", "...할 말이 있으면 빨리."]},
    "식사": {"pages": ["(조용히 먹고 있다)", "...뭔가?"]},
    "수면": {"pages": ["(자고 있다)", "...zzZ"]},
    "사냥": {"pages": ["...조용히 해.", "사냥감이 달아나잖아."]},
    "정비": {"pages": ["...활을 손보는 중이다.", "나중에 와라."]},
    "준비": {"pages": ["...지금 준비 중이다.", "..."]},
}


def _get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]
