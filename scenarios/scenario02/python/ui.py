# ui.py - UI 훅 함수
#
# C#에서 호출하는 UI 관련 Python 훅
# - get_header(): 상단 정보 (시간/날씨)
# - get_footer(): 하단 정보 (상태바)
# - get_action_text(): 행동 옵션 BBCode 생성
# - ui_get_move_confirm_message(): 이동 확인 다이얼로그 메시지

import morld
import lighting
from ui_style import (
    MUTED, HIGHLIGHT, INFO, DANGER, SUCCESS, WARNING, ACCENT,
    STAT_NORMAL, STAT_CAUTION, STAT_DANGER,
    c, style_muted, style_highlight, style_info,
    style_danger, style_success, style_warning, style_section,
)

MILLIS_PER_MINUTE = 60_000
MILLIS_PER_HOUR = 3_600_000


# ========================================
# 구분선 (즉시 출력)
# ========================================

def divider(color: str = MUTED, length: int = 20) -> str:
    """
    구분선 반환 (즉시 출력 태그 포함)

    Args:
        color: 구분선 색상 (기본: gray)
        length: 구분선 길이 (기본: 20)

    Returns:
        [!][color=...]{구분선}[/color][/!]
    """
    line = "─" * length
    return f"[!][color={color}]{line}[/color][/!]"


def loading_screen(callback, text="로딩 중..."):
    """
    로딩 화면 표시 후 callback 실행 (yield용)

    Animlog lock 모드 + callback 패턴:
    1. lock 모드로 header/footer 가림 (레터박스)
    2. 로딩 텍스트 즉시 표시
    3. 0.1초 대기 (화면 렌더링 보장)
    4. callback 실행 (동기, 화면은 로딩 텍스트 유지)

    Args:
        callback: 로딩 중 실행할 함수 (인자 없음)
        text: 로딩 화면에 표시할 텍스트

    Usage:
        def do_load():
            load_chapter("chapter_1")
        yield ui.loading_screen(do_load)
    """
    anim = Animlog()
    anim.text(f"\n\n\n[center]{text}[/center]", append=False, speed=9999)
    anim.wait(0.1)
    anim.callback(callback)
    return anim.play(mode="lock")


# ========================================
# UI 표시 설정
# ========================================

_show_header = True
_show_footer = True
_ui_locked = False
_darkness_masking_enabled = False  # 기본 비활성화, 챕터에서 명시적으로 활성화


def set_show_header(show: bool):
    """헤더 UI 표시 설정 (False면 숨김)"""
    global _show_header
    _show_header = show


def set_show_footer(show: bool):
    """푸터 UI 표시 설정 (False면 숨김)"""
    global _show_footer
    _show_footer = show


def is_header_visible() -> bool:
    """헤더 UI 표시 여부"""
    return _show_header


def is_footer_visible() -> bool:
    """푸터 UI 표시 여부"""
    return _show_footer


def set_ui_lock(locked: bool):
    """
    UI Lock 설정

    Lock이 켜지면 모든 Focus 타입에서 레터박스 스타일 강제 적용.
    인벤토리/퀘스트/설정 메뉴가 구분선으로 가려짐.
    챕터 0 등에서 조작 제한에 사용.

    Args:
        locked: True면 Lock (레터박스 강제), False면 일반 모드
    """
    global _ui_locked
    _ui_locked = locked


def is_ui_locked() -> bool:
    """UI Lock 상태 여부"""
    return _ui_locked


def set_darkness_masking(enabled: bool):
    """
    어둠 마스킹 on/off 설정

    어두운 곳에서 링크/선택지를 ■로 마스킹하는 기능의 활성화 여부.
    프롤로그나 특정 Dialog 등에서 False로 설정하면 밝기와 무관하게 마스킹 해제.

    Args:
        enabled: True면 활성화 (기본값), False면 비활성화
    """
    global _darkness_masking_enabled
    _darkness_masking_enabled = enabled


def is_darkness_masking_enabled() -> bool:
    """어둠 마스킹 활성화 여부"""
    return _darkness_masking_enabled


# ========================================
# Tab 뷰 전환 시스템
# ========================================
# C#에서 호출하는 탭 관련 Python 훅
# - get_max_tab(focus_type, target_unit_id?): 최대 탭 인덱스 (0=탭 없음)
# - get_tab_content(focus_type, tab, target_unit_id?): 탭 콘텐츠 (None→기존 렌더링)
# - get_tab_labels(focus_type, target_unit_id?): 탭 라벨 리스트

# 현재 렌더 컨텍스트 (C#에서 FlushDisplay 시작 시 설정)
_render_context = {
    "focus_type": "Situation",
    "view_tab": 0,
    "target_unit_id": None,
}


def _set_render_context(focus_type, view_tab, target_unit_id=None):
    """C#에서 FlushDisplay 시 호출 — 현재 Focus 정보 저장 (header 탭 라벨용)"""
    _render_context["focus_type"] = focus_type
    _render_context["view_tab"] = view_tab
    _render_context["target_unit_id"] = target_unit_id


def _can_use_map():
    """플레이어가 지도를 사용할 수 있는지 확인 (can:map 또는 지역별 지도 보유 또는 던전)"""
    try:
        player_id = morld.get_player_id()
        if player_id is None:
            return False

        current_loc = morld.get_unit_location(player_id)

        # 던전 region이면 항상 맵 사용 가능
        if current_loc:
            try:
                from instant_dungeon.manager import get_dungeon_for_region
                dungeon_id, _ = get_dungeon_for_region(current_loc[0])
                if dungeon_id is not None:
                    return True
            except ImportError:
                pass

        props = morld.get_actual_props(player_id)
        if props.get("can:map", 0) >= 1:
            return True
        if current_loc:
            region_map_props = {
                0: "can:map:mansion",
                1: "can:map:forest",
                2: "can:map:city",
            }
            map_prop = region_map_props.get(current_loc[0])
            if map_prop and props.get(map_prop, 0) >= 1:
                return True
    except Exception:
        pass
    return False


def _get_situation_tabs():
    """Situation Focus의 탭 목록 (동적: 지도 아이템 보유 시만 지도 탭 추가)"""
    tabs = [("주변", None)]  # (라벨, 렌더 함수 또는 None=기존 렌더링)
    if _can_use_map():
        tabs.append(("지도", _render_map_tab))
    # 분대 탭은 파티 구현 후 추가
    return tabs


def get_max_tab(focus_type, target_unit_id=None):
    """
    해당 Focus에서 사용 가능한 최대 탭 인덱스 (0 = 탭 없음)

    Args:
        focus_type: Focus 타입 문자열 ("Situation", "Unit" 등)
        target_unit_id: 대상 유닛 ID (Unit Focus에서 사용)

    Returns:
        int: 최대 탭 인덱스 (0이면 탭 비활성화)
    """
    if focus_type == "Situation":
        return len(_get_situation_tabs()) - 1
    elif focus_type == "Unit":
        if target_unit_id is not None and _is_character(target_unit_id):
            return 1  # 대화(0) / 스탯(1)
    return 0


def get_tab_content(focus_type, tab, target_unit_id=None):
    """
    탭별 콘텐츠 반환 (None → 기존 C# 렌더링 사용)

    Args:
        focus_type: Focus 타입 문자열
        tab: 탭 인덱스
        target_unit_id: 대상 유닛 ID

    Returns:
        str or None: 탭 콘텐츠 BBCode 문자열, None이면 기존 렌더링
    """
    if focus_type == "Situation":
        tabs = _get_situation_tabs()
        if 0 <= tab < len(tabs):
            render_fn = tabs[tab][1]
            return render_fn() if render_fn else None
    elif focus_type == "Unit":
        if tab == 0:
            return None  # 기존 RenderUnit
        if tab == 1:
            return _render_stat_tab(target_unit_id)
    return None


def get_tab_labels(focus_type, target_unit_id=None):
    """
    콘텐츠 상단에 표시할 탭 라벨 리스트

    Args:
        focus_type: Focus 타입 문자열
        target_unit_id: 대상 유닛 ID

    Returns:
        list[str]: 탭 라벨 리스트 (비어있으면 탭 표시 안함)
    """
    if focus_type == "Situation":
        return [label for label, _ in _get_situation_tabs()]
    elif focus_type == "Unit":
        if target_unit_id is not None and _is_character(target_unit_id):
            return ["대화", "스탯"]
    return []


def _is_character(unit_id):
    """유닛이 캐릭터(NPC)인지 확인"""
    try:
        info = morld.get_unit_info(unit_id)
        if info and not info.get("is_object", False):
            return True
    except Exception:
        pass
    return False


def _render_map_tab():
    """
    지도 탭 콘텐츠 — 2D 뷰포트 기반 맵

    map_coords의 2D 좌표를 사용하여 그리드 렌더링.
    좌표가 없는 region은 기존 텍스트 리스트로 폴백.
    던전 region에서는 던전 맵 렌더러로 분기.
    """
    try:
        import map_coords
        player_id = morld.get_player_id()
        if player_id is None:
            return "지도를 표시할 수 없습니다."

        current_loc = morld.get_unit_location(player_id)
        if current_loc is None:
            return "현재 위치를 알 수 없습니다."

        region_id, current_local = current_loc

        # 던전 region → 던전 맵 렌더러
        try:
            from instant_dungeon.manager import get_dungeon_for_region
            dungeon_id, dungeon_info = get_dungeon_for_region(region_id)
            if dungeon_info:
                return _render_dungeon_map_tab(dungeon_info, dungeon_id,
                                                region_id, current_local, player_id)
        except ImportError:
            pass

        # 2D 좌표 조회
        all_coords = map_coords.get_all(region_id)
        if not all_coords:
            return _render_map_tab_fallback(region_id, current_local, player_id)

        return _render_region_map(region_id, current_local, player_id, all_coords)
    except Exception as e:
        print(f"[ui] _render_map_tab error: {e}")
        return f"지도 오류: {e}"


def _render_map_tab_fallback(region_id, current_local, player_id):
    """좌표가 없는 region용 텍스트 리스트 폴백"""
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return "지역 정보를 불러올 수 없습니다."

    lines = [f"[b]지도 - {region_info['name']}[/b]", ""]
    for loc in sorted(region_info["locations"], key=lambda x: x["id"]):
        loc_id = loc["id"]
        name = loc.get("name", "???")
        if loc_id == current_local:
            lines.append(f"  {style_highlight(f'> {name}')} {style_muted('(현재 위치)')}")
        else:
            lines.append(f"  - [url=move:{region_id}:{loc_id}]{name}[/url]")
    return "\n".join(lines)


def _render_region_map(region_id, current_local, player_id, all_coords):
    """2D 뷰포트 기반 region 맵 렌더링 — common/region_map 위임"""
    import region_map
    result = region_map.render_region_map(
        region_id, current_local, player_id, all_coords,
        show_characters=True
    )
    if result is None:
        return _render_map_tab_fallback(region_id, current_local, player_id)
    return result


# ========================================
# 던전 맵 렌더러
# ========================================

