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
        from events.scripts.player_creation import (
            run_character_creation, apply_character_creation
        )

        # 챕터 0: 프롤로그 (숲 방황)
        morld.set_prop("chapter", 0)

        # 도입 모놀로그
        yield morld.dialog([
            "......",
            "......의식이 희미하게 떠오른다.",
            "머리가... 아프다.",
            "여기는... 어디지?",
            "기억이... 나지 않는다.",
            "눈앞에 울창한 나무들이 보인다.\n숲 속인 것 같다.",
            "...일단 나 자신에 대해 생각해보자."
        ])

        # 캐릭터 생성 (이름 → 나이 → 체격 → 장비 → 확인)
        # yield from으로 sub-generator의 모든 yield를 전달
        state = yield from run_character_creation()

        # 캐릭터 생성 결과 적용 (이름, prop, 아이템 지급)
        apply_character_creation(state)

        # 완료 메시지
        yield morld.dialog([
            f"그래... 나는 {state['name']}.",
            "기억은 아직 희미하지만...\n적어도 나 자신이 누구인지는 알겠다.",
            "...여기가 어디지? 깊은 숲 속인 것 같다.",
            "일단 움직여서 사람이 있는 곳을 찾아야겠다."
        ])


# ========================================
# Dialog API 시범 - morld.dialog() 테스트
# ========================================

# 1. 레거시 방식 (@ret: 패턴 + while 루프)
@morld.register_script
def intro_with_dialog_legacy(context_unit_id):
    """
    Dialog API 시범 - 레거시 방식 (while 루프)

    사용법: script:intro_with_dialog_legacy

    @ret:값 - 다이얼로그 종료, yield에 값 반환
    """
    # 단순 Yes/No 다이얼로그
    result = yield morld.dialog(
        "[b]Morld - Dialog API 시범 (레거시)[/b]\n\n"
        "게임을 시작하시겠습니까?\n\n"
        "[url=@ret:yes]예[/url]  [url=@ret:no]아니오[/url]",
        autofill="off"
    )

    if result == "yes":
        morld.add_action_log("[시스템] 게임 시작!")
        return {"type": "message", "message": "게임 시작!"}
    else:
        return {"type": "message", "message": "취소되었습니다."}


# 2. 새 API - proc 콜백 방식 (@finish + result)
@morld.register_script
def stat_allocation_new(context_unit_id):
    """
    Dialog API 시범 - 새 통합 API (proc 콜백 + result)

    사용법: script:stat_allocation_new

    yield morld.dialog(text, autofill="off", proc=callback, result=state)
    - proc 콜백: @proc:값 클릭 시 호출되어 새 텍스트 반환
    - result: @finish 클릭 시 반환될 객체
    - @proc_finish:값 - proc 콜백 호출 후 즉시 종료
    """
    state = {"str": 5, "agi": 5, "points": 10}

    def build_stat_text():
        """현재 상태로 다이얼로그 텍스트 생성"""
        return (
            f"[b]스탯 배분 (proc + result)[/b]\n\n"
            f"힘: {state['str']}  [url=@proc:str+]+[/url] [url=@proc:str-]-[/url]\n"
            f"민첩: {state['agi']}  [url=@proc:agi+]+[/url] [url=@proc:agi-]-[/url]\n\n"
            f"남은 포인트: {state['points']}\n\n"
            f"[url=@finish]확인[/url]  [url=@ret:cancel]취소[/url]"
        )

    def handle_stat_action(action):
        """@proc:값 클릭 시 호출되는 콜백"""
        if action == "str+" and state["points"] > 0:
            state["str"] += 1
            state["points"] -= 1
        elif action == "str-" and state["str"] > 1:
            state["str"] -= 1
            state["points"] += 1
        elif action == "agi+" and state["points"] > 0:
            state["agi"] += 1
            state["points"] -= 1
        elif action == "agi-" and state["agi"] > 1:
            state["agi"] -= 1
            state["points"] += 1
        else:
            return None  # 변경 없음

        return build_stat_text()  # 새 텍스트로 화면 업데이트

    # 통합 API로 스탯 배분 UI 표시
    result = yield morld.dialog(
        build_stat_text(),
        autofill="off",
        proc=handle_stat_action,
        result=state  # @finish 시 이 객체가 반환됨
    )

    # result가 dict면 @finish로 종료됨 (state 반환)
    # result가 문자열이면 @ret:값으로 종료됨
    if isinstance(result, dict):
        morld.add_action_log(f"[시스템] 스탯 배분 완료: 힘={result['str']}, 민첩={result['agi']}")
        return {
            "type": "message",
            "message": f"스탯이 설정되었습니다!\n힘: {result['str']}, 민첩: {result['agi']}"
        }
    else:  # cancel
        morld.add_action_log("[시스템] 스탯 배분이 취소되었습니다.")
        return {"type": "message", "message": "스탯 배분이 취소되었습니다."}


# 3. 새 API - 선택 후 즉시 종료 (@proc + return True)
@morld.register_script
def destination_choice(context_unit_id):
    """
    Dialog API 시범 - @proc + return True 패턴

    사용법: script:destination_choice

    @proc:값 클릭 시 proc 콜백 호출
    - return True: 다이얼로그 종료, result 반환
    - return 문자열: 텍스트 업데이트, 다이얼로그 유지
    - return None/False: 변경 없음, 다이얼로그 유지
    """
    state = {"choice": None}

    def handle_choice(action):
        state["choice"] = action
        return True  # 다이얼로그 종료

    result = yield morld.dialog(
        "[b]어디로 갈까?[/b]\n\n"
        "[url=@proc:town]마을[/url]\n"
        "[url=@proc:forest]숲[/url]\n"
        "[url=@proc:cave]동굴[/url]",
        autofill="off",
        proc=handle_choice,
        result=state
    )

    # result는 state dict, state["choice"]에 선택값이 저장됨
    choice = result["choice"] if isinstance(result, dict) else "unknown"
    morld.add_action_log(f"[시스템] 선택: {choice}")
    return {"type": "message", "message": f"{choice}(으)로 이동합니다."}


# 4. book 모드 - 이전/다음 왕복
@morld.register_script
def read_diary(context_unit_id):
    """
    Dialog API 시범 - book 모드 (이전/다음 왕복)

    사용법: script:read_diary
    """
    yield morld.dialog([
        "[b]일기장 - 1페이지[/b]\n\n오늘 숲에서 이상한 소리를 들었다.",
        "[b]일기장 - 2페이지[/b]\n\n그 소리는 동쪽에서 들려왔다.",
        "[b]일기장 - 3페이지[/b]\n\n내일 가서 확인해봐야겠다."
    ], autofill="book")

    return {"type": "message", "message": "일기장을 덮었다."}


# 5. scroll 모드 - 텍스트 누적
@morld.register_script
def memory_flashback(context_unit_id):
    """
    Dialog API 시범 - scroll 모드 (텍스트 누적)

    사용법: script:memory_flashback
    """
    yield morld.dialog([
        "...기억이 떠오른다...",
        "어릴 적, 마을 광장에서...",
        "누군가가 내 손을 잡았다...",
        "\"잊지 마. 넌 특별해.\""
    ], autofill="scroll")

    return {"type": "message", "message": "기억이 스쳐 지나갔다."}
