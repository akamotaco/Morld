# assets/characters/ella.py - 엘라 캐릭터 Asset
#
# 사용법:
#   from assets.characters.ella import Ella
#   ella = Ella()
#   ella.instantiate(5, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


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


class Ella(Character):
    unique_id = "ella"
    name = "엘라"
    type = "female"
    props = {
        "외모:흑발": 1, "외모:올림머리": 1, "외모:보라색눈": 1,
        "성격:냉정함": 1, "성격:리더십": 1,
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
        """엘라의 현재 상태에 맞는 묘사 텍스트 반환 (장소에 있을 때)"""
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

    def get_focus_text(self) -> str:
        """엘라의 현재 상태에 맞는 묘사 텍스트 반환 (클릭했을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        activity = info.get("activity")
        mood_list = info.get("mood", [])

        # activity 기반
        if activity == "관리":
            return "서류를 검토하며 무언가 기록하고 있다."
        if activity == "조회":
            return "모두를 둘러보며 하루 일과를 지시하고 있다."
        if activity == "식사":
            return "우아하게 식사 중이다."
        if activity == "수면":
            return "단정한 자세로 잠들어 있다."

        # mood 기반
        if "기쁨" in mood_list:
            return "표정 변화는 적지만, 눈빛이 부드러워졌다."
        if "슬픔" in mood_list:
            return "평소보다 더 차가워 보인다. 무언가 생각에 잠겨 있다."
        if "분노" in mood_list:
            return "눈빛이 날카롭다. 함부로 다가가기 어렵다."

        # 기본
        return "단정하게 올린 흑발의 위엄있는 여성. 보라색 눈이 냉정해 보인다."

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반"""
        import morld

        if self._event_flags.get("first_meet"):
            return None

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True

        def handler():
            yield morld.dialog([
                "...깨어났군.",
                "나는 엘라. 이 저택을 관리하고 있다.",
                "네가 숲에서 쓰러져 있는 걸 발견한 건 이틀 전이다.",
                "기억을 잃었다고 들었다. 불쌍하군.",
                "당분간 여기서 지내도 좋다.",
                "단, 규칙은 지켜라. 모두의 안전이 달려 있으니까."
            ])

        return handler()

    def npc_talk(self, player_id):
        """대화 - Generator 기반"""
        import morld

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info is None:
            return

        activity = unit_info.get("activity")
        dialogue = _get_dialogue(activity)

        name = unit_info.get("name", self.name)
        pages = [f"[{name}]"] + dialogue["pages"]

        yield morld.dialog(pages)


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

    SCHEDULE = [
        {"name": "기상", "region_id": 0, "location_id": 11, "start": 330, "end": 390, "activity": "준비"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 450, "activity": "식사"},
        {"name": "조회", "region_id": 0, "location_id": 1, "start": 450, "end": 510, "activity": "조회"},
        {"name": "관리", "region_id": 0, "location_id": 11, "start": 540, "end": 720, "activity": "관리"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "순찰", "region_id": 0, "location_id": 1, "start": 840, "end": 900, "activity": "순찰"},
        {"name": "관리", "region_id": 0, "location_id": 11, "start": 900, "end": 1080, "activity": "관리"},
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "휴식", "region_id": 0, "location_id": 11, "start": 1200, "end": 1350, "activity": "휴식"},
        {"name": "수면", "region_id": 0, "location_id": 11, "start": 1380, "end": 330, "activity": "수면"},
    ]

    def think(self):
        """엘라의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 커스텀 로직이 필요하면 여기에 추가
        # 예: 저택 전체를 관리하며 순찰

        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
