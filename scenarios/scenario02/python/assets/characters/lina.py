# assets/characters/lina.py - 리나 캐릭터 Asset
#
# 사용법:
#   from assets.characters.lina import Lina
#   lina = Lina()
#   lina.instantiate(1, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


# ========================================
# 대화 데이터
# ========================================

DIALOGUES = {
    "default": {"pages": ["응? 뭐야뭐야?", "...심심한 거야? 나도 좀 심심했는데!"]},
    "식사": {"pages": ["(맛있게 먹고 있다)", "냠냠... 뭐야?"]},
    "수면": {"pages": ["(자고 있다)", "...zzZ"]},
    "채집": {"pages": ["지금 채집 중이야!", "조금만 기다려~"]},
    "휴식": {"pages": ["후아~ 오늘 피곤하다~", "...뭐야, 나도 놀아줄까?"]},
    "준비": {"pages": ["잠깐만! 준비 중이야!", "..."]},
}


def _get_dialogue(activity):
    """activity에 맞는 대화 반환"""
    if activity and activity in DIALOGUES:
        return DIALOGUES[activity]
    return DIALOGUES["default"]


class Lina(Character):
    unique_id = "lina"
    name = "리나"
    type = "female"
    props = {
        "외모:금발": 1, "외모:단발": 1, "외모:녹색눈": 1,
        "성격:명랑함": 1, "성격:활발함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 7,
    }
    actions = ["script:npc_talk:대화"]
    mood = []

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

    def get_describe_text(self) -> str:
        """리나의 현재 상태에 맞는 묘사 텍스트 반환 (장소에 있을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        name = info.get("name", self.name)
        activity = info.get("activity")
        region_id = info.get("region_id")
        location_id = info.get("location_id")

        # activity 기반
        if activity == "채집":
            return f"{name}가 채집 준비를 하고 있다."
        if activity == "식사":
            return f"{name}가 맛있게 밥을 먹고 있다."
        if activity == "수면":
            return f"{name}가 새근새근 잠들어 있다."
        if activity == "휴식":
            return f"{name}가 기지개를 켜며 쉬고 있다."

        # 위치 기반
        if (region_id, location_id) == (0, 23):
            return f"{name}가 열매를 따고 있다."
        if (region_id, location_id) == (0, 1):
            return f"{name}가 소파에 앉아 발을 흔들고 있다."

        # 기본
        return f"{name}가 밝은 표정으로 주변을 둘러본다."

    def get_focus_text(self) -> str:
        """리나의 현재 상태에 맞는 묘사 텍스트 반환 (클릭했을 때)"""
        import morld

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return ""

        activity = info.get("activity")
        mood_list = info.get("mood", [])

        # activity 기반
        if activity == "채집":
            return "바구니를 들고 열심히 열매를 따고 있다."
        if activity == "식사":
            return "맛있게 음식을 먹고 있다."
        if activity == "수면":
            return "새근새근 잠들어 있다. 평화로운 얼굴이다."

        # mood 기반
        if "기쁨" in mood_list:
            return "환하게 웃고 있다. 에너지가 넘쳐 보인다."
        if "슬픔" in mood_list:
            return "평소와 달리 기운이 없어 보인다."

        # 기본
        return "밝은 금발 단발머리의 활기찬 소녀. 녹색 눈이 반짝인다."

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
        instance_id = self.instance_id

        def handler():
            yield morld.dialog([
                "안녕! 넌 누구야?",
                "처음 보는 얼굴인데... 혹시 밖에서 온 거야?",
                "나는 리나! 여기서 채집을 맡고 있어!",
                "앞으로 잘 지내자~!"
            ])
            # 다이얼로그 후 플레이어 따라다니기
            morld.set_npc_job(instance_id, "follow", 30, player_id)

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

@register_agent_class("lina")
class LinaAgent(BaseAgent):
    """
    리나 AI - 채집 담당

    특징:
    - 활발하고 명랑함
    - 날씨가 좋으면 일찍 채집터로
    - 플레이어 호감도 높으면 근처에 머무름
    """

    SCHEDULE = [
        {"name": "기상", "region_id": 0, "location_id": 7, "start": 360, "end": 390, "activity": "준비"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 480, "activity": "식사"},
        {"name": "채집", "region_id": 0, "location_id": 23, "start": 540, "end": 720, "activity": "채집"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "채집", "region_id": 0, "location_id": 23, "start": 840, "end": 1020, "activity": "채집"},
        {"name": "귀가", "region_id": 0, "location_id": 1, "start": 1080, "end": 1110, "activity": "휴식"},
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "자유시간", "region_id": 0, "location_id": 1, "start": 1170, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 0, "location_id": 7, "start": 1320, "end": 360, "activity": "수면"},
    ]

    def think(self):
        """리나의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 커스텀 로직이 필요하면 여기에 추가
        # 예: 날씨가 좋으면 일찍 채집터로

        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
