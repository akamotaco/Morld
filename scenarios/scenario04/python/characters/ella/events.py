# characters/ella/events.py - 엘라 관련 이벤트

import morld
from characters.ella.data import CHARACTER_ID
from characters.ella.dialogues import get_dialogue

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


def npc_talk(context_unit_id):
    """대화 스크립트 함수"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None or unit_info.get("id") != CHARACTER_ID:
        return None

    activity = unit_info.get("activity")
    dialogue = get_dialogue(activity)

    name = unit_info.get("name", "엘라")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
