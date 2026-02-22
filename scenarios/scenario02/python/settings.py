# settings.py - 게임 설정 UI
#
# 게임 설정 화면을 제공합니다.
# - 디버그 모드
# - 시간 정지
# - 시간 자동 흐름
# - 게임 종료

import morld
import ui


# ============================================
# 연애 모드
# ============================================

# 기본값: False (OFF). 연애 콘텐츠 활성화 시 True로 변경.
_romance_enabled = False  # ← 이 값을 True로 변경하면 기본 ON


def is_romance_enabled() -> bool:
    """연애 모드 활성화 여부"""
    return _romance_enabled


def set_romance_enabled(enabled: bool):
    """연애 모드 설정"""
    global _romance_enabled
    _romance_enabled = enabled
    # 플레이어 can: prop 연동 (스킨십/강제 행위 표시 제어)
    player_id = _get_player_id()
    if player_id >= 0:
        value = 1 if enabled else 0
        morld.set_unit_prop(player_id, "can:romance", value)
        morld.set_unit_prop(player_id, "can:force_romance", value)
        morld.set_unit_prop(player_id, "can:masturbate", value)


# ============================================
# 수간 모드
# ============================================

_bestiality_enabled = False


def is_bestiality_enabled() -> bool:
    """수간 모드 활성화 여부 (연애 모드 ON 필수)"""
    return _bestiality_enabled and _romance_enabled


def set_bestiality_enabled(enabled: bool):
    """수간 모드 설정"""
    global _bestiality_enabled
    _bestiality_enabled = enabled
    player_id = _get_player_id()
    if player_id >= 0:
        morld.set_unit_prop(player_id, "can:bestiality", 1 if enabled else 0)


# ============================================
# 성추행 모드
# ============================================

_harassment_enabled = False


def is_harassment_enabled() -> bool:
    """성추행 모드 활성화 여부"""
    return _harassment_enabled


def set_harassment_enabled(enabled: bool):
    """성추행 모드 설정"""
    global _harassment_enabled
    _harassment_enabled = enabled
    player_id = _get_player_id()
    if player_id >= 0:
        value = 1 if enabled else 0
        morld.set_unit_prop(player_id, "can:harassment", value)
        morld.set_unit_prop(player_id, "can:self_expose", value)


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

# (이름, 실시간 초, 게임 밀리초)
# 실시간 1초 기준, 게임 시간 양으로 속도 조절
AUTO_TIME_PRESETS = [
    ("느리게", 1.0, 1_000),        # 1초마다 게임 1초 (X 1단위씩 이동)
    ("보통", 1.0, 30_000),         # 1초마다 게임 30초 (1/2분)
    ("빠르게", 1.0, 60_000),       # 1초마다 게임 1분
    ("매우 빠르게", 1.0, 180_000), # 1초마다 게임 3분
    ("초고속", 1.0, 300_000),      # 1초마다 게임 5분
]


# ============================================
# 타이핑 속도 프리셋
# ============================================

# (이름, 초당 문자 수)
# 0 = 즉시 출력 (타이핑 효과 비활성화)
TYPING_SPEED_PRESETS = [
    ("끄기", 0),        # 즉시 출력
    ("느리게", 25),     # 초당 25자
    ("보통", 50),       # 초당 50자 (기본)
    ("빠르게", 100),    # 초당 100자
]


def get_typing_speed_preset_name() -> str:
    """현재 타이핑 속도에 해당하는 프리셋 이름 반환"""
    speed = morld.get_typing_speed()
    for name, preset_speed in TYPING_SPEED_PRESETS:
        if speed == preset_speed:
            return name
    return f"{speed}자/초"


def get_current_preset_name() -> str:
    """현재 간격에 해당하는 프리셋 이름 반환"""
    real_sec, game_millis = morld.get_auto_time_flow_interval()
    for name, preset_sec, preset_millis in AUTO_TIME_PRESETS:
        if abs(real_sec - preset_sec) < 0.01 and game_millis == preset_millis:
            return name
    return f"{real_sec}초/{game_millis}ms"


# ============================================
# UI 렌더링
# ============================================

