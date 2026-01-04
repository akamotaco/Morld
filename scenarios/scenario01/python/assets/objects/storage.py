# assets/objects/storage.py - 창고 오브젝트 (선반, 낡은 캐비닛)

import morld
from assets import registry

# ========================================
# Asset 정의
# ========================================

SHELF = {
    "unique_id": "shelf",
    "name": "선반",
    "actions": ["script:examine_shelf:조사"],
    "appearance": {
        "default": "벽에 붙은 나무 선반이다. 먼지와 거미줄 사이로 오래된 공구들과 깨진 유리병들이 흩어져 있다."
    },
    "hidden_item": "note1",
    "examine_message": "선반을 살펴보니 먼지 사이에 쪽지가 끼어 있다."
}

OLD_CABINET = {
    "unique_id": "old_cabinet",
    "name": "낡은 캐비닛",
    "actions": ["script:unlock_cabinet:열기"],
    "appearance": {
        "default": "바닥에 세워진 낡은 철제 캐비닛이다. 녹슨 자물쇠가 달려 있다. 안에 뭔가 들어있는 것 같다.",
        "unlocked": "열린 캐비닛이다. 안에는 먼지만 남아있다."
    },
    "lock_key": "rusty_key",
    "locked_msg": "자물쇠가 잠겨 있다. 녹슨 열쇠가 필요해 보인다.",
    "hidden_item": "silver_key"
}


# ========================================
# 스크립트 함수
# ========================================

def examine_shelf(context_unit_id):
    """선반 조사"""
    player_id = morld.get_player_id()
    uid = SHELF["unique_id"]

    flag_name = f"examined_{uid}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 조사한 곳이다. 더 이상 볼 것이 없다."],
            "time_consumed": 0
        }

    morld.set_flag(flag_name, 1)

    item_iid = registry.get_instance_id(SHELF["hidden_item"])
    if item_iid is not None:
        morld.give_item(player_id, item_iid, 1)

    return {
        "type": "monologue",
        "pages": [SHELF["examine_message"]],
        "time_consumed": 1
    }


def unlock_cabinet(context_unit_id):
    """낡은 캐비닛 열기"""
    player_id = morld.get_player_id()
    uid = OLD_CABINET["unique_id"]

    flag_name = f"unlocked_{uid}"
    if morld.get_flag(flag_name) > 0:
        return {
            "type": "monologue",
            "pages": ["이미 열려 있다. 안은 비어 있다."],
            "time_consumed": 0
        }

    # 열쇠 보유 확인
    key_iid = registry.get_instance_id(OLD_CABINET["lock_key"])
    if key_iid is None or not morld.has_item(player_id, key_iid):
        return {
            "type": "monologue",
            "pages": [OLD_CABINET["locked_msg"]],
            "time_consumed": 0
        }

    # 열쇠 소모
    morld.lost_item(player_id, key_iid, 1)

    # 잠금 해제
    morld.set_flag(flag_name, 1)
    morld.add_action_log("자물쇠를 열었다")

    # 아이템 지급
    item_iid = registry.get_instance_id(OLD_CABINET["hidden_item"])
    if item_iid is not None:
        morld.give_item(player_id, item_iid, 1)

    return {
        "type": "monologue",
        "pages": [
            "열쇠로 자물쇠를 열었다.",
            "안에서 은빛으로 빛나는 열쇠를 발견했다!"
        ],
        "time_consumed": 1
    }


def register():
    """창고 오브젝트 Asset 등록"""
    registry.register_object(SHELF)
    registry.register_object(OLD_CABINET)
