# settings.py - 게임 설정 UI
#
# 게임 설정 화면을 제공합니다.
# - 디버그 모드
# - 시간 정지
# - 시간 자동 흐름
# - 게임 종료

import morld


# ============================================
# 설정 상태 변수
# ============================================

_auto_time_flow = True


def _get_player_id() -> int:
    """플레이어 ID 조회"""
    player_id = morld.get_player_id()
    return player_id if player_id is not None else -1


def is_debug_mode() -> bool:
    """디버그 모드 여부 (플레이어의 can:debug_* 확인)"""
    player_id = _get_player_id()
    if player_id < 0:
        return False
    return morld.get_unit_prop(player_id, "can:debug_*") >= 1


def set_debug_mode(enabled: bool):
    """디버그 모드 설정 (플레이어의 can:debug_* wildcard prop 토글)"""
    player_id = _get_player_id()
    if player_id < 0:
        return
    value = 1 if enabled else 0
    # can:debug_* wildcard prop으로 debug_ 계열 모든 액션 제어
    morld.set_unit_prop(player_id, "can:debug_*", value)


def is_auto_time_flow() -> bool:
    """시간 자동 흐름 여부"""
    return _auto_time_flow


def set_auto_time_flow(enabled: bool):
    """시간 자동 흐름 설정"""
    global _auto_time_flow
    _auto_time_flow = enabled


# ============================================
# UI 렌더링
# ============================================

def render_settings_ui(confirm_quit: bool = False) -> str:
    """
    설정 UI 렌더링

    Args:
        confirm_quit: 게임 종료 확인 상태
    """
    lines = ["[b]설정[/b]", ""]

    # 게임 종료 확인 다이얼로그
    if confirm_quit:
        lines.append("[color=yellow]게임을 종료하시겠습니까?[/color]")
        lines.append("")
        lines.append("[url=@proc:quit_yes]예[/url]  [url=@proc:quit_no]아니오[/url]")
        return "\n".join(lines)

    # 디버그 모드
    debug_on = is_debug_mode()
    debug_status = "[color=lime]ON[/color]" if debug_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_debug]디버그 모드[/url]: {debug_status}")

    # 시간 정지
    frozen = morld.is_time_frozen()
    frozen_status = "[color=cyan]정지[/color]" if frozen else "[color=gray]흐름[/color]"
    lines.append(f"[url=@proc:toggle_frozen]시간 정지[/url]: {frozen_status}")

    # 시간 자동 흐름
    auto_status = "[color=lime]ON[/color]" if _auto_time_flow else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_auto_time]시간 자동 흐름[/url]: {auto_status}")

    lines.append("")
    lines.append("[color=gray]────────────────────[/color]")
    lines.append("")

    # 게임 종료
    lines.append("[url=@proc:quit]게임 종료[/url]")

    lines.append("")
    lines.append("[url=@finish]닫기[/url]")

    return "\n".join(lines)


def show_settings_ui():
    """
    설정 UI 다이얼로그 표시 (Generator)
    """
    state = {"refresh": True, "confirm_quit": False}

    def proc(action):
        global _auto_time_flow

        if action == "init" or state.get("refresh"):
            state["refresh"] = False
            return render_settings_ui(state.get("confirm_quit", False))

        # 디버그 모드 토글
        if action == "toggle_debug":
            new_state = not is_debug_mode()
            set_debug_mode(new_state)
            morld.add_action_log(f"디버그 모드: {'ON' if new_state else 'OFF'}")
            return render_settings_ui()

        # 시간 정지 토글
        if action == "toggle_frozen":
            current = morld.is_time_frozen()
            morld.set_time_frozen(not current)
            status = "정지" if not current else "흐름"
            morld.add_action_log(f"시간: {status}")
            return render_settings_ui()

        # 시간 자동 흐름 토글
        if action == "toggle_auto_time":
            _auto_time_flow = not _auto_time_flow
            morld.add_action_log(f"시간 자동 흐름: {'ON' if _auto_time_flow else 'OFF'}")
            return render_settings_ui()

        # 게임 종료 확인
        if action == "quit":
            state["confirm_quit"] = True
            return render_settings_ui(confirm_quit=True)

        # 게임 종료 확인 - 예
        if action == "quit_yes":
            morld.quit_game()
            return True  # 다이얼로그 종료

        # 게임 종료 확인 - 아니오
        if action == "quit_no":
            state["confirm_quit"] = False
            return render_settings_ui()

        return None

    yield morld.dialog("", autofill="off", proc=proc, result=state)
