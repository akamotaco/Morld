# ui.py - UI 훅 함수
#
# C#에서 호출하는 UI 관련 Python 훅
# - get_header(): 상단 정보 (시간/날씨)
# - get_footer(): 하단 정보 (상태바)
# - get_action_text(): 행동 옵션 BBCode 생성
# - ui_get_move_confirm_message(): 이동 확인 다이얼로그 메시지

import morld
import lighting

MILLIS_PER_MINUTE = 60_000
MILLIS_PER_HOUR = 3_600_000


# ========================================
# 구분선 (즉시 출력)
# ========================================

def divider(color: str = "gray", length: int = 20) -> str:
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
                if cong > 1.0:
                    congestion_text = f" [color=yellow]혼잡x{cong:.1f}[/color]"
                elif cong > 0.5:
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
            return "[color=yellow][어두움][/color]"
        else:  # 암흑
            return "[color=red][암흑][/color]"
    except Exception as e:
        print(f"[ui] _get_brightness_text error: {e}")
        return ""


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
        lines.append(f"[color=gray][{geo_text}] X:{int(position_x)}/{int(location_length)}[/color]")

        # 시간 정지 상태 표시
        if morld.is_time_frozen():
            lines.append("[color=cyan][시간 정지][/color]")

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
                parts.append(f"[color=cyan]체온 {body_temp:.1f}℃[/color]")
            elif body_temp > 37.5:
                parts.append(f"[color=red]체온 {body_temp:.1f}℃[/color]")
            else:
                parts.append(f"체온 {body_temp:.1f}℃")
        except ImportError:
            pass

        # 젖음 (> 0일 때만)
        try:
            import humidity
            wetness = humidity.get_unit_wetness(player_id)
            if wetness and wetness > 0:
                parts.append(f"[color=cyan]젖음 {wetness:.0f}%[/color]")
        except ImportError:
            pass

        # 오염 (> 0일 때만)
        try:
            import pollution
            pol = pollution.get_unit_pollution(player_id)
            if pol and pol > 0:
                parts.append(f"[color=orange]오염 {pol:.0f}[/color]")
        except ImportError:
            pass

        # 욕구 (임계치 근처일 때만 표시)
        try:
            import needs
            excretion = needs.get_excretion(player_id)
            if excretion >= 50:
                color = "red" if excretion >= 70 else "yellow"
                parts.append(f"[color={color}]배변 {excretion:.0f}[/color]")

            fatigue = needs.get_fatigue(player_id)
            if fatigue >= 50:
                color = "red" if fatigue >= 80 else "yellow"
                parts.append(f"[color={color}]피로 {fatigue:.0f}[/color]")

            cleanliness = needs.get_cleanliness(player_id)
            if cleanliness >= 50:
                color = "red" if cleanliness >= 70 else "yellow"
                parts.append(f"[color={color}]불결 {cleanliness:.0f}[/color]")
        except ImportError:
            pass

        return " | ".join(parts) if parts else ""
    except Exception as e:
        print(f"[ui] _get_environment_status_text error: {e}")
        return ""


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
    lines.append("[url=inventory]인벤토리[/url]  [url=quest]퀘스트[/url]  [url=settings]설정[/url]")

    status_text = get_status_text()
    if status_text:
        lines.append(status_text)

    # 환경 상태 (체온/젖음/오염)
    env_text = _get_environment_status_text()
    if env_text:
        lines.append(env_text)

    # 플레이어 자세 정보 (기본 자세가 아닌 경우만 표시)
    posture_text = _get_posture_text()
    if posture_text:
        lines.append(posture_text)

    return "\n".join(lines)


# 자세 정보 매핑
# - lying: 눕기 (침구류) - 이동 불가, 오브젝트 필요
# - sitting: 앉기 (의자류) - 이동 불가, 오브젝트 필요
# - crouch: 웅크리기 - 이동 가능, 속도 50%
# - prone: 엎드리기 - 이동 가능, 속도 25%
# - standing: 서기 (기본) - 이동 가능, 속도 100%
#
# speed: 이동 속도 계수 (100 = 기본)
# can_toggle: 자세 로테이션에 포함되는지 (standing/crouch/prone만 해당)
POSTURE_INFO = {
    "standing": {"name": "서기", "can_move": True, "speed": 100, "can_toggle": True},
    "lying": {"name": "눕기", "can_move": False, "speed": 0, "can_toggle": False},
    "sitting": {"name": "앉기", "can_move": False, "speed": 0, "can_toggle": False},
    "crouch": {"name": "웅크리기", "can_move": True, "speed": 50, "can_toggle": True},
    "prone": {"name": "엎드리기", "can_move": True, "speed": 25, "can_toggle": True},
}

