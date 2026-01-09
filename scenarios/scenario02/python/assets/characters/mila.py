# assets/characters/mila.py - 밀라 캐릭터 Asset
#
# 사용법:
#   from assets.characters.mila import Mila
#   mila = Mila()
#   mila.instantiate(3, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


# ========================================
# 대화 데이터
# ========================================

DIALOGUES = {
    "default": {"pages": ["안녕하세요!", "뭔가 필요하신 게 있으세요?"]},
    "식사": {"pages": ["맛있게 드셨으면 좋겠어요.", "더 필요하시면 말씀해 주세요!"]},
    "수면": {"pages": ["(자고 있다)", "...zzZ"]},
    "요리": {"pages": ["(요리 중이다)", "잠시만요, 지금 손을 뗄 수가 없어요!"]},
    "설거지": {"pages": ["설거지 중이에요.", "금방 끝날 거예요~"]},
    "정리": {"pages": ["지금 정리 중이에요.", "조금만 기다려 주세요."]},
    "휴식": {"pages": ["후~ 잠시 쉬고 있어요.", "오늘 뭐 드시고 싶은 거 있으세요?"]},
    "준비": {"pages": ["지금 준비 중이에요~", "조금만 기다려 주세요!"]},
}


def _get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]


class Mila(Character):
    unique_id = "mila"
    name = "밀라"
    type = "female"
    props = {
        "외모:갈색머리": 1, "외모:중간머리": 1, "외모:갈색눈": 1,
        "성격:다정함": 1, "성격:걱정많음": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 6,
    }
    actions = ["script:npc_talk:대화", "script:debug_props:속성 보기"]
    mood = []

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

    def get_describe_text(self) -> str:
        """밀라의 현재 상태에 맞는 묘사 텍스트 반환 (장소에 있을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        name = info.get("name", self.name)
        activity = info.get("activity")
        region_id = info.get("region_id")
        location_id = info.get("location_id")

        # activity 기반
        if activity == "요리":
            return f"{name}가 분주하게 요리하고 있다."
        if activity == "식사":
            return f"{name}가 다른 사람들이 먹는 모습을 흐뭇하게 바라본다."
        if activity == "수면":
            return f"{name}가 포근하게 잠들어 있다."
        if activity == "휴식":
            return f"{name}가 따뜻한 차를 마시고 있다."

        # 위치 기반
        if (region_id, location_id) == (0, 2):
            return f"{name}가 요리에 열중하고 있다."
        if (region_id, location_id) == (0, 3):
            return f"{name}가 식탁을 정리하고 있다."

        # 기본
        return f"{name}가 다정한 눈으로 주변을 살핀다."

    def get_focus_text(self) -> str:
        """밀라의 현재 상태에 맞는 묘사 텍스트 반환 (클릭했을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        activity = info.get("activity")
        mood_list = info.get("mood", [])

        # activity 기반
        if activity == "요리":
            return "앞치마를 두르고 열심히 요리하고 있다."
        if activity == "식사":
            return "다른 사람들이 맛있게 먹는지 살피고 있다."
        if activity == "수면":
            return "평화롭게 잠들어 있다."

        # mood 기반
        if "기쁨" in mood_list:
            return "온화하게 웃고 있다. 보는 사람도 기분이 좋아진다."
        if "슬픔" in mood_list:
            return "걱정스러운 표정이다. 무언가 마음에 걸리는 것 같다."

        # 기본
        return "부드러운 갈색 머리의 다정한 여성. 따뜻한 갈색 눈이 편안함을 준다."

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반"""
        import morld

        if self._event_flags.get("first_meet"):
            return None

        # self.instance_id 직접 사용
        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True

        def handler():
            yield morld.dialog([
                "어머, 깨어나셨군요!",
                "저는 밀라예요. 여기서 요리를 맡고 있어요.",
                "많이 힘드셨죠? 기억은... 좀 나세요?",
                "괜찮아요, 천천히 쉬세요. 필요한 게 있으면 말씀해 주세요."
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

@register_agent_class("mila")
class MilaAgent(BaseAgent):
    """
    밀라 AI - 요리 담당

    특징:
    - 다정하고 걱정 많음
    - 식사 시간 근처에는 주방에 반드시 있음
    - 플레이어가 아프면 걱정하며 지켜봄
    """

    SCHEDULE = [
        {"name": "기상", "region_id": 0, "location_id": 9, "start": 300, "end": 360, "activity": "준비"},
        {"name": "아침준비", "region_id": 0, "location_id": 2, "start": 360, "end": 420, "activity": "요리"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 480, "activity": "식사"},
        {"name": "설거지", "region_id": 0, "location_id": 2, "start": 480, "end": 540, "activity": "설거지"},
        {"name": "점심준비", "region_id": 0, "location_id": 2, "start": 660, "end": 720, "activity": "요리"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "휴식", "region_id": 0, "location_id": 1, "start": 840, "end": 960, "activity": "휴식"},
        {"name": "저녁준비", "region_id": 0, "location_id": 2, "start": 1020, "end": 1110, "activity": "요리"},
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "정리", "region_id": 0, "location_id": 2, "start": 1170, "end": 1260, "activity": "정리"},
        {"name": "수면", "region_id": 0, "location_id": 9, "start": 1320, "end": 300, "activity": "수면"},
    ]

    def think(self):
        """밀라의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 커스텀 로직이 필요하면 여기에 추가
        # 예: 플레이어가 아프면 걱정하며 지켜봄

        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
