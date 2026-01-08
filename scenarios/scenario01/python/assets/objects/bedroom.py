# assets/objects/bedroom.py - 침실 오브젝트 (침대 밑, 화장대 서랍)

import morld
from assets.base import Object
from assets.items.golden_key import get_item_instance


class BedUnder(Object):
    """침대 밑"""
    unique_id = "bed_under"
    name = "침대 밑"
    actions = ["script:examine_bed:조사"]
    focus_text = {
        "default": "헤진 시트가 덮인 낡은 침대다. 침대 밑 어둠 속에 무언가가 있는 것 같다. 손을 넣어봐야 할 것 같다."
    }
    hidden_items = ["diary", "old_letter"]
    examine_message = "침대 밑에 손을 넣어보니... 오래된 일기장과 봉투에 담긴 편지가 있다!"


class VanityDrawer(Object):
    """화장대 서랍"""
    unique_id = "vanity_drawer"
    name = "화장대 서랍"
    actions = ["script:open_vanity_drawer:열기"]
    focus_text = {
        "default": "화장대에 달린 작은 서랍이다. 4자리 숫자 잠금장치가 달려있다. 누군가 소중한 것을 숨겨둔 것 같다.",
        "unlocked": "열린 서랍이다. 화장품과 먼지만 남아있다."
    }
    password = "3749"
    hidden_item = "study_memo"


# ========================================
# 스크립트 함수
# ========================================

def examine_bed(context_unit_id):
    """침대 밑 조사 - Generator 기반"""
    player_id = morld.get_player_id()

    flag_name = f"examined_{BedUnder.unique_id}"
    if morld.get_prop(flag_name) > 0:
        yield morld.dialog(["이미 조사한 곳이다. 더 이상 볼 것이 없다."])
        return

    morld.set_prop(flag_name, 1)

    # 다중 아이템 지급
    for item_uid in BedUnder.hidden_items:
        item = get_item_instance(item_uid)
        if item:
            morld.give_item(player_id, item.instance_id, 1)

    yield morld.dialog([BedUnder.examine_message])


def open_vanity_drawer(context_unit_id):
    """화장대 서랍 열기 - 비밀번호 잠금 - Generator 기반"""
    flag_name = f"unlocked_{VanityDrawer.unique_id}"
    if morld.get_prop(flag_name) > 0:
        yield morld.dialog(["이미 열려 있다. 안은 비어 있다."])
        return

    # 비밀번호 입력 UI
    morld.set_prop("password_target_uid", 0)  # vanity_drawer marker
    morld.set_prop("password_input", 0)
    morld.set_prop("password_digits", 0)

    yield morld.dialog(
        "4자리 비밀번호를 입력하세요:\n\n[    ]\n\n" +
        "[url=script:input_digit:1][ 1 ][/url] [url=script:input_digit:2][ 2 ][/url] [url=script:input_digit:3][ 3 ][/url]\n" +
        "[url=script:input_digit:4][ 4 ][/url] [url=script:input_digit:5][ 5 ][/url] [url=script:input_digit:6][ 6 ][/url]\n" +
        "[url=script:input_digit:7][ 7 ][/url] [url=script:input_digit:8][ 8 ][/url] [url=script:input_digit:9][ 9 ][/url]\n" +
        "        [url=script:input_digit:0][ 0 ][/url]\n\n" +
        "[url=script:cancel_password][ 취소 ][/url]",
        autofill="off"
    )


def on_password_success():
    """비밀번호 성공 시 호출 (scripts.py에서 호출) - Generator 기반"""
    player_id = morld.get_player_id()

    morld.set_prop(f"unlocked_{VanityDrawer.unique_id}", 1)
    morld.add_action_log("서랍을 열었다")

    item = get_item_instance(VanityDrawer.hidden_item)
    if item:
        morld.give_item(player_id, item.instance_id, 1)

    yield morld.dialog([
        "딸깍!",
        "비밀번호가 맞았다. 서랍이 열렸다!",
        "안에서 메모를 발견했다."
    ])
