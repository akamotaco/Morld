# village_map.py - S04 마을 지도 시스템
#
# common/grid_renderer + grid_viewport 사용.
# 전체 공개, 줌아웃 고정, 클릭 이동.

import morld
from grid_renderer import GridBuffer, draw_line, render_viewport, center_camera_on, MAP_FONT
from grid_viewport import get_viewport, build_zoom_configs
from text_utils import str_width, truncate_to_width

# 그리드 셀 크기 (문자 단위)
_CELL_W = 10
_CELL_H = 3

# Location 2D 좌표 저장소: (region_id, loc_id) -> (map_x, map_y)
_location_coords = {}

# 뷰포트 ID
_VIEWPORT_ID = "village_map"


def reset():
    _location_coords.clear()


def register_location(region_id, loc_id, map_x, map_y):
    """Location의 2D 좌표 등록"""
    _location_coords[(region_id, loc_id)] = (map_x, map_y)


def render_village_map(region_id):
    """마을 지도 BBCode 렌더링"""
    player_id = morld.get_player_id()
    if not player_id:
        return "지도를 표시할 수 없습니다."

    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return "현재 위치를 알 수 없습니다."

    _, current_loc_id = current_loc

    # 1. Location 정보 수집
    locations = _collect_locations(region_id)
    if not locations:
        return "지도 정보가 없습니다."

    # 2. Gate 연결 수집
    connections = _collect_connections(region_id, locations)

    # 3. 그리드 범위 계산
    min_x = min(loc["map_x"] for loc in locations.values())
    max_x = max(loc["map_x"] for loc in locations.values())
    min_y = min(loc["map_y"] for loc in locations.values())
    max_y = max(loc["map_y"] for loc in locations.values())

    grid_w = (max_x - min_x + 1) * _CELL_W + 2  # +2 for border
    grid_h = (max_y - min_y + 1) * _CELL_H + 2

    # 4. 그리드 생성
    grid = GridBuffer(grid_w, grid_h)
    grid.draw_border()

    # 5. 연결선 그리기
    for (loc_a, loc_b) in connections:
        if loc_a in locations and loc_b in locations:
            ax = (locations[loc_a]["map_x"] - min_x) * _CELL_W + _CELL_W // 2 + 1
            ay = (locations[loc_a]["map_y"] - min_y) * _CELL_H + _CELL_H // 2 + 1
            bx = (locations[loc_b]["map_x"] - min_x) * _CELL_W + _CELL_W // 2 + 1
            by = (locations[loc_b]["map_y"] - min_y) * _CELL_H + _CELL_H // 2 + 1
            draw_line(grid, ax, ay, bx, by)

    # 6. Location 배치
    for loc_id, loc in locations.items():
        gx = (loc["map_x"] - min_x) * _CELL_W + 1 + 1  # +1 border +1 padding
        gy = (loc["map_y"] - min_y) * _CELL_H + _CELL_H // 2 + 1

        is_current = (loc_id == current_loc_id)
        marker = "@" if is_current else "●"
        name = loc["name"]
        display = truncate_to_width(name, _CELL_W - 2)

        grid.set_cell(gx, gy, marker, ("location", loc_id, is_current))
        for i, ch in enumerate(display):
            grid.set_cell(gx + 1 + i, gy, ch, ("name", loc_id, is_current))

    # 7. 뷰포트 (마을은 전체 공개 — 전체가 보이도록)
    vp = get_viewport(_VIEWPORT_ID)
    vp["view_w"] = grid_w
    vp["view_h"] = grid_h
    cam_x, cam_y = 0, 0

    # 8. 렌더링
    def style_fn(ch, meta, x, y):
        if meta is None:
            return ch

        if meta[0] == "border":
            return f"[color=#666666]{ch}[/color]"
        elif meta[0] == "location":
            loc_id = meta[1]
            is_current = meta[2]
            if is_current:
                return f"[color=#ffff00]{ch}[/color]"
            else:
                return f"[url=move:{region_id}:{loc_id}][color=#66ccff]{ch}[/color][/url]"
        elif meta[0] == "name":
            loc_id = meta[1]
            is_current = meta[2]
            if is_current:
                return f"[color=#ffff00]{ch}[/color]"
            else:
                return f"[url=move:{region_id}:{loc_id}][color=#66ccff]{ch}[/color][/url]"
        elif meta[0] == "line" or meta[0] == "line_corner":
            return f"[color=#555555]{ch}[/color]"
        return ch

    map_text = render_viewport(grid, cam_x, cam_y, grid_w, grid_h, style_fn=style_fn)

    return f"[font={MAP_FONT}]{map_text}[/font]"


def _collect_locations(region_id):
    """region 내 2D 좌표가 등록된 Location 수집"""
    locations = {}
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return locations

    for loc_data in region_info.get("locations", []):
        if isinstance(loc_data, dict):
            loc_id = loc_data.get("id", -1)
        else:
            loc_id = int(loc_data)

        key = (region_id, loc_id)
        if key not in _location_coords:
            continue

        loc_info = morld.get_location_info(region_id, loc_id)
        if not loc_info:
            continue

        map_x, map_y = _location_coords[key]
        locations[loc_id] = {
            "loc_id": loc_id,
            "name": loc_info.get("name", "???"),
            "map_x": map_x,
            "map_y": map_y,
        }

    return locations


def _collect_connections(region_id, locations):
    """같은 region 내 Gate 연결 수집"""
    connections = set()
    for loc_id in locations:
        gates = morld.get_location_gates(region_id, loc_id)
        if not gates:
            continue
        for gate in gates:
            conn_region = gate.get("connected_region")
            conn_loc = gate.get("connected_location")
            if conn_region == region_id and conn_loc in locations:
                pair = tuple(sorted([loc_id, conn_loc]))
                connections.add(pair)
    return connections
