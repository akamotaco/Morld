# ui.py - S04 TextUI
#
# C#의 TextUI 시스템이 호출하는 인터페이스 구현.
# S02 ui.py 호환 + S04 고유 기능.

import morld

# ========================================
# UI 상태
# ========================================

_ui_locked = False
_darkness_masking_enabled = True
_show_header = True
_show_footer = True

# 렌더 컨텍스트 (C#에서 FlushDisplay 시 설정)
_render_context = {
    "focus_type": "Situation",
    "view_tab": 0,
    "target_unit_id": None,
}


# ========================================
# C#에서 호출하는 필수 인터페이스
# ========================================

def set_ui_lock(locked: bool):
    global _ui_locked
    _ui_locked = locked


def is_ui_locked() -> bool:
    return _ui_locked


def set_darkness_masking(enabled: bool):
    global _darkness_masking_enabled
    _darkness_masking_enabled = enabled


def is_darkness_masking_enabled() -> bool:
    return _darkness_masking_enabled


def is_header_visible() -> bool:
    return _show_header


def is_footer_visible() -> bool:
    return _show_footer


def _set_render_context(focus_type, view_tab, target_unit_id=None):
    """C#에서 FlushDisplay 시 호출 — 현재 Focus 정보 저장"""
    _render_context["focus_type"] = focus_type
    _render_context["view_tab"] = view_tab
    _render_context["target_unit_id"] = target_unit_id


# ========================================
# 헤더 / 본문 / 푸터 / 액션
# ========================================

def get_header():
    """헤더 텍스트 (C#에서 호출)"""
    time_info = morld.get_time_info()
    if not time_info:
        return ""

    month = time_info.get("month", 1)
    day = time_info.get("day", 1)
    hour = time_info.get("hour", 0)
    minute = time_info.get("minute", 0)

    player_id = morld.get_player_id()
    loc_name = "???"
    if player_id:
        loc = morld.get_unit_location(player_id)
        if loc:
            region_id, loc_id = loc
            loc_info = morld.get_location_info(region_id, loc_id)
            if loc_info:
                loc_name = loc_info.get("name", "???")

    tab_line = _get_tab_label_line()
    header = f"{month}월 {day}일 {hour:02d}:{minute:02d} | {loc_name}"
    if tab_line:
        header += f"\n{tab_line}"
    return header


def get_footer():
    """푸터 텍스트 (C#에서 호출)"""
    player_id = morld.get_player_id()
    if not player_id:
        return ""

    import survival, economy
    hp = survival.get_health(player_id)
    satiety = survival.get_satiety(player_id)
    money = economy.get_money(player_id)

    return f"HP:{hp}  포만감:{satiety}  소지금:{money:,}원"


def get_action_text():
    """액션 텍스트 (C#에서 호출) — 현재 위치에서 가능한 행동"""
    player_id = morld.get_player_id()
    if not player_id:
        return ""

    loc = morld.get_unit_location(player_id)
    if not loc:
        return ""

    region_id, loc_id = loc
    lines = []

    # 이동 가능한 Gate
    gates = morld.get_location_gates(region_id, loc_id)
    if gates:
        for gate in gates:
            conn_region = gate.get("connected_region", 0)
            conn_loc = gate.get("connected_location", 0)
            conn_info = morld.get_location_info(conn_region, conn_loc)
            conn_name = conn_info.get("name", "???") if conn_info else "???"
            lines.append(f"[url=move:{conn_region}:{conn_loc}]{conn_name}으로 이동[/url]")

    if not lines:
        lines.append("(이동 가능한 곳이 없다)")

    return "\n".join(lines)


# ========================================
# 탭 시스템
# ========================================

def _get_tab_label_line():
    """헤더 하단 탭 라벨"""
    focus = _render_context.get("focus_type", "Situation")
    tab = _render_context.get("view_tab", 0)

    if focus == "Situation":
        tabs = ["주변", "지도"]
        parts = []
        for i, label in enumerate(tabs):
            if i == tab:
                parts.append(f"[b][{label}][/b]")
            else:
                parts.append(f"[url=tab:{i}]{label}[/url]")
        return " ".join(parts)

    return ""


def get_max_tab(focus_type, target_unit_id=None):
    """최대 탭 인덱스 (C#에서 호출)"""
    if focus_type == "Situation":
        return 1  # 0=주변, 1=지도
    return 0


def get_tab_content(focus_type, tab, target_unit_id=None):
    """탭 콘텐츠 (C#에서 호출). None→기존 렌더링."""
    if focus_type == "Situation" and tab == 1:
        return build_map_tab()
    return None


def get_tab_labels(focus_type, target_unit_id=None):
    """탭 라벨 리스트 (C#에서 호출)"""
    if focus_type == "Situation":
        return ["주변", "지도"]
    return []


# ========================================
# 지도 탭
# ========================================

def build_map_tab():
    """지도 탭 콘텐츠"""
    player_id = morld.get_player_id()
    if not player_id:
        return "지도를 표시할 수 없습니다."

    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return "현재 위치를 알 수 없습니다."

    region_id = current_loc[0]

    from village_map import render_village_map
    return render_village_map(region_id)
