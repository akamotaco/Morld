# ui.py - UI 훅 함수
#
# C#에서 호출하는 UI 관련 Python 훅
# - get_header(): 상단 정보 (시간/날씨)
# - get_footer(): 하단 정보 (상태바)
# - get_action_text(): 행동 옵션 BBCode 생성
# - ui_get_move_confirm_message(): 이동 확인 다이얼로그 메시지

import morld


# ========================================
# UI 표시 설정
# ========================================

_show_header = True
_show_footer = True


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
        if weather:
            return f"{time_str} / {weather}"
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

        # 시간/날씨 정보
        time_text = get_time_weather_text()
        if time_text:
            lines.append(time_text)

        # 시간 정지 상태 표시
        if morld.is_time_frozen():
            lines.append("[color=cyan][시간 정지][/color]")

        return "\n".join(lines)
    except Exception as e:
        print(f"[ui] get_header error: {e}")
        return ""


def get_footer():
    """
    하단 푸터 반환 (인벤토리 + 상태바)

    Focus 화면 최하단에 표시됩니다.
    구분선 포함.

    Returns:
        str: 구분선 + 인벤토리 + 상태바 BBCode (빈 문자열이면 표시 안함)
    """
    # 푸터 숨김 상태면 빈 문자열
    if not _show_footer:
        return ""

    lines = []
    lines.append("[color=gray]────────────────────[/color]")
    lines.append("[url=inventory]인벤토리[/url]")

    status_text = get_status_text()
    if status_text:
        lines.append(status_text)

    return "\n".join(lines)


def get_info_header(show_time=True, show_status=True):
    """
    통합 정보 헤더 반환 (레거시 - 하위 호환용)

    Returns:
        str: 포맷팅된 헤더 BBCode (빈 문자열이면 표시 안함)
    """
    lines = []

    if show_time:
        time_text = get_time_weather_text()
        if time_text:
            lines.append(f"[color=gray]{time_text}[/color]")

    if show_status:
        status_text = get_status_text()
        if status_text:
            lines.append(status_text)

    if not lines:
        return ""

    return "[color=gray]────────────────────[/color]\n" + "\n".join(lines)


def format_time(minutes):
    """분 단위 시간을 읽기 좋은 형식으로 변환"""
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hours}시간 {mins}분"
    return f"{hours}시간"


def ui_get_move_confirm_message(travel_time_minutes):
    """
    이동 확인 다이얼로그 메시지 생성

    C#의 ExecuteMoveWithConfirm()에서 호출됩니다.
    threshold 이상의 이동 시간일 때 표시할 메시지를 반환합니다.

    Args:
        travel_time_minutes: 이동 시간 (분)

    Returns:
        str: 다이얼로그에 표시할 메시지
    """
    time_text = format_time(int(travel_time_minutes))
    return f"이동하는 데 {time_text}이 걸립니다. 이동하시겠습니까?"


def get_action_text():
    """
    행동 옵션 BBCode 생성

    C#의 morld.get_actions_list()로 기본 행동 리스트를 받아
    Python에서 최종 BBCode를 생성합니다.

    구조:
    - [이동 가능:] C#에서 생성 (경로 목록)
    - [행동:] Python에서 생성 (멍때리기, 낮잠 등)

    토글 마크업 형식:
    - [url=toggle:ID]▶텍스트[/url] - 토글 버튼
    - [hidden=ID]...[/hidden=ID] - 펼침 시 표시되는 내용

    Returns:
        str: 행동 옵션 BBCode 문자열 (줄바꿈으로 구분)
    """
    lines = []

    # C#에서 기본 행동 리스트 가져오기 (이동 경로 등)
    default_actions = morld.get_actions_list()
    for action in default_actions:
        lines.append(action)

    # 행동 섹션 헤더
    lines.append("")
    lines.append("[color=cyan]행동:[/color]")

    # 멍때리기 (시간 선택 토글)
    # ToggleRenderer가 [hidden=idle]...[/hidden=idle] 영역을 펼침/접힘 처리
    lines.append("  [url=toggle:idle]▶멍때리기[/url]")
    lines.append("[hidden=idle]")
    lines.append("    [url=idle:1]1분[/url]")
    lines.append("    [url=idle:5]5분[/url]")
    lines.append("    [url=idle:15]15분[/url]")
    lines.append("    [url=idle:30]30분[/url]")
    lines.append("[/hidden=idle]")

    # 시간 기반 조건부 행동
    minute_of_day = morld.get_game_time()  # 분 단위 (0~1439)
    hour = minute_of_day // 60

    # 낮잠 (6시~18시만 가능)
    if 6 <= hour < 18:
        lines.append("  [url=idle:240]낮잠 (4시간)[/url]")
    else:
        lines.append("  [color=gray]낮잠 (4시간)[/color]")

    # 상태바는 get_footer()로 분리됨 (C#에서 별도 호출)

    return "\n".join(lines)
