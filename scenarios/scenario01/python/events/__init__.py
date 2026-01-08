# events/__init__.py - 이벤트 핸들러 패키지 (scenario01)
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 이벤트 클래스 기반 라우팅
#
# 방 탈출 시나리오: 플레이어만 존재, NPC 없음

from . import registry

# 이벤트 클래스 import (자동 등록)
from . import reach


def on_event_list(ev_list):
    """
    이벤트 리스트 처리 (C#에서 호출)

    Args:
        ev_list: [["game_start"], ["on_reach", 0, 0, 6], ["on_meet", 0, 1], ...]

    Returns:
        첫 번째 모놀로그 결과 또는 None
    """
    import morld
    player_id = morld.get_player_id()

    for event in ev_list:
        event_type = event[0]

        if event_type == "game_start":
            result = registry.handle_game_start()
            if result:
                return result

        elif event_type == "on_reach":
            unit_id = event[1]
            region_id = event[2]
            location_id = event[3]

            if unit_id == player_id:
                result = registry.handle_reach(player_id, region_id, location_id)
                if result:
                    return result

        elif event_type == "on_meet":
            unit_ids = event[1:]
            if player_id in unit_ids:
                # 플레이어 포함 만남 이벤트
                result = registry.handle_meet(player_id, unit_ids)
                if result:
                    return result
            else:
                # NPC 간 만남 이벤트 (플레이어 미포함)
                result = registry.handle_npc_meet(unit_ids)
                # NPC 간 이벤트는 다이얼로그 없음 - 결과 반환 안 함

    return None


# C#에서 호출하는 메인 진입점
__all__ = ['on_event_list']