# 자세 로테이션 순서 (서기 → 웅크리기 → 엎드리기 → 서기)
POSTURE_ROTATION = ["standing", "crouch", "prone"]


def get_current_posture() -> str:
    """
    플레이어 현재 자세 반환

    Returns:
        str: 자세 키 ("standing", "crouch", "prone", "sitting", "lying")
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return "standing"

    posture_props = morld.get_unit_props_by_type(player_id, "posture")
    if not posture_props:
        return "standing"
    return list(posture_props.keys())[0]


def get_posture_speed() -> int:
    """
    현재 자세의 이동 속도 계수 반환 (C#에서 호출)

    Returns:
        int: 속도 계수 (100=기본, 50=웅크리기, 25=엎드리기)
    """
    posture = get_current_posture()
    info = POSTURE_INFO.get(posture)
    if info is None:
        return 100
    return info.get("speed", 100)


# ========================================
# 은신 시스템 (Stealth)
# ========================================
#
# status:stealth prop 값:
# - 1: 은신 중 (NPC 감지 회피 가능)
# - 0: 발각됨 (현재 Location에서만 유지)
# - (없음): 일반 상태
#
# 은신 진입 조건:
# - 자세가 crouch 또는 prone
# - 같은 Location에 NPC가 없음
#
# 은신 해제 조건:
# - 자세 변경 (standing)
# - 발각됨
# - 휴대 광원 켜기
# - 수동 해제
# - Location 이동 (발각 상태만 해제)

def get_stealth_state() -> int | None:
    """
    현재 은신 상태 반환

    Returns:
        1: 은신 중
        0: 발각됨
        None: 일반 상태
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return None

    stealth = morld.get_unit_prop(player_id, "status:stealth")
    return stealth


def is_stealth_posture(posture: str = None) -> bool:
    """
    은신 가능한 자세인지 확인

    Args:
        posture: 확인할 자세 (None이면 현재 자세)

    Returns:
        bool: crouch 또는 prone이면 True
    """
    if posture is None:
        posture = get_current_posture()
    return posture in ["crouch", "prone"]


def check_stealth_entry() -> bool:
    """
    은신 진입 조건 확인 및 상태 설정

    조건:
    - 자세가 crouch 또는 prone
    - 같은 Location에 NPC가 없음

    Returns:
        bool: 은신 진입 성공 여부
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return False

    # 이미 은신 중이면 스킵
    if get_stealth_state() == 1:
        return True

    # 발각 상태면 진입 불가
    if get_stealth_state() == 0:
        return False

    # 자세 확인
    posture = get_current_posture()
    if not is_stealth_posture(posture):
        return False

    # 현재 Location 확인
    player_loc = morld.get_unit_location(player_id)
    if player_loc is None:
        return False

    # 같은 Location에 NPC가 있는지 확인
    # get_units_at_location은 캐릭터만 반환 (IsObject=false), 이동 중인 유닛 제외
    region_id, local_id = player_loc
    npcs = morld.get_units_at_location(region_id, local_id)
    if npcs is None:
        npcs = []
    # 플레이어 제외
    npc_count = len([u for u in npcs if u != player_id])
    if npc_count > 0:
        return False

    # 은신 진입
    morld.set_unit_prop(player_id, "status:stealth", 1)
    print(f"[stealth] 은신 상태 진입")
    return True


def exit_stealth(reason: str = ""):
    """
    은신 상태 해제

    Args:
        reason: 해제 사유 (로그용)
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return

    stealth = get_stealth_state()
    if stealth is not None:
        morld.clear_prop(player_id, "status:stealth")
        if reason:
            print(f"[stealth] 은신 상태 해제: {reason}")
        else:
            print(f"[stealth] 은신 상태 해제")


def on_posture_changed(old_posture: str, new_posture: str):
    """
    자세 변경 시 은신 상태 처리

    Args:
        old_posture: 이전 자세
        new_posture: 새 자세
    """
    # standing으로 변경 → 은신 해제
    if new_posture == "standing":
        exit_stealth("자세 변경 (서기)")
        return

    # crouch/prone으로 변경 → 은신 진입 시도
    if is_stealth_posture(new_posture):
        check_stealth_entry()


def toggle_posture() -> str:
    """
    자세 로테이션: 서기 → 웅크리기 → 엎드리기 → 서기

    sitting/lying 상태에서는 로테이션 불가 (먼저 일어나야 함)
    자세 변경 시 은신 상태도 함께 처리됨

    Returns:
        str: 새 자세 이름 또는 에러 메시지
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return "플레이어를 찾을 수 없습니다."

    current = get_current_posture()
    info = POSTURE_INFO.get(current)

    # sitting/lying은 로테이션 불가
    if info and not info.get("can_toggle", False):
        return f"현재 자세({info['name']})에서는 자세를 바꿀 수 없습니다. 먼저 일어나세요."

    # 다음 자세 결정
    try:
        idx = POSTURE_ROTATION.index(current)
        next_idx = (idx + 1) % len(POSTURE_ROTATION)
        next_posture = POSTURE_ROTATION[next_idx]
    except ValueError:
        # 현재 자세가 rotation에 없으면 standing으로
        next_posture = "standing"

    # 기존 posture prop 제거
    posture_props = morld.get_unit_props_by_type(player_id, "posture")
    for prop_name in posture_props:
        morld.clear_prop(player_id, f"posture:{prop_name}")

    # 새 posture prop 설정 (standing이면 prop 없음)
    if next_posture != "standing":
        morld.set_unit_prop(player_id, f"posture:{next_posture}", 1)

    # 은신 상태 처리
    on_posture_changed(current, next_posture)

    next_info = POSTURE_INFO.get(next_posture, {})
    print(f"[ui] toggle_posture: {current} -> {next_posture}")
    return next_info.get("name", next_posture)


def _get_posture_text() -> str:
    """
    플레이어 자세 및 은신 상태 텍스트 반환 (클릭 가능)

    표시 형식:
    - [서기]                    # 일반 상태
    - [웅크리기]                # 이동 가능 자세, NPC 있음
    - [웅크리기] [은신 중]      # 은신 상태
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    posture = get_current_posture()

    # posture는 posture:sitting = 1 형태로 저장됨
    posture_props = morld.get_unit_props_by_type(player_id, "posture")

    # seated_on 상태 확인
    seated_on_props = morld.get_unit_props_by_type(player_id, "seated_on")
    has_seated_on = bool(seated_on_props)

    # === 상태 불일치 검증 ===
    # posture가 이동 불가 자세인데 seated_on이 없음 → 버그
    posture_info = POSTURE_INFO.get(posture)
    if posture_info and not posture_info["can_move"] and not has_seated_on:
        print(f"[ui] WARNING: posture={posture} but seated_on is missing! (inconsistent state)")

    # seated_on이 있는데 posture가 standing → 버그
    if has_seated_on and posture == "standing":
        print(f"[ui] WARNING: seated_on is set but posture=standing! (inconsistent state)")

    # posture prop이 2개 이상 → 버그
    if len(posture_props) >= 2:
        print(f"[ui] ERROR: Multiple posture props detected: {list(posture_props.keys())}!")

    info = POSTURE_INFO.get(posture)
    if info is None:
        # 알 수 없는 자세 (fallback)
        return f"[color=gray]자세: {posture}[/color]"

    # 클릭 가능 여부 결정 (can_toggle인 경우만)
    can_toggle = info.get("can_toggle", False)

    # 은신 상태 확인
    stealth = get_stealth_state()
    stealth_text = ""
    if stealth == 1:
        stealth_text = " [color=cyan][은신 중][/color]"

    # 이동 가능 여부에 따라 색상 표시
    if info["can_move"]:
        if can_toggle:
            # 클릭하면 자세 변경 (posture:toggle 액션)
            return f"[url=posture:toggle][color=gray]자세: {info['name']}[/color][/url]{stealth_text}"
        else:
            return f"[color=gray]자세: {info['name']}[/color]{stealth_text}"
    else:
        # 이동 불가 자세는 클릭 불가 (먼저 일어나야 함)
        return f"[color=yellow]자세: {info['name']} (이동 불가)[/color]"


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

    # 표시할 경로 필터링 (is_hidden 제외) 및 gate_x 순 정렬
    routes = [r for r in info["routes"] if not r["is_hidden"]]
    routes.sort(key=lambda r: r["gate_x"])

    if not routes:
        return lines

    # 헤더
    lines.append("[color=cyan]이동 가능 지역:[/color]")

    # 상단 구분선
    if geometry == "ring":
        lines.append("[color=gray]-vvv-----------[/color]")
    else:
        lines.append("[color=gray]---------------[/color]")

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
        prefix = f"[color=yellow]{marker}[/color]" if is_closest else "●"

        # 앉은 상태 또는 blocked → grey out (클릭 불가)
        if seated or route["is_blocked"]:
            if is_closest:
                lines.append(f"  {prefix}[color=gray]{route['name']}[/color]")
            else:
                lines.append(f"  [color=gray]- {route['name']}[/color]")
        else:
            region_tag = f" [{route['region_name']}]" if route["is_region_gate"] else ""
            travel_min = route["travel_time"] // MILLIS_PER_MINUTE
            meta = f"move:{route['region_id']}:{route['local_id']}"
            lines.append(f"  [url={meta}]{prefix}{route['name']}{region_tag} ({travel_min}분)[/url]")

    # 하단 구분선
    if geometry == "ring":
        lines.append("[color=gray]-^^^-----------[/color]")
    else:
        lines.append("[color=gray]---------------[/color]")

    return lines


def get_action_text():
    """
    행동 옵션 BBCode 생성

    구조:
    - [이동] morld.get_movement_info()로 경로 데이터 → Python에서 렌더링
    - [행동:] Python에서 생성 (멍때리기, 낮잠 등)

    토글 마크업 형식:
    - [url=toggle:ID]▶텍스트[/url] - 토글 버튼
    - [hidden=ID]...[/hidden=ID] - 펼침 시 표시되는 내용

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
    posture_info = POSTURE_INFO.get(player_posture)
    can_move = posture_info["can_move"] if posture_info else True

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
    lines.append("[color=cyan]행동:[/color]")

    # 눕기/앉기 상태 → "일어나기" 행동 추가 (맨 위에)
    if not can_move and seated_on is not None:
        # 오브젝트 이름 가져오기
        obj_info = morld.get_unit_info(seated_on)
        obj_name = obj_info.get("name", "오브젝트") if obj_info else "오브젝트"
        lines.append(f"  [url=call:stand_up:{seated_on}]{obj_name}에서 일어나기[/url]")

    # 멍때리기 (시간 선택 토글)
    # ToggleRenderer가 [hidden=idle]...[/hidden=idle] 영역을 펼침/접힘 처리
    lines.append("  [url=toggle:idle]▶멍때리기[/url]")
    lines.append("[hidden=idle]")
    lines.append(f"    [url=idle:{1 * MILLIS_PER_MINUTE}]1분[/url]")
    lines.append(f"    [url=idle:{5 * MILLIS_PER_MINUTE}]5분[/url]")
    lines.append(f"    [url=idle:{15 * MILLIS_PER_MINUTE}]15분[/url]")
    lines.append(f"    [url=idle:{30 * MILLIS_PER_MINUTE}]30분[/url]")
    lines.append("[/hidden=idle]")

    # 시간 기반 조건부 행동
    millis_of_day = morld.get_game_time()  # 밀리초 단위 (0~86,399,999)
    hour = millis_of_day // MILLIS_PER_HOUR

    # 낮잠 (6시~18시만 가능)
    if 6 <= hour < 18:
        lines.append(f"  [url=idle:{240 * MILLIS_PER_MINUTE}]낮잠 (4시간)[/url]")
    else:
        lines.append("  [color=gray]낮잠 (4시간)[/color]")

    # 지도 (can:map 또는 지역별 지도 prop 보유 시)
    # get_actual_props로 passive_props 포함된 실제 props 조회
    if player_id is not None:
        player_actual_props = morld.get_actual_props(player_id)
        can_use_map = False

        # 나침반(can:map) - 모든 지역에서 사용 가능
        if player_actual_props.get("can:map", 0) >= 1:
            can_use_map = True
        else:
            # 지역별 지도 - 현재 region에서만 사용 가능
            current_loc = morld.get_unit_location(player_id)
            if current_loc:
                current_region_id = current_loc[0]
                # Region ID → 지도 prop 매핑
                region_map_props = {
                    0: "can:map:mansion",   # 저택 지역
                    1: "can:map:forest",    # 숲 지역
                    2: "can:map:city",      # 도시 지역
                }
                map_prop = region_map_props.get(current_region_id)
                if map_prop and player_actual_props.get(map_prop, 0) >= 1:
                    can_use_map = True

        if can_use_map:
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
                                text += f"[color=gray]> {label}[/color]"
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
                        history_text += f"[color=gray]> {selected_label}[/color]"
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
