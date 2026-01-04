# assets/characters/ella.py - 엘라 캐릭터 Asset
#
# 사용법:
#   from assets.characters.ella import Ella
#   ella = Ella()
#   ella.instantiate(5, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


class Ella(Character):
    unique_id = "ella"
    name = "엘라"
    type = "female"
    tags = {
        "외모:흑발": 1, "외모:올림머리": 1, "외모:보라색눈": 1,
        "성격:냉정함": 1, "성격:리더십": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 5,
    }
    actions = ["script:npc_talk:대화"]
    appearance = {
        "default": "단정하게 올린 흑발의 위엄있는 여성. 보라색 눈이 냉정해 보인다.",
        "기쁨": "표정 변화는 적지만, 눈빛이 부드러워졌다.",
        "슬픔": "평소보다 더 차가워 보인다. 무언가 생각에 잠겨 있다.",
        "분노": "눈빛이 날카롭다. 함부로 다가가기 어렵다.",
        "식사": "우아하게 식사 중이다.",
        "수면": "단정한 자세로 잠들어 있다.",
        "관리": "서류를 검토하며 무언가 기록하고 있다.",
        "조회": "모두를 둘러보며 하루 일과를 지시하고 있다."
    }
    mood = []
    schedule_stack = [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 11, "start": 330, "end": 390, "activity": "준비"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 450, "activity": "식사"},
                {"name": "조회", "regionId": 0, "locationId": 1, "start": 450, "end": 510, "activity": "조회"},
                {"name": "관리", "regionId": 0, "locationId": 11, "start": 540, "end": 720, "activity": "관리"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "순찰", "regionId": 0, "locationId": 1, "start": 840, "end": 900, "activity": "순찰"},
                {"name": "관리", "regionId": 0, "locationId": 11, "start": 900, "end": 1080, "activity": "관리"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "휴식", "regionId": 0, "locationId": 11, "start": 1200, "end": 1350, "activity": "휴식"},
                {"name": "수면", "regionId": 0, "locationId": 11, "start": 1380, "end": 330, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]

    def get_describe_text(self) -> str:
        """엘라의 현재 상태에 맞는 묘사 텍스트 반환"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        name = info.get("name", self.name)
        activity = info.get("activity")
        region_id = info.get("region_id")
        location_id = info.get("location_id")

        # activity 기반
        if activity == "관리":
            return f"{name}가 서류를 검토하고 있다."
        if activity == "조회":
            return f"{name}가 모두에게 지시를 내리고 있다."
        if activity == "식사":
            return f"{name}가 우아하게 식사 중이다."
        if activity == "수면":
            return f"{name}가 단정한 자세로 잠들어 있다."
        if activity == "휴식":
            return f"{name}가 창밖을 바라보고 있다."

        # 위치 기반
        if (region_id, location_id) == (0, 1):
            return f"{name}가 거실 중앙에 서서 상황을 파악하고 있다."
        if (region_id, location_id) == (0, 11):
            return f"{name}가 책상에서 서류를 정리하고 있다."

        # 기본
        return f"{name}가 위엄있게 서 있다."


# ========================================
# 대화 데이터
# ========================================

DIALOGUES = {
    "default": {"pages": ["무슨 용건이냐?", "...간단히 말해라."]},
    "식사": {"pages": ["(식사 중이다)", "...나중에 와라."]},
    "수면": {"pages": ["(자고 있다)", "...zzZ"]},
    "관리": {"pages": ["지금 바쁘다.", "...급한 일이 아니라면 나중에 와라."]},
    "조회": {"pages": ["지금 조회 중이다.", "잠시 기다려라."]},
    "순찰": {"pages": ["순찰 중이다.", "무슨 일이냐?"]},
    "휴식": {"pages": ["......", "무슨 일이냐?"]},
    "준비": {"pages": ["지금 준비 중이다.", "잠시 후에 와라."]},
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

        unit_id = get_instance_id("ella")
        if unit_id is None:
            return None

        unit_info = morld.get_unit_info(unit_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        events._flags["first_meet"] = True
        return {
            "type": "monologue",
            "pages": [
                "...깨어났군.",
                "나는 엘라. 이 저택을 관리하고 있다.",
                "네가 숲에서 쓰러져 있는 걸 발견한 건 이틀 전이다.",
                "기억을 잃었다고 들었다. 불쌍하군.",
                "당분간 여기서 지내도 좋다.",
                "단, 규칙은 지켜라. 모두의 안전이 달려 있으니까."
            ],
            "time_consumed": 5,
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

        name = unit_info.get("name", "엘라")
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

@register_agent_class("ella")
class EllaAgent(BaseAgent):
    """
    엘라 AI - 관리자

    특징:
    - 냉정하고 리더십 있음
    - 스케줄을 엄격히 준수
    - 저택 전체를 관리하며 순찰
    """

    def think(self):
        """엘라의 행동 결정"""
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
