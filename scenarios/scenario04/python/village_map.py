# village_map.py - S04 마을 지도 시스템
#
# map_coords (common) 모듈 기반 2D 뷰포트 지도.
# S02 던전 지도 인터페이스를 따름:
# - 뷰포트 + 줌/스크롤 컨트롤
# - 기본 = 최대 줌아웃 (전체 보임)
# - 하단에 Location 링크 리스트
# - D2Coding 모노스페이스 폰트

import morld
import map_coords
from grid_renderer import MAP_FONT
from grid_viewport import get_viewport, build_zoom_configs, scroll, zoom, toggle_names
from grid_viewport import DEFAULT_VIEW_W as _VIEW_W, DEFAULT_VIEW_H as _VIEW_H
from text_utils import str_width, truncate_to_width
from ui_style import c

# 그리드 셀 크기
_CELL_W = 10
_CELL_H = 3

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
    """마을 지도 BBCode 렌더링 (S02 던전 지도 인터페이스)"""
    player_id = morld.get_player_id()
    if not player_id:
        return "지도를 표시할 수 없습니다."

    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return "현재 위치를 알 수 없습니다."

    _, current_loc_id = current_loc

    # 1. Location 수집 (map_coords 기반)
    all_coords = map_coords.get_all(region_id)
    locations = _collect_locations(region_id, all_coords)
    if not locations:
        return "지도 정보가 없습니다."

    # 2. Gate 연결 수집
    connections = _collect_connections(region_id, locations)

    # 3. 그리드 범위
    min_x = min(loc["map_x"] for loc in locations.values())
    max_x = max(loc["map_x"] for loc in locations.values())
    min_y = min(loc["map_y"] for loc in locations.values())
    max_y = max(loc["map_y"] for loc in locations.values())

    map_w = (max_x - min_x + 1) * _CELL_W
    map_h = (max_y - min_y + 1) * _CELL_H

    # 4. 줌 설정
    vp = get_viewport(_VIEWPORT_ID)
    zoom_configs = build_zoom_configs(len(locations), map_w, map_h)
    vp["_zoom_configs"] = zoom_configs

    # 마을 지도: 기본 = 최대 줌아웃 (마지막 config)
    if vp.get("_initialized") is None:
        vp["zoom"] = len(zoom_configs) - 1
        vp["_initialized"] = True
    if vp["zoom"] >= len(zoom_configs):
        vp["zoom"] = len(zoom_configs) - 1

    zoom_cfg = zoom_configs[vp["zoom"]]
    grid_w = zoom_cfg["grid_w"]
    grid_h = zoom_cfg["grid_h"]

    # 5. 그리드 생성
    grid = [[' '] * grid_w for _ in range(grid_h)]
    grid_meta = [[None] * grid_w for _ in range(grid_h)]

    # 6. 위치 매핑
    positions = {}  # loc_id -> (gx, gy)
    for loc_id, loc in locations.items():
        cx = (loc["map_x"] - min_x + 0.5) / (max_x - min_x + 1)
        cy = (loc["map_y"] - min_y + 0.5) / (max_y - min_y + 1)
        gx = max(1, min(grid_w - 2, int(cx * (grid_w - 2)) + 1))
        gy = max(1, min(grid_h - 2, int(cy * (grid_h - 2)) + 1))
        positions[loc_id] = (gx, gy)

    # 7. 연결선
    for (loc_a, loc_b) in connections:
        if loc_a in positions and loc_b in positions:
            ax, ay = positions[loc_a]
            bx, by = positions[loc_b]
            is_current_path = (loc_a == current_loc_id or loc_b == current_loc_id)
            _draw_line_raw(grid, ax, ay, bx, by, grid_w, grid_h,
                           highlight=is_current_path)

    # 8. Location 심볼
    for loc_id, loc in locations.items():
        gx, gy = positions[loc_id]
        is_current = (loc_id == current_loc_id)
        symbol = "@" if is_current else "●"
        if 0 <= gx < grid_w and 0 <= gy < grid_h:
            grid[gy][gx] = symbol
            grid_meta[gy][gx] = ("location", loc_id, is_current)

    # 9. 뷰포트 카메라
    if vp["auto_center"] and current_loc_id in positions:
        px, py = positions[current_loc_id]
        vp["cam_x"] = px - _VIEW_W // 2
        vp["cam_y"] = py - _VIEW_H // 2

    # 클램핑
    if grid_w <= _VIEW_W:
        vp["cam_x"] = (grid_w - _VIEW_W) // 2
    else:
        vp["cam_x"] = max(0, min(grid_w - _VIEW_W, vp["cam_x"]))
    if grid_h <= _VIEW_H:
        vp["cam_y"] = (grid_h - _VIEW_H) // 2
    else:
        vp["cam_y"] = max(0, min(grid_h - _VIEW_H, vp["cam_y"]))

    vx, vy = vp["cam_x"], vp["cam_y"]

    # 10. 스크롤/줌 컨트롤 (S02 패턴)
    can_left = vx > 0 if grid_w > _VIEW_W else False
    can_right = vx < grid_w - _VIEW_W if grid_w > _VIEW_W else False
    can_up = vy > 0 if grid_h > _VIEW_H else False
    can_down = vy < grid_h - _VIEW_H if grid_h > _VIEW_H else False
    can_zoom_in = vp["zoom"] > 0
    can_zoom_out = vp["zoom"] < len(zoom_configs) - 1

    def _scroll_btn(direction, symbol, can):
        if can:
            return f"[url=map:scroll:{direction}%]{symbol}[/url]"
        return c("#555555", symbol)

    def _zoom_btn(direction, symbol, can):
        if can:
            return f"[url=map:zoom:{direction}%]{symbol}[/url]"
        return c("#555555", symbol)

    _show_names = vp.get("show_names", True)
    _names_icon = c("#66ccff", "Aa") if _show_names else c("#888888", "Aa")

    lines = ["[!]"]

    ctrl = (
        f"  {_scroll_btn('left', '◀', can_left)}"
        f" {_scroll_btn('up', '▲', can_up)}"
        f" {_scroll_btn('down', '▼', can_down)}"
        f" {_scroll_btn('right', '▶', can_right)}"
        f"  [url=map:scroll:center%]{c('#aaaaaa', '◎')}[/url]"
        f"  {_zoom_btn('in', '+', can_zoom_in)}"
        f" {_zoom_btn('out', '−', can_zoom_out)}"
        f"  [url=map:toggle_names%]{_names_icon}[/url]"
    )
    lines.append(ctrl)

    # 11. BBCode 그리드 렌더링
    border_color = "#999999"
    lines.append(f"[font={MAP_FONT}]")
    lines.append(c(border_color, "┌" + "─" * _VIEW_W + "┐"))

    for y in range(vy, vy + _VIEW_H):
        row = c(border_color, "│")
        _name_skip = 0

        for x in range(vx, vx + _VIEW_W):
            if _name_skip > 0:
                _name_skip -= 1
                continue

            if x < 0 or x >= grid_w or y < 0 or y >= grid_h:
                row += " "
                continue

            meta = grid_meta[y][x]
            ch = grid[y][x]

            if meta is not None and meta[0] == "location":
                loc_id = meta[1]
                is_current = meta[2]
                if is_current:
                    row += c("#ffff00", ch)
                else:
                    row += f"[url=move:{region_id}:{loc_id}]{c('#66ccff', ch)}[/url]"

                # 이름 표시
                if _show_names:
                    name = locations[loc_id]["name"]
                    avail = 0
                    for _cx in range(x + 1, min(vx + _VIEW_W, grid_w)):
                        _cm = grid_meta[y][_cx]
                        if _cm is not None and _cm[0] == "location":
                            break
                        avail += 1
                    if avail >= 2:
                        trunc = truncate_to_width(name, avail)
                        if is_current:
                            row += c("#ffff00", trunc)
                        else:
                            row += f"[url=move:{region_id}:{loc_id}]{c('#66ccff', trunc)}[/url]"
                        _name_skip = str_width(trunc)

            elif ch in ('═', '║'):
                row += c("#66ccff", ch.replace('═', '─').replace('║', '│'))
            elif ch in ('─', '│', '┐', '└', '┘', '┌'):
                row += c("#888888", ch)
            else:
                row += ch

        row += c(border_color, "│")
        lines.append(row)

    lines.append(c(border_color, "└" + "─" * _VIEW_W + "┘"))
    lines.append("[/font]")

    # 12. 범례
    lines.append(
        f"  {c('#ffff00', '@')}현재  "
        f"{c('#66ccff', '●')}이동 가능"
    )

    # 13. 하단 Location 링크 리스트 (S02 패턴)
    for loc_id, loc in sorted(locations.items(),
                               key=lambda x: (x[1]["map_y"], x[1]["map_x"])):
        name = loc["name"]
        gx, gy = positions[loc_id]
        in_viewport = (vx <= gx < vx + _VIEW_W and vy <= gy < vy + _VIEW_H)

        if loc_id == current_loc_id:
            lines.append(f"  {c('#ffff00', '@')} {c('#ffff00', name)}")
        elif in_viewport:
            lines.append(f"  [url=move:{region_id}:{loc_id}]{c('#66ccff', '●')} {c('#66ccff', name)}[/url]")
        else:
            lines.append(f"  {c('#aaaaaa', '●')} {c('#aaaaaa', name)}")

    lines.append("[/!]")
    return "\n".join(lines)


