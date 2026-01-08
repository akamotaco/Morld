# events/game_start/prologue.py - 프롤로그 시작 이벤트
#
# 게임 시작 시 캐릭터 생성 흐름

import morld
from events.base import GameStartEvent
from events import registry


@registry.register
class PrologueStart(GameStartEvent):
    """게임 시작 - 캐릭터 생성"""
    once = True

    def handle(self, **ctx):
        from assets.characters.player import NAME_OPTIONS

        # 챕터 0: 프롤로그 (숲 방황)
        morld.set_prop("chapter", 0)

        yield morld.dialog("......")
        yield morld.dialog("......의식이 희미하게 떠오른다.")
        yield morld.dialog("머리가... 아프다.")
        yield morld.dialog("여기는... 어디지?")
        yield morld.dialog("기억이... 나지 않는다.")
        yield morld.dialog("눈앞에 울창한 나무들이 보인다.\n숲 속인 것 같다.")
        yield morld.dialog("...일단 나 자신에 대해 생각해보자.")

        # 이름 선택 페이지 (button_type: none - 링크로만 진행)
        name_options = "\n".join([
            f"[url=script:set_name:{name}]{name}[/url]"
            for name in NAME_OPTIONS
        ])
        yield morld.dialog(f"내 이름은...?\n\n{name_options}")


# ========================================
# Dialog API 시범 - morld.dialog() 테스트
# ========================================
@morld.register_script
def intro_with_dialog(context_unit_id):
    """
    Dialog API 시범 함수

    사용법: script:intro_with_dialog

    yield morld.dialog()를 사용하여 BBCode 기반 다이얼로그 표시
    @ret:값 - 다이얼로그 종료, yield에 값 반환
    @proc:값 - generator에 값 전달, 다이얼로그 유지
    """
    # 1. 단순 Yes/No 다이얼로그
    result = yield morld.dialog(
        "[b]Morld - Dialog API 시범[/b]\n\n"
        "게임을 시작하시겠습니까?\n\n"
        "[url=@ret:yes]예[/url]  [url=@ret:no]아니오[/url]"
    )

    if result == "yes":
        # 2. 스탯 배분 다이얼로그 (@proc: 사용)
        state = {"str": 5, "agi": 5, "points": 10}

        while True:
            result = yield morld.dialog(
                f"[b]스탯 배분[/b]\n\n"
                f"힘: {state['str']}  [url=@proc:str+]+[/url] [url=@proc:str-]−[/url]\n"
                f"민첩: {state['agi']}  [url=@proc:agi+]+[/url] [url=@proc:agi-]−[/url]\n\n"
                f"남은 포인트: {state['points']}\n\n"
                f"[url=@ret:confirm]확인[/url]  [url=@ret:cancel]취소[/url]"
            )

            if result == "confirm":
                morld.add_action_log(f"[시스템] 스탯 배분 완료: 힘={state['str']}, 민첩={state['agi']}")
                return {
                    "type": "message",
                    "message": f"스탯이 설정되었습니다!\n힘: {state['str']}, 민첩: {state['agi']}"
                }
            elif result == "cancel":
                morld.add_action_log("[시스템] 스탯 배분이 취소되었습니다.")
                return {
                    "type": "message",
                    "message": "스탯 배분이 취소되었습니다."
                }
            elif result == "str+" and state["points"] > 0:
                state["str"] += 1
                state["points"] -= 1
            elif result == "str-" and state["str"] > 1:
                state["str"] -= 1
                state["points"] += 1
            elif result == "agi+" and state["points"] > 0:
                state["agi"] += 1
                state["points"] -= 1
            elif result == "agi-" and state["agi"] > 1:
                state["agi"] -= 1
                state["points"] += 1
    else:
        morld.add_action_log("[시스템] 게임 시작이 취소되었습니다.")
        return {
            "type": "message",
            "message": "게임 시작이 취소되었습니다."
        }


