# assets/characters/mila.py - 밀라 캐릭터 Asset
#
# 사용법:
#   from assets.characters.mila import Mila
#   mila = Mila()
#   mila.instantiate(3, REGION_ID, location_id)

from assets.base import Character
from think import BaseAgent, register_agent_class


class Mila(Character):
    unique_id = "mila"
    name = "밀라"
    type = "female"
    tags = {
        "외모:갈색머리": 1, "외모:중간머리": 1, "외모:갈색눈": 1,
        "성격:다정함": 1, "성격:걱정많음": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 6,
    }
    actions = ["script:npc_talk:대화"]
    appearance = {
        "default": "부드러운 갈색 머리의 다정한 여성. 따뜻한 갈색 눈이 편안함을 준다.",
        "기쁨": "온화하게 웃고 있다. 보는 사람도 기분이 좋아진다.",
        "슬픔": "걱정스러운 표정이다. 무언가 마음에 걸리는 것 같다.",
        "식사": "다른 사람들이 맛있게 먹는지 살피고 있다.",
        "수면": "평화롭게 잠들어 있다.",
        "요리": "앞치마를 두르고 열심히 요리하고 있다."
    }
    mood = []
    schedule_stack = [
        {
            "name": "일상",
            "schedule": [
                {"name": "기상", "regionId": 0, "locationId": 9, "start": 300, "end": 360, "activity": "준비"},
                {"name": "아침준비", "regionId": 0, "locationId": 2, "start": 360, "end": 420, "activity": "요리"},
                {"name": "아침식사", "regionId": 0, "locationId": 3, "start": 420, "end": 480, "activity": "식사"},
                {"name": "설거지", "regionId": 0, "locationId": 2, "start": 480, "end": 540, "activity": "설거지"},
                {"name": "점심준비", "regionId": 0, "locationId": 2, "start": 660, "end": 720, "activity": "요리"},
                {"name": "점심식사", "regionId": 0, "locationId": 3, "start": 720, "end": 780, "activity": "식사"},
                {"name": "휴식", "regionId": 0, "locationId": 1, "start": 840, "end": 960, "activity": "휴식"},
                {"name": "저녁준비", "regionId": 0, "locationId": 2, "start": 1020, "end": 1110, "activity": "요리"},
                {"name": "저녁식사", "regionId": 0, "locationId": 3, "start": 1110, "end": 1170, "activity": "식사"},
                {"name": "정리", "regionId": 0, "locationId": 2, "start": 1170, "end": 1260, "activity": "정리"},
                {"name": "수면", "regionId": 0, "locationId": 9, "start": 1320, "end": 300, "activity": "수면"}
            ],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]


# ========================================
# Presence Text (위치 기반 묘사)
# ========================================

PRESENCE_TEXT = {
    "activity:요리": "{name}가 분주하게 요리하고 있다.",
    "activity:식사": "{name}가 다른 사람들이 먹는 모습을 흐뭇하게 바라본다.",
    "activity:수면": "{name}가 포근하게 잠들어 있다.",
    "activity:휴식": "{name}가 따뜻한 차를 마시고 있다.",
    "0:2": "{name}가 요리에 열중하고 있다.",
    "0:3": "{name}가 식탁을 정리하고 있다.",
    "default": "{name}가 다정한 눈으로 주변을 살핀다."
}


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

        unit_id = get_instance_id("mila")
        if unit_id is None:
            return None

        unit_info = morld.get_unit_info(unit_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        events._flags["first_meet"] = True
        return {
            "type": "monologue",
            "pages": [
                "어머, 깨어나셨군요!",
                "저는 밀라예요. 여기서 요리를 맡고 있어요.",
                "많이 힘드셨죠? 기억은... 좀 나세요?",
                "괜찮아요, 천천히 쉬세요. 필요한 게 있으면 말씀해 주세요."
            ],
            "time_consumed": 3,
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

        name = unit_info.get("name", "밀라")
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

@register_agent_class("mila")
class MilaAgent(BaseAgent):
    """
    밀라 AI - 요리 담당

    특징:
    - 다정하고 걱정 많음
    - 식사 시간 근처에는 주방에 반드시 있음
    - 플레이어가 아프면 걱정하며 지켜봄
    """

    def think(self):
        """밀라의 행동 결정"""
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
