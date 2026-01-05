# assets/objects/corridor.py - 복도 오브젝트 (그림 액자, 괘종시계, 우산꽂이, 서재 문)

import morld
from assets.base import Object


class PictureFrame(Object):
    """그림 액자"""
    unique_id = "picture_frame"
    name = "그림 액자"
    actions = ["script:examine_picture:조사"]
    focus_text = {
        "default": "벽에 비스듬히 걸린 오래된 풍경화다. 금박 액자 테두리가 벗겨져 있다. 그림 뒤에 뭔가 숨겨져 있을 것 같은 느낌이 든다."
    }
    examine_message = "그림 뒤쪽을 살펴보니 '4'와 '9'라는 숫자가 적혀 있다."


class GrandfatherClock(Object):
    """괘종시계"""
    unique_id = "grandfather_clock"
    name = "괘종시계"
    actions = ["script:examine_clock:조사"]
    focus_text = {
        "default": "복도 끝에 서있는 커다란 괘종시계다. 시계는 멈춰있고, 시각은 18:42를 가리키고 있다. 문양이 새겨진 장식이 눈에 띈다."
    }


class UmbrellaStand(Object):
    """우산꽂이"""
    unique_id = "umbrella_stand"
    name = "우산꽂이"
    actions = ["script:examine_umbrella:조사"]
    focus_text = {
        "default": "구리 재질의 우산꽂이다. 낡은 우산 몇 개와 지팡이가 꽂혀 있다. 바닥에 뭔가 떨어져 있는 것 같다."
    }


class StudyDoor(Object):
    """서재 문"""
    unique_id = "study_door"
    name = "서재 문"
    actions = ["script:unlock_study_door:열기"]
    focus_text = {
        "default": "두꺼운 참나무 문이다. 전자식 4자리 비밀번호 잠금장치가 설치되어 있다.",
        "unlocked": "열린 서재 문이다. 안에서 오래된 책 냄새가 풍겨온다."
    }
    password = "2847"


# ========================================
# 스크립트 함수
# ========================================

def examine_picture(context_unit_id):
    """그림 액자 조사 - 숫자 힌트"""
    flag_name = f"examined_{PictureFrame.unique_id}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    morld.set_flag(flag_name, 1)

    return {
        "type": "monologue",
        "pages": [PictureFrame.examine_message],
        "time_consumed": 1
    }


def examine_clock(context_unit_id):
    """괘종시계 조사"""
    return {
        "type": "monologue",
        "pages": [
            "오래된 괘종시계다.",
            "시계는 18시 42분에 멈춰있다.",
            "태엽을 감아도 움직이지 않는다.",
            "시계 바닥에 '1842년 제작'이라고 새겨져 있다."
        ],
        "time_consumed": 1
    }


def examine_umbrella(context_unit_id):
    """우산꽂이 조사"""
    return {
        "type": "monologue",
        "pages": [
            "우산꽂이를 뒤적여본다.",
            "낡은 우산들과 지팡이... 그리고 바닥에 동전 몇 개가 굴러다닌다.",
            "특별히 쓸모있어 보이는 건 없다."
        ],
        "time_consumed": 1
    }


def unlock_study_door(context_unit_id):
    """서재 문 비밀번호 입력"""
    if morld.get_flag("study_unlocked") > 0:
        return {
            "type": "monologue",
            "pages": ["서재 문은 이미 열려 있다."],
            "time_consumed": 0
        }

    # 비밀번호 입력 UI (서재 문 전용)
    morld.set_flag("password_target_uid", -1)  # 특수: 서재 문
    morld.set_flag("password_input", 0)
    morld.set_flag("password_digits", 0)

    return {
        "type": "monologue",
        "pages": [
            "서재 문에 비밀번호 잠금장치가 있다.\n4자리 비밀번호를 입력하세요:\n\n[    ]\n\n" +
            "[url=script:input_study_digit:1][ 1 ][/url] [url=script:input_study_digit:2][ 2 ][/url] [url=script:input_study_digit:3][ 3 ][/url]\n" +
            "[url=script:input_study_digit:4][ 4 ][/url] [url=script:input_study_digit:5][ 5 ][/url] [url=script:input_study_digit:6][ 6 ][/url]\n" +
            "[url=script:input_study_digit:7][ 7 ][/url] [url=script:input_study_digit:8][ 8 ][/url] [url=script:input_study_digit:9][ 9 ][/url]\n" +
            "        [url=script:input_study_digit:0][ 0 ][/url]\n\n" +
            "[url=script:cancel_password][ 취소 ][/url]"
        ],
        "time_consumed": 0,
        "button_type": "none"
    }


def input_study_digit(context_unit_id, digit):
    """서재 문 비밀번호 숫자 입력"""
    digit = int(digit)

    current_input = morld.get_flag("password_input")
    current_digits = morld.get_flag("password_digits")

    new_input = current_input * 10 + digit
    new_digits = current_digits + 1

    morld.set_flag("password_input", new_input)
    morld.set_flag("password_digits", new_digits)

    if new_digits >= 4:
        return verify_study_password(context_unit_id)

    # 현재 입력 상태 표시
    display = str(new_input).zfill(new_digits)
    display_padded = display + "_" * (4 - new_digits)

    return {
        "type": "update",
        "pages": [
            f"서재 문 비밀번호:\n\n[{display_padded}]\n\n" +
            "[url=script:input_study_digit:1][ 1 ][/url] [url=script:input_study_digit:2][ 2 ][/url] [url=script:input_study_digit:3][ 3 ][/url]\n" +
            "[url=script:input_study_digit:4][ 4 ][/url] [url=script:input_study_digit:5][ 5 ][/url] [url=script:input_study_digit:6][ 6 ][/url]\n" +
            "[url=script:input_study_digit:7][ 7 ][/url] [url=script:input_study_digit:8][ 8 ][/url] [url=script:input_study_digit:9][ 9 ][/url]\n" +
            "        [url=script:input_study_digit:0][ 0 ][/url]\n\n" +
            "[url=script:cancel_password][ 취소 ][/url]"
        ],
        "time_consumed": 0,
        "button_type": "none"
    }


def verify_study_password(context_unit_id):
    """서재 문 비밀번호 검증"""
    input_password = str(morld.get_flag("password_input")).zfill(4)

    if input_password == StudyDoor.password:
        morld.set_flag("study_unlocked", 1)
        morld.add_action_log("서재 문이 열렸다")
        return {
            "type": "monologue",
            "pages": [
                "딸깍!",
                "비밀번호가 맞았다!",
                "서재 문이 열렸다. 이제 들어갈 수 있다."
            ],
            "time_consumed": 1
        }
    else:
        return {
            "type": "monologue",
            "pages": ["삐빅- 비밀번호가 틀렸다."],
            "time_consumed": 0
        }
