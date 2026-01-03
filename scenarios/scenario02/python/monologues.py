# -*- coding: utf-8 -*-
"""
시나리오 02: 방탈출 - 모놀로그 및 이벤트 핸들러
"""

import morld

# ============================================================
# 오브젝트 데이터 (숨겨진 아이템, 잠금 상태 등)
# ============================================================

# 오브젝트별 숨겨진 아이템 (object_id -> item_id 또는 [item_ids])
HIDDEN_ITEMS = {
    100: 1,   # 낡은 상자 -> 녹슨 열쇠
    102: 4,   # 선반 -> 쪽지1
    103: 2,   # 낡은 캐비닛 -> 은열쇠 (잠금)
    104: None,  # 벽난로 -> 숫자 힌트 (아이템 없음)
    105: 5,   # 소파 쿠션 -> 쪽지2
    106: None,  # 냉장고 -> 숫자 힌트 (아이템 없음)
    107: 10,  # 찬장 -> 황금열쇠 머리 (잠금) - 기존 금고 메모 대신
    108: 7,   # 침대 밑 -> 일기장
    109: 9,   # 화장대 서랍 -> 서재 메모 (비밀번호 잠금)
    110: None,  # 그림 액자 -> 숫자 힌트 (아이템 없음)
    111: 11,  # 금고 -> 황금열쇠 몸통 (비밀번호 잠금) - 기존 황금열쇠 대신
    112: 6,   # 책상 서랍 -> 쪽지3
}

# 오브젝트별 잠금 정보 (object_id -> {type, key/password, message})
LOCK_INFO = {
    103: {"type": "key", "key_item": 1, "key_tag": "녹슨열쇠", "locked_msg": "자물쇠가 잠겨 있다. 녹슨 열쇠가 필요해 보인다."},
    107: {"type": "key", "key_item": 2, "key_tag": "은열쇠", "locked_msg": "자물쇠가 잠겨 있다. 은색 열쇠가 필요해 보인다."},
    109: {"type": "password", "password": "3749", "locked_msg": "4자리 비밀번호가 필요하다."},
    111: {"type": "password", "password": "1842", "locked_msg": "4자리 비밀번호가 필요하다."},
}

# 오브젝트별 조사 메시지
EXAMINE_MESSAGES = {
    100: "낡은 나무 상자를 열어보니 녹슨 열쇠가 있다!",
    102: "선반을 살펴보니 먼지 사이에 쪽지가 끼어 있다.",
    104: "벽난로 안쪽을 살펴보니... 재 속에 '3'이라는 숫자가 새겨져 있다.",
    105: "소파 쿠션 밑을 뒤져보니 쪽지가 나왔다.",
    106: "냉장고 문에 '7'이라는 숫자 자석이 붙어 있다.",
    108: "침대 밑에 손을 넣어보니... 오래된 일기장이 있다!",
    110: "그림 뒤쪽을 살펴보니 '4'와 '9'라는 숫자가 적혀 있다.",
    112: "책상 서랍을 열어보니 쪽지가 있다.",
}

# 아이템별 읽기 내용
ITEM_CONTENTS = {
    4: "\"빛이 없으면 길도 없다\"\n\n\"첫 번째는 불꽃 속에,\n두 번째는 차가운 곳에,\n세 번째와 네 번째는 벽에 걸린 눈 속에.\"",
    5: "\"화장대 서랍을 열고 싶다면\n숫자를 찾아라.\n\n불꽃이 처음이요,\n냉기가 다음이요,\n그림이 마지막이니라.\"",
    6: "\"연도를 기억하라 - 1842\"",
    7: "저택 주인의 일기장이다.\n\n\"1842년 10월 31일.\n이 저택에 무언가가 있다.\n정문의 열쇠를 금고에 숨겼다.\n금고 비밀번호는 저택이 지어진 해...\"",
    8: "\"금고 번호는 저택이 지어진 해\"",
    9: "\"서재 문 비밀번호: 2847\"",
}

# ============================================================
# 오브젝트 상호작용 함수
# ============================================================

def examine_object(context_unit_id):
    """오브젝트 조사 (숨겨진 아이템 획득)"""
    object_id = context_unit_id
    player_id = morld.get_player_id()

    # 이미 조사했는지 확인
    flag_name = f"examined_{object_id}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    # 조사 완료 표시
    morld.set_flag(flag_name, 1)

    # 메시지 가져오기
    message = EXAMINE_MESSAGES.get(object_id, "특별한 것은 없다.")

    # 숨겨진 아이템이 있으면 지급
    hidden_item = HIDDEN_ITEMS.get(object_id)
    if hidden_item is not None:
        morld.give_item(player_id, hidden_item, 1)

    return {
        "type": "monologue",
        "pages": [message],
        "time_consumed": 1
    }

