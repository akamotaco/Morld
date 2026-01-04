# assets/items/notes.py - 쪽지류 (쪽지1, 쪽지2, 쪽지3)

from assets import registry

# ========================================
# Asset 정의
# ========================================

NOTE1 = {
    "unique_id": "note1",
    "name": "쪽지 1",
    "passiveTags": {},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container", "script:read_note1:읽기@inventory"],
    # 쪽지 내용 (스크립트에서 사용)
    "content": '''"빛이 없으면 길도 없다"

"첫 번째는 불꽃 속에,
두 번째는 차가운 곳에,
세 번째와 네 번째는 벽에 걸린 눈 속에."'''
}

NOTE2 = {
    "unique_id": "note2",
    "name": "쪽지 2",
    "passiveTags": {},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container", "script:read_note2:읽기@inventory"],
    "content": '''"화장대 서랍을 열고 싶다면
숫자를 찾아라.

불꽃이 처음이요,
냉기가 다음이요,
그림이 마지막이니라."'''
}

NOTE3 = {
    "unique_id": "note3",
    "name": "쪽지 3",
    "passiveTags": {},
    "equipTags": {},
    "value": 0,
    "actions": ["take@container", "script:read_note3:읽기@inventory"],
    "content": '''"연도를 기억하라 - 1842"'''
}


# ========================================
# 스크립트 함수
# ========================================

def read_note1(context_unit_id):
    """쪽지 1 읽기"""
    return {
        "type": "monologue",
        "pages": [NOTE1["content"]],
        "time_consumed": 0
    }


def read_note2(context_unit_id):
    """쪽지 2 읽기"""
    return {
        "type": "monologue",
        "pages": [NOTE2["content"]],
        "time_consumed": 0
    }


def read_note3(context_unit_id):
    """쪽지 3 읽기"""
    return {
        "type": "monologue",
        "pages": [NOTE3["content"]],
        "time_consumed": 0
    }


def register():
    """쪽지류 Asset 등록"""
    registry.register_item(NOTE1)
    registry.register_item(NOTE2)
    registry.register_item(NOTE3)
