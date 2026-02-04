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
    별도 RichTextLabel로 분리되어 구분선 불필요.

    Returns:
        str: 인벤토리 + 상태바 BBCode (빈 문자열이면 표시 안함)
    """
    # 푸터 숨김 상태면 빈 문자열
    if not _show_footer:
        return ""

    lines = []
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
            if state["history"]:
                # 새로 추가된 부분만 분리
                if text.startswith(state["history"]):
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

                    state["choices"][choice_id] = choice_value

                    # 현재까지의 텍스트를 히스토리에 저장
                    current = _render()
                    # [!]...[/!] 제거하고 저장
                    if current.startswith("[!]"):
                        end_idx = current.find("[/!]")
                        if end_idx > 0:
                            state["history"] = current[3:end_idx] + current[end_idx+4:]
                        else:
                            state["history"] = current
                    else:
                        state["history"] = current

                    # 새 화면 렌더링
                    return _render()

            return None

        # 초기 화면
        initial = _render()
        return morld.dialog(initial, autofill="off", proc=_proc)
