# assets/objects/kitchen.py - 주방 오브젝트 (냉장고, 찬장)

import morld
from assets.base import Object
from assets.items.golden_key import get_item_instance


class Refrigerator(Object):
    """냉장고"""
    unique_id = "refrigerator"
    name = "냉장고"
    actions = ["script:examine_refrigerator:조사"]
    focus_text = {
        "default": "1950년대 스타일의 오래된 냉장고다. 녹이 슬어 문이 삐걱거린다. 문에 무언가 붙어있다."
    }
    examine_message = "냉장고 문에 '7'이라는 숫자 자석이 붙어 있다."


class Cupboard(Object):
    """찬장"""
    unique_id = "cupboard"
    name = "찬장"
    actions = ["script:unlock_cupboard:열기"]
    focus_text = {
        "default": "주방 구석에 놓인 큼지막한 찬장이다. 은색 자물쇠로 잠겨있다. 유리창 너머로 안에 뭔가 반짝이는 게 보인다.",
        "unlocked": "열린 찬장이다. 먼지 쌓인 접시들만 남아있다."
    }
    lock_key = "silver_key"
    locked_msg = "자물쇠가 잠겨 있다. 은색 열쇠가 필요해 보인다."
    hidden_item = "golden_key_head"


# ========================================
# 스크립트 함수
# ========================================

def examine_refrigerator(context_unit_id):
    """냉장고 조사 - 숫자 힌트"""
    flag_name = f"examined_{Refrigerator.unique_id}"
    if morld.get_prop(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    morld.set_prop(flag_name, 1)

    return {
        "type": "monologue",
        "pages": [Refrigerator.examine_message],
        "time_consumed": 1
    }


def unlock_cupboard(context_unit_id):
    """찬장 열기"""
    player_id = morld.get_player_id()

    flag_name = f"unlocked_{Cupboard.unique_id}"
    if morld.get_prop(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 열려 있다. 안은 비어 있다."],
            "time_consumed": 0
        }

    # 열쇠 보유 확인
    key = get_item_instance(Cupboard.lock_key)
    if not key or not morld.has_item(player_id, key.instance_id):
        return {
            "type": "monologue",
            "pages": [Cupboard.locked_msg],
            "time_consumed": 0
        }

    # 열쇠 소모
    morld.lost_item(player_id, key.instance_id, 1)

    # 잠금 해제
    morld.set_prop(flag_name, 1)
    morld.add_action_log("자물쇠를 열었다")

    # 아이템 지급
    item = get_item_instance(Cupboard.hidden_item)
    if item:
        morld.give_item(player_id, item.instance_id, 1)

    return {
        "type": "monologue",
        "pages": [
            "열쇠로 자물쇠를 열었다.",
            "안쪽 깊숙한 곳에서 황금빛 열쇠의 머리 부분을 발견했다!",
            "몸통 부분을 찾아서 조합해야 할 것 같다..."
        ],
        "time_consumed": 1
    }