def render_settings_ui(confirm_quit: bool = False, show_interval_menu: bool = False, show_typing_menu: bool = False) -> str:
    """
    설정 UI 렌더링

    Args:
        confirm_quit: 게임 종료 확인 상태
        show_interval_menu: 시간 간격 메뉴 표시 여부
        show_typing_menu: 타이핑 속도 메뉴 표시 여부
    """
    lines = ["[b]설정[/b]", ""]

    # 게임 종료 확인 다이얼로그
    if confirm_quit:
        lines.append("[color=yellow]게임을 종료하시겠습니까?[/color]")
        lines.append("")
        lines.append("[url=@proc:quit_yes]예[/url]  [url=@proc:quit_no]아니오[/url]")
        return "[!]" + "\n".join(lines) + "[/!]"

    # 디버그 모드
    debug_on = is_debug_mode()
    debug_status = "[color=lime]ON[/color]" if debug_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_debug]디버그 모드[/url]: {debug_status}")

    # 연애 모드
    romance_on = is_romance_enabled()
    romance_status = "[color=lime]ON[/color]" if romance_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_romance]연애 모드[/url]: {romance_status}")

    # 수간 모드 (연애 모드 ON 시에만 표시)
    if is_romance_enabled():
        beast_on = is_bestiality_enabled()
        beast_status = "[color=red]ON[/color]" if beast_on else "[color=gray]OFF[/color]"
        lines.append(f"  [url=@proc:toggle_bestiality]수간 모드[/url]: {beast_status}")

    # 적대 모드
    import combat
    hostile_on = combat.is_hostile_mode()
    hostile_status = "[color=red]ON[/color]" if hostile_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_hostile]적대 모드[/url]: {hostile_status}")

    # 성추행 모드
    harass_on = is_harassment_enabled()
    harass_status = "[color=red]ON[/color]" if harass_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_harassment]성추행 모드[/url]: {harass_status}")

    # 달리기
    player_id = _get_player_id()
    sprint_on = morld.get_unit_prop(player_id, "이동:달리기") if player_id >= 0 else 0
    sprint_status = "[color=yellow]ON[/color]" if sprint_on else "[color=gray]OFF[/color]"
    lines.append(f"[url=@proc:toggle_sprint]달리기[/url]: {sprint_status}")

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
        for name, real_sec, game_millis in AUTO_TIME_PRESETS:
            game_sec = game_millis // 1000
            # 현재 선택된 프리셋은 하이라이트
            if name == preset_name:
                lines.append(f"    [color=lime]● {name}[/color] ({real_sec}초 → {game_sec}초)")
            else:
                lines.append(f"    [url=@proc:set_interval:{real_sec}:{game_millis}]○ {name}[/url] ({real_sec}초 → {game_sec}초)")

    lines.append("")

    # 타이핑 속도 설정 (토글 메뉴)
    typing_preset = get_typing_speed_preset_name()
    typing_icon = "▼" if show_typing_menu else "▶"
    lines.append(f"[url=@proc:toggle_typing_menu]{typing_icon} 타이핑 속도[/url]: [color=yellow]{typing_preset}[/color]")

    if show_typing_menu:
        current_speed = morld.get_typing_speed()
        for name, speed in TYPING_SPEED_PRESETS:
            if speed == current_speed:
                lines.append(f"  [color=lime]● {name}[/color]")
            else:
                lines.append(f"  [url=@proc:set_typing_speed:{speed}]○ {name}[/url]")

    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # 게임 종료
    lines.append("[url=@proc:quit]게임 종료[/url]")

    lines.append("")
    lines.append("[url=@finish]닫기[/url]")

    # 전체를 즉시 출력으로 감싸기 (ui.divider()의 [!][/!]는 중첩 처리됨)
    return "[!]" + "\n".join(lines) + "[/!]"


