# ui.py - UI 훅 함수
#
# C#에서 호출하는 UI 관련 Python 훅
# - get_status_header(): 상태바 헤더 (체력, 포만감)
# - get_action_text(): 행동 옵션 BBCode 생성
# - ui_get_move_confirm_message(): 이동 확인 다이얼로그 메시지

import morld


def get_status_header():
    """
    상태바 헤더 반환 (메인 화면 상단)

    C#의 DescribeSystem에서 호출됩니다.
    체력, 포만감 상태바와 상태 이상 메시지를 반환합니다.

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
        print(f"[ui] get_status_header error: {e}")
        return ""


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

    # 인벤토리
    lines.append("  [url=inventory]인벤토리[/url]")

    # 멍때리기 (시간 선택 토글)
    # ToggleRenderer가 [hidden=idle]...[/hidden=idle] 영역을 펼침/접힘 처리
    lines.append("  [url=toggle:idle]▶멍때리기[/url]")
    lines.append("[hidden=idle]")
    lines.append("    [url=idle:15]15분[/url]")
    lines.append("    [url=idle:30]30분[/url]")
    lines.append("    [url=idle:60]1시간[/url]")
    lines.append("    [url=idle:240]4시간[/url]")
    lines.append("[/hidden=idle]")

    # 시간 기반 조건부 행동
    minute_of_day = morld.get_game_time()  # 분 단위 (0~1439)
    hour = minute_of_day // 60

    # 낮잠 (6시~18시만 가능)
    if 6 <= hour < 18:
        lines.append("  [url=idle:240]낮잠 (4시간)[/url]")
    else:
        lines.append("  [color=gray]낮잠 (4시간)[/color]")

    # 상태바 (체력, 포만감) - 행동 섹션 아래에 표시
    status_header = get_status_header()
    if status_header:
        lines.append("")
        lines.append("[color=gray]────────────────────[/color]")
        lines.append(status_header)

    return "\n".join(lines)
