# events/sleep.py - 수면 관련 함수
#
# 플레이어/NPC의 노숙(침대 없이 잠자기) 기능

import morld
import ui


def rough_sleep():
    """노숙하기 - 침대 없이 잠자기

    플레이어가 아무 곳에서나 잠을 잘 수 있음.
    실내/야외에 따라 다른 메시지 표시.
    향후: 체력/피로 회복량 감소 적용.
    """
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)

    loc_info = morld.get_location_info(
        player_info["region_id"], player_info["location_id"])

    is_indoor = loc_info.get("is_indoor", False) if loc_info else False

    if is_indoor:
        yield ui.dialog(["바닥에 누워 잠을 청했다.", "딱딱하지만 지붕이라도 있다."])
    else:
        yield ui.dialog(["풀밭 위에 누워 잠을 청했다.", "별이 보인다... 하지만 불안하다."])

    morld.advance_time(480 * 60_000)  # 8시간
