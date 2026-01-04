# events/handlers.py - 이벤트 핸들러 (EventSystem용)
#
# 위치 도착, 만남 등 이벤트 처리

import morld

from assets.characters import get_character_event_handler
from assets.characters.player import events as player_events

# 발생한 이벤트 ID 집합 (중복 방지)
_triggered_events = set()


# ============================================================
# 메인 진입점 (C#에서 호출)
# ============================================================

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
            result = _handle_game_start()
            if result:
                return result

        elif event_type == "on_reach":
            unit_id = event[1]
            region_id = event[2]
            location_id = event[3]

            if unit_id == player_id:
                result = _handle_player_reach(region_id, location_id)
                if result:
                    return result
            else:
                # NPC 도착 (필요시 처리)
                _handle_npc_reach(unit_id, region_id, location_id)

        elif event_type == "on_meet":
            unit_ids = event[1:]
            if player_id in unit_ids:
                result = _handle_player_meet(player_id, unit_ids)
                if result:
                    return result
            else:
                _handle_npc_meet(unit_ids)

    return None


# ============================================================
# 내부 핸들러
# ============================================================

def _handle_game_start():
    """게임 시작 이벤트"""
    event_id = "game_start"
    if event_id in _triggered_events:
        return None

    _triggered_events.add(event_id)

    if hasattr(player_events, "on_game_start"):
        return player_events.on_game_start()

    return None


def _handle_player_reach(region_id, location_id):
    """플레이어 도착 이벤트"""
    # 앞마당 도착 (저택 region 0, 앞마당 location 12)
    if region_id == 0 and location_id == 12:
        event_id = "reach:front_yard"
        if event_id not in _triggered_events:
            _triggered_events.add(event_id)
            return player_events.on_reach_front_yard()

    return None


def _handle_npc_reach(unit_id, region_id, location_id):
    """NPC 도착 이벤트 - 상태 변경만 (모놀로그 없음)"""
    # 필요시 플래그 설정 등
    pass


def _handle_player_meet(player_id, unit_ids):
    """플레이어-NPC 만남 이벤트"""
    # 플레이어가 수면 중이면 만남 이벤트 무시
    player_info = morld.get_unit_info(player_id)
    if player_info and player_info.get("activity") == "수면":
        return None

    other_ids = [uid for uid in unit_ids if uid != player_id]

    for other_id in other_ids:
        handler = get_character_event_handler(other_id)
        if handler and hasattr(handler, "on_meet_player"):
            result = handler.on_meet_player(player_id)
            if result:
                return result

    return None


def _handle_npc_meet(unit_ids):
    """NPC끼리 만남 - 상태 변경만"""
    pass


# ============================================================
# 스크립트 함수 라우터
# ============================================================

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


# ============================================================
# 캐릭터 생성 함수들 (player/events.py로 위임)
# ============================================================

@morld.register_script
def set_name(context_unit_id, name):
    """이름 설정"""
    return player_events.set_name(context_unit_id, name)


@morld.register_script
def set_age(context_unit_id, age):
    """나이 설정"""
    return player_events.set_age(context_unit_id, age)


@morld.register_script
def set_body(context_unit_id, body_type):
    """신체 설정"""
    return player_events.set_body(context_unit_id, body_type)


@morld.register_script
def set_equipment(context_unit_id, equip_id):
    """장비 설정"""
    return player_events.set_equipment(context_unit_id, equip_id)


@morld.register_script
def after_collapse(context_unit_id):
    """쓰러진 후 콜백"""
    return player_events.after_collapse(context_unit_id)
