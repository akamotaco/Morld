# characters/lina/events.py - 리나 관련 이벤트

import morld
from characters.lina.data import CHARACTER_ID
from characters.lina.dialogues import get_dialogue

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
            "어? 일어났구나!",
            "나는 리나야! 반가워~",
            "네가 숲에서 쓰러져 있는 걸 우리가 발견했거든.",
            "다행히 큰 부상은 없었어. 푹 쉬어!"
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

    name = unit_info.get("name", "리나")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
