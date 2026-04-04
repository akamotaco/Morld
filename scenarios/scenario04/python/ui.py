# ui.py - S04 TextUI 기본
#
# S02의 ui.py를 기반으로 S04 마을/던전 UI 구성.
# 초기에는 최소 기능만 구현.

import morld

# UI 상태
_ui_locked = False
_darkness_masking = True


def set_ui_lock(locked: bool):
    global _ui_locked
    _ui_locked = locked


def set_darkness_masking(enabled: bool):
    global _darkness_masking
    _darkness_masking = enabled


def build_header():
    """헤더 텍스트 (시간, 위치 정보)"""
    time_info = morld.get_time_info()
    if not time_info:
        return ""

    month = time_info.get("month", 1)
    day = time_info.get("day", 1)
    hour = time_info.get("hour", 0)
    minute = time_info.get("minute", 0)

    player_id = morld.get_player_id()
    if player_id:
        loc_info = morld.get_unit_location(player_id)
        loc_name = loc_info.get("name", "???") if loc_info else "???"
    else:
        loc_name = "???"

    return f"{month}월 {day}일 {hour:02d}:{minute:02d} | {loc_name}"


def build_content():
    """본문 텍스트 (현재 위치 묘사 + 주변 정보)"""
    player_id = morld.get_player_id()
    if not player_id:
        return "..."

    # 기본: 위치 묘사
    lines = []

    loc_info = morld.get_unit_location(player_id)
    if loc_info:
        loc_name = loc_info.get("name", "???")
        lines.append(f"[b]{loc_name}[/b]")
        lines.append("")

    return "\n".join(lines)


def build_map_tab():
    """지도 탭 콘텐츠"""
    player_id = morld.get_player_id()
    if not player_id:
        return "지도를 표시할 수 없습니다."

    current_loc = morld.get_unit_location(player_id)
    if not current_loc:
        return "현재 위치를 알 수 없습니다."

    region_id = current_loc[0]

    # 마을 region → 마을 지도
    from village_map import render_village_map
    return render_village_map(region_id)


def build_footer():
    """푸터 텍스트 (캐릭터 상태)"""
    return ""
