# characters/cheolsu/events.py - 철수 관련 이벤트

import morld
from characters.cheolsu.data import CHARACTER_ID
from characters.cheolsu.dialogues import get_dialogue

# 이벤트 플래그
_flags = {}


def on_meet_player(player_id):
    """플레이어와 처음 만났을 때"""
    if _flags.get("first_meet"):
        return None

    # 수면 중이면 이벤트 발생하지 않음 (플래그도 설정 안함)
    unit_info = morld.get_unit_info(CHARACTER_ID)
    if unit_info and unit_info.get("activity") == "수면":
        return None

    _flags["first_meet"] = True
    return {
        "type": "monologue",
        "pages": [
            "어? 처음 보는 얼굴이네.",
            "나는 철수라고 해. 반가워!",
            "이 마을에 처음 왔어? 둘러보려면 도움이 필요하면 말해."
        ],
        "time_consumed": 2,
        "button_type": "ok"
    }


def on_reach_together(player_id, location_id):
    """플레이어와 같은 장소에 도착했을 때"""
    # 특정 장소에서의 대화
    if location_id == 3:  # 공원
        event_id = f"reach_together_park"
        if event_id in _flags:
            return None
        _flags[event_id] = True
        return {
            "type": "monologue",
            "pages": ["오, 여기서 보네! 공원 좋지?"],
            "time_consumed": 1,
            "button_type": "ok"
        }
    return None


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
