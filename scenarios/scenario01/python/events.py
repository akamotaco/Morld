# events.py - 이벤트 핸들러 (EventSystem용)
# 시나리오 01: 직업 선택 + 마을 탐험

import morld

# 기존 monologues.py의 함수들 임포트
from monologues import get_monologue, get_job_select_monologue

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
    # 예시: (0, 5): "on_reach_forest",
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
    """게임 시작 이벤트 - 인트로 + 직업 선택"""
    event_id = "game_start"
    if event_id in _triggered_events:
        return None

    _triggered_events.add(event_id)

    # 기존 monologues.py의 로직 재사용
    mono = get_monologue("intro_001")
    if mono:
        # 인트로 페이지 + 직업 선택 페이지 결합
        job_mono = get_job_select_monologue()
        combined_pages = mono["pages"] + job_mono["pages"]
        return {
            "type": "monologue",
            "pages": combined_pages,
            "time_consumed": mono.get("time_consumed", 0),
            "button_type": "ok"  # script: 링크가 있는 페이지는 자동으로 버튼 없음 처리됨
        }

    return None

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
# 위치별 핸들러 (REACH_EVENTS에 등록된 함수들)
# ============================================================

# 예시:
# def on_reach_forest():
#     """숲 첫 방문"""
#     return {
#         "type": "monologue",
#         "pages": ["숲에 들어왔다.", "어딘가 불길한 기운이 느껴진다."],
#         "time_consumed": 0,
#         "button_type": "ok"
#     }
