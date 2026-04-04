# village_map.py - S04 마을 지도 시스템
#
# 요구사항:
# - 전체 공개 (어둠 없음)
# - 최대 줌아웃 고정 (스크롤 불필요)
# - 한 클릭 = 어디든 이동 (move: URL)
# - Location에 2D 좌표 (map:x, map:y prop)
# - Gate 연결이 선으로 표시
# - D2Coding 모노스페이스 폰트 사용
#
# 각 Location은 map:x, map:y prop을 가짐.
# 그리드에 Location을 배치하고 Gate 연결을 선으로 표시.

import morld

_MAP_FONT = "res://assets/fonts/D2Coding-Ver1.3.2-20180524-all.ttc"

# 그리드 셀 크기 (문자 단위)
_CELL_W = 10  # 한 셀의 가로 문자 수
_CELL_H = 3   # 한 셀의 세로 문자 수


def render_village_map(region_id: int) -> str:
    """마을 지도 BBCode 렌더링"""
    player_id = morld.get_player_id()
    if not player_id:
        return "지도를 표시할 수 없습니다."

    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return "현재 위치를 알 수 없습니다."

    _, current_loc_id = current_loc

    # 1. Location 정보 수집 (map:x, map:y prop이 있는 것만)
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

    grid_w = (max_x - min_x + 1) * _CELL_W
    grid_h = (max_y - min_y + 1) * _CELL_H

    # 4. 빈 그리드 생성
    grid = [[' '] * grid_w for _ in range(grid_h)]

    # 5. 연결선 그리기
    for (loc_a, loc_b) in connections:
        if loc_a in locations and loc_b in locations:
            _draw_connection(grid, locations[loc_a], locations[loc_b],
                             min_x, min_y)

    # 6. Location 배치
    for loc_id, loc in locations.items():
        _draw_location(grid, loc, min_x, min_y,
                       is_current=(loc_id == current_loc_id))

    # 7. BBCode 출력
    lines = []
    for row in grid:
        lines.append(''.join(row))

    map_text = '\n'.join(lines)

    # 8. 클릭 이동 링크 생성
    nav_lines = _build_nav_links(locations, current_loc_id, region_id)

    result = f"[font={_MAP_FONT}]{map_text}[/font]\n\n{nav_lines}"
    return result


def _collect_locations(region_id: int) -> dict:
    """region 내 map:x, map:y prop이 있는 Location 수집"""
    locations = {}
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return locations

    for loc_id in region_info.get("locations", []):
        loc_info = morld.get_location_info(region_id, loc_id)
        if not loc_info:
            continue

        unit_id = morld.get_location_unit_id(region_id, loc_id)
        if not unit_id:
            continue

        map_x = morld.get_unit_prop(unit_id, "map:x")
        map_y = morld.get_unit_prop(unit_id, "map:y")

        if map_x is not None and map_y is not None:
            locations[loc_id] = {
                "loc_id": loc_id,
                "name": loc_info.get("name", "???"),
                "map_x": int(map_x),
                "map_y": int(map_y),
            }

    return locations


def _collect_connections(region_id: int, locations: dict) -> set:
    """같은 region 내 Gate 연결 수집 (중복 제거)"""
    connections = set()
    for loc_id in locations:
        gates = morld.get_gates(region_id, loc_id)
        if not gates:
            continue
        for gate in gates:
            conn_region = gate.get("connected_region")
            conn_loc = gate.get("connected_location")
            if conn_region == region_id and conn_loc in locations:
                pair = tuple(sorted([loc_id, conn_loc]))
                connections.add(pair)
    return connections


def _draw_location(grid, loc, min_x, min_y, is_current):
    """그리드에 Location 셀 그리기"""
    gx = (loc["map_x"] - min_x) * _CELL_W
    gy = (loc["map_y"] - min_y) * _CELL_H

    name = loc["name"]
    # 셀 폭에 맞게 자르기
    display_name = name[:_CELL_W - 2]

    # 현재 위치면 마커 표시
    marker = "@" if is_current else " "

    # 셀 중앙에 이름 배치
    cx = gx + 1
    cy = gy + 1  # 셀 중앙 행

    # 이름 쓰기
    for i, ch in enumerate(f"{marker}{display_name}"):
        if cx + i < len(grid[0]):
            grid[cy][cx + i] = ch


def _draw_connection(grid, loc_a, loc_b, min_x, min_y):
    """두 Location 사이에 연결선 그리기"""
    ax = (loc_a["map_x"] - min_x) * _CELL_W + _CELL_W // 2
    ay = (loc_a["map_y"] - min_y) * _CELL_H + _CELL_H // 2
    bx = (loc_b["map_x"] - min_x) * _CELL_W + _CELL_W // 2
    by = (loc_b["map_y"] - min_y) * _CELL_H + _CELL_H // 2

    # 간단한 직선/L자 연결
    if ay == by:
        # 수평
        for x in range(min(ax, bx), max(ax, bx) + 1):
            if 0 <= x < len(grid[0]) and 0 <= ay < len(grid):
                if grid[ay][x] == ' ':
                    grid[ay][x] = '─'
    elif ax == bx:
        # 수직
        for y in range(min(ay, by), max(ay, by) + 1):
            if 0 <= ax < len(grid[0]) and 0 <= y < len(grid):
                if grid[y][ax] == ' ':
                    grid[y][ax] = '│'
    else:
        # L자: 먼저 수평 → 수직
        for x in range(min(ax, bx), max(ax, bx) + 1):
            if 0 <= x < len(grid[0]) and 0 <= ay < len(grid):
                if grid[ay][x] == ' ':
                    grid[ay][x] = '─'
        for y in range(min(ay, by), max(ay, by) + 1):
            if 0 <= bx < len(grid[0]) and 0 <= y < len(grid):
                if grid[y][bx] == ' ':
                    grid[y][bx] = '│'
        # 꺾이는 점
        if 0 <= bx < len(grid[0]) and 0 <= ay < len(grid):
            grid[ay][bx] = '┐' if bx > ax else '┌'


def _build_nav_links(locations: dict, current_loc_id: int, region_id: int) -> str:
    """클릭 이동 링크 목록"""
    lines = []
    for loc_id, loc in sorted(locations.items(), key=lambda x: (x[1]["map_y"], x[1]["map_x"])):
        name = loc["name"]
        if loc_id == current_loc_id:
            lines.append(f"  [color=yellow]@ {name}[/color] (현재 위치)")
        else:
            # move: URL로 직접 이동
            lines.append(f"  [url=move:{region_id}:{loc_id}]{name}[/url]")
    return '\n'.join(lines)
