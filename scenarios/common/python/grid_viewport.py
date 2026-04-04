# grid_viewport.py - 공통 뷰포트 관리
#
# 줌/스크롤/카메라 상태 관리.
# S02 던전 지도, S04 마을 지도에서 공통 사용.

# === 기본 상수 ===
DEFAULT_VIEW_W = 36
DEFAULT_VIEW_H = 12
DEFAULT_SCROLL_STEP = 5
DEFAULT_ZOOM_SCALES = [3.5, 2.5, 1.5, 1.0, 0.7]
DEFAULT_ZOOM_INDEX = 2


# === 뷰포트 상태 ===

_viewports = {}  # viewport_id -> state dict


def reset():
    _viewports.clear()


def get_viewport(viewport_id):
    """뷰포트 상태 가져오기 (없으면 생성)"""
    if viewport_id not in _viewports:
        _viewports[viewport_id] = {
            "cam_x": 0,
            "cam_y": 0,
            "zoom": DEFAULT_ZOOM_INDEX,
            "auto_center": True,
            "show_names": True,
            "view_w": DEFAULT_VIEW_W,
            "view_h": DEFAULT_VIEW_H,
            "_zoom_configs": None,
        }
    return _viewports[viewport_id]


def remove_viewport(viewport_id):
    _viewports.pop(viewport_id, None)


# === 줌 설정 빌더 ===

def build_zoom_configs(room_count, map_w=400, map_h=400,
                       view_w=None, view_h=None, zoom_scales=None):
    """
    맵 크기 비례 줌 레벨 생성.

    Args:
        room_count: 방/location 수 (그리드 크기 기준)
        map_w, map_h: 맵 실제 범위 (비율 결정)
        view_w, view_h: 뷰포트 크기
        zoom_scales: 줌 배율 리스트

    Returns:
        [{"grid_w": int, "grid_h": int}, ...]
    """
    if view_w is None:
        view_w = DEFAULT_VIEW_W
    if view_h is None:
        view_h = DEFAULT_VIEW_H
    if zoom_scales is None:
        zoom_scales = DEFAULT_ZOOM_SCALES

    map_aspect = max(map_w, 1) / max(map_h, 1)
    base = max(room_count * 4, 20)

    configs = []
    for scale in zoom_scales:
        s = max(1, int(base * scale))
        if map_aspect >= 1.0:
            gw = int(s * map_aspect)
            gh = s
        else:
            gw = s
            gh = int(s / map_aspect)
        configs.append({"grid_w": max(view_w, gw), "grid_h": max(view_h, gh)})

    # 마지막(최대 줌아웃) = 뷰포트 크기 강제
    configs[-1] = {"grid_w": view_w, "grid_h": view_h}
    return configs


# === 스크롤/줌 조작 ===

def scroll(viewport_id, direction, step=None):
    """뷰포트 스크롤"""
    vp = get_viewport(viewport_id)
    if step is None:
        step = DEFAULT_SCROLL_STEP

    vp["auto_center"] = False
    if direction == "left":
        vp["cam_x"] -= step
    elif direction == "right":
        vp["cam_x"] += step
    elif direction == "up":
        vp["cam_y"] -= step
    elif direction == "down":
        vp["cam_y"] += step
    elif direction == "center":
        vp["auto_center"] = True


def zoom(viewport_id, direction):
    """뷰포트 줌"""
    vp = get_viewport(viewport_id)
    configs = vp.get("_zoom_configs")
    if not configs:
        return

    max_zoom = len(configs) - 1
    if direction == "in" and vp["zoom"] > 0:
        vp["zoom"] -= 1
    elif direction == "out" and vp["zoom"] < max_zoom:
        vp["zoom"] += 1


def toggle_names(viewport_id):
    """지형 명칭 표시 토글"""
    vp = get_viewport(viewport_id)
    vp["show_names"] = not vp.get("show_names", True)