# 방 타입별 기호 (BBCode 태그 충돌 방지 — 대괄호 사용 안 함)
_ROOM_SYMBOLS = {
    "start":       "◇",  # 입구
    "boss":        "★",  # 보스
    "treasure":    "◆",  # 보물
    "normal":      "●",  # 일반
    "stairs_down": "▽",  # 하층 계단
    "stairs_up":   "△",  # 상층 계단
}

# 공통 뷰포트/렌더링 상수 (grid_viewport/grid_renderer에서 가져옴)
from grid_viewport import (
    get_viewport as _gv_get_viewport, build_zoom_configs as _gv_build_zoom_configs,
    scroll as _gv_scroll, zoom as _gv_zoom, toggle_names as _gv_toggle_names,
    DEFAULT_VIEW_W as _VIEW_W, DEFAULT_VIEW_H as _VIEW_H,
    DEFAULT_SCROLL_STEP as _SCROLL_STEP,
)
from grid_renderer import MAP_FONT as _MAP_FONT


def _get_active_map_viewport_id():
    """현재 활성 맵 뷰포트 ID 반환 (던전 또는 region 맵)"""
    player_id = morld.get_player_id()
    if not player_id:
        return None
    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return None
    region_id = current_loc[0]

    # 던전 region이면 던전 뷰포트
    try:
        from instant_dungeon.manager import get_dungeon_for_region
        dungeon_id, dungeon_info = get_dungeon_for_region(region_id)
        if dungeon_info:
            vp_id = f"dungeon_{dungeon_id}"
            vp = _gv_get_viewport(vp_id)
            if vp.get("_initialized"):
                return vp_id
    except ImportError:
        pass

    # region 맵 뷰포트
    vp_id = f"region_map_{region_id}"
    vp = _gv_get_viewport(vp_id)
    if vp.get("_initialized"):
        return vp_id
    return None


def map_scroll(direction):
    """맵 스크롤 (URL 핸들러에서 호출)"""
    vp_id = _get_active_map_viewport_id()
    if vp_id:
        _gv_scroll(vp_id, direction)


def map_toggle_names():
    """지형 명칭 표시 토글 (URL 핸들러에서 호출)"""
    vp_id = _get_active_map_viewport_id()
    if vp_id:
        _gv_toggle_names(vp_id)


def map_zoom(direction):
    """맵 줌 (URL 핸들러에서 호출)"""
    vp_id = _get_active_map_viewport_id()
    if vp_id:
        _gv_zoom(vp_id, direction)


# 텍스트 유틸 — common/text_utils.py에서 가져옴 (하위 호환 래핑)
from text_utils import char_width as _char_width, str_width as _str_width, truncate_to_width as _truncate_to_width


