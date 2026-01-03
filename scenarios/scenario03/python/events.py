# events.py - 메인 이벤트 핸들러
# C#의 EventSystem에서 호출하는 진입점

import morld
from characters import get_character_event_handler
from characters.player import events as player_events
from objects.furniture import mirror_look

# 발생한 이벤트 ID 집합 (중복 방지)
_triggered_events = set()


def on_event_list(ev_list):
    """
    이벤트 리스트 처리 (C#에서 호출)

    Args:
        ev_list: [["game_start"], ["on_reach", 0, 0, 6], ["on_meet", 0, 1], ...]

    Returns:
        첫 번째 모놀로그 결과 또는 None
    """
    player_id = morld.get_player_id()

    for event in ev_list:
        event_type = event[0]

        if event_type == "game_start":
            result = handle_game_start()
            if result:
                return result

        elif event_type == "on_reach":
            unit_id = event[1]
            region_id = event[2]
            location_id = event[3]

            if unit_id == player_id:
                result = handle_player_reach(region_id, location_id)
                if result:
                    return result

        elif event_type == "on_meet":
            unit_ids = event[1:]
            if player_id in unit_ids:
                result = handle_player_meet(player_id, unit_ids)
                if result:
                    return result

    return None


def handle_game_start():
    """게임 시작 이벤트"""
    event_id = "game_start"
    if event_id in _triggered_events:
        return None

    _triggered_events.add(event_id)

    # 플레이어 캐릭터의 게임 시작 이벤트 호출
    if hasattr(player_events, "on_game_start"):
        return player_events.on_game_start()

    return None


def handle_player_reach(region_id, location_id):
    """플레이어 도착 이벤트"""
    # 위치별 일회성 이벤트 체크
    event_id = f"reach:{region_id}:{location_id}"

    # 현재는 특별한 위치 이벤트 없음
    # 추후 확장 가능
    return None


def handle_player_meet(player_id, unit_ids):
    """플레이어-NPC 만남 이벤트"""
    other_ids = [uid for uid in unit_ids if uid != player_id]

    for other_id in other_ids:
        handler = get_character_event_handler(other_id)
        if handler and hasattr(handler, "on_meet_player"):
            result = handler.on_meet_player(player_id)
            if result:
                return result

    return None


# === 스크립트 함수 라우터 ===
# script:함수명:인자 형식으로 호출되는 함수들

def npc_talk(context_unit_id):
    """
    NPC 대화 - 각 캐릭터의 events.py에서 처리
    context_unit_id로 캐릭터 판별 후 해당 캐릭터의 npc_talk 호출
    """
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

    # 기본 대화
    name = unit_info.get("name", "???")
    return {
        "type": "monologue",
        "pages": [f"[{name}]", "......", "별 말이 없다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def job_select(context_unit_id, job_type):
    """직업 선택 - player/events.py로 위임"""
    return player_events.job_select(context_unit_id, job_type)


def job_confirm(context_unit_id, job_type):
    """직업 확정 - player/events.py로 위임"""
    return player_events.job_confirm(context_unit_id, job_type)


# mirror_look은 objects/furniture.py에서 import됨
