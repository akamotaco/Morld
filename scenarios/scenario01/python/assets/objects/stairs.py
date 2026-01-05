# assets/objects/stairs.py - 계단 오브젝트 (부서진 계단, 창문)

import morld
from assets.base import Object


class BrokenStep(Object):
    """부서진 계단"""
    unique_id = "broken_step"
    name = "부서진 계단"
    actions = ["script:examine_step:조사"]
    focus_text = {
        "default": "계단 중간에 부서진 단이 있다. 틈새로 무언가가 보이는 것 같기도 하다..."
    }


class StairWindow(Object):
    """창문"""
    unique_id = "stair_window"
    name = "창문"
    actions = ["script:examine_window:조사"]
    focus_text = {
        "default": "계단 옆에 달린 창문이다. 두꺼운 커튼으로 가려져 있다. 밖으로 나갈 수 있을까?"
    }


# ========================================
# 스크립트 함수
# ========================================

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
    flag_name = f"examined_{StairWindow.unique_id}"

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
