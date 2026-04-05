# ui.py - S04 TextUI
#
# engine.ui_base 기반 + S04 전용 시스템 (침식/신뢰/사기/파티) 반영.

import morld
import lighting
from ui_style import (
    MUTED, HIGHLIGHT, INFO, DANGER, SUCCESS, WARNING, ACCENT,
    STAT_NORMAL, STAT_CAUTION, STAT_DANGER,
    c, style_muted, style_highlight, style_info,
    style_danger, style_success, style_warning, style_section,
)
from engine.ui_base import (
    MILLIS_PER_MINUTE, MILLIS_PER_HOUR, CHAIN_PREFIX,
    divider,
    stat_bar, is_character,
    format_time, dialog,
    render_page,
    set_show_header, set_show_footer,
    is_header_visible, is_footer_visible,
    set_ui_lock, is_ui_locked,
    set_render_context as _set_render_context,
    get_render_context as _get_render_context,
    get_time_weather_text,
    get_status_text,
    get_tab_label_line,
)


# ========================================
# Darkness masking — engine/lighting에 위임
# ========================================

def set_darkness_masking(enabled):
    lighting.set_darkness_masking(enabled)

def is_darkness_masking_enabled():
    return lighting.is_darkness_masking_enabled()


# ========================================
# 탭 시스템 (S04 전용 구성)
# ========================================

def _can_use_map():
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
        if target_unit_id is not None and is_character(target_unit_id):
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
        if target_unit_id is not None and is_character(target_unit_id):
            return ["대화", "스탯"]
    return []


def _get_tab_label_line():
    ctx = _get_render_context()
    labels = get_tab_labels(ctx["focus_type"], ctx["target_unit_id"])
    return get_tab_label_line(labels=labels, view_tab=ctx["view_tab"])


# ========================================
# 지도 탭
# ========================================

def _render_map_tab():
    try:
        player_id = morld.get_player_id()
        if not player_id:
            return "지도를 표시할 수 없습니다."
        current_loc = morld.get_unit_location(player_id)
        if not current_loc:
            return "현재 위치를 알 수 없습니다."

        from village_map import render_village_map
        return render_village_map(current_loc[0])
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
# NPC 스탯 탭 (S04 전용)
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
            lines.append(f"  체력   {stat_bar(hp, max_hp)} {hp:.0f}")
            lines.append(f"  포만감 {stat_bar(sat, 100)} {sat:.0f}")
        except (ImportError, Exception):
            pass

        try:
            import needs
            fatigue = needs.get_fatigue(unit_id)
            cleanliness = needs.get_cleanliness(unit_id)
            lines.append(f"  피로   {stat_bar(fatigue, 100)} {fatigue:.0f}")
            lines.append(f"  불결   {stat_bar(cleanliness, 100)} {cleanliness:.0f}")
        except (ImportError, Exception):
            pass

        # 침식
        try:
            import erosion
            ero = erosion.get_erosion(unit_id)
            lines.append(f"  침식   {stat_bar(ero, 200)} {ero:.0f}/200")
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


# ========================================
# Header
# ========================================

def get_header():
    if not is_header_visible():
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
        brightness_text = lighting.get_brightness_text()
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
# Footer (S04 전용)
# ========================================


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
    if not is_footer_visible():
        return ""

    lines = []

    # 메뉴
    lines.append("[url=inventory]인벤토리[/url]  [url=settings]설정[/url]")

    # 파티 정보 (위자드리 스타일)
    party_text = _get_party_display()
    if party_text:
        lines.append(party_text)

    return "\n".join(lines)


