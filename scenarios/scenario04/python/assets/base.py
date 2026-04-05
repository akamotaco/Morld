# assets/base.py - S04 에셋 클래스 (Pi-World Engine 기반)
#
# engine/asset_base.py를 상속하여 S04 전용 속성 추가.

from engine.asset_base import (
    CharacterBase, ObjectBase, ItemBase, LocationBase,
    TextSelector, select_text,
    Asset, Unit,
)


class Character(CharacterBase):
    """S04 캐릭터 — 4스탯 + 클래스 시스템"""

    # 기본 스탯 (S04 전용: 근력/민첩/체력/정신)
    base_str = 10
    base_agi = 10
    base_vit = 10
    base_mnd = 10

    # 클래스
    character_class = None  # "척후", "타격수" 등

    # 특수 존재 여부 (던전의 힘 사용 가능)
    is_special = False

    # 무게
    weight = 70.0


class Object(ObjectBase):
    """S04 오브젝트"""
    pass


class Item(ItemBase):
    """S04 아이템"""
    weight = 1.0
    category = "misc"


class Location(LocationBase):
    """S04 장소"""
    pass
