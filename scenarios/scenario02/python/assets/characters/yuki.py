# assets/characters/yuki.py - 유키 캐릭터 Asset
#
# 사용법:
#   from assets.characters.yuki import Yuki
#   yuki = Yuki()
#   yuki_id = morld.create_id("unit")
#   yuki.instantiate(yuki_id, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


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


class Yuki(Character):
    unique_id = "yuki"
    name = "유키"
    type = "female"
    props = {
        "외모:은발": 1, "외모:장발": 1, "외모:붉은눈": 1,
        "성격:수줍음": 1, "성격:얌전함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 5,
    }
    actions = ["call:talk:대화", "call:debug_props:속성 보기"]
    mood = []

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

    def get_describe_text(self) -> str:
        """유키의 현재 상태에 맞는 묘사 텍스트 반환 (장소에 있을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        name = info.get("name", self.name)
        activity = info.get("activity")
        region_id = info.get("region_id")
        location_id = info.get("location_id")

        # activity 기반
        if activity == "청소":
            return f"{name}가 조용히 청소하고 있다."
        if activity == "빨래":
            return f"{name}가 빨래를 널고 있다."
        if activity == "식사":
            return f"{name}가 조용히 식사 중이다."
        if activity == "수면":
            return f"{name}가 새근새근 잠들어 있다."
        if activity == "휴식":
            return f"{name}가 책을 읽고 있다."

        # 위치 기반
        if (region_id, location_id) == (0, 4):
            return f"{name}가 욕실을 청소하고 있다."
        if (region_id, location_id) == (0, 1):
            return f"{name}가 소파 구석에 앉아 책을 읽고 있다."

        # 기본
        return f"{name}가 조용히 서 있다."

    def get_focus_text(self) -> str:
        """유키의 현재 상태에 맞는 묘사 텍스트 반환 (클릭했을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        activity = info.get("activity")
        mood_list = info.get("mood", [])

        # activity 기반
        if activity == "청소":
            return "열심히 청소하고 있다."
        if activity == "빨래":
            return "빨래를 정성스럽게 널고 있다."
        if activity == "식사":
            return "조용히 음식을 먹고 있다."
        if activity == "수면":
            return "새근새근 잠들어 있다. 인형 같다."

        # mood 기반
        if "기쁨" in mood_list:
            return "살짝 볼이 붉어지며 희미하게 웃는다."
        if "슬픔" in mood_list:
            return "고개를 숙이고 있다. 말을 걸기 어려워 보인다."

        # 기본
        return "은빛 긴 머리의 조용한 소녀. 붉은 눈이 신비로운 느낌을 준다."

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반 (묘사 형식)"""
        import morld

        if self._event_flags.get("first_meet"):
            return None

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True

        def handler():
            yield morld.dialog([
                "은빛 머리카락의 소녀가 있다.",
                "낯선 이의 등장에 경계하는 눈빛을 보낸다.",
                "붉은 눈동자가 차갑게 빛난다.",
                "입술을 굳게 다문 채 한 발짝 뒤로 물러선다.",
                "엘라 뒤에 숨듯 서서, 여전히 경계를 풀지 않는다."
            ])

        return handler()

    def talk(self):
        """대화 - Generator 기반 (Character.talk 오버라이드)"""
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

@register_agent_class("yuki")
class YukiAgent(BaseAgent):
    """
    유키 AI - 도심 은신처 생활

    특징:
    - 수줍고 얌전함
    - 은신처에서 조용히 지냄
    - 엘라를 의지함
    """

    # 도심 은신처 스케줄 (region_id=2, location_id=5=은신처)
    SCHEDULE = [
        {"name": "기상", "region_id": 2, "location_id": 5, "start": 420, "end": 480, "activity": "준비"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "start": 480, "end": 540, "activity": "식사"},
        {"name": "청소", "region_id": 2, "location_id": 5, "start": 540, "end": 660, "activity": "청소"},
        {"name": "독서", "region_id": 2, "location_id": 5, "start": 660, "end": 720, "activity": "휴식"},
        {"name": "점심식사", "region_id": 2, "location_id": 5, "start": 720, "end": 780, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "start": 780, "end": 1020, "activity": "휴식"},
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "start": 1080, "end": 1140, "activity": "식사"},
        {"name": "독서", "region_id": 2, "location_id": 5, "start": 1140, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "start": 1320, "end": 420, "activity": "수면"},
    ]

    def think(self):
        """유키의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