def _render_dungeon_map_tab(dungeon_info, dungeon_id, region_id, current_local, player_id):
    """
    던전 맵 탭 — 2D 그리드 기반 BBCode 렌더링

    BSP 좌표 → 텍스트 그리드 매핑 → FoW 적용 → BBCode 출력
    다층 던전: 현재 층 렌더링 + 층 전환 헤더
    캐릭터는 코드네임(A,B,C...)으로 맵에 표시, 아래 범례에 풀네임
    """
    try:
        from instant_dungeon import fog
        from instant_dungeon.fog import HIDDEN, VISIBLE, REVEALED
        from instant_dungeon.manager import get_floor_for_region

        # v2: floors_generated dict 기반
        floors_generated = dungeon_info.get("floors_generated", {})
        current_floor = None
        floor_info = get_floor_for_region(dungeon_id, region_id)

        if floor_info:
            rooms = floor_info.get("rooms", [])
            corridors = floor_info.get("corridors", [])
            locations = floor_info.get("locations", {})
            current_floor = floor_info.get("floor", 0)
            fog_id = f"{dungeon_id}_F{current_floor}"
        elif not floors_generated:
            # 입구만 생성된 상태 (아직 expand 안 됨)
            return "던전 내부를 탐색 중..."
        else:
            return "현재 층 정보를 찾을 수 없습니다."

        if not rooms:
            return "던전 정보가 없습니다."

        # 다층 데이터 (층 전환 UI용)
        floors_data = sorted(floors_generated.values(), key=lambda f: f.get("floor", 0)) if floors_generated else None

        # 현재 방 ID (location_id → room_id 역매핑)
        current_room_id = None
        loc_to_room = {}
        for rid, lid in locations.items():
            loc_to_room[lid] = rid
            if lid == current_local:
                current_room_id = rid

        # FoW 갱신 + 상태 조회 (다층: fog_id = dungeon_id_F{floor})
        if current_room_id is not None:
            fog.update_fog(fog_id, current_room_id)
        fog_state = fog.get_fog_state(fog_id)
        adjacency = fog.get_adjacency(fog_id)

        # BSP 범위 계산 (줌 configs보다 먼저 — 비율 결정에 필요)
        bsp_max_x = max(r.x + r.w for r in rooms)
        bsp_max_y = max(r.y + r.h for r in rooms)
        bsp_max_x = max(bsp_max_x, 1)
        bsp_max_y = max(bsp_max_y, 1)

        # 줌 레벨에 따른 그리드 크기 (BSP 실제 비율 반영)
        _zoom_configs = _gv_build_zoom_configs(len(rooms), bsp_max_x, bsp_max_y)
        _vp_id = f"dungeon_{dungeon_id}"
        _vp_temp = _gv_get_viewport(_vp_id)
        _vp_temp["_zoom_configs"] = _zoom_configs
        if _vp_temp.get("_initialized") is None:
            _vp_temp["_initialized"] = True
        _zoom_cfg = _zoom_configs[min(_vp_temp["zoom"], len(_zoom_configs) - 1)]
        grid_w = _zoom_cfg["grid_w"]
        grid_h = _zoom_cfg["grid_h"]

        # 방 중심 → 그리드 좌표 매핑
        positions = {}
        for room in rooms:
            cx = (room.x + room.w // 2)
            cy = (room.y + room.h // 2)
            # 가장자리 1셀 마진만 유지
            gx = int(cx * (grid_w - 2) / bsp_max_x) + 1
            gy = int(cy * (grid_h - 2) / bsp_max_y) + 1
            gx = max(1, min(grid_w - 2, gx))
            gy = max(1, min(grid_h - 2, gy))
            positions[room.id] = (gx, gy)

        # 충돌 해결 (같은 좌표에 여러 방 → 밀어내기)
        occupied = {}
        for room_id, (gx, gy) in list(positions.items()):
            key = (gx, gy)
            while key in occupied:
                gx += 4
                if gx >= grid_w - 4:
                    gx = 3
                    gy += 2
                key = (gx, gy)
            occupied[key] = room_id
            positions[room_id] = (gx, gy)

        # ── 캐릭터 조회 + 코드네임 할당 ──
        # VISIBLE 방에 있는 캐릭터 수집, 순서대로 A, B, C... 할당
        room_chars = {}      # room_id → [(name, is_creature, codename)]
        codename_legend = [] # [(codename, name, is_creature)]
        codename_idx = 0

        for room in rooms:
            vis = fog_state.get(room.id, HIDDEN)
            if vis < VISIBLE:
                continue
            loc_id = locations.get(room.id)
            if loc_id is None:
                continue
            unit_ids = morld.get_characters_at_location(region_id, loc_id)
            chars = []
            for uid in unit_ids:
                if uid == player_id:
                    continue
                info = morld.get_unit_info(uid)
                if info and not info.get("is_object", False):
                    name = info.get("name", "?")
                    is_creature = info.get("is_creature", False)
                    codename = chr(ord('A') + codename_idx) if codename_idx < 26 else '?'
                    codename_idx += 1
                    chars.append((name, is_creature, codename))
                    codename_legend.append((codename, name, is_creature))
            if chars:
                room_chars[room.id] = chars

        # ── 그리드 초기화 + 지도 외곽선 ──
        grid = [[' '] * grid_w for _ in range(grid_h)]
        grid_meta = [[None] * grid_w for _ in range(grid_h)]

        # 지도 외곽선 (내부 그리드 가장자리)
        for x in range(1, grid_w - 1):
            grid[0][x] = '─'
            grid[grid_h - 1][x] = '─'
            grid_meta[0][x] = ("map_border", 0, False, False, 0)
            grid_meta[grid_h - 1][x] = ("map_border", 0, False, False, 0)
        for y in range(1, grid_h - 1):
            grid[y][0] = '│'
            grid[y][grid_w - 1] = '│'
            grid_meta[y][0] = ("map_border", 0, False, False, 0)
            grid_meta[y][grid_w - 1] = ("map_border", 0, False, False, 0)
        grid[0][0] = '┌'; grid[0][grid_w - 1] = '┐'
        grid[grid_h - 1][0] = '└'; grid[grid_h - 1][grid_w - 1] = '┘'
        for corner in [(0, 0), (0, grid_w - 1), (grid_h - 1, 0), (grid_h - 1, grid_w - 1)]:
            grid_meta[corner[0]][corner[1]] = ("map_border", 0, False, False, 0)

        # ── 복도 + Bridge 그리기 (발견된 것만) ──
        bridges = floor_info.get("bridges", []) if floors_data else dungeon_info.get("bridges", [])
        all_connections = list(corridors) + list(bridges or [])
        current_adj = adjacency.get(current_room_id, set()) if current_room_id is not None else set()
        for conn in all_connections:
            vis_a = fog_state.get(conn.room_a, HIDDEN)
            vis_b = fog_state.get(conn.room_b, HIDDEN)
            both_visible = vis_a >= VISIBLE and vis_b >= VISIBLE
            was_revealed = fog.is_corridor_revealed(fog_id, conn.room_a, conn.room_b)
            if both_visible or was_revealed:
                ax, ay = positions.get(conn.room_a, (0, 0))
                bx, by = positions.get(conn.room_b, (0, 0))
                dim = not both_visible
                # 현재 방 ↔ 인접 방 경로 하이라이트
                is_active = (
                    current_room_id is not None
                    and ((conn.room_a == current_room_id and conn.room_b in current_adj)
                         or (conn.room_b == current_room_id and conn.room_a in current_adj))
                )
                _draw_corridor(grid, ax, ay, bx, by, dim=dim, highlight=is_active, grid_w=grid_w, grid_h=grid_h)

        # ── 방 그리기 (모든 방 — HIDDEN은 ·, REVEALED은 흐리게, VISIBLE은 밝게) ──
        for room in rooms:
            vis = fog_state.get(room.id, HIDDEN)
            gx, gy = positions[room.id]
            is_current = (room.id == current_room_id)
            is_adjacent = room.id in adjacency.get(current_room_id, set()) if current_room_id is not None else False

            if vis == HIDDEN:
                symbol = "·"
            elif is_current:
                symbol = "@"
            else:
                symbol = _ROOM_SYMBOLS.get(room.room_type, "?")

            # 방 기호 배치
            if 0 <= gx < grid_w and 0 <= gy < grid_h:
                grid[gy][gx] = symbol
                grid_meta[gy][gx] = ("room", room.id, is_current, is_adjacent, vis)

            # 캐릭터 코드네임 (방 기호 오른쪽에 배치)
            if room.id in room_chars:
                offset = 1
                while gx + offset < grid_w and grid_meta[gy][gx + offset] is not None:
                    offset += 1
                for _name, _is_creature, codename in room_chars[room.id]:
                    cx = gx + offset
                    if 0 <= cx < grid_w and 0 <= gy < grid_h and grid[gy][cx] == ' ':
                        grid[gy][cx] = codename
                        grid_meta[gy][cx] = ("char", room.id, _is_creature, False, vis)
                    offset += 1

        # ── BBCode 생성 ──
        lines = []
        fog_mode = fog.get_fog_mode(dungeon_id)
        mode_label = {"volatile": "안개", "permanent": "탐험", "none": "전체"}.get(fog_mode, fog_mode)
        room_count = sum(1 for v in fog_state.values() if v >= VISIBLE)
        # 헤더 — 층 전환 UI
        header = "[!][b]던전 지도[/b]"
        if floors_data and len(floors_data) > 1:
            floor_tabs = []
            for fd in floors_data:
                f_num = fd["floor"]
                label = f"{f_num + 1}F"
                if f_num == current_floor:
                    floor_tabs.append(c("#ffff00", f"▶{label}"))
                else:
                    # 다른 층의 입구 location으로 이동 (계단 통해야 하지만 맵에서 조회용)
                    floor_tabs.append(style_muted(label))
            header += "  " + " ".join(floor_tabs)
        header += f"  {style_muted(f'{mode_label} | 발견 {room_count}/{len(rooms)}')}"
        lines.append(header)

        # 현재 위치 풀네임 표시
        if current_room_id is not None:
            cur_loc_id = locations.get(current_room_id)
            if cur_loc_id is not None:
                cur_info = morld.get_location_info(region_id, cur_loc_id)
                cur_name = cur_info.get("name", "") if cur_info else ""
                if cur_name:
                    lines.append(f"  {c('#ffff00', '@')} {c('#ffff00', cur_name)}")

        # ── 뷰포트 계산 ──
        vp = _gv_get_viewport(_vp_id)
        zoom_cfg = _zoom_configs[min(vp["zoom"], len(_zoom_configs) - 1)]
        grid_w = zoom_cfg["grid_w"]
        grid_h = zoom_cfg["grid_h"]
        if vp["auto_center"] and current_room_id is not None and current_room_id in positions:
            px, py = positions[current_room_id]
            vp["cam_x"] = px - _VIEW_W // 2
            vp["cam_y"] = py - _VIEW_H // 2

        # 뷰포트 범위 클램핑
        # 그리드가 뷰포트보다 작으면 자동 중앙 (스크롤 불가)
        # 그리드가 뷰포트보다 크면 그리드 내에서만 이동 (빈 공간 진입 불가)
        # overscroll=True 시 뷰포트 절반만큼 오버스크롤 허용
        _overscroll = False  # 옵션: True면 가장자리가 중앙까지 올 수 있음
        if grid_w <= _VIEW_W:
            vp["cam_x"] = (grid_w - _VIEW_W) // 2  # 중앙 고정
        elif _overscroll:
            half_w = _VIEW_W // 2
            vp["cam_x"] = max(-half_w, min(grid_w - half_w, vp["cam_x"]))
        else:
            vp["cam_x"] = max(0, min(grid_w - _VIEW_W, vp["cam_x"]))

        if grid_h <= _VIEW_H:
            vp["cam_y"] = (grid_h - _VIEW_H) // 2  # 중앙 고정
        elif _overscroll:
            half_h = _VIEW_H // 2
            vp["cam_y"] = max(-half_h, min(grid_h - half_h, vp["cam_y"]))
        else:
            vp["cam_y"] = max(0, min(grid_h - _VIEW_H, vp["cam_y"]))
        vx, vy = vp["cam_x"], vp["cam_y"]

        # 스크롤 컨트롤 (한계 도달 또는 그리드≤뷰포트 시 회색)
        if grid_w <= _VIEW_W:
            can_left = can_right = False
        elif _overscroll:
            can_left = vx > -(_VIEW_W // 2)
            can_right = vx < grid_w - (_VIEW_W // 2)
        else:
            can_left = vx > 0
            can_right = vx < grid_w - _VIEW_W

        if grid_h <= _VIEW_H:
            can_up = can_down = False
        elif _overscroll:
            can_up = vy > -(_VIEW_H // 2)
            can_down = vy < grid_h - (_VIEW_H // 2)
        else:
            can_up = vy > 0
            can_down = vy < grid_h - _VIEW_H

        def _scroll_btn(direction, symbol, can):
            if can:
                return f"[url=map:scroll:{direction}%]{symbol}[/url]"
            return c("#555555", symbol)

        can_zoom_in = vp["zoom"] > 0                          # + = 큰 그리드 방향
        can_zoom_out = vp["zoom"] < len(_zoom_configs) - 1   # - = 작은 그리드 방향

        def _zoom_btn(direction, symbol, can):
            if can:
                return f"[url=map:zoom:{direction}%]{symbol}[/url]"
            return c("#555555", symbol)

        _show_names = vp.get("show_names", True)
        _names_icon = c("#66ccff", "Aa") if _show_names else c("#888888", "Aa")

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

        border_color = "#999999"

        # 모노스페이스 폰트 시작 (맵 그리드 정렬용)
        lines.append(f"[font={_MAP_FONT}]")

        # 뷰포트 상단 테두리
        lines.append(c(border_color, "┌" + "─" * _VIEW_W + "┐"))

        for y in range(vy, vy + _VIEW_H):
            row = ""
            _name_skip = 0  # 이름이 차지한 칸 수 (빈 칸 skip용)

            for x in range(vx, vx + _VIEW_W):
                # 이름이 차지한 빈 칸 건너뛰기
                if _name_skip > 0:
                    _name_skip -= 1
                    continue

                # 그리드 밖이면 빈 칸
                if x < 0 or x >= grid_w or y < 0 or y >= grid_h:
                    row += " "
                    continue
                meta = grid_meta[y][x]
                ch = grid[y][x]

                if meta is not None and meta[0] == "map_border":
                    row += c("#666666", ch)
                elif meta is None:
                    if ch in ('═', '║'):
                        row += c("#66ccff", ch.replace('═', '─').replace('║', '│'))
                    elif ch in ('─', '│', '┐', '└', '┘', '┌', '├', '┤', '┬', '┴', '┼'):
                        row += c("#888888", ch)
                    elif ch in ('╌', '╎'):
                        row += c("#555555", ch.replace('╌', '─').replace('╎', '│'))
                    else:
                        row += ch
                elif meta[0] == "room":
                    _, room_id, is_current, is_adjacent, vis = meta
                    loc_id = locations.get(room_id)

                    # ── 이름 수집 (심볼+이름을 하나의 URL로) ──
                    name_text = ""
                    if vis >= REVEALED and _show_names:
                        avail = 0
                        for _cx in range(x + 1, vx + _VIEW_W):
                            if 0 <= _cx < grid_w and 0 <= y < grid_h:
                                _cm = grid_meta[y][_cx]
                                if _cm is not None and _cm[0] == "room":
                                    _rv = _cm[4]
                                    if _rv >= REVEALED:
                                        break
                                elif _cm is not None and _cm[0] == "char":
                                    break
                            avail += 1
                        if avail >= 4:
                            _ri = morld.get_location_info(region_id, loc_id) if loc_id is not None else None
                            _rname = _ri.get("name", "") if _ri else ""
                            if _rname:
                                if _str_width(_rname) <= avail:
                                    name_text = _rname
                                else:
                                    name_text = _truncate_to_width(_rname, avail - 2) + ".."
                                _name_skip = _str_width(name_text)

                    # ── 심볼 + 이름 출력 ──
                    display = ch + name_text
                    if vis == HIDDEN:
                        row += c("#333333", ch)
                    elif is_current:
                        row += c("#ffff00", display)
                    elif is_adjacent and loc_id is not None:
                        row += f"[url=move:{region_id}:{loc_id}%]{display}[/url]"
                    elif vis == REVEALED:
                        row += c("#666666", display)
                    else:
                        row += c("#aaaaaa", display)

                elif meta[0] == "char":
                    _, _room_id, is_creature, _, _ = meta
                    color = "#ff6666" if is_creature else "#66ff66"
                    row += c(color, ch)
                else:
                    row += ch

            # 좌우 테두리 (항상 _VIEW_W 폭)
            lines.append(c(border_color, "│") + row + c(border_color, "│"))

        # 뷰포트 하단 테두리
        lines.append(c(border_color, "└" + "─" * _VIEW_W + "┘"))

        # 모노스페이스 폰트 끝
        lines.append("[/font]")

        # ── 범례 ──
        legend = (
            f"  {c('#ffff00', '@')}현재  "
            f"{c('#66ccff', '●')}인접  "
            f"{c('#aaaaaa', '◇')}입구  "
            f"{c('#ff6666', '★')}보스  "
            f"{c('#66ff66', '◆')}보물  "
            f"{c('#cccccc', '▽')}하층  "
            f"{c('#cccccc', '△')}상층"
        )
        lines.append(legend)

        # 캐릭터 범례
        if codename_legend:
            char_parts = []
            for codename, name, is_creature in codename_legend:
                color = "#ff6666" if is_creature else "#66ff66"
                char_parts.append(f"{c(color, codename)}={name}")
            lines.append("  " + "  ".join(char_parts))

        # ── 뷰포트 내 보이는 방 목록 ──
        visible_in_vp = []
        for room in rooms:
            vis = fog_state.get(room.id, HIDDEN)
            if vis < REVEALED:
                continue
            if room.id not in positions:
                continue
            rgx, rgy = positions[room.id]
            # 뷰포트 내인지 체크
            if not (vx <= rgx < vx + _VIEW_W and vy <= rgy < vy + _VIEW_H):
                continue
            loc_id = locations.get(room.id)
            _loc_info = morld.get_location_info(region_id, loc_id) if loc_id is not None else None
            room_name = _loc_info.get("name", "") if _loc_info else ""
            if not room_name:
                continue
            is_current = (room.id == current_room_id)
            is_adjacent = room.id in adjacency.get(current_room_id, set()) if current_room_id is not None else False
            symbol = _ROOM_SYMBOLS.get(room.room_type, "?")
            if is_current:
                symbol = "@"
            visible_in_vp.append((symbol, room_name, is_current, is_adjacent, vis, room.id, loc_id))

        if visible_in_vp:
            for symbol, room_name, is_current, is_adjacent, vis, rid, lid in visible_in_vp:
                if is_current:
                    lines.append(f"  {c('#ffff00', symbol)} {c('#ffff00', room_name)}")
                elif is_adjacent and lid is not None:
                    lines.append(f"  [url=move:{region_id}:{lid}%]{symbol} {room_name}[/url]")
                elif vis == REVEALED:
                    lines.append(f"  {c('#666666', symbol)} {c('#666666', room_name)}")
                else:
                    lines.append(f"  {c('#aaaaaa', symbol)} {c('#aaaaaa', room_name)}")

        # 층간 이동 + 나가기 링크
        if current_room_id is not None:
            current_room = None
            for room in rooms:
                if room.id == current_room_id:
                    current_room = room
                    break

            if current_room:
                action_links = []

                # 계단: 내려가기 (stairs_down → 아래 층의 stairs_up)
                if current_room.room_type == "stairs_down" and floors_data and current_floor is not None:
                    next_floor = current_floor + 1
                    for fd in floors_data:
                        if fd["floor"] == next_floor:
                            # 아래 층의 stairs_up 방 찾기
                            for r in fd["rooms"]:
                                if r.room_type == "stairs_up":
                                    target_loc = fd["locations"].get(r.id)
                                    if target_loc is not None:
                                        action_links.append(
                                            f"[url=move:{fd['region_id']}:{target_loc}]"
                                            f"{c('#ccccff', f'▽ {next_floor + 1}F로 내려가기')}[/url]"
                                        )
                                    break
                            break

                # 계단: 올라가기 (stairs_up → 위 층의 stairs_down)
                if current_room.room_type == "stairs_up" and floors_data and current_floor is not None:
                    prev_floor = current_floor - 1
                    for fd in floors_data:
                        if fd["floor"] == prev_floor:
                            for r in fd["rooms"]:
                                if r.room_type == "stairs_down":
                                    target_loc = fd["locations"].get(r.id)
                                    if target_loc is not None:
                                        action_links.append(
                                            f"[url=move:{fd['region_id']}:{target_loc}]"
                                            f"{c('#ccccff', f'△ {prev_floor + 1}F로 올라가기')}[/url]"
                                        )
                                    break
                            break

                # 입구: 나가기
                if current_room.room_type == "start":
                    ext_r = dungeon_info.get("_entrance_ext_region")
                    ext_l = dungeon_info.get("_entrance_ext_location")
                    if ext_r is not None and ext_l is not None:
                        action_links.append(
                            f"[url=move:{ext_r}:{ext_l}]{c('#ffcc00', '◇ 던전에서 나가기')}[/url]"
                        )

                if action_links:
                    lines.append("")
                    for link in action_links:
                        lines.append(f"  {link}")

        lines.append("[/!]")
        return "\n".join(lines)
    except Exception as e:
        print(f"[ui] _render_dungeon_map_tab error: {e}")
        import traceback
        try:
            traceback.print_exc()
        except Exception:
            pass
        return f"던전 지도 오류: {e}"


def _draw_corridor(grid, ax, ay, bx, by, dim=False, highlight=False, grid_w=50, grid_h=20):
    """두 점 사이 L자형 복도 그리기 (box-drawing 문자)"""
    h = grid_h
    w = grid_w
    if highlight:
        h_char = '═'
        v_char = '║'
    elif dim:
        h_char = '╌'
        v_char = '╎'
    else:
        h_char = '─'
        v_char = '│'

    # 수평 이동 (ax → bx, y=ay)
    x = ax
    step = 1 if bx > ax else -1
    while x != bx:
        if 0 <= x < w and 0 <= ay < h and grid[ay][x] == ' ':
            grid[ay][x] = h_char
        x += step

    # 수직 이동 (bx, ay → by)
    y = ay
    step = 1 if by > ay else -1
    while y != by:
        if 0 <= bx < w and 0 <= y < h and grid[y][bx] == ' ':
            grid[y][bx] = v_char
        y += step

    # 꺾이는 지점
    if ax != bx and ay != by:
        if 0 <= bx < w and 0 <= ay < h and grid[ay][bx] == ' ':
            if (bx > ax and by > ay):
                grid[ay][bx] = '┐'
            elif (bx > ax and by < ay):
                grid[ay][bx] = '┘'
            elif (bx < ax and by > ay):
                grid[ay][bx] = '┌'
            elif (bx < ax and by < ay):
                grid[ay][bx] = '└'


def _render_stat_tab(unit_id):
    """캐릭터 스탯 탭 콘텐츠"""
    try:
        info = morld.get_unit_info(unit_id)
        if not info:
            return "유닛 정보를 불러올 수 없습니다."

        name = info.get("name", "???")
        lines = []
        lines.append(f"[b]{name}[/b]")
        lines.append("")

        # 상태 (survival + needs)
        lines.append(style_section("상태"))
        try:
            import survival
            stats = survival.get_survival_stats(unit_id)
            hp = stats.get("health", 0)
            max_hp = stats.get("max_health", 100)
            sat = stats.get("satiety", 0)
            max_sat = stats.get("max_satiety", 100)
            lines.append(f"  체력   {_stat_bar(hp, max_hp)} {hp:.0f}")
            lines.append(f"  포만감 {_stat_bar(sat, max_sat)} {sat:.0f}")
        except (ImportError, Exception):
            pass

        try:
            import needs as needs_mod
            fatigue = needs_mod.get_fatigue(unit_id)
            cleanliness = needs_mod.get_cleanliness(unit_id)
            excretion = needs_mod.get_excretion(unit_id)
            lines.append(f"  피로   {_stat_bar(fatigue, 100)} {fatigue:.0f}")
            lines.append(f"  불결   {_stat_bar(cleanliness, 100)} {cleanliness:.0f}")
            lines.append(f"  배변욕 {_stat_bar(excretion, 100)} {excretion:.0f}")
        except (ImportError, Exception):
            pass
        lines.append("")

        # 장비
        lines.append(style_section("장비"))
        try:
            equipped_ids = morld.get_equipped_items(unit_id)
            if equipped_ids:
                for item_id in equipped_ids:
                    item_info = morld.get_item_info(item_id)
                    if item_info:
                        item_name = item_info.get("name", "???")
                        slot = item_info.get("equip_slot", "")
                        if slot:
                            lines.append(f"  {slot}: {item_name}")
                        else:
                            lines.append(f"  {item_name}")
            else:
                lines.append("  (장비 없음)")
        except Exception:
            lines.append("  (장비 정보 없음)")
        lines.append("")

        # 관계 (플레이어와의)
        lines.append(style_section("관계"))
        try:
            props = morld.get_unit_props(unit_id) or {}
            # 관계 prop 탐색
            aff = _find_relation_prop(props, "호감")
            reb = _find_relation_prop(props, "반발")
            sub = _find_relation_prop(props, "복종")
            des = _find_relation_prop(props, "욕망")
            lines.append(f"  호감 {aff}  반발 {reb}")
            lines.append(f"  복종 {sub}  욕망 {des}")
        except Exception:
            lines.append("  (관계 정보 없음)")
        lines.append("")

        # 뒤로 버튼
        lines.append("[url=back]◁뒤로[/url]")

        return "\n".join(lines)
    except Exception as e:
        print(f"[ui] _render_stat_tab error: {e}")
        return f"스탯 오류: {e}"


def _stat_bar(value, max_val, length=10):
    """값을 막대 바로 변환 (████░░░░)"""
    if value is None or max_val <= 0:
        return "░" * length
    ratio = max(0, min(1, value / max_val))
    filled = int(ratio * length)
    return "█" * filled + "░" * (length - filled)


def _find_relation_prop(props, relation_type):
    """관계 prop에서 값 찾기 (관계:플레이어:호감 등)"""
    for key, val in props.items():
        if key.startswith("관계:") and key.endswith(f":{relation_type}"):
            return int(val) if val else 0
    return 0


# ========================================
# Header / Footer 시스템
# ========================================

def get_time_weather_text():
    """
    시간 + 날씨 정보 텍스트 반환

    C# GameTime.ToString()과 동일한 포맷:
    "{year}년 {month}월 {day}일 ({weekday}) {hour:02d}:{minute:02d} / {weather}"

    Returns:
        str: "1년 4월 1일 (수) 20:00 / 흐림" 형식 또는 빈 문자열
    """
    try:
        time_info = morld.get_time_info()
        if not time_info:
            return ""

        # 시간 포맷팅 (C# GameTime.ToString() 동일)
        year = time_info.get("year", 1)
        month = time_info.get("month", 1)
        day = time_info.get("day", 1)
        weekday = time_info.get("weekday", "")
        hour = time_info.get("hour", 0)
        minute = time_info.get("minute", 0)
        time_str = f"{year}년 {month}월 {day}일 ({weekday}) {hour:02d}:{minute:02d}"

        # 날씨 (실외일 때만)
        weather = time_info.get("weather", "")

        # 플레이어 위치 조회 (온도/습도 공용)
        loc = None
        try:
            player_id = morld.get_player_id()
            if player_id is not None:
                loc = morld.get_unit_location(player_id)
        except Exception:
            pass

        # 온도 (temperature 모듈이 있으면 표시)
        temp_text = ""
        try:
            import temperature
            if loc:
                temp = temperature.get_temperature(loc[0], loc[1])
                if temp is not None:
                    temp_text = f" {temp:.0f}℃"
        except ImportError:
            pass

        # 습도 + 날씨 강도 (humidity 모듈이 있으면 표시)
        humidity_text = ""
        weather_display = weather
        try:
            import humidity
            weather_display = humidity.get_weather_display() or weather
            if loc:
                h = humidity.get_humidity(loc[0], loc[1])
                if h is not None:
                    humidity_text = f" 습도{h:.0f}%"
        except ImportError:
            pass

        # 혼잡도 (congestion 모듈이 있으면 표시, 혼잡 시에만)
        congestion_text = ""
        try:
            import congestion
            if loc:
                cong = congestion.get_congestion(loc[0], loc[1])
                if cong is not None and cong > 1.0:
                    congestion_text = f" {style_highlight(f'혼잡x{cong:.1f}')}"
                elif cong is not None and cong > 0.5:
                    congestion_text = f" 혼잡x{cong:.1f}"
        except ImportError:
            pass

        if weather_display:
            return f"{time_str} / {weather_display}{temp_text}{humidity_text}{congestion_text}"
        if temp_text:
            return f"{time_str}{temp_text}{humidity_text}{congestion_text}"
        return time_str
    except Exception as e:
        print(f"[ui] get_time_weather_text error: {e}")
        return ""


def get_status_text():
    """
    캐릭터 상태 텍스트 반환 (체력/포만감 바 + 상태 이상)

    Returns:
        str: 상태바 BBCode 문자열 (빈 문자열이면 표시 안함)
    """
    try:
        import survival
        player_id = morld.get_player_id()
        if player_id is None:
            return ""

        lines = []

        # 상태바 (체력, 포만감)
        status_bar = survival.get_status_bar(player_id)
        if status_bar:
            lines.append(status_bar)

        # 상태 이상 메시지
        status_msg = survival.get_status_message(player_id)
        if status_msg:
            lines.append(status_msg)

        return "\n".join(lines)
    except ImportError:
        return ""  # survival 모듈이 없으면 빈 문자열
    except Exception as e:
        print(f"[ui] get_status_text error: {e}")
        return ""


def _get_brightness_text() -> str:
    """
    현재 위치의 밝기 레벨 텍스트 반환

    Returns:
        str: "[밝음]", "[color=yellow][어두움][/color]", "[color=red][암흑][/color]"
    """
    try:
        level = lighting.get_brightness_level()
        if level == "밝음":
            return "[밝음]"
        elif level == "어두움":
            return style_highlight("[어두움]")
        else:  # 암흑
            return style_danger("[암흑]")
    except Exception as e:
        print(f"[ui] _get_brightness_text error: {e}")
        return ""


def _get_tab_label_line():
    """
    현재 Focus의 탭 라벨 줄 반환

    탭이 2개 이상일 때만 표시.
    현재 활성 탭은 [▶이름] 형식 (클릭 불가),
    비활성 탭은 [이름] 형식 (클릭으로 전환).

    Returns:
        str: "[▶주변]  [지도]" 형식 또는 빈 문자열
    """
    focus_type = _render_context["focus_type"]
    view_tab = _render_context["view_tab"]
    target_unit_id = _render_context["target_unit_id"]

    labels = get_tab_labels(focus_type, target_unit_id)
    if len(labels) == 0:
        return ""
    # TODO: 탭 1개일 때도 표시할지 검토 (현재는 1개여도 표시)
    # if len(labels) <= 1:
    #     return ""

    parts = []
    for i, label in enumerate(labels):
        if i == view_tab:
            parts.append(c(ACCENT, f"[▶{label}]"))
        else:
            parts.append(f"[url=tab:{i}%][{label}][/url]")

    return "  ".join(parts)


def get_header():
    """
    상단 헤더 반환 (위치 + 시간/날씨 정보)

    Focus 화면 최상단에 표시됩니다.
    모든 Focus 화면에서 통일된 형식으로 사용됩니다.

    Returns:
        str: "[font_size=20][위치][/font_size]\n[시간/날씨]" 형식
             또는 빈 문자열
    """
    # 헤더 숨김 상태면 빈 문자열
    if not _show_header:
        return ""

    try:
        time_info = morld.get_time_info()
        if not time_info:
            return ""

        lines = []

        # 위치 정보 (백색, 큰 글씨)
        region_name = time_info.get("region_name", "")
        location_name = time_info.get("location_name", "")
        if region_name and location_name:
            location_text = f"{region_name} - {location_name}"
        elif location_name:
            location_text = location_name
        elif region_name:
            location_text = region_name
        else:
            location_text = ""

        if location_text:
            lines.append(f"[font_size=20]{location_text}[/font_size]")

        # 시간/날씨 정보 + 밝기
        time_text = get_time_weather_text()
        brightness_text = _get_brightness_text()
        if time_text and brightness_text:
            lines.append(f"{time_text} {brightness_text}")
        elif time_text:
            lines.append(time_text)
        elif brightness_text:
            lines.append(brightness_text)

        # Pi-World 디버깅 정보 (지형 형태 + X 좌표)
        # geometry: 0 = ring (원), 1 = line (선)
        geometry = time_info.get("geometry", 0)
        location_length = time_info.get("location_length", 0)
        position_x = time_info.get("position_x", 0)
        geo_text = "선" if geometry == 1 else "원"
        lines.append(style_muted(f"[{geo_text}] X:{int(position_x)}/{int(location_length)}"))

        # 시간 정지 상태 표시
        if morld.is_time_frozen():
            lines.append(style_info("[시간 정지]"))

        return "\n".join(lines)
    except Exception as e:
        print(f"[ui] get_header error: {e}")
        return ""


def _get_environment_status_text():
    """
    플레이어의 환경 상태 텍스트 (체온/젖음/오염)

    Returns:
        str: "체온 36.5℃ | 젖음 20% | 오염 15" 형식 (빈 문자열이면 표시 안함)
    """
    try:
        player_id = morld.get_player_id()
        if player_id is None:
            return ""

        parts = []

        # 체온 (항상 표시)
        try:
            import temperature
            body_temp = temperature.get_body_temperature(player_id)
            if body_temp < 35.5:
                parts.append(style_info(f"체온 {body_temp:.1f}℃"))
            elif body_temp > 37.5:
                parts.append(style_danger(f"체온 {body_temp:.1f}℃"))
            else:
                parts.append(f"체온 {body_temp:.1f}℃")
        except ImportError:
            pass

        # 젖음 (> 0일 때만)
        try:
            import humidity
            wetness = humidity.get_unit_wetness(player_id)
            if wetness and wetness > 0:
                parts.append(style_info(f"젖음 {wetness:.0f}%"))
        except ImportError:
            pass

        # 오염 (> 0일 때만)
        try:
            import pollution
            pol = pollution.get_unit_pollution(player_id)
            if pol and pol > 0:
                parts.append(style_warning(f"오염 {pol:.0f}"))
        except ImportError:
            pass

        # 욕구 (임계치 근처일 때만 표시)
        try:
            import needs
            excretion = needs.get_excretion(player_id)
            if excretion >= 50:
                clr = STAT_DANGER if excretion >= 70 else STAT_CAUTION
                parts.append(c(clr, f"배변 {excretion:.0f}"))

            fatigue = needs.get_fatigue(player_id)
            if fatigue >= 50:
                clr = STAT_DANGER if fatigue >= 80 else STAT_CAUTION
                parts.append(c(clr, f"피로 {fatigue:.0f}"))

            cleanliness = needs.get_cleanliness(player_id)
            if cleanliness >= 50:
                clr = STAT_DANGER if cleanliness >= 70 else STAT_CAUTION
                parts.append(c(clr, f"불결 {cleanliness:.0f}"))
        except ImportError:
            pass

        return " | ".join(parts) if parts else ""
    except Exception as e:
        print(f"[ui] _get_environment_status_text error: {e}")
        return ""


def _get_movement_arrows() -> str:
    """
    Footer용 X축 이동 화살표 (2단계: «50, ‹10, ›10, »50)

    Returns:
        str: "« ‹ X=50 › »" 형태의 BBCode (빈 문자열이면 표시 안함)
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    time_info = morld.get_time_info()
    if not time_info:
        return ""

    loc_length = int(time_info.get("location_length", 0))
    if loc_length <= 0:
        return ""  # 레거시 점 location → 화살표 불필요

    cur_x = int(time_info.get("position_x", 0))
    is_ring = time_info.get("geometry", 0) == 0  # 0=ring, 1=line

    # 이동 불가 체크 (앉기/눕기)
    posture_props = morld.get_unit_props_by_type(player_id, "posture")
    if posture_props:
        posture = list(posture_props.keys())[0]
        if posture in ("sitting", "lying"):
            return ""

    parts = []

    # 왼쪽 화살표 (큰 스텝 → 작은 스텝 순)
    for step in [50, 10]:
        if is_ring:
            left_x = (cur_x - step) % loc_length
        else:
            left_x = max(0, cur_x - step)
        arrow = "«" if step == 50 else "‹"
        if left_x != cur_x:
            parts.append(f"[url=move_x:{left_x}]{arrow}[/url]")
        else:
            parts.append(style_muted(arrow))

    # 현재 위치 표시
    parts.append(f"X={cur_x}")

    # 오른쪽 화살표 (작은 스텝 → 큰 스텝 순)
    for step in [10, 50]:
        if is_ring:
            right_x = (cur_x + step) % loc_length
        else:
            right_x = min(loc_length, cur_x + step)
        arrow = "›" if step == 10 else "»"
        if right_x != cur_x:
            parts.append(f"[url=move_x:{right_x}]{arrow}[/url]")
        else:
            parts.append(style_muted(arrow))

    return " ".join(parts)


def get_footer():
    """
    하단 푸터 반환 (인벤토리 + 상태바 + 환경상태 + 자세)

    Focus 화면 최하단에 표시됩니다.
    별도 RichTextLabel로 분리되어 구분선 불필요.

    Returns:
        str: 인벤토리 + 상태바 + 환경상태 + 자세 BBCode (빈 문자열이면 표시 안함)
    """
    # 푸터 숨김 상태면 빈 문자열
    if not _show_footer:
        return ""

    lines = []
    player_id = morld.get_player_id()
    _exhausted = player_id is not None and morld.get_unit_prop(player_id, "상태:탈진")
    if _exhausted:
        lines.append(f"{style_muted('인벤토리  퀘스트')}  [url=settings]설정[/url]")
    else:
        lines.append("[url=inventory]인벤토리[/url]  [url=quest]퀘스트[/url]  [url=settings]설정[/url]")

    status_text = get_status_text()
    if status_text:
        lines.append(status_text)

    # 환경 상태 (체온/젖음/오염)
    env_text = _get_environment_status_text()
    if env_text:
        lines.append(env_text)

    # 스탠스 + 자세 토글 (한 줄)
    toggle_parts = []
    stance_text = _get_stance_text()
    if stance_text:
        toggle_parts.append(stance_text)
    posture_text = _get_posture_text()
    if posture_text:
        toggle_parts.append(posture_text)
    if toggle_parts:
        lines.append("  ".join(toggle_parts))

    # X축 이동 화살표
    movement_text = _get_movement_arrows()
    if movement_text:
        lines.append(movement_text)

    return "\n".join(lines)


# ========================================
# 이동 모드 (stance) + 은신 (stealth) — 분리 시스템
# ========================================
#
# stance: 이동 중 자세 (crouch/walk/run)
#   - stance:crouch = 1 → 50% 속도, 소음 10
#   - 기본 (없음) = walk → 100% 속도, 소음 20
#   - stance:run = 1 → 150% 속도, 소음 40
#
# stealth: 독립 ON/OFF (status:stealth)
#   - 소리 기반 자동 해제 (sound._check_stealth_break)
#
# posture: 가구 전용 (sitting/lying) — 이동 불가, 기존 유지

_STANCE_ROTATION = ["walk", "crouch", "run"]


def _get_current_stance(unit_id=None):
    """현재 이동 모드 반환"""
    if unit_id is None:
        unit_id = morld.get_player_id()
    if unit_id is None:
        return "walk"
    if morld.get_unit_prop(unit_id, "stance:crouch"):
        return "crouch"
    if morld.get_unit_prop(unit_id, "stance:run") or morld.get_unit_prop(unit_id, "이동:달리기"):
        return "run"
    return "walk"


def cycle_stance():
    """이동 모드 순환: 걷기 → 앉기 → 뛰기 (C#에서 호출)"""
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    current = _get_current_stance(player_id)

    # 가구에 앉아있으면 변경 불가
    seated_on = morld.get_unit_props_by_type(player_id, "seated_on")
    if seated_on:
        return "이동 불가"

    # 기존 stance prop 제거
    morld.clear_prop(player_id, "stance:crouch")
    morld.clear_prop(player_id, "stance:run")
    morld.clear_prop(player_id, "이동:달리기")

    # 다음 모드
    try:
        idx = _STANCE_ROTATION.index(current)
        next_stance = _STANCE_ROTATION[(idx + 1) % len(_STANCE_ROTATION)]
    except ValueError:
        next_stance = "walk"

    if next_stance == "crouch":
        morld.set_unit_prop(player_id, "stance:crouch", 1)
    elif next_stance == "run":
        morld.set_unit_prop(player_id, "stance:run", 1)

    print(f"[ui] cycle_stance: {current} -> {next_stance}")
    return next_stance


def toggle_stealth():
    """은신 ON/OFF 토글 (C#에서 호출)"""
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    from engine import stealth
    if stealth.is_unit_stealthed(player_id):
        stealth.exit_unit_stealth(player_id)
        return "은신 해제"
    else:
        stealth.enter_stealth(player_id)
        return "은신"


def _get_stance_text() -> str:
    """전투/평화 스탠스 토글 버튼 텍스트 반환"""
    import combat
    if combat.is_hostile_mode():
        return f"[url=stance:toggle]{style_danger('[전투 태세]')}[/url]"
    else:
        return f"[url=stance:toggle]{style_muted('[평화]')}[/url]"


def toggle_stance() -> str:
    """
    전투/평화 스탠스 토글

    전투 스탠스: can:attack, can:steal 활성화 (공격 액션 표시)
    평화 스탠스: can:attack, can:steal 비활성화 (공격 액션 숨김)

    Returns:
        str: 새 스탠스 이름
    """
    import combat
    current = combat.is_hostile_mode()
    combat.set_hostile_mode(not current)
    new_stance = "전투" if not current else "평화"
    print(f"[ui] toggle_stance: {'전투' if current else '평화'} -> {new_stance}")
    # on_meet 재발생 → NPC 반응
    morld.clear_player_meetings()
    return new_stance


def _get_posture_text() -> str:
    """은신 토글 + 이동 모드 표시"""
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    # 가구에 앉아있으면 자세만 표시
    posture_props = morld.get_unit_props_by_type(player_id, "posture")
    if posture_props:
        posture = list(posture_props.keys())[0]
        if posture in ("sitting", "lying"):
            posture_names = {"sitting": "앉기", "lying": "눕기"}
            return style_highlight(f"자세: {posture_names.get(posture, posture)} (이동 불가)")

    # 탈진 중 변경 불가
    if morld.get_unit_prop(player_id, "상태:탈진"):
        return style_muted("[변경 불가]")

    parts = []

    # 은신 토글
    from engine import stealth
    if stealth.is_unit_stealthed(player_id):
        parts.append(f"[url=stealth:toggle]{c('#55ff55', '[은신 해제]')}[/url]")
    else:
        parts.append(f"[url=stealth:toggle]{style_muted('[은신]')}[/url]")

    # 이동 모드 (앉기/걷기/뛰기)
    stance = _get_current_stance(player_id)
    stance_labels = {"crouch": "앉기", "walk": "걷기", "run": "뛰기"}
    label = stance_labels.get(stance, "걷기")
    parts.append(f"[url=posture:cycle]{style_muted(f'[{label}]')}[/url]")

    return "  ".join(parts)


def format_time(millis):
    """밀리초 단위 시간을 읽기 좋은 형식으로 변환"""
    total_minutes = millis // MILLIS_PER_MINUTE
    if total_minutes < 60:
        return f"{total_minutes}분"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if mins > 0:
        return f"{hours}시간 {mins}분"
    return f"{hours}시간"


def ui_get_move_confirm_message(travel_time_millis):
    """
    이동 확인 다이얼로그 메시지 생성

    C#의 ExecuteMoveWithConfirm()에서 호출됩니다.
    threshold 이상의 이동 시간일 때 표시할 메시지를 반환합니다.

    Args:
        travel_time_millis: 이동 시간 (밀리초)

    Returns:
        str: 다이얼로그에 표시할 메시지
    """
    time_text = format_time(int(travel_time_millis))
    return f"이동하는 데 {time_text}이 걸립니다. 이동하시겠습니까?"


def get_surrounding_exclude(observer_id):
    """주변 인물 표시용 exclude list 반환

    S02: 플레이어 자신 + 은신/이동 중 유닛 제외 (파티 개념 없음)
    """
    from engine import unit_filter
    location = morld.get_unit_location(observer_id)
    return unit_filter.get_exclude_list(
        observer_id,
        unit_ids=[observer_id],
        presets=["stealthed", "in_transit"],
        location=location,
    )


def _render_movement(info: dict) -> list:
    """
    이동 UI 렌더링 - Gate X 순서로 나열, 플레이어 위치 삽입

    Args:
        info: morld.get_movement_info() 반환값
    Returns:
        list[str]: BBCode 줄 목록
    """
    lines = []
    geometry = info["geometry"]  # "ring" or "line"
    player_x = info["player_x"]

    # 상태 체크
    seated = info.get("seated", False)
    player_id = morld.get_player_id()
    hiding = False
    if player_id is not None:
        props = morld.get_actual_props(player_id)
        hiding = props.get("hiding", 0) >= 1
        # 탈진 중 이동 불가
        if props.get("상태:탈진", 0):
            seated = True

    # 표시할 경로 필터링 (is_hidden 제외) 및 gate_x 순 정렬
    routes = [r for r in info["routes"] if not r["is_hidden"]]
    routes.sort(key=lambda r: r["gate_x"])

    if not routes:
        return lines

    # 헤더
    lines.append(style_info("이동 가능 지역:"))

    # 상단 구분선
    if geometry == "ring":
        lines.append(style_muted("-vvv-----------"))
    else:
        lines.append(style_muted("---------------"))

    # 플레이어 마커 결정
    if seated:
        marker = "□" if hiding else "■"
    else:
        marker = "▷" if hiding else "▶"

    # 가장 가까운 Gate 인덱스 찾기
    closest_idx = 0
    closest_dist = abs(routes[0]["gate_x"] - player_x)
    for i, route in enumerate(routes):
        dist = abs(route["gate_x"] - player_x)
        if dist < closest_dist:
            closest_dist = dist
            closest_idx = i

    for i, route in enumerate(routes):
        is_closest = (i == closest_idx)
        prefix = style_highlight(marker) if is_closest else "●"

        # 앉은 상태 또는 blocked → grey out (클릭 불가)
        if seated or route["is_blocked"]:
            if is_closest:
                lines.append(f"  {prefix}{style_muted(route['name'])}")
            else:
                lines.append(f"  {style_muted(f'- {route["name"]}')}")
        else:
            region_tag = f" [{route['region_name']}]" if route["is_region_gate"] else ""
            travel_min = route["travel_time"] // MILLIS_PER_MINUTE
            meta = f"move:{route['region_id']}:{route['local_id']}"
            lines.append(f"  [url={meta}]{prefix}{route['name']}{region_tag} ({travel_min}분)[/url]")

    # 하단 구분선
    if geometry == "ring":
        lines.append(style_muted("-^^^-----------"))
    else:
        lines.append(style_muted("---------------"))

    return lines


def get_action_text():
    """
    행동 옵션 BBCode 생성

    구조:
    - [이동] morld.get_movement_info()로 경로 데이터 → Python에서 렌더링
    - [행동:] Python에서 생성 (멍때리기, 낮잠 등)

    토글 마크업 형식 (InteractiveTextUI):
    - [toggle key=ID]헤더[content]내용[/toggle]

    Returns:
        str: 행동 옵션 BBCode 문자열 (줄바꿈으로 구분)
    """
    lines = []

    # 플레이어 상태 확인
    player_id = morld.get_player_id()
    player_posture = None
    seated_on = None
    if player_id is not None:
        # posture는 posture:sitting = 1 형태로 저장됨
        posture_props = morld.get_unit_props_by_type(player_id, "posture")
        if posture_props:
            player_posture = list(posture_props.keys())[0]  # "sitting", "lying" 등
        # seated_on은 seated_on:{object_id} = {hash} 형태
        seated_on_props = morld.get_unit_props_by_type(player_id, "seated_on")
        if seated_on_props:
            seated_on = int(list(seated_on_props.keys())[0])  # object_id

    # 이동 불가 자세 확인 (눕기/앉기)
    can_move = player_posture not in ("sitting", "lying")

    # 이동 UI 항상 표시 (이동 불가 시 grey out)
    movement_info = morld.get_movement_info()
    if movement_info is not None:
        # posture로 인한 이동 불가 상태를 movement_info에 반영
        if not can_move:
            movement_info["seated"] = True
        lines.extend(_render_movement(movement_info))

    # C#에서 나머지 행동 리스트 가져오기 (앉은 상태 등)
    default_actions = morld.get_actions_list()
    for action in default_actions:
        lines.append(action)

    # 행동 섹션 헤더
    lines.append("")
    lines.append(style_info("행동:"))

    # 눕기/앉기 상태 → "일어나기" 행동 추가 (맨 위에)
    if not can_move and seated_on is not None:
        # 오브젝트 이름 가져오기
        obj_info = morld.get_unit_info(seated_on)
        obj_name = obj_info.get("name", "오브젝트") if obj_info else "오브젝트"
        lines.append(f"  [url=call:stand_up:{seated_on}]{obj_name}에서 일어나기[/url]")

    # 시간 보내기 (토글)
    millis_of_day = morld.get_game_time()  # 밀리초 단위 (0~86,399,999)
    hour = millis_of_day // MILLIS_PER_HOUR

    spend_time_content = []
    spend_time_content.append(f"    [url=wait:{5 * MILLIS_PER_MINUTE}]누군가를 기다리기 (~5분)[/url]")
    spend_time_content.append(f"    [url=idle:{30 * MILLIS_PER_MINUTE}]멍때리기 (30분)[/url]")
    if 6 <= hour < 18:
        spend_time_content.append(f"    [url=idle:{240 * MILLIS_PER_MINUTE}]낮잠자기 (4시간)[/url]")
    else:
        spend_time_content.append(f"    {style_muted('낮잠자기 (4시간)')}")
    content_str = "\n".join(spend_time_content)
    lines.append(f"  [toggle key=spend_time]시간 보내기[content]{content_str}[/toggle]")

    # 지도 (can:map 또는 지역별 지도 prop 보유 시)
    if _can_use_map():
        lines.append("  [url=map:open]지도[/url]")

    # 상태바는 get_footer()로 분리됨 (C#에서 별도 호출)

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
#                         대화 시스템 (Dialog System)
# ════════════════════════════════════════════════════════════════════════════
#
# 세 가지 대화 타입을 제공합니다:
#
# ┌─────────────┬────────────────────────────────────────────────────────────┐
# │ Lines       │ 단답형: 조건 → 텍스트 매핑, 유저 인터랙션 없음             │
# │ (단답형)    │ - 첫 번째 만족하는 조건의 대사 출력                        │
# │             │ - "확인" 버튼만 있음                                       │
# │             │ - 예: NPC 인사말, 상태 메시지                              │
# ├─────────────┼────────────────────────────────────────────────────────────┤
# │ Sequence    │ 페이지형: 페이지가 교체되며 진행                           │
# │ (페이지형)  │ - "다음" 버튼으로 페이지 이동                              │
# │             │ - + 접두사로 연쇄 출력 (이전 내용 누적)                    │
# │             │ - 예: 나레이션, 설명문                                     │
# ├─────────────┼────────────────────────────────────────────────────────────┤
# │ Conversation│ 누적형: 히스토리가 쌓이며 진행                             │
# │ (누적형)    │ - 선택지 클릭 시 기존 텍스트 유지 + 응답 추가              │
# │             │ - 선택한 항목은 회색으로 표시                              │
# │             │ - 예: NPC 대화, 첫 만남 이벤트                             │
# └─────────────┴────────────────────────────────────────────────────────────┘
#
# 공통 인터페이스:
#   - 생성자에서 npc_name 지정 (선택)
#   - 빌더 패턴으로 내용 추가
#   - .end() 메서드로 Dialog 객체 반환 (yield용)
#
# ════════════════════════════════════════════════════════════════════════════

# 연쇄 출력 접두사 (이 문자로 시작하면 이전 페이지 누적)
CHAIN_PREFIX = "+"


# ----------------------------------------
# Lines: 단답형 대화
# ----------------------------------------
# 조건에 따라 다른 대사를 출력하는 단순 대화
# 유저 인터랙션 없이 "확인" 버튼만 표시
#
# 사용법:
#   lines = ui.Lines("세라")
#   lines.when(affection >= 80, "...다음에 또 와.", "...조심해서 가.")
#   lines.when(affection >= 50, "...또 뭐야.")
#   lines.default("...")
#   yield lines.end()
#
# 조건 평가:
#   - 위에서 아래로 순서대로 평가
#   - 첫 번째 True인 조건의 대사 출력
#   - 모든 조건 불만족 시 default 대사 출력
# ----------------------------------------

class Lines:
    """
    단답형 대화 빌더

    조건에 따른 단일 응답을 출력합니다.
    유저 인터랙션 없이 "확인" 버튼만 표시됩니다.
    """

    def __init__(self, npc_name: str = None):
        """
        Args:
            npc_name: NPC 이름 (대사 앞에 [이름] 자동 추가)
        """
        self.npc_name = npc_name
        self._conditions = []
        self._default_lines = None

    def when(self, condition: bool, *lines):
        """
        조건부 대사 추가

        Args:
            condition: 조건 (bool로 평가되는 값)
            *lines: 조건이 참일 때 표시할 대사들

        Returns:
            self (체이닝용)
        """
        self._conditions.append((condition, lines))
        return self

    def default(self, *lines):
        """
        기본 대사 설정 (모든 조건 불만족 시)

        Args:
            *lines: 기본 대사들

        Returns:
            self (체이닝용)
        """
        self._default_lines = lines
        return self

    def end(self, button_text: str = "확인"):
        """
        대화 종료 및 Dialog 객체 반환

        Args:
            button_text: 종료 버튼 텍스트

        Returns:
            morld.dialog() 객체 (yield용)
        """
        # 첫 번째 만족하는 조건 찾기
        selected_lines = None
        for condition, lines in self._conditions:
            if condition:
                selected_lines = lines
                break

        # 조건 없으면 default 사용
        if selected_lines is None:
            selected_lines = self._default_lines or ("...",)

        # 텍스트 조합
        content = "\n".join(selected_lines)
        if self.npc_name:
            content = f"[{self.npc_name}]\n{content}"

        return morld.dialog(content)


# ----------------------------------------
# Sequence: 페이지형 대화
# ----------------------------------------
# 페이지 단위로 교체되며 진행하는 대화
# "다음" 버튼으로 페이지 이동, 마지막에 "확인"
#
# 사용법:
#   seq = ui.Sequence("세라")
#   seq.add("첫 번째 페이지")
#   seq.add("+두 번째 (연쇄)")   # 이전 내용 누적
#   seq.add("세 번째 (새로)")    # 새로 시작
#   yield seq.end()
#
# 연쇄 출력 (+):
#   - + 접두사: 이전 내용 유지 + 새 내용 타이핑
#   - \\+: + 리터럴 (이스케이프)
# ----------------------------------------

class Sequence:
    """
    페이지형 대화 빌더

    페이지가 교체되며 진행됩니다.
    + 접두사로 연쇄 출력(이전 내용 누적)을 지원합니다.
    """

    def __init__(self, npc_name: str = None):
        """
        Args:
            npc_name: NPC 이름 (각 페이지 앞에 [이름] 자동 추가)
        """
        self.npc_name = npc_name
        self._pages = []

    def add(self, *lines):
        """
        페이지 추가

        Args:
            *lines: 페이지 내용 (여러 줄)
                    첫 줄이 "+"로 시작하면 연쇄 출력

        Returns:
            self (체이닝용)
        """
        content = "\n".join(lines)
        if self.npc_name and not content.startswith("+") and not content.startswith("\\+"):
            content = f"[{self.npc_name}]\n{content}"
        elif self.npc_name and content.startswith("+"):
            # 연쇄 출력에서도 NPC 이름 추가 (+ 뒤에)
            content = f"+[{self.npc_name}]\n{content[1:]}"
        self._pages.append(content)
        return self

    def add_raw(self, text: str):
        """
        페이지 추가 (원본 텍스트 그대로)

        Args:
            text: 페이지 내용 (NPC 이름 자동 추가 안 함)

        Returns:
            self (체이닝용)
        """
        self._pages.append(text)
        return self

    def end(self, button_text: str = "확인"):
        """
        대화 종료 및 Dialog 객체 반환

        Args:
            button_text: 종료 버튼 텍스트 (현재 미사용, 향후 확장용)

        Returns:
            morld.dialog() 객체 (yield용)
        """
        if not self._pages:
            return morld.dialog("...")

        if len(self._pages) == 1:
            return morld.dialog(self._pages[0])

        return dialog(self._pages)


# ----------------------------------------
# dialog() 함수 (레거시 호환)
# ----------------------------------------
# Sequence 클래스의 간편 버전
# 기존 코드와의 호환성을 위해 유지
# ----------------------------------------

def _render_page(pages: list, state: dict) -> str:
    """
    현재 페이지 렌더링 (연쇄 출력 처리 포함)

    Args:
        pages: 페이지 리스트
        state: {"page": int, "accumulated": str}

    Returns:
        렌더링된 텍스트 (마지막 페이지면 버튼 없음)
    """
    idx = state["page"]
    page = pages[idx]

    # 이스케이프 처리: \+ → +
    if page.startswith("\\+"):
        page = page[1:]
        state["accumulated"] = page
        text = page
    elif page.startswith(CHAIN_PREFIX):
        # 연쇄 출력: 이전 내용 + 새 내용
        new_text = page[len(CHAIN_PREFIX):]
        if state["accumulated"]:
            text = f"[!]{state['accumulated']}\n[/!]{new_text}"
            state["accumulated"] = state["accumulated"] + "\n" + new_text
        else:
            text = new_text
            state["accumulated"] = new_text
    else:
        # 일반 페이지: 새로 시작
        text = page
        state["accumulated"] = page

    # 버튼 추가
    if idx < len(pages) - 1:
        # 다음 페이지가 있으면 "다음" 버튼
        text += "\n\n[url=@proc:next]다음[/url]"
    else:
        # 마지막 페이지면 "확인" 버튼 (다이얼로그 종료)
        text += "\n\n[url=@proc:finish]확인[/url]"

    return text


def dialog(content, **kwargs):
    """
    향상된 다이얼로그 - 문자열 또는 리스트(다 페이지) 지원

    단일 페이지:
        yield ui.dialog("텍스트")

    다 페이지 (연쇄 출력 지원):
        yield ui.dialog([
            "첫 번째 페이지",
            "+두 번째 (연쇄)",   # 이전 내용 누적, 새 내용 타이핑
            "세 번째 (새로)",    # 새로 시작
        ])

    이스케이프:
        "\\+로 시작"  # "+"를 리터럴로 사용

    Args:
        content: 문자열 또는 페이지 리스트
        **kwargs: morld.dialog()에 전달할 추가 인자

    Returns:
        Dialog 객체 (yield용)
    """
    # 문자열: 기존 동작
    if isinstance(content, str):
        return morld.dialog(content, **kwargs)

    # 리스트: autofill이 지정되면 C# 처리에 맡김
    if "autofill" in kwargs and kwargs["autofill"] not in ("off", None):
        return morld.dialog(content, **kwargs)

    # 리스트: proc 기반 다 페이지 (autofill 없거나 "off")
    pages = content
    state = {"page": 0, "accumulated": ""}

    # 첫 페이지 렌더링 (morld.dialog에 직접 전달)
    initial_text = _render_page(pages, state)

    def proc(action):
        if action == "init":
            return None  # 초기 텍스트는 이미 전달됨

        if action == "next":
            state["page"] += 1
            if state["page"] >= len(pages):
                return True  # 종료
            return _render_page(pages, state)

        if action == "finish":
            return True  # 마지막 페이지에서 확인 → 다이얼로그 종료

        return None

    # autofill="off"로 기본 버튼 비활성화 (직접 "다음" 추가)
    return morld.dialog(initial_text, autofill="off", proc=proc, **kwargs)


# ----------------------------------------
# Conversation: 누적형 대화
# ----------------------------------------
# CRPG 스타일 대화 시스템
# 선택하면 기존 텍스트 유지 + 선택 텍스트 회색 표시 + 새 응답 추가
#
# 사용법:
#   conv = ui.Conversation("세라")
#   conv.say("...일어났군.")
#   conv.say("...기억은 있나?")
#   conv.ask([
#       ("기억이 없다", "no_memory"),
#       ("여기가 어디야?", "where"),
#   ])
#   conv.respond("no_memory", "...그렇군.", "...너만 그런 건 아니다.")
#   conv.respond("where", "...저택이다.", "...숲 속에 있는.")
#   conv.ask([...])  # 다음 선택지
#   conv.say("...무리하지 마라.")  # 공통 마무리
#   yield conv.end()
#
# 메서드:
#   - say(*lines): NPC 대사 (이름 자동 추가)
#   - narration(*lines): 나레이션 (이름 없이)
#   - ask(options): 선택지 [("표시", "값"), ...]
#   - respond(value, *lines): 특정 선택에 대한 응답
#   - branch(conditions): 여러 선택 응답 {"값": ["대사"], ...}
#   - end(button_text): 다이얼로그 반환
#
# 히스토리 누적:
#   - 이미 표시된 텍스트는 [!]...[/!] 태그로 즉시 표시
#   - 새로 추가되는 텍스트만 타이핑 애니메이션
#   - 선택한 항목은 [color=gray]> 선택[/color] 형식으로 표시
#
# 중간 종료 (@exit):
#   - 선택지 값을 "@exit"로 지정하면 대화 즉시 종료
#   - respond() 없이 바로 다이얼로그가 닫힘
#   - 예: conv.ask([("계속", "continue"), ("헤어지기", "@exit")])
# ----------------------------------------

class Conversation:
    """
    누적형 대화 빌더

    CRPG 스타일로 대화가 화면에 쌓입니다.
    선택한 항목은 회색으로 표시되어 히스토리에 남습니다.
    ask() → respond() 패턴으로 분기 대화를 구성합니다.
    """

    def __init__(self, npc_name: str = None):
        """
        Args:
            npc_name: NPC 이름 (대사 앞에 [이름] 자동 추가)
        """
        self.npc_name = npc_name
        self._steps = []  # 대화 단계 리스트
        self._current_choice_id = 0  # 선택지 그룹 ID

    def say(self, *lines):
        """
        NPC 대사 추가 (무조건 표시)

        Args:
            *lines: 대사 줄들
        """
        self._steps.append({
            "type": "say",
            "lines": lines,
        })
        return self

    def narration(self, *lines):
        """
        나레이션 추가 (NPC 이름 없이)

        Args:
            *lines: 나레이션 줄들
        """
        self._steps.append({
            "type": "narration",
            "lines": lines,
        })
        return self

    def ask(self, options: list):
        """
        선택지 추가

        Args:
            options: [("표시 텍스트", "값"), ...] 형태의 리스트
        """
        self._current_choice_id += 1
        self._steps.append({
            "type": "ask",
            "options": options,
            "choice_id": self._current_choice_id,
        })
        return self

    def respond(self, choice_value: str, *lines):
        """
        특정 선택지에 대한 응답 추가

        Args:
            choice_value: ask()에서 지정한 값
            *lines: 응답 대사들
        """
        self._steps.append({
            "type": "respond",
            "choice_value": choice_value,
            "lines": lines,
        })
        return self

    def branch(self, conditions: dict):
        """
        조건부 분기 (여러 선택에 대한 응답을 한 번에)

        Args:
            conditions: {"choice_value": ["대사1", "대사2"], ...}
        """
        for choice_value, lines in conditions.items():
            self._steps.append({
                "type": "respond",
                "choice_value": choice_value,
                "lines": lines if isinstance(lines, (list, tuple)) else [lines],
            })
        return self

    def end(self, finish_text: str = "확인"):
        """
        대화 종료 및 Dialog 객체 반환

        Args:
            finish_text: 종료 버튼 텍스트

        Returns:
            morld.dialog() 객체 (yield용)
        """
        state = {
            "step": 0,
            "history": "",
            "choices": {},  # choice_id -> selected_value
            "finished": False,
            "last_content": "",  # 버튼 제외한 순수 content (타이핑 효과용)
        }

        def _format_npc_line(line):
            """NPC 이름이 있으면 첫 줄에 [이름] 추가"""
            if self.npc_name and not line.startswith("[") and not line.startswith("("):
                return f"[{self.npc_name}]\n{line}"
            return line

        def _render():
            """현재 상태에서 표시할 텍스트 생성"""
            text = ""
            pending_choices = None  # 아직 선택 안 된 선택지

            for i, step in enumerate(self._steps):
                step_type = step["type"]

                if step_type == "say":
                    # 무조건 표시
                    lines = step["lines"]
                    content = "\n".join(lines)
                    if self.npc_name:
                        content = f"[{self.npc_name}]\n" + content
                    if text:
                        text += "\n\n"
                    text += content

                elif step_type == "narration":
                    # 나레이션 (NPC 이름 없이)
                    content = "\n".join(step["lines"])
                    if text:
                        text += "\n\n"
                    text += content

                elif step_type == "ask":
                    choice_id = step["choice_id"]
                    if choice_id in state["choices"]:
                        # 이미 선택됨 - 선택한 항목 표시
                        selected = state["choices"][choice_id]
                        for label, value in step["options"]:
                            if value == selected:
                                if text:
                                    text += "\n\n"
                                text += style_muted(f"> {label}")
                                break
                    else:
                        # 아직 선택 안 됨 - 선택지 표시
                        pending_choices = step
                        break  # 여기서 멈춤

                elif step_type == "respond":
                    # 해당 선택이 있을 때만 표시
                    choice_value = step["choice_value"]
                    # 가장 최근 ask의 선택과 비교
                    for prev_step in reversed(self._steps[:i]):
                        if prev_step["type"] == "ask":
                            choice_id = prev_step["choice_id"]
                            if state["choices"].get(choice_id) == choice_value:
                                lines = step["lines"]
                                content = "\n".join(lines)
                                if self.npc_name:
                                    content = f"[{self.npc_name}]\n" + content
                                if text:
                                    text += "\n\n"
                                text += content
                            break

            # 버튼 추가 전 content 저장 (타이핑 효과용)
            state["last_content"] = text

            # 선택지 또는 종료 버튼 추가
            if pending_choices:
                if text:
                    text += "\n\n"
                for label, value in pending_choices["options"]:
                    text += f"[url=@proc:choice_{pending_choices['choice_id']}_{value}]{label}[/url]\n"
            elif not state["finished"]:
                # 모든 단계 완료 - 종료 버튼
                if text:
                    text += "\n\n"
                text += f"[url=@proc:finish]{finish_text}[/url]"

            # 기존 히스토리는 즉시 표시, 새 부분만 타이핑
            if state["history"] and text.startswith(state["history"]):
                new_part = text[len(state["history"]):]
                if new_part.startswith("\n\n"):
                    new_part = new_part[2:]
                return f"[!]{state['history']}[/!]\n\n{new_part}"
            return text

        def _proc(action):
            if action == "finish":
                state["finished"] = True
                return True  # 다이얼로그 종료

            if action.startswith("choice_"):
                # choice_{id}_{value} 형식
                parts = action.split("_", 2)
                if len(parts) >= 3:
                    choice_id = int(parts[1])
                    choice_value = parts[2]

                    # @exit: 대화 즉시 종료
                    if choice_value == "@exit":
                        state["finished"] = True
                        return True

                    # 선택한 항목의 label 찾기
                    selected_label = None
                    for step in self._steps:
                        if step["type"] == "ask" and step["choice_id"] == choice_id:
                            for label, value in step["options"]:
                                if value == choice_value:
                                    selected_label = label
                                    break
                            break

                    # 선택 전 content + 선택한 항목 표시를 history에 저장
                    # (타이핑 효과: 이전 내용 + 선택지는 즉시 표시, 응답만 타이핑)
                    history_text = state["last_content"]
                    if selected_label:
                        # _render와 동일한 형식으로: text가 있을 때만 \n\n 추가
                        if history_text:
                            history_text += "\n\n"
                        history_text += style_muted(f"> {selected_label}")
                    state["history"] = history_text

                    # 선택 반영
                    state["choices"][choice_id] = choice_value

                    # 새 화면 렌더링 (새 응답은 타이핑 효과 적용)
                    return _render()

            return None

        # 초기 화면
        initial = _render()
        return morld.dialog(initial, autofill="off", proc=_proc)


# ════════════════════════════════════════════════════════════════════════════
#                         애니메이션 시스템 (Animlog)
# ════════════════════════════════════════════════════════════════════════════
#
# 실시간 기반 애니메이션 시퀀스 시스템
# Dialog와 달리 시간 기반으로 자동 진행되며, 클릭 시 스킵 가능
#
# UI 모드:
#   - normal: header/footer 보이고 입력 가능 (기본)
#   - lock: header/footer 가림 (레터박스), 집중 연출용
#   - block: header/footer 보이지만 입력 불가, 전투용
#
# 사용법:
#   anim = ui.Animlog()
#   anim.text("니체는 말했다.")              # 기본 타이핑
#   anim.text("신.은.죽.었다.", delay=2.0)   # 글자당 2초
#   anim.wait(0.5)                           # 0.5초 대기
#   anim.text("새 장면", append=False)       # 화면 교체
#   anim.callback(my_func, arg1, arg2)       # Python 함수 호출
#   anim.clear()                             # 화면 클리어
#   yield anim.play(mode="lock")             # 실행 (lock 모드)
#
# ════════════════════════════════════════════════════════════════════════════


class Animlog:
    """
    애니메이션 로그 빌더 - 실시간 기반 시퀀스

    Dialog와 달리 시간 기반으로 자동 진행됩니다.
    클릭 시 즉시 스킵되며, scale로 재생 속도를 조절할 수 있습니다.
    """

    def __init__(self, npc_name: str = None):
        """
        Args:
            npc_name: NPC 이름 (텍스트 앞에 [이름] 자동 추가)
        """
        self.npc_name = npc_name
        self._steps = []

    def _format_with_name(self, text: str) -> str:
        """NPC 이름 포맷팅"""
        if self.npc_name and text:
            return f"[{self.npc_name}]\n{text}"
        return text

    def text(
        self,
        content: str,
        delay: float = None,
        speed: float = 50.0,
        append: bool = True
    ) -> "Animlog":
        """
        텍스트 표시 스텝 추가

        Args:
            content: 표시할 텍스트
            delay: 글자당 초 (설정 시 speed 무시)
            speed: 초당 글자 수 (기본 50, Dialog 타이핑과 동일)
            append: True면 이전 텍스트에 누적, False면 화면 교체

        Returns:
            self (체이닝용)
        """
        formatted = self._format_with_name(content) if not append else content
        # append=False일 때만 NPC 이름 추가 (새 화면이므로)
        if append and self.npc_name and content and not self._steps:
            # 첫 번째 스텝이면서 append=True면 이름 추가
            formatted = self._format_with_name(content)

        self._steps.append({
            "type": "text",
            "content": formatted,
            "delay": delay,
            "speed": speed,
            "append": append,
        })
        return self

    def wait(self, duration: float) -> "Animlog":
        """
        대기 스텝 추가

        Args:
            duration: 대기 시간 (초)

        Returns:
            self (체이닝용)
        """
        self._steps.append({
            "type": "wait",
            "duration": duration,
        })
        return self

    def callback(self, func, *args, **kwargs) -> "Animlog":
        """
        콜백 스텝 추가 - 애니메이션 중 Python 함수 호출

        Args:
            func: 호출할 Python 함수
            *args: 위치 인자
            **kwargs: 키워드 인자

        Returns:
            self (체이닝용)
        """
        self._steps.append({
            "type": "callback",
            "func": func,
            "args": args,
            "kwargs": kwargs,
        })
        return self

    def clear(self) -> "Animlog":
        """
        클리어 스텝 추가 - 화면 내용 삭제

        Returns:
            self (체이닝용)
        """
        self._steps.append({
            "type": "clear",
        })
        return self

    def play(self, scale: float = 1.0, mode: str = "normal"):
        """
        애니메이션 실행

        Args:
            scale: 재생 속도 배율 (기본 1.0, 설정에서 조정 가능)
            mode: UI 모드
                - "normal": header/footer 보이고 입력 가능
                - "lock": header/footer 가림 (레터박스), 집중 연출용
                - "block": header/footer 보이지만 입력 불가, 전투용

        Returns:
            morld.animlog() 객체 (yield용)
        """
        return morld.animlog(self._steps, scale=scale, mode=mode)
