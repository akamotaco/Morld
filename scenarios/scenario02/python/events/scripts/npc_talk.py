# events/scripts/npc_talk.py - NPC 대화 스크립트 함수

import morld
from assets.characters import get_character_event_handler


@morld.register_script
def npc_talk(context_unit_id):
    """NPC 대화"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None:
        return {
            "type": "monologue",
            "pages": ["...?"],
            "time_consumed": 1,
            "button_type": "ok"
        }

    unit_id = unit_info.get("id")
    handler = get_character_event_handler(unit_id)

    if handler and hasattr(handler, "npc_talk"):
        return handler.npc_talk(context_unit_id)

    name = unit_info.get("name", "???")
    return {
        "type": "monologue",
        "pages": [f"[{name}]", "......", "별 말이 없다."],
        "time_consumed": 1,
        "button_type": "ok"
    }
