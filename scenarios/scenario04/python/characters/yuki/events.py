# characters/yuki/events.py - 유키 관련 이벤트

import morld
from characters.yuki.data import CHARACTER_ID
from characters.yuki.dialogues import get_dialogue

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
            "...!",
            "...깨어나셨군요.",
            "...유키... 라고 해요.",
            "...필요한 게 있으면... 말해주세요...",
            "(살짝 고개를 숙이고 물러난다)"
        ],
        "time_consumed": 2,
        "button_type": "ok"
    }


def npc_talk(context_unit_id):
    """대화 스크립트 함수"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None or unit_info.get("id") != CHARACTER_ID:
        return None

    activity = unit_info.get("activity")
    dialogue = get_dialogue(activity)

    name = unit_info.get("name", "유키")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
