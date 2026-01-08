# events/__init__.py - 이벤트 핸들러 패키지
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 스크립트 함수 자동 등록 (@morld.register_script)
# - 캐릭터별 이벤트 핸들러 위임

from . import registry

# 이벤트 클래스 import (자동 등록)
from . import game_start
from . import reach
from . import meet

# 스크립트 함수 import (@morld.register_script 자동 등록)
from . import scripts

# 캐릭터 이벤트 핸들러 (on_meet_player 등)
from assets.characters import get_character_event_handler


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
                # 먼저 등록된 MeetEvent 체크 (플레이어 포함)
                result = registry.handle_meet(player_id, unit_ids)
                if result:
                    return result

                # 캐릭터별 on_meet_player 핸들러 체크
                result = _handle_character_meet(player_id, unit_ids)
                if result:
                    return result
            else:
                # NPC 간 만남 이벤트 (플레이어 미포함)
                result = registry.handle_npc_meet(unit_ids)
                # NPC 간 이벤트는 다이얼로그 없음 - 결과 반환 안 함
                # (로그만 출력하고 계속 진행)

    return None


def _handle_character_meet(player_id, unit_ids):
    """캐릭터별 on_meet_player 핸들러 호출

    get_character_event_handler()는 이제 캐릭터 인스턴스를 직접 반환.
    인스턴스의 on_meet_player() 메서드를 호출.
    """
    other_ids = [uid for uid in unit_ids if uid != player_id]

    for other_id in other_ids:
        handler = get_character_event_handler(other_id)
        if handler and hasattr(handler, "on_meet_player"):
            result = handler.on_meet_player(player_id)
            if result:
                return result

    return None


# C#에서 호출하는 메인 진입점
__all__ = ['on_event_list']
