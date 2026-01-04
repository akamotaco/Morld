# -*- coding: utf-8 -*-
"""
시나리오01: 방탈출 - 공통 스크립트 함수
Asset 기반 구조에서 스크립트 함수들을 export
"""

import morld

# ============================================================
# 아이템 스크립트 함수들 import (assets에서)
# ============================================================
from assets.items.notes import read_note1, read_note2, read_note3
from assets.items.documents import read_diary, read_old_letter, read_study_memo
from assets.items.golden_key import combine_golden_key

# 호환성을 위한 alias
combine_key = combine_golden_key

# ============================================================
# 오브젝트 스크립트 함수들 import (assets에서)
# ============================================================
from assets.objects.basement import examine_old_box, toggle_switch
from assets.objects.storage import examine_shelf, unlock_cabinet
from assets.objects.living_room import examine_fireplace, examine_sofa
from assets.objects.kitchen import examine_refrigerator, unlock_cupboard
from assets.objects.bedroom import examine_bed, open_vanity_drawer
from assets.objects.study import open_safe, examine_desk
from assets.objects.corridor import (
    examine_picture, examine_clock, examine_umbrella,
    unlock_study_door, input_study_digit, verify_study_password
)
from assets.objects.stairs import examine_step, examine_window
from assets.objects.entrance import escape, show_ending

# 비밀번호 시스템용 모듈 참조
from assets.objects import bedroom as vanity_module
from assets.objects import study as safe_module

# PASSWORD_OBJECTS 매핑 (password_target_uid 값으로 조회)
PASSWORD_OBJECTS = {
    0: vanity_module,  # vanity_drawer
    1: safe_module,    # safe
}


# ============================================================
# 비밀번호 시스템 (공통)
# ============================================================

def input_digit(context_unit_id, digit):
    """비밀번호 숫자 입력 (공통)"""
    digit = int(digit)

    current_input = morld.get_flag("password_input")
    current_digits = morld.get_flag("password_digits")

    # 새 숫자 추가
    new_input = current_input * 10 + digit
    new_digits = current_digits + 1

    morld.set_flag("password_input", new_input)
    morld.set_flag("password_digits", new_digits)

    # 4자리 완성되면 검증
    if new_digits >= 4:
        return verify_password(context_unit_id)

    # 현재 입력 상태 표시
    display = str(new_input).zfill(new_digits)
    display_padded = display + "_" * (4 - new_digits)

    return {
        "type": "update",
        "pages": [
            f"4자리 비밀번호를 입력하세요:\n\n[{display_padded}]\n\n" +
            "[url=script:input_digit:1][ 1 ][/url] [url=script:input_digit:2][ 2 ][/url] [url=script:input_digit:3][ 3 ][/url]\n" +
            "[url=script:input_digit:4][ 4 ][/url] [url=script:input_digit:5][ 5 ][/url] [url=script:input_digit:6][ 6 ][/url]\n" +
            "[url=script:input_digit:7][ 7 ][/url] [url=script:input_digit:8][ 8 ][/url] [url=script:input_digit:9][ 9 ][/url]\n" +
            "        [url=script:input_digit:0][ 0 ][/url]\n\n" +
            "[url=script:cancel_password][ 취소 ][/url]"
        ],
        "time_consumed": 0,
        "button_type": "none"
    }


def verify_password(context_unit_id):
    """비밀번호 검증 (공통)"""
    target_uid = morld.get_flag("password_target_uid")
    input_password = str(morld.get_flag("password_input")).zfill(4)

    # 오브젝트별 비밀번호 정보 가져오기
    obj_module = PASSWORD_OBJECTS.get(target_uid)
    if not obj_module:
        return {"type": "monologue", "pages": ["오류가 발생했다."], "time_consumed": 0}

    correct_password = obj_module.PASSWORD

    if input_password == correct_password:
        # 성공 시 해당 오브젝트의 콜백 호출
        return obj_module.on_password_success()
    else:
        # 실패
        return {
            "type": "monologue",
            "pages": ["삐빅- 비밀번호가 틀렸다."],
            "time_consumed": 0
        }


def cancel_password(context_unit_id):
    """비밀번호 입력 취소"""
    morld.clear_flag("password_target_uid")
    morld.clear_flag("password_input")
    morld.clear_flag("password_digits")
    return {
        "type": "monologue",
        "pages": ["입력을 취소했다."],
        "time_consumed": 0
    }
