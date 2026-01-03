# events.py - 이벤트 핸들러 (EventSystem용)
# 위치 도착, 만남 등 이벤트 처리

import morld

# ============================================================
# 플래그 관리
# ============================================================

_flags = {}                    # 범용 플래그 (key → value)
_triggered_events = set()      # 발생한 이벤트 ID 집합

def set_flag(key, value=True):
    """플래그 설정"""
    _flags[key] = value

def get_flag(key, default=None):
    """플래그 조회"""
    return _flags.get(key, default)

def has_flag(key):
    """플래그 존재 여부"""
    return key in _flags

def clear_flag(key):
    """플래그 삭제"""
    _flags.pop(key, None)

# ============================================================
# 위치별 도착 이벤트 등록
# key: (region_id, location_id)
# value: 핸들러 함수명 (문자열)
# ============================================================

REACH_EVENTS = {
    (0, 6): "on_reach_bedroom",     # 침실
}

# ============================================================
# 메인 진입점 (C#에서 호출)
# ============================================================

def on_event_list(ev_list):
    """
    이벤트 리스트를 받아서 순차 처리

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

            # 플레이어만 다이얼로그 표시
            if unit_id == player_id:
                result = handle_player_reach(region_id, location_id)
                if result:
                    return result
            else:
                # NPC 도착 (상태 변경만, 모놀로그 없음)
                handle_npc_reach(unit_id, region_id, location_id)

        elif event_type == "on_meet":
            unit_ids = event[1:]
            is_player_involved = player_id in unit_ids

            if is_player_involved:
                result = handle_player_meet(unit_ids)
                if result:
                    return result
            else:
                handle_npc_meet(unit_ids)

    return None

# ============================================================
# 이벤트 핸들러 구현
# ============================================================

def handle_game_start():
    """게임 시작 이벤트"""
    event_id = "game_start"
    if event_id in _triggered_events:
        return None

    _triggered_events.add(event_id)

    return {
        "type": "monologue",
        "pages": [
            "...어디지, 여기는?",
            "머리가 지끈거린다.\n기억이... 잘 나지 않는다.",
            "일단 이 저택에서 나가야 할 것 같다."
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }

def handle_player_reach(region_id, location_id):
    """플레이어 도착 이벤트 - 모놀로그 표시 가능"""
    key = (region_id, location_id)
    handler_name = REACH_EVENTS.get(key)

    if handler_name is None:
        return None

    # 일회성 체크
    event_id = f"reach:{region_id}:{location_id}"
    if event_id in _triggered_events:
        return None

    handler = globals().get(handler_name)
    if handler:
        result = handler()
        if result:
            _triggered_events.add(event_id)
        return result

    return None

def handle_npc_reach(unit_id, region_id, location_id):
    """NPC 도착 이벤트 - 상태 변경만 (모놀로그 없음)"""
    # 필요시 플래그 설정 등
    pass

def handle_player_meet(unit_ids):
    """플레이어-NPC 만남 - 모놀로그 표시 가능"""
    # 필요시 특정 NPC와의 만남 처리
    return None

def handle_npc_meet(unit_ids):
    """NPC끼리 만남 - 상태 변경만"""
    pass

# ============================================================
# 위치별 핸들러
# ============================================================

def on_reach_bedroom():
    """침실 첫 방문 - 알 수 없는 목소리"""
    return {
        "type": "monologue",
        "pages": [
            "...어디선가 희미한 소리가 들린다.",
            "\"...나...가...\"",
            "목소리가 사라졌다.\n환청이었을까?"
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }
