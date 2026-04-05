# ui.py - S04 TextUI
#
# S02 ui.py와 동일한 C# 인터페이스.
# S04 전용 시스템 (침식/신뢰/사기/파티) 반영.

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

# 연쇄 출력 접두사
CHAIN_PREFIX = "+"


# ========================================
# 구분선 (즉시 출력)
# ========================================

def divider(color=MUTED, length=20):
    line = "─" * length
    return f"[!][color={color}]{line}[/color][/!]"


# ========================================
# UI 상태
# ========================================

_show_header = True
_show_footer = True
_ui_locked = False
_darkness_masking_enabled = False

_render_context = {
    "focus_type": "Situation",
    "view_tab": 0,
    "target_unit_id": None,
}


def set_show_header(show):
    global _show_header
    _show_header = show

def set_show_footer(show):
    global _show_footer
    _show_footer = show

def is_header_visible():
    return _show_header

def is_footer_visible():
    return _show_footer

def set_ui_lock(locked):
    global _ui_locked
    _ui_locked = locked

def is_ui_locked():
    return _ui_locked

def set_darkness_masking(enabled):
    global _darkness_masking_enabled
    _darkness_masking_enabled = enabled

def is_darkness_masking_enabled():
    return _darkness_masking_enabled

def _set_render_context(focus_type, view_tab, target_unit_id=None):
    _render_context["focus_type"] = focus_type
    _render_context["view_tab"] = view_tab
    _render_context["target_unit_id"] = target_unit_id


# ========================================
# 탭 시스템
# ========================================

def _can_use_map():
    """지도 사용 가능 여부 (S04: 항상 가능)"""
    return morld.get_player_id() is not None


def _get_situation_tabs():
    tabs = [("주변", None)]
    if _can_use_map():
        tabs.append(("지도", _render_map_tab))
    return tabs


def get_max_tab(focus_type, target_unit_id=None):
    if focus_type == "Situation":
        return len(_get_situation_tabs()) - 1
    elif focus_type == "Unit":
        if target_unit_id is not None and _is_character(target_unit_id):
            return 1
    return 0


def get_tab_content(focus_type, tab, target_unit_id=None):
    if focus_type == "Situation":
        tabs = _get_situation_tabs()
        if 0 <= tab < len(tabs):
            render_fn = tabs[tab][1]
            return render_fn() if render_fn else None
    elif focus_type == "Unit":
        if tab == 1:
            return _render_stat_tab(target_unit_id)
    return None


def get_tab_labels(focus_type, target_unit_id=None):
    if focus_type == "Situation":
        return [label for label, _ in _get_situation_tabs()]
    elif focus_type == "Unit":
        if target_unit_id is not None and _is_character(target_unit_id):
            return ["대화", "스탯"]
    return []


def _is_character(unit_id):
    try:
        info = morld.get_unit_info(unit_id)
        if info and not info.get("is_object", False):
            return True
    except Exception:
        pass
    return False


def _get_tab_label_line():
    focus_type = _render_context["focus_type"]
    view_tab = _render_context["view_tab"]
    target_unit_id = _render_context["target_unit_id"]
    labels = get_tab_labels(focus_type, target_unit_id)
    if not labels:
        return ""
    parts = []
    for i, label in enumerate(labels):
        if i == view_tab:
            parts.append(c(ACCENT, f"[▶{label}]"))
        else:
            parts.append(f"[url=tab:{i}][{label}][/url]")
    return "  ".join(parts)


# ========================================
# 지도 탭
# ========================================

def _render_map_tab():
    try:
        import map_coords
        player_id = morld.get_player_id()
        if not player_id:
            return "지도를 표시할 수 없습니다."
        current_loc = morld.get_unit_location(player_id)
        if not current_loc:
            return "현재 위치를 알 수 없습니다."

        region_id = current_loc[0]
        all_coords = map_coords.get_all(region_id)
        if not all_coords:
            return _render_map_tab_fallback(region_id, current_loc[1], player_id)

        import region_map
        result = region_map.render_region_map(
            region_id, current_loc[1], player_id, all_coords,
            show_characters=False
        )
        return result or _render_map_tab_fallback(region_id, current_loc[1], player_id)
    except Exception as e:
        print(f"[ui] _render_map_tab error: {e}")
        return f"지도 오류: {e}"


def _render_map_tab_fallback(region_id, current_local, player_id):
    region_info = morld.get_region_info(region_id)
    if not region_info:
        return "지역 정보를 불러올 수 없습니다."
    lines = [f"[b]지도 - {region_info['name']}[/b]", ""]
    for loc in sorted(region_info["locations"], key=lambda x: x["id"] if isinstance(x, dict) else x):
        loc_id = loc["id"] if isinstance(loc, dict) else int(loc)
        loc_info = morld.get_location_info(region_id, loc_id)
        name = loc_info.get("name", "???") if loc_info else "???"
        if loc_id == current_local:
            lines.append(f"  {style_highlight(f'> {name}')} {style_muted('(현재 위치)')}")
        else:
            lines.append(f"  - [url=move:{region_id}:{loc_id}]{name}[/url]")
    return "\n".join(lines)


def map_scroll(direction):
    from village_map import map_scroll as _scroll
    _scroll(direction)

def map_zoom(direction):
    from village_map import map_zoom as _zoom
    _zoom(direction)

def map_toggle_names():
    from village_map import map_toggle_names as _toggle
    _toggle()


# ========================================
# NPC 스탯 탭
# ========================================

def _render_stat_tab(unit_id):
    try:
        info = morld.get_unit_info(unit_id)
        if not info:
            return "유닛 정보를 불러올 수 없습니다."

        name = info.get("name", "???")
        lines = [f"[b]{name}[/b]", ""]

        # 상태
        lines.append(style_section("상태"))
        try:
            import survival
            hp = survival.get_health(unit_id)
            max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
            sat = survival.get_satiety(unit_id)
            lines.append(f"  체력   {_stat_bar(hp, max_hp)} {hp:.0f}")
            lines.append(f"  포만감 {_stat_bar(sat, 100)} {sat:.0f}")
        except (ImportError, Exception):
            pass

        try:
            import needs
            fatigue = needs.get_fatigue(unit_id)
            cleanliness = needs.get_cleanliness(unit_id)
            lines.append(f"  피로   {_stat_bar(fatigue, 100)} {fatigue:.0f}")
            lines.append(f"  불결   {_stat_bar(cleanliness, 100)} {cleanliness:.0f}")
        except (ImportError, Exception):
            pass

        # 침식
        try:
            import erosion
            ero = erosion.get_erosion(unit_id)
            lines.append(f"  침식   {_stat_bar(ero, 200)} {ero:.0f}/200")
        except (ImportError, Exception):
            pass
        lines.append("")

        # 전투 스탯 (S04 전용)
        lines.append(style_section("능력치"))
        char_class = morld.get_unit_prop(unit_id, "character_class") or "없음"
        lines.append(f"  클래스: {char_class}")
        for stat_name, prop_key in [("근력", "base_str"), ("민첩", "base_agi"),
                                     ("체력", "base_vit"), ("정신", "base_mnd")]:
            val = morld.get_unit_prop(unit_id, prop_key) or 0
            lines.append(f"  {stat_name} {val}")
        lines.append("")

        # 신뢰/사기 (S04 전용)
        lines.append(style_section("파티"))
        try:
            import trust
            t = trust.get_trust(unit_id)
            lines.append(f"  신뢰도 {t}")
        except (ImportError, Exception):
            pass
        try:
            import morale
            m = morale.get_morale(unit_id)
            lines.append(f"  사기   {m}")
        except (ImportError, Exception):
            pass
        lines.append("")

        lines.append("[url=back]◁뒤로[/url]")
        return "\n".join(lines)
    except Exception as e:
        print(f"[ui] _render_stat_tab error: {e}")
        return f"스탯 오류: {e}"


def _stat_bar(value, max_val, length=10):
    if value is None or max_val <= 0:
        return "░" * length
    ratio = max(0, min(1, value / max_val))
    filled = int(ratio * length)
    return "█" * filled + "░" * (length - filled)


# ========================================
# Header
# ========================================

def get_time_weather_text():
    try:
        time_info = morld.get_time_info()
        if not time_info:
            return ""

        year = time_info.get("year", 1)
        month = time_info.get("month", 1)
        day = time_info.get("day", 1)
        weekday = time_info.get("weekday", "")
        hour = time_info.get("hour", 0)
        minute = time_info.get("minute", 0)
        time_str = f"{year}년 {month}월 {day}일 ({weekday}) {hour:02d}:{minute:02d}"

        weather = time_info.get("weather", "")

        # 온도
        temp_text = ""
        try:
            import temperature
            loc = None
            player_id = morld.get_player_id()
            if player_id:
                loc = morld.get_unit_location(player_id)
            if loc:
                temp = temperature.get_temperature(loc[0], loc[1])
                if temp is not None:
                    temp_text = f" {temp:.0f}℃"
        except ImportError:
            pass

        # 혼잡도
        congestion_text = ""
        try:
            import congestion
            if player_id:
                loc = morld.get_unit_location(player_id)
                if loc:
                    cong = congestion.get_congestion(loc[0], loc[1])
                    if cong is not None and cong > 1.0:
                        congestion_text = f" {style_highlight(f'혼잡x{cong:.1f}')}"
        except ImportError:
            pass

        if weather:
            return f"{time_str} / {weather}{temp_text}{congestion_text}"
        return f"{time_str}{temp_text}{congestion_text}"
    except Exception as e:
        print(f"[ui] get_time_weather_text error: {e}")
        return ""


def _get_brightness_text():
    try:
        level = lighting.get_brightness_level()
        if level == "밝음":
            return "[밝음]"
        elif level == "어두움":
            return style_highlight("[어두움]")
        else:
            return style_danger("[암흑]")
    except Exception:
        return ""


def get_header():
    if not _show_header:
        return ""
    try:
        time_info = morld.get_time_info()
        if not time_info:
            return ""

        lines = []

        # 위치
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

        # 시간/날씨 + 밝기
        time_text = get_time_weather_text()
        brightness_text = _get_brightness_text()
        if time_text and brightness_text:
            lines.append(f"{time_text} {brightness_text}")
        elif time_text:
            lines.append(time_text)

        # Pi-World 좌표
        geometry = time_info.get("geometry", 0)
        location_length = time_info.get("location_length", 0)
        position_x = time_info.get("position_x", 0)
        geo_text = "선" if geometry == 1 else "원"
        lines.append(style_muted(f"[{geo_text}] X:{int(position_x)}/{int(location_length)}"))

        if morld.is_time_frozen():
            lines.append(style_info("[시간 정지]"))

        return "\n".join(lines)
    except Exception as e:
        print(f"[ui] get_header error: {e}")
        return ""


# ========================================
# Footer
# ========================================

def get_status_text():
    try:
        import survival
        player_id = morld.get_player_id()
        if not player_id:
            return ""

        lines = []
        status_bar = survival.get_status_bar(player_id)
        if status_bar:
            lines.append(status_bar)
        status_msg = survival.get_status_message(player_id)
        if status_msg:
            lines.append(status_msg)
        return "\n".join(lines)
    except ImportError:
        return ""
    except Exception as e:
        print(f"[ui] get_status_text error: {e}")
        return ""


def _get_environment_status_text():
    try:
        player_id = morld.get_player_id()
        if not player_id:
            return ""
        parts = []

        # 체온
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

        # 침식 (S04 핵심)
        try:
            import erosion
            ero = erosion.get_erosion(player_id)
            if ero >= 100:
                parts.append(style_danger(f"침식 {ero}"))
            elif ero >= 50:
                parts.append(c(STAT_CAUTION, f"침식 {ero}"))
            elif ero > 0:
                parts.append(f"침식 {ero}")
        except ImportError:
            pass

        # 욕구 (임계치 근처만)
        try:
            import needs
            fatigue = needs.get_fatigue(player_id)
            if fatigue >= 50:
                clr = STAT_DANGER if fatigue >= 80 else STAT_CAUTION
                parts.append(c(clr, f"피로 {fatigue:.0f}"))
        except ImportError:
            pass

        # 소지금
        try:
            import economy
            money = economy.get_money(player_id)
            parts.append(f"소지금:{money:,}원")
        except ImportError:
            pass

        return " | ".join(parts) if parts else ""
    except Exception as e:
        print(f"[ui] _get_environment_status_text error: {e}")
        return ""


def _get_movement_arrows():
    player_id = morld.get_player_id()
    if not player_id:
        return ""
    time_info = morld.get_time_info()
    if not time_info:
        return ""

    loc_length = int(time_info.get("location_length", 0))
    if loc_length <= 0:
        return ""

    cur_x = int(time_info.get("position_x", 0))
    is_ring = time_info.get("geometry", 0) == 0

    parts = []
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

    parts.append(f"X={cur_x}")

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
    if not _show_footer:
        return ""

    lines = []
    player_id = morld.get_player_id()

    # 메뉴
    lines.append("[url=inventory]인벤토리[/url]  [url=settings]설정[/url]")

    # 상태바
    status_text = get_status_text()
    if status_text:
        lines.append(status_text)

    # 환경 상태
    env_text = _get_environment_status_text()
    if env_text:
        lines.append(env_text)

    # X축 이동 화살표
    movement_text = _get_movement_arrows()
    if movement_text:
        lines.append(movement_text)

    return "\n".join(lines)


# ========================================
# 이동 UI
# ========================================

def _render_movement(info):
    lines = []
    geometry = info["geometry"]
    player_x = info["player_x"]
    routes = [r for r in info["routes"] if not r["is_hidden"]]
    routes.sort(key=lambda r: r["gate_x"])

    if not routes:
        return lines

    lines.append(style_info("이동 가능 지역:"))

    if geometry == "ring":
        lines.append(style_muted("-vvv-----------"))
    else:
        lines.append(style_muted("---------------"))

    marker = "▶"
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

        if route["is_blocked"]:
            if is_closest:
                lines.append(f"  {prefix}{style_muted(route['name'])}")
            else:
                route_name = route["name"]
                lines.append(f"  {style_muted(f'- {route_name}')}")
        else:
            region_tag = f" [{route['region_name']}]" if route["is_region_gate"] else ""
            travel_min = route["travel_time"] // MILLIS_PER_MINUTE
            meta = f"move:{route['region_id']}:{route['local_id']}"
            lines.append(f"  [url={meta}]{prefix}{route['name']}{region_tag} ({travel_min}분)[/url]")

    if geometry == "ring":
        lines.append(style_muted("-^^^-----------"))
    else:
        lines.append(style_muted("---------------"))

    return lines


# ========================================
# 행동 옵션
# ========================================

def get_action_text():
    lines = []
    player_id = morld.get_player_id()
    if not player_id:
        return ""

    # 이동
    movement_info = morld.get_movement_info()
    if movement_info is not None:
        lines.extend(_render_movement(movement_info))

    # C# 행동 리스트
    default_actions = morld.get_actions_list()
    for action in default_actions:
        lines.append(action)

    # 행동 섹션
    lines.append("")
    lines.append(style_info("행동:"))

    # 시간 보내기
    millis_of_day = morld.get_game_time()
    hour = millis_of_day // MILLIS_PER_HOUR if millis_of_day else 0
    if 22 <= hour or hour < 6:
        lines.append(f"  [url=idle:{480 * MILLIS_PER_MINUTE}]잠자기 (8시간)[/url]")
    lines.append(f"  [url=idle:{30 * MILLIS_PER_MINUTE}]멍때리기 (30분)[/url]")
    lines.append(f"  [url=idle:{240 * MILLIS_PER_MINUTE}]낮잠자기 (4시간)[/url]")

    return "\n".join(lines)


# ========================================
# 유틸리티
# ========================================

def format_time(millis):
    total_minutes = millis // MILLIS_PER_MINUTE
    if total_minutes < 60:
        return f"{total_minutes}분"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if mins > 0:
        return f"{hours}시간 {mins}분"
    return f"{hours}시간"


def ui_get_move_confirm_message(travel_time_millis):
    time_text = format_time(int(travel_time_millis))
    return f"이동하는 데 {time_text}이 걸립니다. 이동하시겠습니까?"


# ========================================
# 다이얼로그
# ========================================

def _render_page(pages, state):
    idx = state["page"]
    page = pages[idx]

    if page.startswith("\\+"):
        page = page[1:]
        state["accumulated"] = page
        text = page
    elif page.startswith(CHAIN_PREFIX):
        new_text = page[len(CHAIN_PREFIX):]
        if state["accumulated"]:
            text = f"[!]{state['accumulated']}\n[/!]{new_text}"
            state["accumulated"] = state["accumulated"] + "\n" + new_text
        else:
            text = new_text
            state["accumulated"] = new_text
    else:
        text = page
        state["accumulated"] = page

    if idx < len(pages) - 1:
        text += "\n\n[url=@proc:next]다음[/url]"
    else:
        text += "\n\n[url=@proc:finish]확인[/url]"

    return text


def dialog(content, **kwargs):
    """다이얼로그 — 문자열 또는 리스트(다페이지) 지원"""
    if isinstance(content, str):
        return morld.dialog(content, **kwargs)

    if "autofill" in kwargs and kwargs["autofill"] not in ("off", None):
        return morld.dialog(content, **kwargs)

    pages = content
    state = {"page": 0, "accumulated": ""}

    def handler(action):
        if action == "init":
            return _render_page(pages, state)
        if action == "next":
            state["page"] += 1
            if state["page"] < len(pages):
                return _render_page(pages, state)
            return True
        if action == "finish":
            return True
        return None

    return morld.dialog(
        _render_page(pages, state),
        autofill="off", proc=handler, **kwargs
    )
