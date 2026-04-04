# region_map.py - 범용 Region 지도 렌더러
#
# Gate 그래프 + map_coords 기반 2D 뷰포트 지도.
# S02/S04 공통 사용.
#
# 사용법:
#   from region_map import render_region_map
#   bbcode = render_region_map(region_id, current_local, player_id, all_coords)

import morld
from grid_viewport import get_viewport, build_zoom_configs
from grid_viewport import DEFAULT_VIEW_W as _VIEW_W, DEFAULT_VIEW_H as _VIEW_H
from grid_renderer import MAP_FONT as _MAP_FONT
from text_utils import str_width as _str_width, truncate_to_width as _truncate_to_width
from ui_style import c, style_success

# 셀 크기 (그리드 좌표 → 텍스트 좌표 변환)
_CELL_W = 10
_CELL_H = 3


def render_region_map(region_id, current_local, player_id, all_coords,
                      viewport_id=None, show_characters=True):
    """2D 뷰포트 기반 region 맵 BBCode 렌더링.

    Args:
        region_id: Region ID
        current_local: 플레이어 현재 Location ID
        player_id: 플레이어 Unit ID
        all_coords: {loc_id: (x, y), ...} — map_coords.get_all() 결과
        viewport_id: 뷰포트 키 (None이면 자동 생성)
        show_characters: 하단 리스트에 NPC 이름 표시 여부

    Returns:
        str: BBCode 문자열
    """
    if viewport_id is None:
        viewport_id = f"region_map_{region_id}"

    # Location 데이터 수집
    locations, connections = _collect_map_data(region_id, all_coords)
    if not locations:
        return None  # 호출자가 폴백 처리

    # 그리드 범위
    min_x = min(loc["map_x"] for loc in locations.values())
    max_x = max(loc["map_x"] for loc in locations.values())
    min_y = min(loc["map_y"] for loc in locations.values())
    max_y = max(loc["map_y"] for loc in locations.values())

    map_w = (max_x - min_x + 1) * _CELL_W
    map_h = (max_y - min_y + 1) * _CELL_H

    # 뷰포트
    vp = get_viewport(viewport_id)
    zoom_configs = build_zoom_configs(len(locations), map_w, map_h)
    vp["_zoom_configs"] = zoom_configs

    # 기본 = 최대 줌아웃
    if vp.get("_initialized") is None:
        vp["zoom"] = len(zoom_configs) - 1
        vp["_initialized"] = True
    if vp["zoom"] >= len(zoom_configs):
        vp["zoom"] = len(zoom_configs) - 1

    zoom_cfg = zoom_configs[vp["zoom"]]
    grid_w = zoom_cfg["grid_w"]
    grid_h = zoom_cfg["grid_h"]

    # 그리드 생성
    grid = [[' '] * grid_w for _ in range(grid_h)]
    grid_meta = [[None] * grid_w for _ in range(grid_h)]

    # 위치 매핑 (맵 좌표 → 그리드 좌표)
    positions = {}
    for loc_id, loc in locations.items():
        cx = (loc["map_x"] - min_x + 0.5) / (max_x - min_x + 1)
        cy = (loc["map_y"] - min_y + 0.5) / (max_y - min_y + 1)
        gx = max(1, min(grid_w - 2, int(cx * (grid_w - 2)) + 1))
        gy = max(1, min(grid_h - 2, int(cy * (grid_h - 2)) + 1))
        positions[loc_id] = (gx, gy)

    # 연결선
    for (loc_a, loc_b) in connections:
        if loc_a in positions and loc_b in positions:
            ax, ay = positions[loc_a]
            bx, by = positions[loc_b]
            is_current_path = (loc_a == current_local or loc_b == current_local)
            _draw_map_line(grid, ax, ay, bx, by, grid_w, grid_h,
                           highlight=is_current_path)

    # Location 심볼
    for loc_id in locations:
        gx, gy = positions[loc_id]
        is_current = (loc_id == current_local)
        symbol = "@" if is_current else "●"
        if 0 <= gx < grid_w and 0 <= gy < grid_h:
            grid[gy][gx] = symbol
            grid_meta[gy][gx] = ("location", loc_id, is_current)

    # 캐릭터 수집 (show_characters=True 일 때만)
    location_characters = {}
    if show_characters:
        for loc_id in locations:
            unit_ids = morld.get_characters_at_location(region_id, loc_id)
            chars = []
            for uid in unit_ids:
                if uid == player_id:
                    continue
                info = morld.get_unit_info(uid)
                if info and not info.get("is_object", False):
                    chars.append(info.get("name", "???"))
            if chars:
                location_characters[loc_id] = chars

    # 뷰포트 카메라
    if vp["auto_center"] and current_local in positions:
        px, py = positions[current_local]
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

    # === BBCode 출력 ===
    lines = ["[!]"]

    # 스크롤/줌 컨트롤
    lines.append(_build_controls(vp, vx, vy, grid_w, grid_h, zoom_configs))

    # 그리드 렌더링
    border_color = "#999999"
    lines.append(f"[font={_MAP_FONT}]")
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
                if vp.get("show_names", True):
                    name = locations[loc_id]["name"]
                    avail = 0
                    for _cx in range(x + 1, min(vx + _VIEW_W, grid_w)):
                        _cm = grid_meta[y][_cx]
                        if _cm is not None and _cm[0] == "location":
                            break
                        avail += 1
                    if avail >= 2:
                        trunc = _truncate_to_width(name, avail)
                        if is_current:
                            row += c("#ffff00", trunc)
                        else:
                            row += f"[url=move:{region_id}:{loc_id}]{c('#66ccff', trunc)}[/url]"
                        _name_skip = _str_width(trunc)

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

    # 범례
    lines.append(
        f"  {c('#ffff00', '@')}현재  "
        f"{c('#66ccff', '●')}이동 가능"
    )

    # 하단 Location 링크 리스트
    for loc_id, loc in sorted(locations.items(),
                               key=lambda x: (x[1]["map_y"], x[1]["map_x"])):
        name = loc["name"]
        gx, gy = positions[loc_id]
        in_viewport = (vx <= gx < vx + _VIEW_W and vy <= gy < vy + _VIEW_H)

        char_text = ""
        if show_characters:
            chars = location_characters.get(loc_id, [])
            if chars:
                char_text = f" {style_success(f'[{", ".join(chars)}]')}"

        if loc_id == current_local:
            lines.append(f"  {c('#ffff00', '@')} {c('#ffff00', name)}{char_text}")
        elif in_viewport:
            lines.append(f"  [url=move:{region_id}:{loc_id}]{c('#66ccff', '●')} {c('#66ccff', name)}[/url]{char_text}")
        else:
            lines.append(f"  {c('#aaaaaa', '●')} {c('#aaaaaa', name)}{char_text}")

    lines.append("[/!]")
    return "\n".join(lines)


