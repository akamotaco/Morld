# characters/younghee/events.py - 영희 관련 이벤트

import morld
from characters.younghee.data import CHARACTER_ID
from characters.younghee.dialogues import get_dialogue

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
            "어머, 처음 뵙는 분이네요.",
            "저는 이 잡화상점을 운영하는 영희라고 해요.",
            "필요한 물건이 있으시면 언제든 말씀해주세요!"
        ],
        "time_consumed": 2,
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
