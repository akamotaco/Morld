# settings.py - 게임 설정 UI
#
# 게임 설정 화면을 제공합니다.
# - 디버그 모드
# - 시간 정지
# - 시간 자동 흐름
# - 게임 종료

import morld


# ============================================
# 플레이어 ID 조회
# ============================================


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
    """시간 자동 흐름 여부 (C# AutoTimeFlowSystem 연동)"""
    return morld.is_auto_time_flow()


def set_auto_time_flow(enabled: bool):
    """시간 자동 흐름 설정 (C# AutoTimeFlowSystem 연동)"""
    morld.set_auto_time_flow(enabled)


# ============================================
# 자동 시간 흐름 프리셋
# ============================================

# (이름, 실시간 초, 게임 분)
AUTO_TIME_PRESETS = [
    ("느리게", 10.0, 1),      # 10초마다 1분
    ("보통", 5.0, 1),         # 5초마다 1분
    ("빠르게", 2.0, 1),       # 2초마다 1분
    ("매우 빠르게", 1.0, 1),  # 1초마다 1분
    ("초고속", 0.5, 1),       # 0.5초마다 1분
]


def get_current_preset_name() -> str:
    """현재 간격에 해당하는 프리셋 이름 반환"""
    real_sec, game_min = morld.get_auto_time_flow_interval()
    for name, preset_sec, preset_min in AUTO_TIME_PRESETS:
        if abs(real_sec - preset_sec) < 0.01 and game_min == preset_min:
            return name
    return f"{real_sec}초/{game_min}분"


# ============================================
# UI 렌더링
# ============================================

def render_settings_ui(confirm_quit: bool = False, show_interval_menu: bool = False) -> str:
    """
    설정 UI 렌더링

    Args:
        confirm_quit: 게임 종료 확인 상태
        show_interval_menu: 시간 간격 메뉴 표시 여부
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
    auto_on = is_auto_time_flow()
    auto_status = "[color=lime]ON[/color]" if auto_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_auto_time]시간 자동 흐름[/url]: {auto_status}")

    # 시간 간격 설정 (토글 메뉴)
    preset_name = get_current_preset_name()
    toggle_icon = "▼" if show_interval_menu else "▶"
    lines.append(f"  [url=@proc:toggle_interval_menu]{toggle_icon} 시간 간격[/url]: [color=yellow]{preset_name}[/color]")

    if show_interval_menu:
        for name, real_sec, game_min in AUTO_TIME_PRESETS:
            # 현재 선택된 프리셋은 하이라이트
            if name == preset_name:
                lines.append(f"    [color=lime]● {name}[/color] ({real_sec}초 → {game_min}분)")
            else:
                lines.append(f"    [url=@proc:set_interval:{real_sec}:{game_min}]○ {name}[/url] ({real_sec}초 → {game_min}분)")

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
    state = {"refresh": True, "confirm_quit": False, "show_interval_menu": False}

    def proc(action):
        if action == "init" or state.get("refresh"):
            state["refresh"] = False
            return render_settings_ui(
                confirm_quit=state.get("confirm_quit", False),
                show_interval_menu=state.get("show_interval_menu", False)
            )

        # 디버그 모드 토글
        if action == "toggle_debug":
            new_state = not is_debug_mode()
            set_debug_mode(new_state)
            morld.add_action_log(f"디버그 모드: {'ON' if new_state else 'OFF'}")
            return render_settings_ui(show_interval_menu=state.get("show_interval_menu", False))

        # 시간 정지 토글
        if action == "toggle_frozen":
            current = morld.is_time_frozen()
            morld.set_time_frozen(not current)
            status = "정지" if not current else "흐름"
            morld.add_action_log(f"시간: {status}")
            return render_settings_ui(show_interval_menu=state.get("show_interval_menu", False))

        # 시간 자동 흐름 토글
        if action == "toggle_auto_time":
            new_state = not is_auto_time_flow()
            set_auto_time_flow(new_state)
            morld.add_action_log(f"시간 자동 흐름: {'ON' if new_state else 'OFF'}")
            return render_settings_ui(show_interval_menu=state.get("show_interval_menu", False))

        # 시간 간격 메뉴 토글
        if action == "toggle_interval_menu":
            state["show_interval_menu"] = not state.get("show_interval_menu", False)
            return render_settings_ui(show_interval_menu=state["show_interval_menu"])

        # 시간 간격 설정
        if action.startswith("set_interval:"):
            parts = action.split(":")
            if len(parts) == 3:
                real_sec = float(parts[1])
                game_min = int(parts[2])
                morld.set_auto_time_flow_interval(real_sec, game_min)
                # 프리셋 이름 찾기
                preset_name = "사용자 설정"
                for name, preset_sec, preset_min in AUTO_TIME_PRESETS:
                    if abs(real_sec - preset_sec) < 0.01 and game_min == preset_min:
                        preset_name = name
                        break
                morld.add_action_log(f"시간 간격: {preset_name}")
            return render_settings_ui(show_interval_menu=state.get("show_interval_menu", False))

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
            return render_settings_ui(show_interval_menu=state.get("show_interval_menu", False))

        return None

    yield morld.dialog("", autofill="off", proc=proc, result=state)
