# assets/characters/sera.py - 세라 캐릭터 Asset
#
# 사용법:
#   from assets.characters.sera import Sera
#   sera = Sera()
#   sera.instantiate(2, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


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


class Sera(Character):
    unique_id = "sera"
    name = "세라"
    type = "female"
    tags = {
        "외모:흑발": 1, "외모:장발": 1, "외모:갈색눈": 1,
        "성격:과묵함": 1, "성격:듬직함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 5,
    }
    actions = ["script:npc_talk:대화"]
    mood = []

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

    def get_describe_text(self) -> str:
        """세라의 현재 상태에 맞는 묘사 텍스트 반환 (장소에 있을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        name = info.get("name", self.name)
        activity = info.get("activity")
        region_id = info.get("region_id")
        location_id = info.get("location_id")

        # activity 기반
        if activity == "사냥":
            return f"{name}가 활을 점검하고 있다."
        if activity == "식사":
            return f"{name}가 조용히 식사 중이다."
        if activity == "수면":
            return f"{name}가 조용히 잠들어 있다."
        if activity == "휴식":
            return f"{name}가 벽에 기대어 쉬고 있다."

        # 위치 기반
        if (region_id, location_id) == (0, 24):
            return f"{name}가 사냥감을 추적하고 있다."
        if (region_id, location_id) == (0, 1):
            return f"{name}가 창가에 서서 밖을 바라본다."

        # 기본
        return f"{name}가 과묵하게 서 있다."

    def get_focus_text(self) -> str:
        """세라의 현재 상태에 맞는 묘사 텍스트 반환 (클릭했을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        activity = info.get("activity")
        mood_list = info.get("mood", [])

        # activity 기반
        if activity == "사냥":
            return "활을 들고 날카로운 눈으로 주변을 살핀다."
        if activity == "식사":
            return "조용히 음식을 먹고 있다."
        if activity == "수면":
            return "경계심 없이 잠들어 있다."

        # mood 기반
        if "기쁨" in mood_list:
            return "표정 변화는 적지만, 눈가가 부드러워졌다."
        if "슬픔" in mood_list:
            return "평소보다 더 말이 없다. 어딘가 먼 곳을 보고 있다."

        # 기본
        return "긴 흑발을 묶은 과묵한 여성. 날카로운 갈색 눈이 인상적이다."

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때"""
        import morld

        if self._event_flags.get("first_meet"):
            return None

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True
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
            "npc_jobs": {self.instance_id: {"action": "follow", "duration": 2}}
        }

    def npc_talk(self, player_id):
        """대화"""
        import morld

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info is None:
            return None

        activity = unit_info.get("activity")
        dialogue = _get_dialogue(activity)

        name = unit_info.get("name", self.name)
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

@register_agent_class("sera")
class SeraAgent(BaseAgent):
    """
    세라 AI - 사냥 담당

    특징:
    - 과묵하고 듬직함
    - 사냥에 집중, 스케줄을 철저히 따름
    - 플레이어에게 무관심하지만 위험시 보호
    """

    SCHEDULE = [
        {"name": "기상", "region_id": 0, "location_id": 8, "start": 300, "end": 360, "activity": "준비"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 450, "activity": "식사"},
        {"name": "사냥", "region_id": 0, "location_id": 24, "start": 480, "end": 720, "activity": "사냥"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "사냥", "region_id": 0, "location_id": 24, "start": 840, "end": 1080, "activity": "사냥"},
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "장비정비", "region_id": 0, "location_id": 8, "start": 1200, "end": 1290, "activity": "정비"},
        {"name": "수면", "region_id": 0, "location_id": 8, "start": 1290, "end": 300, "activity": "수면"},
    ]

    def think(self):
        """세라의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 커스텀 로직이 필요하면 여기에 추가
        # 예: 플레이어가 위험하면 보호하러 가기

        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
