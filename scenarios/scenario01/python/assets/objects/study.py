# assets/objects/study.py - 서재 오브젝트 (금고, 책상 서랍)

import morld
from assets.base import Object
from assets.items.golden_key import get_item_instance


class Safe(Object):
    """금고"""
    unique_id = "safe"
    name = "금고"
    actions = ["script:open_safe:열기"]
    focus_text = {
        "default": "책상 옆에 놓인 묵직한 철제 금고다. 4자리 다이얼 자물쇠가 달려있다. 안에 중요한 것이 들어있을 것 같다.",
        "unlocked": "열린 금고다. 먼지와 오래된 서류 조각들만 남아있다."
    }
    password = "1842"
    hidden_item = "golden_key_body"


class DeskDrawer(Object):
    """책상 서랍"""
    unique_id = "desk_drawer"
    name = "책상 서랍"
    actions = ["script:examine_desk:조사"]
    focus_text = {
        "default": "낡은 오크나무 책상의 서랍이다. 손잡이가 녹슬었지만 열 수 있을 것 같다."
    }
    hidden_item = "note3"
    examine_message = "책상 서랍을 열어보니 쪽지가 있다."


# ========================================
# 스크립트 함수
# ========================================

def open_safe(context_unit_id):
    """금고 열기 - 비밀번호 잠금"""
    flag_name = f"unlocked_{Safe.unique_id}"
    if morld.get_prop(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 열려 있다. 안은 비어 있다."],
            "time_consumed": 0
        }

    # 비밀번호 입력 UI
    morld.set_prop("password_target_uid", 1)  # safe marker
    morld.set_prop("password_input", 0)
    morld.set_prop("password_digits", 0)

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


def on_password_success():
    """비밀번호 성공 시 호출 (scripts.py에서 호출)"""
    player_id = morld.get_player_id()

    morld.set_prop(f"unlocked_{Safe.unique_id}", 1)
    morld.add_action_log("금고를 열었다")

    item = get_item_instance(Safe.hidden_item)
    if item:
        morld.give_item(player_id, item.instance_id, 1)

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


def examine_desk(context_unit_id):
    """책상 서랍 조사"""
    player_id = morld.get_player_id()

    flag_name = f"examined_{DeskDrawer.unique_id}"
    if morld.get_prop(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    morld.set_prop(flag_name, 1)

    item = get_item_instance(DeskDrawer.hidden_item)
    if item:
        morld.give_item(player_id, item.instance_id, 1)

    return {
        "type": "monologue",
        "pages": [DeskDrawer.examine_message],
        "time_consumed": 1
    }
