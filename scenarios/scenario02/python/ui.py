# ui.py - UI 훅 함수
#
# C#에서 호출하는 UI 관련 Python 훅
# - get_header(): 상단 정보 (시간/날씨)
# - get_footer(): 하단 정보 (상태바)
# - get_action_text(): 행동 옵션 BBCode 생성
# - ui_get_move_confirm_message(): 이동 확인 다이얼로그 메시지

import morld

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
    lines.append(divider())
    lines.append("[url=inventory]인벤토리[/url]  [url=quest]퀘스트[/url]  [url=settings]설정[/url]")

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

    return divider() + "\n" + "\n".join(lines)


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

    # 은신 상태 체크
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

    # 플레이어 마커 — 가장 가까운 Gate의 ●를 ▶/▷로 대체
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

        # 경로 표시
        if route["is_blocked"]:
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

    # 이동 UI (Gate X 순서, 플레이어 위치 표시)
    movement_info = morld.get_movement_info()
    if movement_info is not None:
        lines.extend(_render_movement(movement_info))

    # C#에서 나머지 행동 리스트 가져오기 (앉은 상태 등)
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
    player_id = morld.get_player_id()
    if player_id is not None:
        player_props = morld.get_actual_props(player_id)
        can_use_map = False

        # 나침반(can:map) - 모든 지역에서 사용 가능
        if player_props.get("can:map", 0) >= 1:
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
                if map_prop and player_props.get(map_prop, 0) >= 1:
                    can_use_map = True

        if can_use_map:
            lines.append("  [url=map:open]지도[/url]")

    # 상태바는 get_footer()로 분리됨 (C#에서 별도 호출)

    return "\n".join(lines)


# ========================================
# 다이얼로그 래퍼 (다 페이지 지원)
# ========================================

# 연쇄 출력 접두사 (이 문자로 시작하면 이전 페이지 누적)
CHAIN_PREFIX = "+"


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
