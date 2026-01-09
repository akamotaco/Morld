# -*- coding: utf-8 -*-
"""
시나리오01: 방탈출 - 공통 스크립트 함수
Asset 기반 구조에서 스크립트 함수들을 export

Note: 대부분의 오브젝트/아이템 스크립트는 call: 액션으로 전환되어
인스턴스 메서드로 구현됨. 이 파일에는 공용 비밀번호 UI 함수와
script: 액션을 사용하는 탈출/엔딩 스크립트만 남아 있음.
"""

import morld

# ============================================================
# 오브젝트 스크립트 import (script: 액션 사용)
# ============================================================
# entrance.py - script: 액션 사용 (탈출/엔딩)
from assets.objects.entrance import escape, show_ending


# ============================================================
# 비밀번호 입력 UI (공통 - bedroom.py, study.py에서 import)
# @proc: 패턴 기반 - 다이얼로그 내부에서 상태 변경
# ============================================================

def _build_password_ui(current_input, current_digits):
    """비밀번호 입력 UI 문자열 생성"""
    display = str(current_input).zfill(current_digits) if current_digits > 0 else ""
    display_padded = display + "_" * (4 - current_digits)

    return (
        f"4자리 비밀번호를 입력하세요:\n\n[{display_padded}]\n\n"
        "[url=@proc:1][ 1 ][/url] [url=@proc:2][ 2 ][/url] [url=@proc:3][ 3 ][/url]\n"
        "[url=@proc:4][ 4 ][/url] [url=@proc:5][ 5 ][/url] [url=@proc:6][ 6 ][/url]\n"
        "[url=@proc:7][ 7 ][/url] [url=@proc:8][ 8 ][/url] [url=@proc:9][ 9 ][/url]\n"
        "        [url=@proc:0][ 0 ][/url]\n\n"
        "[url=@proc:cancel][ 취소 ][/url]"
    )


def _create_password_proc(state):
    """비밀번호 입력 proc 콜백 생성"""
    def proc(action):
        if action == "init":
            return _build_password_ui(state["input"], state["digits"])

        if action == "cancel":
            state["cancelled"] = True
            return True  # 다이얼로그 종료

        # 숫자 입력
        try:
            digit = int(action)
        except ValueError:
            return None

        state["input"] = state["input"] * 10 + digit
        state["digits"] += 1

        # 4자리 완성되면 종료
        if state["digits"] >= 4:
            return True  # 다이얼로그 종료, result로 state 반환

        # UI 갱신
        return _build_password_ui(state["input"], state["digits"])

    return proc
