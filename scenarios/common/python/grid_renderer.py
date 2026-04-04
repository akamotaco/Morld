# grid_renderer.py - 공통 그리드 렌더러
#
# 2D 텍스트 그리드 + 메타데이터 + BBCode 렌더링.
# S02 던전 지도, S04 마을 지도에서 공통 사용.

MAP_FONT = "res://assets/fonts/D2Coding-Ver1.3.2-20180524-all.ttc"


class GridBuffer:
    """2D 텍스트 그리드 + 셀별 메타데이터"""

    def __init__(self, width, height, fill=' '):
        self.width = width
        self.height = height
        self.grid = [[fill] * width for _ in range(height)]
        self.meta = [[None] * width for _ in range(height)]

    def set_cell(self, x, y, char, metadata=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = char
            if metadata is not None:
                self.meta[y][x] = metadata

    def get_cell(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x], self.meta[y][x]
        return ' ', None

    def draw_border(self):
        """외곽선 그리기 (box-drawing)"""
        w, h = self.width, self.height
        for x in range(1, w - 1):
            self.set_cell(x, 0, '─', ("border",))
            self.set_cell(x, h - 1, '─', ("border",))
        for y in range(1, h - 1):
            self.set_cell(0, y, '│', ("border",))
            self.set_cell(w - 1, y, '│', ("border",))
        self.set_cell(0, 0, '┌', ("border",))
        self.set_cell(w - 1, 0, '┐', ("border",))
        self.set_cell(0, h - 1, '└', ("border",))
        self.set_cell(w - 1, h - 1, '┘', ("border",))


def draw_line(grid, ax, ay, bx, by, dim=False, highlight=False):
    """두 점 사이 L자형 연결선 (box-drawing 문자)"""
    if highlight:
        h_char, v_char = '═', '║'
    elif dim:
        h_char, v_char = '╌', '╎'
    else:
        h_char, v_char = '─', '│'

    # 수평 이동
    x = ax
    step = 1 if bx > ax else -1
    while x != bx:
        ch, meta = grid.get_cell(x, ay)
        if ch == ' ':
            grid.set_cell(x, ay, h_char, ("line", dim, highlight))
        x += step

    # 수직 이동
    y = ay
    step = 1 if by > ay else -1
    while y != by:
        ch, meta = grid.get_cell(bx, y)
        if ch == ' ':
            grid.set_cell(bx, y, v_char, ("line", dim, highlight))
        y += step

    # 꺾이는 지점
    if ax != bx and ay != by:
        ch, meta = grid.get_cell(bx, ay)
        if ch == ' ':
            if bx > ax and by > ay:
                corner = '┐'
            elif bx > ax and by < ay:
                corner = '┘'
            elif bx < ax and by > ay:
                corner = '┌'
            else:
                corner = '└'
            grid.set_cell(bx, ay, corner, ("line_corner",))


def render_viewport(grid, cam_x, cam_y, view_w, view_h, style_fn=None):
    """
    그리드의 뷰포트 영역을 문자열로 렌더링.

    Args:
        grid: GridBuffer
        cam_x, cam_y: 카메라 위치 (좌상단)
        view_w, view_h: 뷰포트 크기
        style_fn: (char, metadata) -> str 스타일링 함수. None이면 char 그대로.

    Returns:
        str (줄바꿈 포함)
    """
    lines = []
    for y in range(cam_y, cam_y + view_h):
        row = ""
        for x in range(cam_x, cam_x + view_w):
            ch, meta = grid.get_cell(x, y)
            if style_fn:
                row += style_fn(ch, meta, x, y)
            else:
                row += ch
        lines.append(row)
    return '\n'.join(lines)


def clamp_camera(cam_x, cam_y, grid_w, grid_h, view_w, view_h):
    """카메라를 그리드 범위 내로 클램프"""
    if grid_w <= view_w:
        cam_x = (grid_w - view_w) // 2
    else:
        cam_x = max(0, min(grid_w - view_w, cam_x))

    if grid_h <= view_h:
        cam_y = (grid_h - view_h) // 2
    else:
        cam_y = max(0, min(grid_h - view_h, cam_y))

    return cam_x, cam_y


def center_camera_on(target_x, target_y, grid_w, grid_h, view_w, view_h):
    """특정 위치를 뷰포트 중앙에 배치"""
    cam_x = target_x - view_w // 2
    cam_y = target_y - view_h // 2
    return clamp_camera(cam_x, cam_y, grid_w, grid_h, view_w, view_h)