def toggle_switch(context_unit_id):
    """배전함 스위치 조작"""
    player_id = morld.get_player_id()

    # 현재 스위치 상태 확인
    current = morld.get_flag("power")

    if current > 0:
        morld.clear_flag("power")
        return {
            "type": "monologue",
            "pages": ["스위치를 내렸다.", "주변이 다시 어두워졌다."],
            "time_consumed": 1
        }
    else:
        morld.set_flag("power", 1)
        # 액션 로그에 문 열림 소리 추가
        morld.add_action_log("문이 열리는 소리가 들렸다")
        return {
            "type": "monologue",
            "pages": [
                "스위치를 올렸다.",
                "철컥- 하는 소리와 함께 희미한 불빛이 들어온다.",
                "어디선가 문이 열리는 소리가 들린다..."
            ],
            "time_consumed": 1
        }

def unlock_object(context_unit_id):
    """잠긴 오브젝트 열기 (열쇠 필요)"""
    object_id = context_unit_id
    player_id = morld.get_player_id()

    # 잠금 정보 확인
    lock = LOCK_INFO.get(object_id)
    if not lock:
        return examine_object(context_unit_id)

    # 이미 열렸는지 확인
    flag_name = f"unlocked_{object_id}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 열려 있다. 안은 비어 있다."],
            "time_consumed": 0
        }

    # 열쇠 타입인 경우
    if lock["type"] == "key":
        # 열쇠 보유 확인
        if not morld.has_item(player_id, lock["key_item"]):
            return {
                "type": "monologue",
                "pages": [lock["locked_msg"]],
                "time_consumed": 0
            }

        # 열쇠 소모 (액션 로그 자동 생성)
        morld.lost_item(player_id, lock["key_item"], 1)

        # 잠금 해제
        morld.set_flag(flag_name, 1)
        morld.add_action_log("자물쇠를 열었다")

        # 숨겨진 아이템 지급
        hidden_item = HIDDEN_ITEMS.get(object_id)
        if hidden_item is not None:
            morld.give_item(player_id, hidden_item, 1)
            # 오브젝트별 특수 메시지
            if object_id == 107:  # 찬장 -> 황금열쇠 머리
                return {
                    "type": "monologue",
                    "pages": [
                        "열쇠로 자물쇠를 열었다.",
                        "안쪽 깊숙한 곳에서 황금빛 열쇠의 머리 부분을 발견했다!",
                        "몸통 부분을 찾아서 조합해야 할 것 같다..."
                    ],
                    "time_consumed": 1
                }
            elif object_id == 103:  # 낡은 캐비닛 -> 은열쇠
                return {
                    "type": "monologue",
                    "pages": [
                        "열쇠로 자물쇠를 열었다.",
                        "안에서 은빛으로 빛나는 열쇠를 발견했다!"
                    ],
                    "time_consumed": 1
                }
            else:
                return {
                    "type": "monologue",
                    "pages": [
                        "열쇠로 자물쇠를 열었다.",
                        "안에서 무언가를 발견했다!"
                    ],
                    "time_consumed": 1
                }
        else:
            return {
                "type": "monologue",
                "pages": ["열쇠로 자물쇠를 열었다. 안은 비어 있다."],
                "time_consumed": 1
            }

    # 비밀번호 타입인 경우 -> 비밀번호 입력 UI로
    return password_lock(context_unit_id)

def password_lock(context_unit_id):
    """비밀번호 잠금 오브젝트"""
    object_id = context_unit_id

    # 이미 열렸는지 확인
    flag_name = f"unlocked_{object_id}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 열려 있다. 안은 비어 있다."],
            "time_consumed": 0
        }

    lock = LOCK_INFO.get(object_id)
    if not lock or lock["type"] != "password":
        return {
            "type": "monologue",
            "pages": ["잠겨 있지 않다."],
            "time_consumed": 0
        }

    # 비밀번호 입력 초기화
    morld.set_flag("password_target", object_id)
    morld.set_flag("password_input", 0)
    morld.set_flag("password_digits", 0)

    # 비밀번호 입력 UI 표시
    return {
        "type": "monologue",
        "pages": [
            "4자리 비밀번호를 입력하세요:\n\n[    ]\n\n" +
            "[url=script:input_digit:1][ 1 ][/url] [url=script:input_digit:2][ 2 ][/url] [url=script:input_digit:3][ 3 ][/url]\n" +
            "[url=script:input_digit:4][ 4 ][/url] [url=script:input_digit:5][ 5 ][/url] [url=script:input_digit:6][ 6 ][/url]\n" +
            "[url=script:input_digit:7][ 7 ][/url] [url=script:input_digit:8][ 8 ][/url] [url=script:input_digit:9][ 9 ][/url]\n" +
            "        [url=script:input_digit:0][ 0 ][/url]\n\n" +
            "[url=script:cancel_password][ 취소 ][/url]"
        ],
        "time_consumed": 0,
        "button_type": "none"
    }

