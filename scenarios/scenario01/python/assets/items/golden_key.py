# assets/items/golden_key.py - 황금열쇠 (머리 + 몸통 + 완성품 + 조합)

import morld
from assets.base import Item


class GoldenKeyHead(Item):
    """황금열쇠 머리"""
    unique_id = "golden_key_head"
    name = "황금열쇠 머리"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:combine_golden_key:조합@inventory"]


class GoldenKeyBody(Item):
    """황금열쇠 몸통"""
    unique_id = "golden_key_body"
    name = "황금열쇠 몸통"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:combine_golden_key:조합@inventory"]


class GoldenKey(Item):
    """황금열쇠 (완성품)"""
    unique_id = "golden_key"
    name = "황금열쇠"
    passive_props = {"황금열쇠": 1}
    equip_props = {}
    value = 0
    actions = ["take@container"]


# ========================================
# 인스턴스 레지스트리 (world/mansion.py에서 등록)
# ========================================

_instances = {}


def register_item_instance(unique_id: str, instance):
    """아이템 인스턴스 등록"""
    _instances[unique_id] = instance


def get_item_instance(unique_id: str):
    """아이템 인스턴스 조회"""
    return _instances.get(unique_id)


# ========================================
# 스크립트 함수
# ========================================

def combine_golden_key(context_unit_id):
    """황금열쇠 조합"""
    player_id = morld.get_player_id()

    # 인스턴스 조회
    head = get_item_instance("golden_key_head")
    body = get_item_instance("golden_key_body")
    result = get_item_instance("golden_key")

    if not all([head, body, result]):
        return {
            "type": "monologue",
            "pages": ["조합할 수 없다."],
            "time_consumed": 0
        }

    # 재료 확인
    has_head = morld.has_item(player_id, head.instance_id)
    has_body = morld.has_item(player_id, body.instance_id)

    if not has_head or not has_body:
        if has_head:
            return {
                "type": "monologue",
                "pages": [
                    "황금열쇠의 머리 부분이다.",
                    "몸통 부분이 없으면 조합할 수 없다."
                ],
                "time_consumed": 0
            }
        elif has_body:
            return {
                "type": "monologue",
                "pages": [
                    "황금열쇠의 몸통 부분이다.",
                    "머리 부분이 없으면 조합할 수 없다."
                ],
                "time_consumed": 0
            }
        else:
            return {
                "type": "monologue",
                "pages": ["조합할 재료가 없다."],
                "time_consumed": 0
            }

    # 조합 진행
    morld.lost_item(player_id, head.instance_id, 1)
    morld.lost_item(player_id, body.instance_id, 1)
    morld.give_item(player_id, result.instance_id, 1)
    morld.add_action_log("황금열쇠를 완성했다")

    return {
        "type": "monologue",
        "pages": [
            "두 파츠를 맞춰본다...",
            "철컥!",
            "완벽하게 들어맞았다!",
            "황금열쇠가 완성되었다!",
            "이제 정문을 열 수 있을 것 같다!"
        ],
        "time_consumed": 1
    }
