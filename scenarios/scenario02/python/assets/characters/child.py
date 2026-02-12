# assets/characters/child.py - 아이 NPC 캐릭터 Asset
#
# 출산 시 동적 생성되는 아이 NPC.
# pregnancy.spawn_child()에서 인스턴스 생성 후 속성 설정.

from assets.base import Character


class Child(Character):
    """아이 NPC — 출산 시 동적 생성"""
    unique_id = "child"
    name = "아이"
    type = "male"  # 출산 시 랜덤 결정

    props = {
        "나이": 0,
        "생존:체력": 50,
        "생존:최대체력": 50,
        "생존:포만감": 100,
        "부모:어머니": "",
        "부모:아버지": "",
    }

    DESCRIBE_RULES = [
        ({}, "{name}(이)가 있다."),
    ]

    FOCUS_RULES = [
        ({}, "{name} — 아직 어린아이다."),
    ]
