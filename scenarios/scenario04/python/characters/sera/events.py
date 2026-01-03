# characters/sera/events.py - 세라 관련 이벤트

import morld
from characters.sera.data import CHARACTER_ID
from characters.sera.dialogues import get_dialogue

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
            "......",
            "...일어났군.",
            "...세라다. 사냥을 맡고 있다.",
            "...무리하지 마라."
        ],
        "time_consumed": 2,
        "button_type": "ok",
        "freeze_others": True  # 대화 중 NPC들이 떠나지 않도록
    }


def npc_talk(context_unit_id):
    """대화 스크립트 함수"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None or unit_info.get("id") != CHARACTER_ID:
        return None

    activity = unit_info.get("activity")
    dialogue = get_dialogue(activity)

    name = unit_info.get("name", "세라")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
