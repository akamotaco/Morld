# assets/objects/corridor.py - 복도 오브젝트 (그림 액자, 괘종시계, 우산꽂이, 서재 문)

import morld
from assets.base import Object


class PictureFrame(Object):
    """그림 액자"""
    unique_id = "picture_frame"
    name = "그림 액자"
    actions = ["call:examine:조사"]
    focus_text = {
        "default": "벽에 비스듬히 걸린 오래된 풍경화다. 금박 액자 테두리가 벗겨져 있다. 그림 뒤에 뭔가 숨겨져 있을 것 같은 느낌이 든다."
    }
    examine_message = "그림 뒤쪽을 살펴보니 '4'와 '9'라는 숫자가 적혀 있다."

    def examine(self):
        """그림 액자 조사 - 숫자 힌트 - Generator 기반 인스턴스 메서드"""
        flag_name = f"flag:examined_{self.unique_id}"
        if morld.get_prop(flag_name) > 0:
            yield morld.dialog(["이미 조사한 곳이다. 더 이상 볼 것이 없다."])
            return

        morld.set_prop(flag_name, 1)

        yield morld.dialog([self.examine_message])


class GrandfatherClock(Object):
    """괘종시계"""
    unique_id = "grandfather_clock"
    name = "괘종시계"
    actions = ["call:examine:조사"]
    focus_text = {
        "default": "복도 끝에 서있는 커다란 괘종시계다. 시계는 멈춰있고, 시각은 18:42를 가리키고 있다. 문양이 새겨진 장식이 눈에 띈다."
    }

    def examine(self):
        """괘종시계 조사 - Generator 기반 인스턴스 메서드"""
        yield morld.dialog([
            "오래된 괘종시계다.",
            "시계는 18시 42분에 멈춰있다.",
            "태엽을 감아도 움직이지 않는다.",
            "시계 바닥에 '1842년 제작'이라고 새겨져 있다."
        ])


class UmbrellaStand(Object):
    """우산꽂이"""
    unique_id = "umbrella_stand"
    name = "우산꽂이"
    actions = ["call:examine:조사"]
    focus_text = {
        "default": "구리 재질의 우산꽂이다. 낡은 우산 몇 개와 지팡이가 꽂혀 있다. 바닥에 뭔가 떨어져 있는 것 같다."
    }

    def examine(self):
        """우산꽂이 조사 - Generator 기반 인스턴스 메서드"""
        yield morld.dialog([
            "우산꽂이를 뒤적여본다.",
            "낡은 우산들과 지팡이... 그리고 바닥에 동전 몇 개가 굴러다닌다.",
            "특별히 쓸모있어 보이는 건 없다."
        ])


class StudyDoor(Object):
    """서재 문"""
    unique_id = "study_door"
    name = "서재 문"
    actions = ["call:unlock:열기"]
    focus_text = {
        "default": "두꺼운 참나무 문이다. 전자식 4자리 비밀번호 잠금장치가 설치되어 있다.",
        "unlocked": "열린 서재 문이다. 안에서 오래된 책 냄새가 풍겨온다."
    }
    password = "2847"

    def unlock(self):
        """서재 문 비밀번호 입력 - Generator 기반 인스턴스 메서드"""
        if morld.get_prop("flag:study_unlocked") > 0:
            yield morld.dialog(["서재 문은 이미 열려 있다."])
            return

        # @proc: 패턴 기반 비밀번호 입력
        state = {
            "input": 0,
            "digits": 0,
            "cancelled": False
        }

        result = yield morld.dialog(
            "",
            autofill="off",
            proc=_create_study_password_proc(state),
            result=state
        )

        if result.get("cancelled"):
            yield morld.dialog(["입력을 취소했다."])
            return

        # 비밀번호 검증
        input_password = str(result["input"]).zfill(4)
        if input_password == self.password:
            morld.set_prop("flag:study_unlocked", 1)
            morld.add_action_log("서재 문이 열렸다")
            yield morld.dialog([
                "딸깍!",
                "비밀번호가 맞았다!",
                "서재 문이 열렸다. 이제 들어갈 수 있다."
            ])
        else:
            yield morld.dialog(["삐빅- 비밀번호가 틀렸다."])


# ========================================
# 비밀번호 입력 UI (@proc: 패턴 기반)
# ========================================

def _build_study_password_ui(current_input, current_digits):
    """서재 문 비밀번호 입력 UI 문자열 생성"""
    display = str(current_input).zfill(current_digits) if current_digits > 0 else ""
    display_padded = display + "_" * (4 - current_digits)

    return (
        f"서재 문 비밀번호:\n\n[{display_padded}]\n\n"
        "[url=@proc:1][ 1 ][/url] [url=@proc:2][ 2 ][/url] [url=@proc:3][ 3 ][/url]\n"
        "[url=@proc:4][ 4 ][/url] [url=@proc:5][ 5 ][/url] [url=@proc:6][ 6 ][/url]\n"
        "[url=@proc:7][ 7 ][/url] [url=@proc:8][ 8 ][/url] [url=@proc:9][ 9 ][/url]\n"
        "        [url=@proc:0][ 0 ][/url]\n\n"
        "[url=@proc:cancel][ 취소 ][/url]"
    )


def _create_study_password_proc(state):
    """서재 문 비밀번호 입력 proc 콜백 생성"""
    def proc(action):
        if action == "init":
            return _build_study_password_ui(state["input"], state["digits"])

        if action == "cancel":
            state["cancelled"] = True
            return True

        try:
            digit = int(action)
        except ValueError:
            return None

        state["input"] = state["input"] * 10 + digit
        state["digits"] += 1

        if state["digits"] >= 4:
            return True

        return _build_study_password_ui(state["input"], state["digits"])

    return proc


# 레거시 스크립트 함수 유지 (scripts.py에서 import됨 - 호환성)
@morld.register_script
def input_study_digit(context_unit_id, digit):
    """[레거시] 서재 문 비밀번호 숫자 입력"""
    pass  # @proc: 패턴으로 대체됨


@morld.register_script
def verify_study_password(context_unit_id):
    """[레거시] 서재 문 비밀번호 검증"""
    pass  # @proc: 패턴으로 대체됨