# === 헬퍼 ===

def _draw_line_raw(grid, ax, ay, bx, by, grid_w, grid_h, highlight=False):
    """그리드에 직접 L자형 선 그리기"""
    if highlight:
        h_char, v_char = '═', '║'
    else:
        h_char, v_char = '─', '│'

    x = ax
    step = 1 if bx > ax else -1
    while x != bx:
        if 0 <= x < grid_w and 0 <= ay < grid_h and grid[ay][x] == ' ':
            grid[ay][x] = h_char
        x += step

    y = ay
    step = 1 if by > ay else -1
    while y != by:
        if 0 <= bx < grid_w and 0 <= y < grid_h and grid[y][bx] == ' ':
            grid[y][bx] = v_char
        y += step

    if ax != bx and ay != by:
        if 0 <= bx < grid_w and 0 <= ay < grid_h and grid[ay][bx] == ' ':
            if bx > ax and by > ay:
                grid[ay][bx] = '┐'
            elif bx > ax and by < ay:
                grid[ay][bx] = '┘'
            elif bx < ax and by > ay:
                grid[ay][bx] = '┌'
            else:
                grid[ay][bx] = '└'


def _collect_locations(region_id, all_coords):
    """map_coords 기반으로 Location 데이터 수집"""
    locations = {}
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return locations

    for loc_data in region_info.get("locations", []):
        if isinstance(loc_data, dict):
            loc_id = loc_data.get("id", -1)
        else:
            loc_id = int(loc_data)

        if loc_id not in all_coords:
            continue

        loc_info = morld.get_location_info(region_id, loc_id)
        if not loc_info:
            continue

        map_x, map_y = all_coords[loc_id]
        locations[loc_id] = {
            "loc_id": loc_id,
            "name": loc_info.get("name", "???"),
            "map_x": map_x,
            "map_y": map_y,
        }

    return locations


def _collect_connections(region_id, locations):
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