def _get_party_display():
    """파티 패널 — 위자드리 스타일 뷰포트 병합

    플레이어(좌 절반, 가로 배치) + 파티원(우 절반, 균등 분배)
    각 뷰포트를 독립 렌더링 후 줄 단위 병합.
    """
    try:
        import party
        import survival
        from text_utils import str_width, truncate_to_width, pad_to_width

        members = party.get_members()
        if not members:
            return ""

        leader_id = party.get_leader()
        others = [m for m in members if m != leader_id]

        # --- 폭 계산 (외곽선 포함) ---
        TOTAL_WIDTH = 140
        BORDER_COLOR = "#999999"
        # 내부 콘텐츠 폭 = 전체 - 좌우 외곽(2) - 내부 구분선(파티원 수)
        num_seps = len(others)  # 플레이어│멤1│멤2 → 구분선 = 파티원 수
        inner_w = TOTAL_WIDTH - 2 - num_seps
        if others:
            player_w = inner_w // 2
            remaining_w = inner_w - player_w
            member_w = remaining_w // len(others)
        else:
            player_w = inner_w
            member_w = 0

        # --- 뷰포트 렌더링 ---
        player_lines = _render_player_viewport(leader_id, player_w)
        member_viewports = [_render_member_viewport(mid, member_w) for mid in others]

        PANEL_HEIGHT = 3
        _pad_viewport(player_lines, PANEL_HEIGHT, player_w)
        for vp in member_viewports:
            _pad_viewport(vp, PANEL_HEIGHT, member_w)

        # --- 외곽선 + 줄 단위 병합 ---
        from grid_renderer import MAP_FONT
        bc = lambda s: c(BORDER_COLOR, s)
        rows = []
        rows.append(f"[font={MAP_FONT}]")

        # 상단: ┌───┬───┬───┐
        top = "┌" + "─" * player_w
        for _ in others:
            top += "┬" + "─" * member_w
        top += "┐"
        rows.append(bc(top))

        # 본문: │내용│내용│내용│
        for i in range(PANEL_HEIGHT):
            row = bc("│") + player_lines[i]
            for vp in member_viewports:
                row += bc("│") + vp[i]
            row += bc("│")
            rows.append(row)

        # 하단: └───┴───┴───┘
        bot = "└" + "─" * player_w
        for _ in others:
            bot += "┴" + "─" * member_w
        bot += "┘"
        rows.append(bc(bot))

        rows.append("[/font]")
        return "\n".join(rows)
    except Exception as e:
        print(f"[ui] _get_party_display error: {e}")
        return ""


def _render_player_viewport(unit_id, width):
    """플레이어 뷰포트 — 4줄 가로 배치"""
    import survival
    from text_utils import str_width, truncate_to_width, pad_to_width

    info = morld.get_unit_info(unit_id)
    name = info.get("name", "???") if info else "???"
    hp = survival.get_health(unit_id)
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    hp_ratio = hp / max_hp if max_hp > 0 else 0

    lines = []
    pw = pad_to_width

    # 줄 1: ◆이름  HP ████░░ 80/100  포만:100  피로:0
    bar = stat_bar(hp, max_hp, length=8)
    hp_val = f"{hp:.0f}/{max_hp:.0f}"
    if hp_ratio <= 0.2:
        hp_val = c(STAT_DANGER, hp_val)
    elif hp_ratio <= 0.5:
        hp_val = c(STAT_CAUTION, hp_val)
    line1 = f"[url=look_unit:{unit_id}]◆{name}[/url]  HP {bar} {hp_val}"
    try:
        stats = survival.get_survival_stats(unit_id)
        sat = stats.get("satiety", 0)
        if sat <= 20:
            line1 += "  " + c(STAT_DANGER, f"포만:{sat:.0f}")
        elif sat <= 50:
            line1 += "  " + c(STAT_CAUTION, f"포만:{sat:.0f}")
        else:
            line1 += f"  포만:{sat:.0f}"
    except Exception:
        pass
    try:
        import needs
        fatigue = needs.get_fatigue(unit_id)
        if fatigue >= 80:
            line1 += "  " + c(STAT_DANGER, f"피로:{fatigue:.0f}")
        elif fatigue >= 50:
            line1 += "  " + c(STAT_CAUTION, f"피로:{fatigue:.0f}")
        else:
            line1 += f"  피로:{fatigue:.0f}"
    except (ImportError, Exception):
        pass
    lines.append(pw(line1, width))

    # 줄 2: Lv.N  사기:높음  침식:25
    parts2 = []
    lv = morld.get_unit_prop(unit_id, "level") or 1
    parts2.append(f"Lv.{lv}")
    try:
        import morale
        m = morale.get_morale(unit_id)
        parts2.append(f"사기:{m}")
    except (ImportError, Exception):
        pass
    try:
        import erosion
        ero = erosion.get_erosion(unit_id)
        if ero >= 100:
            parts2.append(c(STAT_DANGER, f"침식:{ero}"))
        elif ero >= 50:
            parts2.append(c(STAT_CAUTION, f"침식:{ero}"))
        else:
            parts2.append(f"침식:{ero}")
    except (ImportError, Exception):
        pass
    lines.append(pw("  ".join(parts2), width))

    # 줄 3: 자세/은신 + X축 이동
    parts3 = []
    parts3.append(_get_stealth_stance_text(unit_id))
    move_text = _get_movement_arrows()
    if move_text:
        parts3.append(move_text)
    lines.append(pw("  ".join(p for p in parts3 if p), width))

    return lines


