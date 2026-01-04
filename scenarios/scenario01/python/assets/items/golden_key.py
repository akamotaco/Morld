# assets/items/golden_key.py - 황금열쇠 (머리 + 몸통 + 완성품 + 조합)

import morld
from assets import registry

# ========================================
# Asset 정의
# ========================================

# 조합 부품: 머리
GOLDEN_KEY_HEAD = {
    "unique_id": "golden_key_head",
    "name": "황금열쇠 머리",
    "passiveTags": {},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container", "script:combine_golden_key:조합@inventory"]
}

# 조합 부품: 몸통
GOLDEN_KEY_BODY = {
    "unique_id": "golden_key_body",
    "name": "황금열쇠 몸통",
    "passiveTags": {},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container", "script:combine_golden_key:조합@inventory"]
}

# 완성품
GOLDEN_KEY = {
    "unique_id": "golden_key",
    "name": "황금열쇠",
    "passiveTags": {"황금열쇠": 1},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container"]
}

# 조합 레시피
RECIPE = {
    "ingredients": ["golden_key_head", "golden_key_body"],
    "result": "golden_key"
}


# ========================================
# 스크립트 함수
# ========================================

def combine_golden_key(context_unit_id):
    """황금열쇠 조합"""
    player_id = morld.get_player_id()

    # instance_id 조회
    head_id = registry.get_instance_id("golden_key_head")
    body_id = registry.get_instance_id("golden_key_body")
    result_id = registry.get_instance_id("golden_key")

    # 재료 확인
    has_head = head_id is not None and morld.has_item(player_id, head_id)
    has_body = body_id is not None and morld.has_item(player_id, body_id)

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
    morld.lost_item(player_id, head_id, 1)
    morld.lost_item(player_id, body_id, 1)
    morld.give_item(player_id, result_id, 1)
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


def register():
    """황금열쇠 관련 Asset 등록"""
    registry.register_item(GOLDEN_KEY_HEAD)
    registry.register_item(GOLDEN_KEY_BODY)
    registry.register_item(GOLDEN_KEY)
