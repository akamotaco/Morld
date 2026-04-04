# village_map.py - S04 마을 지도 (common/region_map 래퍼)
#
# S02와 동일한 2D 뷰포트 지도.
# 실제 렌더링은 common/region_map.py에 위임.

import morld
import map_coords
from grid_viewport import scroll, zoom, toggle_names

_VIEWPORT_ID = "village_map"


def reset():
    pass


def register_location(region_id, loc_id, map_x, map_y):
    """하위 호환: map_coords.register()로 위임"""
    map_coords.register(region_id, loc_id, map_x, map_y)


# === 스크롤/줌 핸들러 (C# URL 핸들러에서 호출) ===

def map_scroll(direction):
    scroll(_VIEWPORT_ID, direction)

def map_zoom(direction):
    zoom(_VIEWPORT_ID, direction)

def map_toggle_names():
    toggle_names(_VIEWPORT_ID)


# === 메인 렌더러 ===

def render_village_map(region_id):
    """마을 지도 BBCode 렌더링"""
    import region_map

    player_id = morld.get_player_id()
    if not player_id:
        return "지도를 표시할 수 없습니다."

    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return "현재 위치를 알 수 없습니다."

    _, current_loc_id = current_loc
    all_coords = map_coords.get_all(region_id)
    if not all_coords:
        return "지도 정보가 없습니다."

    result = region_map.render_region_map(
        region_id, current_loc_id, player_id, all_coords,
        viewport_id=_VIEWPORT_ID, show_characters=False
    )
    return result or "지도 정보가 없습니다."
