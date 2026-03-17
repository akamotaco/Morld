# ui_style.py — UI 스타일 상수
#
# UI 요소의 색상을 한 곳에서 관리.
# 콘텐츠(대사/묘사/연출)는 자유롭게 [color=...] 사용 가능.
# UI 코드에서만 이 상수를 참조.

# ── 색상 값 ──

MUTED     = "gray"       # 비활성/부차 정보
HIGHLIGHT = "yellow"     # 강조/현재 위치/경고
INFO      = "cyan"       # 시스템 정보
DANGER    = "red"        # 위험
SUCCESS   = "lime"       # 긍정/존재
WARNING   = "orange"     # 주의
ACCENT    = "white"      # 활성 탭/강조 UI

# ── 상태 임계 색상 ──

STAT_NORMAL  = "white"   # 정상 범위
STAT_CAUTION = "yellow"  # 주의 범위
STAT_DANGER  = "red"     # 위험 범위

# ── 헬퍼 함수 ──

def c(color, text):
    """[color=X]text[/color] 축약"""
    return f"[color={color}]{text}[/color]"

def style_muted(text):
    return f"[color={MUTED}]{text}[/color]"

def style_highlight(text):
    return f"[color={HIGHLIGHT}]{text}[/color]"

def style_info(text):
    return f"[color={INFO}]{text}[/color]"

def style_danger(text):
    return f"[color={DANGER}]{text}[/color]"

def style_success(text):
    return f"[color={SUCCESS}]{text}[/color]"

def style_warning(text):
    return f"[color={WARNING}]{text}[/color]"

def style_section(text):
    """섹션 헤더 (── 텍스트 ──)"""
    return f"[color={MUTED}]── {text} ──[/color]"
