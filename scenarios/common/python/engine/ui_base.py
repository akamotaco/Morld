# ui_base.py — 공통 UI 프레임워크
#
# 시나리오 공통 UI 함수 (S02/S04 동일 로직 추출)
# - 글로벌 상태 (header/footer/ui_lock)
# - 렌더 컨텍스트
# - 탭 시스템 프레임워크
# - 유틸리티 (divider, stat_bar, format_time, move_confirm)
# - 대화 시스템 (dialog, render_page)
#
# 시나리오 ui.py에서 import하여 사용.
# 시나리오별 탭 구성/콘텐츠는 시나리오가 제공.

import morld
from ui_style import (
    MUTED, ACCENT,
    c, style_muted, style_highlight,
)

MILLIS_PER_MINUTE = 60_000
MILLIS_PER_HOUR = 3_600_000

CHAIN_PREFIX = "+"


# ========================================
# 글로벌 상태
# ========================================

_show_header = True
_show_footer = True
_ui_locked = False


def set_show_header(show):
    """헤더 UI 표시 설정 (False면 숨김)"""
    global _show_header
    _show_header = show


def set_show_footer(show):
    """푸터 UI 표시 설정 (False면 숨김)"""
    global _show_footer
    _show_footer = show


def is_header_visible():
    """헤더 UI 표시 여부"""
    return _show_header


def is_footer_visible():
    """푸터 UI 표시 여부"""
    return _show_footer


def set_ui_lock(locked):
    """UI Lock 설정

    Lock이 켜지면 모든 Focus 타입에서 레터박스 스타일 강제 적용.
    인벤토리/퀘스트/설정 메뉴가 구분선으로 가려짐.
    """
    global _ui_locked
    _ui_locked = locked


def is_ui_locked():
    """UI Lock 상태 여부"""
    return _ui_locked


def reset():
    """챕터 전환 시 리셋"""
    global _show_header, _show_footer, _ui_locked
    _show_header = True
    _show_footer = True
    _ui_locked = False


# ========================================
# 렌더 컨텍스트
# ========================================

_render_context = {
    "focus_type": "Situation",
    "view_tab": 0,
    "target_unit_id": None,
}


def set_render_context(focus_type, view_tab, target_unit_id=None):
    """C#에서 FlushDisplay 시 호출 — 현재 Focus 정보 저장 (header 탭 라벨용)"""
    _render_context["focus_type"] = focus_type
    _render_context["view_tab"] = view_tab
    _render_context["target_unit_id"] = target_unit_id


def get_render_context():
    """현재 렌더 컨텍스트 반환"""
    return _render_context


# ========================================
# 유틸리티
# ========================================

def divider(color=MUTED, length=20):
    """구분선 반환 (즉시 출력 태그 포함)"""
    line = "─" * length
    return f"[!][color={color}]{line}[/color][/!]"


def stat_bar(value, max_val, length=10):
    """값을 막대 바로 변환 (████░░░░)"""
    if value is None or max_val <= 0:
        return "░" * length
    ratio = max(0, min(1, value / max_val))
    filled = int(ratio * length)
    return "█" * filled + "░" * (length - filled)


def is_character(unit_id):
    """유닛이 캐릭터(NPC)인지 확인"""
    try:
        info = morld.get_unit_info(unit_id)
        if info and not info.get("is_object", False):
            return True
    except Exception:
        pass
    return False


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


def get_move_confirm_message(travel_time_millis):
    """이동 확인 다이얼로그 메시지 생성

    C#의 ExecuteMoveWithConfirm()에서 호출.
    """
    time_text = format_time(int(travel_time_millis))
    return f"이동하는 데 {time_text}이 걸립니다. 이동하시겠습니까?"


# ========================================
# 시간/날씨 텍스트
# ========================================

def get_time_weather_text():
    """시간 + 날씨 정보 텍스트 반환

    C# GameTime.ToString()과 동일한 포맷:
    "{year}년 {month}월 {day}일 ({weekday}) {hour:02d}:{minute:02d} / {weather}"
    """
    try:
        time_info = morld.get_time_info()
        if not time_info:
            return ""

        year = time_info.get("year", 1)
        month = time_info.get("month", 1)
        day = time_info.get("day", 1)
        weekday = time_info.get("weekday", "")
        hour = time_info.get("hour", 0)
        minute = time_info.get("minute", 0)
        time_str = f"{year}년 {month}월 {day}일 ({weekday}) {hour:02d}:{minute:02d}"

        weather = time_info.get("weather", "")

        # 플레이어 위치 조회
        loc = None
        try:
            player_id = morld.get_player_id()
            if player_id is not None:
                loc = morld.get_unit_location(player_id)
        except Exception:
            pass

        # 온도
        temp_text = ""
        try:
            import temperature
            if loc:
                temp = temperature.get_temperature(loc[0], loc[1])
                if temp is not None:
                    temp_text = f" {temp:.0f}℃"
        except ImportError:
            pass

        # 습도 + 날씨 강도
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

        # 혼잡도
        congestion_text = ""
        try:
            import congestion
            if loc:
                cong = congestion.get_congestion(loc[0], loc[1])
                if cong is not None and cong > 1.0:
                    congestion_text = f" {style_highlight(f'혼잡x{cong:.1f}')}"
                elif cong is not None and cong > 0.5:
                    congestion_text = f" 혼잡x{cong:.1f}"
        except ImportError:
            pass

        if weather_display:
            return f"{time_str} / {weather_display}{temp_text}{humidity_text}{congestion_text}"
        if temp_text:
            return f"{time_str}{temp_text}{humidity_text}{congestion_text}"
        return time_str
    except Exception as e:
        print(f"[ui_base] get_time_weather_text error: {e}")
        return ""


