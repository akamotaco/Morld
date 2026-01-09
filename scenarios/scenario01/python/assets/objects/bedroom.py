# assets/objects/bedroom.py - 침실 오브젝트 (침대 밑, 화장대 서랍)

import morld
from assets.base import Object
from assets.items.golden_key import get_item_instance


class BedUnder(Object):
    """침대 밑"""
    unique_id = "bed_under"
    name = "침대 밑"
    actions = ["call:examine:조사"]
    focus_text = {
        "default": "헤진 시트가 덮인 낡은 침대다. 침대 밑 어둠 속에 무언가가 있는 것 같다. 손을 넣어봐야 할 것 같다."
    }
    hidden_items = ["diary", "old_letter"]
    examine_message = "침대 밑에 손을 넣어보니... 오래된 일기장과 봉투에 담긴 편지가 있다!"

    def examine(self):
        """침대 밑 조사 - Generator 기반 인스턴스 메서드"""
        player_id = morld.get_player_id()

        flag_name = f"flag:examined_{self.unique_id}"
        if morld.get_prop(flag_name) > 0:
            yield morld.dialog(["이미 조사한 곳이다. 더 이상 볼 것이 없다."])
            return

        morld.set_prop(flag_name, 1)

        # 다중 아이템 지급
        for item_uid in self.hidden_items:
            item = get_item_instance(item_uid)
            if item:
                morld.give_item(player_id, item.instance_id, 1)

        yield morld.dialog([self.examine_message])


class VanityDrawer(Object):
    """화장대 서랍"""
    unique_id = "vanity_drawer"
    name = "화장대 서랍"
    actions = ["call:open:열기"]
    focus_text = {
        "default": "화장대에 달린 작은 서랍이다. 4자리 숫자 잠금장치가 달려있다. 누군가 소중한 것을 숨겨둔 것 같다.",
        "unlocked": "열린 서랍이다. 화장품과 먼지만 남아있다."
    }
    password = "3749"
    hidden_item = "study_memo"

    def open(self):
        """화장대 서랍 열기 - 비밀번호 잠금 - Generator 기반 인스턴스 메서드"""
        flag_name = f"flag:unlocked_{self.unique_id}"
        if morld.get_prop(flag_name) > 0:
            yield morld.dialog(["이미 열려 있다. 안은 비어 있다."])
            return

        # @proc: 패턴 기반 비밀번호 입력
        from scripts import _build_password_ui, _create_password_proc

        state = {
            "input": 0,
            "digits": 0,
            "cancelled": False,
            "target_uid": 0  # vanity_drawer marker
        }

        result = yield morld.dialog(
            "",
            autofill="off",
            proc=_create_password_proc(state),
            result=state
        )

        if result.get("cancelled"):
            yield morld.dialog(["입력을 취소했다."])
            return

        # 비밀번호 검증
        input_password = str(result["input"]).zfill(4)
        if input_password == self.password:
            yield from on_password_success()
        else:
            yield morld.dialog(["삐빅- 비밀번호가 틀렸다."])


def on_password_success():
    """비밀번호 성공 시 호출 (scripts.py에서 호출) - Generator 기반"""
    player_id = morld.get_player_id()

    morld.set_prop(f"flag:unlocked_{VanityDrawer.unique_id}", 1)
    morld.add_action_log("서랍을 열었다")

    item = get_item_instance(VanityDrawer.hidden_item)
    if item:
        morld.give_item(player_id, item.instance_id, 1)

    yield morld.dialog([
        "딸깍!",
        "비밀번호가 맞았다. 서랍이 열렸다!",
        "안에서 메모를 발견했다."
    ])
