# assets/objects/study.py - 서재 오브젝트 (금고, 책상 서랍)

import morld
from assets.base import Object
from assets.items.golden_key import get_item_instance


class Safe(Object):
    """금고"""
    unique_id = "safe"
    name = "금고"
    actions = ["call:open:열기"]
    focus_text = {
        "default": "책상 옆에 놓인 묵직한 철제 금고다. 4자리 다이얼 자물쇠가 달려있다. 안에 중요한 것이 들어있을 것 같다.",
        "unlocked": "열린 금고다. 먼지와 오래된 서류 조각들만 남아있다."
    }
    password = "1842"
    hidden_item = "golden_key_body"

    def open(self):
        """금고 열기 - 비밀번호 잠금 - Generator 기반 인스턴스 메서드"""
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
            "target_uid": 1  # safe marker
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

    morld.set_prop(f"flag:unlocked_{Safe.unique_id}", 1)
    morld.add_action_log("금고를 열었다")

    item = get_item_instance(Safe.hidden_item)
    if item:
        morld.give_item(player_id, item.instance_id, 1)

    yield morld.dialog([
        "딸깍!",
        "비밀번호가 맞았다. 금고가 열렸다!",
        "안에서 황금빛 열쇠의 몸통 부분을 발견했다!",
        "머리 부분을 찾아서 조합해야 할 것 같다..."
    ])


class DeskDrawer(Object):
    """책상 서랍"""
    unique_id = "desk_drawer"
    name = "책상 서랍"
    actions = ["call:examine:조사"]
    focus_text = {
        "default": "낡은 오크나무 책상의 서랍이다. 손잡이가 녹슬었지만 열 수 있을 것 같다."
    }
    hidden_item = "note3"
    examine_message = "책상 서랍을 열어보니 쪽지가 있다."

    def examine(self):
        """책상 서랍 조사 - Generator 기반 인스턴스 메서드"""
        player_id = morld.get_player_id()

        flag_name = f"flag:examined_{self.unique_id}"
        if morld.get_prop(flag_name) > 0:
            yield morld.dialog(["이미 조사한 곳이다. 더 이상 볼 것이 없다."])
            return

        morld.set_prop(flag_name, 1)

        item = get_item_instance(self.hidden_item)
        if item:
            morld.give_item(player_id, item.instance_id, 1)

        yield morld.dialog([self.examine_message])
