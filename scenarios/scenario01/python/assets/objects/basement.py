# assets/objects/basement.py - 지하실 오브젝트 (낡은 상자, 배전함)

import morld
from assets import registry

# ========================================
# Asset 정의
# ========================================

OLD_BOX = {
    "unique_id": "old_box",
    "name": "낡은 상자",
    "actions": ["script:examine_old_box:조사"],
    "appearance": {
        "default": "구석에 먼지가 수북이 쌓인 낡은 나무 상자가 있다. 뚜껑이 살짝 들려 있어 안을 확인할 수 있을 것 같다."
    },
    # 숨겨진 아이템 정보
    "hidden_item": "rusty_key",
    "examine_message": "낡은 나무 상자를 열어보니 녹슨 열쇠가 있다!"
}

POWER_PANEL = {
    "unique_id": "power_panel",
    "name": "배전함",
    "actions": ["script:toggle_switch:조작"],
    "appearance": {
        "default": "벽에 녹슨 금속 배전함이 설치되어 있다. 커다란 레버 스위치가 내려가 있다. '주의: 고압 전류'라고 적힌 경고문이 희미하게 보인다."
    }
}


# ========================================
# 스크립트 함수
# ========================================

def examine_old_box(context_unit_id):
    """낡은 상자 조사"""
    player_id = morld.get_player_id()
    uid = OLD_BOX["unique_id"]

    # 이미 조사했는지 확인
    flag_name = f"examined_{uid}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    # 조사 완료 표시
    morld.set_flag(flag_name, 1)

    # 아이템 지급 (unique_id로 instance_id 조회)
    item_iid = registry.get_instance_id(OLD_BOX["hidden_item"])
    if item_iid is not None:
        morld.give_item(player_id, item_iid, 1)

    return {
        "type": "monologue",
        "pages": [OLD_BOX["examine_message"]],
        "time_consumed": 1
    }


def toggle_switch(context_unit_id):
    """배전함 스위치 조작"""
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


def register():
    """지하실 오브젝트 Asset 등록"""
    registry.register_object(OLD_BOX)
    registry.register_object(POWER_PANEL)