# ========================================
# 상태 텍스트
# ========================================

def get_status_text():
    """캐릭터 상태 텍스트 반환 (체력/포만감 바 + 상태 이상)"""
    try:
        import survival
        player_id = morld.get_player_id()
        if player_id is None:
            return ""

        lines = []
        status_bar = survival.get_status_bar(player_id)
        if status_bar:
            lines.append(status_bar)
        status_msg = survival.get_status_message(player_id)
        if status_msg:
            lines.append(status_msg)
        return "\n".join(lines)
    except ImportError:
        return ""
    except Exception as e:
        print(f"[ui_base] get_status_text error: {e}")
        return ""


# ========================================
# 탭 시스템
# ========================================

def get_tab_label_line(labels=None, focus_type=None, view_tab=None, target_unit_id=None):
    """현재 Focus의 탭 라벨 줄 반환

    탭이 있을 때만 표시.
    현재 활성 탭은 [▶이름] 형식 (클릭 불가),
    비활성 탭은 [이름] 형식 (클릭으로 전환).

    Args:
        labels: 탭 라벨 리스트 (None이면 렌더 컨텍스트에서 자동 조회)
        focus_type, view_tab, target_unit_id: labels가 None일 때 사용
    """
    if focus_type is None:
        focus_type = _render_context["focus_type"]
    if view_tab is None:
        view_tab = _render_context["view_tab"]

    if labels is None or len(labels) == 0:
        return ""

    parts = []
    for i, label in enumerate(labels):
        if i == view_tab:
            parts.append(c(ACCENT, f"[▶{label}]"))
        else:
            parts.append(f"[url=tab:{i}%][{label}][/url]")

    return "  ".join(parts)


# ========================================
# 대화 시스템
# ========================================

def render_page(pages, state):
    """현재 페이지 렌더링 (연쇄 출력 처리 포함)

    Args:
        pages: 페이지 리스트
        state: {"page": int, "accumulated": str}

    Returns:
        렌더링된 텍스트 (마지막 페이지면 확인 버튼)
    """
    idx = state["page"]
    page = pages[idx]

    # 이스케이프 처리: \+ → +
    if page.startswith("\\+"):
        page = page[1:]
        state["accumulated"] = page
        text = page
    elif page.startswith(CHAIN_PREFIX):
        new_text = page[len(CHAIN_PREFIX):]
        if state["accumulated"]:
            text = f"[!]{state['accumulated']}\n[/!]{new_text}"
            state["accumulated"] = state["accumulated"] + "\n" + new_text
        else:
            text = new_text
            state["accumulated"] = new_text
    else:
        text = page
        state["accumulated"] = page

    if idx < len(pages) - 1:
        text += "\n\n[url=@proc:next]다음[/url]"
    else:
        text += "\n\n[url=@proc:finish]확인[/url]"

    return text


def dialog(content, **kwargs):
    """향상된 다이얼로그 - 문자열 또는 리스트(다 페이지) 지원

    단일 페이지: yield ui.dialog("텍스트")
    다 페이지:   yield ui.dialog(["첫번째", "+두번째(연쇄)", "세번째(새로)"])
    이스케이프:  "\\+로 시작"
    """
    if isinstance(content, str):
        return morld.dialog(content, **kwargs)

    if "autofill" in kwargs and kwargs["autofill"] not in ("off", None):
        return morld.dialog(content, **kwargs)

    pages = content
    state = {"page": 0, "accumulated": ""}
    initial_text = render_page(pages, state)

    def proc(action):
        if action == "init":
            return None
        if action == "next":
            state["page"] += 1
            if state["page"] >= len(pages):
                return True
            return render_page(pages, state)
        if action == "finish":
            return True
        return None

    return morld.dialog(initial_text, autofill="off", proc=proc, **kwargs)
