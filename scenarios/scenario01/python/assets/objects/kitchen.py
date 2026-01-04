# assets/objects/kitchen.py - 주방 오브젝트 (냉장고, 찬장)

import morld
from assets import registry

# ========================================
# Asset 정의
# ========================================

REFRIGERATOR = {
    "unique_id": "refrigerator",
    "name": "냉장고",
    "actions": ["script:examine_refrigerator:조사"],
    "focus_text": {
        "default": "1950년대 스타일의 오래된 냉장고다. 녹이 슬어 문이 삐걱거린다. 문에 무언가 붙어있다."
    },
    # 힌트만 제공 (숫자 7)
    "examine_message": "냉장고 문에 '7'이라는 숫자 자석이 붙어 있다."
}

CUPBOARD = {
    "unique_id": "cupboard",
    "name": "찬장",
    "actions": ["script:unlock_cupboard:열기"],
    "focus_text": {
        "default": "주방 구석에 놓인 큼지막한 찬장이다. 은색 자물쇠로 잠겨있다. 유리창 너머로 안에 뭔가 반짝이는 게 보인다.",
        "unlocked": "열린 찬장이다. 먼지 쌓인 접시들만 남아있다."
    },
    "lock_key": "silver_key",
    "locked_msg": "자물쇠가 잠겨 있다. 은색 열쇠가 필요해 보인다.",
    "hidden_item": "golden_key_head"
}


# ========================================
# 스크립트 함수
# ========================================

def examine_refrigerator(context_unit_id):
    """냉장고 조사 - 숫자 힌트"""
    uid = REFRIGERATOR["unique_id"]

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
        "pages": [REFRIGERATOR["examine_message"]],
        "time_consumed": 1
    }


def unlock_cupboard(context_unit_id):
    """찬장 열기"""
    player_id = morld.get_player_id()
    uid = CUPBOARD["unique_id"]

    flag_name = f"unlocked_{uid}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 열려 있다. 안은 비어 있다."],
            "time_consumed": 0
        }

    # 열쇠 보유 확인
    key_iid = registry.get_instance_id(CUPBOARD["lock_key"])
    if key_iid is None or not morld.has_item(player_id, key_iid):
        return {
            "type": "monologue",
            "pages": [CUPBOARD["locked_msg"]],
            "time_consumed": 0
        }

    # 열쇠 소모
    morld.lost_item(player_id, key_iid, 1)

    # 잠금 해제
    morld.set_flag(flag_name, 1)
    morld.add_action_log("자물쇠를 열었다")

    # 아이템 지급
    item_iid = registry.get_instance_id(CUPBOARD["hidden_item"])
    if item_iid is not None:
        morld.give_item(player_id, item_iid, 1)

    return {
        "type": "monologue",
        "pages": [
            "열쇠로 자물쇠를 열었다.",
            "안쪽 깊숙한 곳에서 황금빛 열쇠의 머리 부분을 발견했다!",
            "몸통 부분을 찾아서 조합해야 할 것 같다..."
        ],
        "time_consumed": 1
    }


def register():
    """주방 오브젝트 Asset 등록"""
    registry.register_object(REFRIGERATOR)
    registry.register_object(CUPBOARD)