def input_digit(context_unit_id, digit):
    """비밀번호 숫자 입력"""
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

    # 현재 입력 상태 표시 (update: Push 없이 현재 모놀로그 내용만 교체)
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
    """비밀번호 검증"""
    object_id = morld.get_flag("password_target")
    input_password = str(morld.get_flag("password_input")).zfill(4)
    player_id = morld.get_player_id()

    lock = LOCK_INFO.get(object_id)
    if not lock:
        return {"type": "monologue", "pages": ["오류가 발생했다."], "time_consumed": 0}

    correct_password = lock["password"]

    if input_password == correct_password:
        # 잠금 해제 성공
        flag_name = f"unlocked_{object_id}"
        morld.set_flag(flag_name, 1)

        # 서재 문 특수 처리
        if object_id == 109:
            morld.add_action_log("서랍을 열었다")
            # 화장대 서랍 -> 서재 메모 획득만
            hidden_item = HIDDEN_ITEMS.get(object_id)
            if hidden_item:
                morld.give_item(player_id, hidden_item, 1)
            return {
                "type": "monologue",
                "pages": [
                    "딸깍!",
                    "비밀번호가 맞았다. 서랍이 열렸다!",
                    "안에서 메모를 발견했다."
                ],
                "time_consumed": 1
            }
        elif object_id == 111:
            morld.add_action_log("금고를 열었다")
            # 금고 -> 황금열쇠 몸통 획득
            hidden_item = HIDDEN_ITEMS.get(object_id)
            if hidden_item:
                morld.give_item(player_id, hidden_item, 1)
            return {
                "type": "monologue",
                "pages": [
                    "딸깍!",
                    "비밀번호가 맞았다. 금고가 열렸다!",
                    "안에서 황금빛 열쇠의 몸통 부분을 발견했다!",
                    "머리 부분을 찾아서 조합해야 할 것 같다..."
                ],
                "time_consumed": 1
            }
        else:
            return {
                "type": "monologue",
                "pages": ["딸깍! 비밀번호가 맞았다!"],
                "time_consumed": 1
            }
    else:
        # 실패
        return {
            "type": "monologue",
            "pages": ["삐빅- 비밀번호가 틀렸다."],
            "time_consumed": 0
        }

def cancel_password(context_unit_id):
    """비밀번호 입력 취소"""
    morld.clear_flag("password_target")
    morld.clear_flag("password_input")
    morld.clear_flag("password_digits")
    return {
        "type": "monologue",
        "pages": ["입력을 취소했다."],
        "time_consumed": 0
    }

def unlock_study_door(context_unit_id):
    """서재 문 비밀번호 입력 (복도 2층에서 사용)"""
    # 이미 열렸는지 확인
    if morld.get_flag("study_unlocked") > 0:
        return {
            "type": "monologue",
            "pages": ["서재 문은 이미 열려 있다."],
            "time_consumed": 0
        }

    # 비밀번호 입력 UI
    morld.set_flag("password_target", -1)  # 특수: 서재 문
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

    # update: Push 없이 현재 모놀로그 내용만 교체
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

    if input_password == "2847":
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

def escape(context_unit_id):
    """정문으로 탈출"""
    player_id = morld.get_player_id()

    # 황금열쇠 확인
    if not morld.has_item(player_id, 3):
        return {
            "type": "monologue",
            "pages": [
                "정문이 굳게 잠겨 있다.",
                "황금빛 자물쇠가 달려 있다. 특별한 열쇠가 필요해 보인다."
            ],
            "time_consumed": 0
        }

    # 황금열쇠 소모 (액션 로그 자동 생성)
    morld.lost_item(player_id, 3, 1)
    morld.add_action_log("정문이 열렸다")

    # 탈출 성공! - 스토리 페이지 후 엔딩 화면으로 전환
    return {
        "type": "monologue",
        "pages": [
            "황금열쇠를 자물쇠에 꽂았다.",
            "철커덕-!",
            "마침내... 문이 열렸다!",
            "차가운 바깥 공기가 느껴진다."
        ],
        "time_consumed": 0,
        "button_type": "ok",
        "done_callback": "show_ending"
    }

