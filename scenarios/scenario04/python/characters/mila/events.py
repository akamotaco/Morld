# characters/mila/events.py - 밀라 관련 이벤트

import morld
from characters.mila.data import CHARACTER_ID
from characters.mila.dialogues import get_dialogue

_flags = {}


def on_meet_player(player_id):
    """플레이어와 처음 만났을 때"""
    if _flags.get("first_meet"):
        return None

    unit_info = morld.get_unit_info(CHARACTER_ID)
    if unit_info and unit_info.get("activity") == "수면":
        return None

    _flags["first_meet"] = True
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


def npc_talk(context_unit_id):
    """대화 스크립트 함수"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None or unit_info.get("id") != CHARACTER_ID:
        return None

    activity = unit_info.get("activity")
    dialogue = get_dialogue(activity)

    name = unit_info.get("name", "밀라")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