# ========================================
# 헬퍼
# ========================================

def _collect_map_data(region_id, all_coords):
    """Location 데이터 + Gate 연결 수집.

    Returns:
        (locations, connections)
        locations: {loc_id: {"name", "map_x", "map_y"}, ...}
        connections: set of (loc_a, loc_b) tuples
    """
    locations = {}
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return locations, set()

    for loc_data in region_info.get("locations", []):
        loc_id = loc_data["id"] if isinstance(loc_data, dict) else int(loc_data)
        if loc_id not in all_coords:
            continue
        loc_info = morld.get_location_info(region_id, loc_id)
        name = loc_info.get("name", "???") if loc_info else "???"
        mx, my = all_coords[loc_id]
        locations[loc_id] = {"name": name, "map_x": mx, "map_y": my}

    connections = set()
    for loc_id in locations:
        gates = morld.get_location_gates(region_id, loc_id)
        if not gates:
            continue
        for gate in gates:
            conn_region = gate.get("connected_region")
            conn_loc = gate.get("connected_location") or gate.get("connected_local")
            if conn_region == region_id and conn_loc in locations:
                connections.add(tuple(sorted([loc_id, conn_loc])))

    return locations, connections


def _build_controls(vp, vx, vy, grid_w, grid_h, zoom_configs):
    """스크롤/줌 컨트롤 BBCode."""
    can_left = vx > 0 if grid_w > _VIEW_W else False
    can_right = vx < grid_w - _VIEW_W if grid_w > _VIEW_W else False
    can_up = vy > 0 if grid_h > _VIEW_H else False
    can_down = vy < grid_h - _VIEW_H if grid_h > _VIEW_H else False
    can_zoom_in = vp["zoom"] > 0
    can_zoom_out = vp["zoom"] < len(zoom_configs) - 1

    def _btn(url_type, direction, symbol, can):
        if can:
            return f"[url=map:{url_type}:{direction}%]{symbol}[/url]"
        return c("#555555", symbol)

    _show_names = vp.get("show_names", True)
    _names_icon = c("#66ccff", "Aa") if _show_names else c("#888888", "Aa")

    return (
        f"  {_btn('scroll', 'left', '◀', can_left)}"
        f" {_btn('scroll', 'up', '▲', can_up)}"
        f" {_btn('scroll', 'down', '▼', can_down)}"
        f" {_btn('scroll', 'right', '▶', can_right)}"
        f"  [url=map:scroll:center%]{c('#aaaaaa', '◎')}[/url]"
        f"  {_btn('zoom', 'in', '+', can_zoom_in)}"
        f" {_btn('zoom', 'out', '−', can_zoom_out)}"
        f"  [url=map:toggle_names%]{_names_icon}[/url]"
    )


def _draw_map_line(grid, ax, ay, bx, by, grid_w, grid_h, highlight=False):
    """그리드에 L자형 연결선."""
    h_char = '═' if highlight else '─'
    v_char = '║' if highlight else '│'

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