def show_ending(context_unit_id):
    """엔딩 화면 표시 (버튼 없음)"""
    return {
        "type": "monologue",
        "pages": [
            "자유다. 드디어 이 저택에서 벗어났다.\n\n━━━━━━━━━━━━━━━━━━━━\n\n[b]탈출 성공![/b]\n\n플레이해주셔서 감사합니다."
        ],
        "time_consumed": 0,
        "button_type": "none"
    }

def read_note(context_unit_id, item_id=None):
    """아이템 읽기 (쪽지, 메모 등)"""
    # context_unit_id는 무시하고 item_id 사용
    if item_id is None:
        return {"type": "monologue", "pages": ["읽을 수 없다."], "time_consumed": 0}

    item_id = int(item_id)
    content = ITEM_CONTENTS.get(item_id, "내용이 없다.")

    return {
        "type": "monologue",
        "pages": [content],
        "time_consumed": 0
    }

def read_diary(context_unit_id):
    """일기장 읽기"""
    return read_note(context_unit_id, 7)

# ============================================================
# 추가 오브젝트 상호작용 (플레이버 텍스트)
# ============================================================

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

def examine_step(context_unit_id):
    """부서진 계단 조사"""
    return {
        "type": "monologue",
        "pages": [
            "부서진 계단 틈새를 들여다본다.",
            "먼지와 거미줄... 그리고 낡은 못 하나.",
            "별다른 것은 없다."
        ],
        "time_consumed": 1
    }

def examine_window(context_unit_id):
    """계단 창문 조사"""
    flag_name = "examined_window"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["창문은 여전히 굳게 잠겨있다. 밖은 어둡다."],
            "time_consumed": 0
        }

    morld.set_flag(flag_name, 1)
    return {
        "type": "monologue",
        "pages": [
            "두꺼운 커튼을 걷어본다.",
            "창문 밖은 칠흑같이 어둡다. 달빛조차 보이지 않는다.",
            "창문은 굳게 잠겨있고, 쇠창살이 설치되어 있다.",
            "...이쪽으로는 나갈 수 없다."
        ],
        "time_consumed": 1
    }

# ============================================================
# 조합 시스템
# ============================================================

def combine_key(context_unit_id, item_id=None):
    """황금열쇠 파츠 조합"""
    player_id = morld.get_player_id()

    # 두 파츠를 모두 가지고 있는지 확인
    has_head = morld.has_item(player_id, 10)  # 황금열쇠 머리
    has_body = morld.has_item(player_id, 11)  # 황금열쇠 몸통

    if not has_head or not has_body:
        # 한쪽 파츠만 있는 경우
        if has_head:
            return {
                "type": "monologue",
                "pages": [
                    "황금열쇠의 머리 부분이다.",
                    "몸통 부분이 없으면 조합할 수 없다."
                ],
                "time_consumed": 0
            }
        elif has_body:
            return {
                "type": "monologue",
                "pages": [
                    "황금열쇠의 몸통 부분이다.",
                    "머리 부분이 없으면 조합할 수 없다."
                ],
                "time_consumed": 0
            }
        else:
            return {
                "type": "monologue",
                "pages": ["조합할 재료가 없다."],
                "time_consumed": 0
            }

    # 두 파츠 모두 있음 -> 조합 진행 (액션 로그 자동 생성)
    morld.lost_item(player_id, 10, 1)  # 머리 제거
    morld.lost_item(player_id, 11, 1)  # 몸통 제거
    morld.give_item(player_id, 3, 1)   # 황금열쇠 지급
    morld.add_action_log("황금열쇠를 완성했다")

    return {
        "type": "monologue",
        "pages": [
            "두 파츠를 맞춰본다...",
            "철컥!",
            "완벽하게 들어맞았다!",
            "황금열쇠가 완성되었다!",
            "이제 정문을 열 수 있을 것 같다!"
        ],
        "time_consumed": 1
    }

# ============================================================
# 모놀로그 헬퍼 (레거시 호환)
# ============================================================

def get_monologue_page_count(monologue_id):
    """모놀로그 페이지 수 반환 (레거시)"""
    return 0
