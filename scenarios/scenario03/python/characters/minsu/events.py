# characters/minsu/events.py - 민수 관련 이벤트

import morld
from characters.minsu.data import CHARACTER_ID
from characters.minsu.dialogues import get_dialogue

# 이벤트 플래그
_flags = {}


def on_meet_player(player_id):
    """플레이어와 처음 만났을 때"""
    if _flags.get("first_meet"):
        return None

    _flags["first_meet"] = True
    return {
        "type": "monologue",
        "pages": [
            "...",
            "(잠깐 쳐다본다)",
            "...민수."
        ],
        "time_consumed": 1,
        "button_type": "ok"
    }


def npc_talk(context_unit_id):
    """대화 스크립트 함수 - script:npc_talk 로 호출됨"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None or unit_info.get("id") != CHARACTER_ID:
        return None

    activity = unit_info.get("activity")
    dialogue = get_dialogue(activity)

    name = unit_info.get("name", "???")
    pages = [f"[{name}]"] + dialogue["pages"]

    return {
        "type": "monologue",
        "pages": pages,
        "time_consumed": 1,
        "button_type": "ok"
    }