def show_settings_ui():
    """
    설정 UI 다이얼로그 표시 (Generator)
    """
    state = {"refresh": True, "confirm_quit": False, "show_interval_menu": False, "show_typing_menu": False}

    def _render():
        """현재 상태로 UI 렌더링"""
        return render_settings_ui(
            confirm_quit=state.get("confirm_quit", False),
            show_interval_menu=state.get("show_interval_menu", False),
            show_typing_menu=state.get("show_typing_menu", False)
        )

    def proc(action):
        if action == "init" or state.get("refresh"):
            state["refresh"] = False
            return _render()

        # 디버그 모드 토글
        if action == "toggle_debug":
            new_state = not is_debug_mode()
            set_debug_mode(new_state)
            morld.add_action_log(f"디버그 모드: {'ON' if new_state else 'OFF'}")
            return _render()

        # 연애 모드 토글
        if action == "toggle_romance":
            new_state = not is_romance_enabled()
            set_romance_enabled(new_state)
            morld.add_action_log(f"연애 모드: {'ON' if new_state else 'OFF'}")
            return _render()

        # 수간 모드 토글
        if action == "toggle_bestiality":
            new_state = not is_bestiality_enabled()
            set_bestiality_enabled(new_state)
            morld.add_action_log(f"수간 모드: {'ON' if new_state else 'OFF'}")
            return _render()

        # 적대 모드 토글
        if action == "toggle_hostile":
            import combat
            combat.set_hostile_mode(not combat.is_hostile_mode())
            status = "ON" if combat.is_hostile_mode() else "OFF"
            morld.add_action_log(f"적대 모드: {status}")
            return _render()

        # 성추행 모드 토글
        if action == "toggle_harassment":
            new_state = not is_harassment_enabled()
            set_harassment_enabled(new_state)
            morld.add_action_log(f"성추행 모드: {'ON' if new_state else 'OFF'}")
            return _render()

        # 달리기 토글
        if action == "toggle_sprint":
            player_id = _get_player_id()
            if player_id >= 0:
                current = morld.get_unit_prop(player_id, "이동:달리기") or 0
                if not current:
                    fatigue = morld.get_unit_prop(player_id, "욕구:피로") or 0
                    if fatigue >= 90:
                        morld.add_action_log("너무 피곤해서 달릴 수 없다.")
                        return _render()
                morld.set_unit_prop(player_id, "이동:달리기", 0 if current else 1)
                status = "ON" if not current else "OFF"
                morld.add_action_log(f"달리기: {status}")
            return _render()

        # 시간 정지 토글
        if action == "toggle_frozen":
            current = morld.is_time_frozen()
            morld.set_time_frozen(not current)
            status = "정지" if not current else "흐름"
            morld.add_action_log(f"시간: {status}")
            return _render()

        # 시간 자동 흐름 토글
        if action == "toggle_auto_time":
            new_state = not is_auto_time_flow()
            set_auto_time_flow(new_state)
            morld.add_action_log(f"시간 자동 흐름: {'ON' if new_state else 'OFF'}")
            return _render()

        # 시간 간격 메뉴 토글
        if action == "toggle_interval_menu":
            state["show_interval_menu"] = not state.get("show_interval_menu", False)
            return _render()

        # 시간 간격 설정
        if action.startswith("set_interval:"):
            parts = action.split(":")
            if len(parts) == 3:
                real_sec = float(parts[1])
                game_millis = int(parts[2])
                morld.set_auto_time_flow_interval(real_sec, game_millis)
                # 프리셋 이름 찾기
                preset_name = "사용자 설정"
                for name, preset_sec, preset_millis in AUTO_TIME_PRESETS:
                    if abs(real_sec - preset_sec) < 0.01 and game_millis == preset_millis:
                        preset_name = name
                        break
                morld.add_action_log(f"시간 간격: {preset_name}")
            return _render()

        # 타이핑 속도 메뉴 토글
        if action == "toggle_typing_menu":
            state["show_typing_menu"] = not state.get("show_typing_menu", False)
            return _render()

        # 타이핑 속도 설정
        if action.startswith("set_typing_speed:"):
            parts = action.split(":")
            if len(parts) == 2:
                speed = int(parts[1])
                morld.set_typing_speed(speed)
                # 프리셋 이름 찾기
                preset_name = f"{speed}자/초"
                for name, preset_speed in TYPING_SPEED_PRESETS:
                    if speed == preset_speed:
                        preset_name = name
                        break
                morld.add_action_log(f"타이핑 속도: {preset_name}")
            return _render()

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
            return _render()

        return None

    yield ui.dialog("", autofill="off", proc=proc, result=state)