def _render_member_viewport(unit_id, width):
    """파티원 뷰포트 — 4줄 compact"""
    import survival
    from text_utils import str_width, truncate_to_width, pad_to_width

    info = morld.get_unit_info(unit_id)
    name = info.get("name", "???") if info else "???"
    hp = survival.get_health(unit_id)
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    hp_ratio = hp / max_hp if max_hp > 0 else 0

    # 이름 말줄임
    display_name = name
    name_w = str_width(name)
    avail = width - 2  # ◇ + 여백
    if name_w > avail:
        display_name = truncate_to_width(name, avail - 2) + ".."

    lines = []
    pw = pad_to_width

    # 줄 1: ◇이름
    lines.append(pw(f"[url=look_unit:{unit_id}]◇{display_name}[/url]", width))

    # 줄 2: HP ████░░
    bar_len = max(4, width - 4)  # "HP " + bar
    bar = stat_bar(hp, max_hp, length=bar_len)
    if hp_ratio <= 0.2:
        bar = c(STAT_DANGER, bar)
    elif hp_ratio <= 0.5:
        bar = c(STAT_CAUTION, bar)
    lines.append(pw(f"HP {bar}", width))

    # 줄 3: 침식 + 사기
    parts3 = []
    try:
        import erosion
        ero = erosion.get_erosion(unit_id)
        if ero >= 100:
            parts3.append(c(STAT_DANGER, f"침식:{ero}"))
        elif ero >= 50:
            parts3.append(c(STAT_CAUTION, f"침식:{ero}"))
        else:
            parts3.append(f"침식:{ero}")
    except (ImportError, Exception):
        pass
    try:
        import morale
        m = morale.get_morale(unit_id)
        parts3.append(f"사기:{m}")
    except (ImportError, Exception):
        pass
    lines.append(pw(" ".join(parts3), width))

    return lines


def _get_player_weapon_text(unit_id):
    """플레이어 장비 무기 텍스트"""
    try:
        equipped = morld.get_equipped_items(unit_id)
        if not equipped:
            return ""
        for item_id in equipped:
            item_info = morld.get_item_info(item_id)
            if item_info and item_info.get("slot") == "weapon":
                name = item_info.get("name", "???")
                corrosion = morld.get_unit_prop(item_id, "부식") or 0
                if corrosion > 0:
                    return f"무기: {name} [부식:{corrosion}]"
                return f"무기: {name}"
        return ""
    except Exception:
        return ""


def _get_stealth_stance_text(unit_id):
    """은신 토글 + 이동 모드 표시"""
    try:
        parts = []

        # 은신 토글
        from engine import stealth
        if stealth.is_unit_stealthed(unit_id):
            parts.append(f"[url=stealth:toggle]{c(SUCCESS, '[은신 해제]')}[/url]")
        else:
            parts.append(f"[url=stealth:toggle]{style_muted('[은신]')}[/url]")

        # 이동 모드 (앉기/걷기/뛰기)
        stance = _get_current_stance(unit_id)
        stance_labels = {"crouch": "앉기", "walk": "걷기", "run": "뛰기"}
        label = stance_labels.get(stance, "걷기")
        parts.append(f"[url=posture:cycle]{style_muted(f'[{label}]')}[/url]")

        return "  ".join(parts)
    except Exception:
        return ""


# 이동 모드 순환 순서
_STANCE_ROTATION = ["walk", "crouch", "run"]


def _get_current_stance(unit_id):
    """현재 이동 모드 반환"""
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

    # 새 stance prop 설정 (walk은 기본이므로 prop 없음)
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
        # S04: 파티 은신 해제
        import stealth as stealth_mod
        stealth_mod.exit_party_stealth()
        return "은신 해제"
    else:
        import stealth as stealth_mod
        stealth_mod.enter_party_stealth()
        return "은신"


def _pad_viewport(lines, target_height, width):
    """뷰포트 줄 수를 target_height에 맞춰 빈 줄 패딩"""
    from text_utils import pad_to_width
    while len(lines) < target_height:
        lines.append(pad_to_width("", width))


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

    # 던전 조우 — 적 발견 시 전투/회피 선택지
    try:
        import dungeon
        if dungeon.has_pending_encounter():
            enc_info = dungeon.get_pending_encounter_info()
            if enc_info:
                lines.append("")
                lines.append(style_danger("⚠ 전방에 적 발견:"))
                if enc_info["discover_text"]:
                    lines.append(f"  {style_muted(enc_info['discover_text'])}")
                names = enc_info["enemy_names"]
                count = enc_info["enemy_count"]
                name_text = names[0] if count == 1 else f"{names[0]} x{count}"
                lines.append(f"  {name_text} (X≈{enc_info['enemy_x']})")
                lines.append(f"  [url=dungeon:engage]{style_danger('전투 돌입')}[/url]")
                lines.append(f"  [url=dungeon:skip]우회 시도[/url]")
    except Exception as e:
        print(f"[ui] dungeon encounter display error: {e}")

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
# C# 호출용 호환 함수
# ========================================

def ui_get_move_confirm_message(travel_time_millis):
    """이동 확인 메시지 — engine.ui_base.get_move_confirm_message 위임"""
    from engine.ui_base import get_move_confirm_message
    return get_move_confirm_message(travel_time_millis)
