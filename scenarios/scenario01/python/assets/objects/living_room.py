# assets/objects/living_room.py - 거실 오브젝트 (벽난로, 소파 쿠션)

import morld
from assets import registry

# ========================================
# Asset 정의
# ========================================

FIREPLACE = {
    "unique_id": "fireplace",
    "name": "벽난로",
    "actions": ["script:examine_fireplace:조사"],
    "focus_text": {
        "default": "대리석 장식이 달린 오래된 벽난로다. 불을 피운 지 오래됐는지 재와 타다 남은 장작이 가득하다. 안쪽을 자세히 살펴보면 뭔가 있을지도..."
    },
    # 힌트만 제공 (숫자 3)
    "examine_message": "벽난로 안쪽을 살펴보니... 재 속에 '3'이라는 숫자가 새겨져 있다."
}

SOFA_CUSHION = {
    "unique_id": "sofa_cushion",
    "name": "소파 쿠션",
    "actions": ["script:examine_sofa:조사"],
    "focus_text": {
        "default": "한때 고급스러웠을 붉은 벨벳 소파다. 쿠션 사이가 벌어져 있어 무언가가 끼어있을 것 같다."
    },
    "hidden_item": "note2",
    "examine_message": "소파 쿠션 밑을 뒤져보니 쪽지가 나왔다."
}


# ========================================
# 스크립트 함수
# ========================================

def examine_fireplace(context_unit_id):
    """벽난로 조사 - 숫자 힌트"""
    uid = FIREPLACE["unique_id"]

    flag_name = f"examined_{uid}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    morld.set_flag(flag_name, 1)

    return {
        "type": "monologue",
        "pages": [FIREPLACE["examine_message"]],
        "time_consumed": 1
    }


def examine_sofa(context_unit_id):
    """소파 쿠션 조사"""
    player_id = morld.get_player_id()
    uid = SOFA_CUSHION["unique_id"]

    flag_name = f"examined_{uid}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    morld.set_flag(flag_name, 1)

    item_iid = registry.get_instance_id(SOFA_CUSHION["hidden_item"])
    if item_iid is not None:
        morld.give_item(player_id, item_iid, 1)

    return {
        "type": "monologue",
        "pages": [SOFA_CUSHION["examine_message"]],
        "time_consumed": 1
    }


def register():
    """거실 오브젝트 Asset 등록"""
    registry.register_object(FIREPLACE)
    registry.register_object(SOFA_CUSHION)
