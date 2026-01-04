# assets/characters/yuki.py - 유키 캐릭터 Asset
#
# 사용법:
#   from assets.characters.yuki import Yuki
#   yuki = Yuki()
#   yuki.instantiate(4, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


class Yuki(Character):
    unique_id = "yuki"
    name = "유키"
    type = "female"
    tags = {
        "외모:은발": 1, "외모:장발": 1, "외모:붉은눈": 1,
        "성격:수줍음": 1, "성격:얌전함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 5,
    }
    actions = ["script:npc_talk:대화"]
    appearance = {
        "default": "은빛 긴 머리의 조용한 소녀. 붉은 눈이 신비로운 느낌을 준다.",
        "기쁨": "살짝 볼이 붉어지며 희미하게 웃는다.",
        "슬픔": "고개를 숙이고 있다. 말을 걸기 어려워 보인다.",
        "식사": "조용히 음식을 먹고 있다.",
        "수면": "새근새근 잠들어 있다. 인형 같다.",
        "청소": "열심히 청소하고 있다.",
        "빨래": "빨래를 정성스럽게 널고 있다."
    }
    mood = []
    schedule_stack = [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 10, "start": 360, "end": 420, "activity": "준비"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 480, "activity": "식사"},
                {"name": "청소", "regionId": 0, "locationId": 1, "start": 540, "end": 660, "activity": "청소"},
                {"name": "빨래", "regionId": 0, "locationId": 4, "start": 660, "end": 720, "activity": "빨래"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "청소", "regionId": 0, "locationId": 5, "start": 840, "end": 960, "activity": "청소"},
                {"name": "휴식", "regionId": 0, "locationId": 10, "start": 960, "end": 1080, "activity": "휴식"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "독서", "regionId": 0, "locationId": 1, "start": 1200, "end": 1320, "activity": "휴식"},
                {"name": "수면", "regionId": 0, "locationId": 10, "start": 1320, "end": 360, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]


# ========================================
# Presence Text (위치 기반 묘사)
# ========================================

PRESENCE_TEXT = {
    "activity:청소": "{name}가 조용히 청소하고 있다.",
    "activity:빨래": "{name}가 빨래를 널고 있다.",
    "activity:식사": "{name}가 조용히 식사 중이다.",
    "activity:수면": "{name}가 새근새근 잠들어 있다.",
    "activity:휴식": "{name}가 책을 읽고 있다.",
    "0:4": "{name}가 욕실을 청소하고 있다.",
    "0:1": "{name}가 소파 구석에 앉아 책을 읽고 있다.",
    "default": "{name}가 조용히 서 있다."
}


# ========================================
# 대화 데이터
# ========================================

DIALOGUES = {
    "default": {"pages": ["...네?", "...무슨 일이세요...?"]},
    "식사": {"pages": ["(조용히 먹고 있다)", "...맛있어요..."]},
    "수면": {"pages": ["(자고 있다)", "...zzZ"]},
    "청소": {"pages": ["...청소 중이에요...", "..."]},
    "빨래": {"pages": ["...빨래를 널고 있어요...", "...조금만 기다려 주세요..."]},
    "휴식": {"pages": ["(책을 읽고 있다)", "...아, 네..."]},
    "준비": {"pages": ["...지금 준비 중이에요...", "..."]},
}


def _get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]


# ========================================
# 이벤트 모듈
# ========================================

class events:
    _flags = {}

    @staticmethod
    def on_meet_player(player_id):
        """플레이어와 처음 만났을 때"""
        import morld
        from assets import get_instance_id

        if events._flags.get("first_meet"):
            return None

        unit_id = get_instance_id("yuki")
        if unit_id is None:
            return None

        unit_info = morld.get_unit_info(unit_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        events._flags["first_meet"] = True
        return {
            "type": "monologue",
            "pages": [
                "...!",
                "...깨어나셨군요.",
                "...유키... 라고 해요.",
                "...필요한 게 있으면... 말해주세요...",
                "(살짝 고개를 숙이고 물러난다)"
            ],
            "time_consumed": 2,
            "button_type": "ok"
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

        name = unit_info.get("name", "유키")
        pages = [f"[{name}]"] + dialogue["pages"]

        return {
            "type": "monologue",
            "pages": pages,
            "time_consumed": 1,
            "button_type": "ok"
        }


# ========================================
# AI Agent
# ========================================

@register_agent_class("yuki")
class YukiAgent(BaseAgent):
    """
    유키 AI - 청소/빨래 담당

    특징:
    - 수줍고 얌전함
    - 스케줄을 묵묵히 따름
    - 플레이어와 마주치면 수줍어함
    """

    def think(self):
        """유키의 행동 결정"""
        info = self.get_info()
        if info is None:
            return None

        entry = self.get_schedule_entry()
        if entry is None:
            return None

        loc = self.get_location()
        if loc is None:
            return None

        target_region = entry["region_id"]
        target_loc = entry["location_id"]
        if loc[0] == target_region and loc[1] == target_loc:
            return None

        path = self.find_path(target_region, target_loc)
        if path:
            self.set_route(path)

        return path
