# assets/items/notes.py - 쪽지류 (쪽지1, 쪽지2, 쪽지3)

from assets.base import Item


class Note1(Item):
    """쪽지 1"""
    unique_id = "note1"
    name = "쪽지 1"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:read_note1:읽기@inventory"]

    content = '''"빛이 없으면 길도 없다"

"첫 번째는 불꽃 속에,
두 번째는 차가운 곳에,
세 번째와 네 번째는 벽에 걸린 눈 속에."'''


class Note2(Item):
    """쪽지 2"""
    unique_id = "note2"
    name = "쪽지 2"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:read_note2:읽기@inventory"]

    content = '''"화장대 서랍을 열고 싶다면
숫자를 찾아라.

불꽃이 처음이요,
냉기가 다음이요,
그림이 마지막이니라."'''


class Note3(Item):
    """쪽지 3"""
    unique_id = "note3"
    name = "쪽지 3"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:read_note3:읽기@inventory"]

    content = '''"연도를 기억하라 - 1842"'''


# ========================================
# 스크립트 함수
# ========================================

def read_note1(context_unit_id):
    """쪽지 1 읽기"""
    return {
        "type": "monologue",
        "pages": [Note1.content],
        "time_consumed": 0
    }


def read_note2(context_unit_id):
    """쪽지 2 읽기"""
    return {
        "type": "monologue",
        "pages": [Note2.content],
        "time_consumed": 0
    }


def read_note3(context_unit_id):
    """쪽지 3 읽기"""
    return {
        "type": "monologue",
        "pages": [Note3.content],
        "time_consumed": 0
    }
