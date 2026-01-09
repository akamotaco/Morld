# events/__init__.py - 이벤트 핸들러 패키지 (scenario01)
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 이벤트 클래스 기반 라우팅
# - 스크립트 함수 등록 (@morld.register_script)
#
# 방 탈출 시나리오: 플레이어만 존재, NPC 없음

from . import registry

# 이벤트 클래스 import (자동 등록)
from . import reach

# 스크립트 함수 등록 (import 시 @morld.register_script 실행)
import scripts


def on_single_event(event):
    """
    단일 이벤트 처리 (C#에서 순차 호출)

    Args:
        event: ["game_start"] 또는 ["on_reach", unit_id, region_id, location_id] 등

    Returns:
        Generator 또는 None
    """
    import morld
    player_id = morld.get_player_id()

    event_type = event[0]

    if event_type == "game_start":
        return registry.handle_game_start()

    elif event_type == "on_reach":
        unit_id = event[1]
        region_id = event[2]
        location_id = event[3]

        if unit_id == player_id:
            return registry.handle_reach(player_id, region_id, location_id)

    elif event_type == "on_meet":
        unit_ids = event[1:]
        if player_id in unit_ids:
            # 플레이어 포함 만남 이벤트 (방탈출에서는 거의 없음)
            return registry.handle_meet(player_id, unit_ids)
        else:
            # NPC 간 만남 이벤트 (방탈출에서는 없음)
            registry.handle_npc_meet(unit_ids)

    return None


def on_event_list(ev_list):
    """
    이벤트 리스트 처리 (C#에서 호출) - 레거시 호환용

    Note: 새 코드는 on_single_event()를 사용

    Args:
        ev_list: [["game_start"], ["on_reach", 0, 0, 6], ["on_meet", 0, 1], ...]

    Returns:
        첫 번째 모놀로그 결과 또는 None
    """
    for event in ev_list:
        result = on_single_event(event)
        if result:
            return result

    return None


def has_pending_meet_events():
    """
    대기 중인 meet 이벤트가 있는지 확인

    방탈출 시나리오에서는 NPC가 없으므로 항상 False 반환
    """
    return False


def clear_pending_meet_events():
    """
    대기 중인 meet 이벤트 모두 제거

    방탈출 시나리오에서는 NPC가 없으므로 아무것도 하지 않음
    """
    pass


# C#에서 호출하는 메인 진입점
__all__ = [
    'on_event_list',
    'on_single_event',
    'has_pending_meet_events',
    'clear_pending_meet_events',
]
