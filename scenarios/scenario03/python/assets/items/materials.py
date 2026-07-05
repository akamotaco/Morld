# assets/items/materials.py - 건축 자재 아이템
#
# 시나리오03 데모용 건축 자재.
# 플랫폼 시설 건설에 사용된다.

from assets.base import Item
from assets.registry import register_item


@register_item
class MetalPipe(Item):
    """금속 파이프 — 구조물 골격용"""
    unique_id = "metal_pipe"
    name = "금속 파이프"
    category = "material"
    value = 5
    passive_props = {}
    actions = []


@register_item
class ConcreteBlock(Item):
    """콘크리트 블록 — 벽체/기초용"""
    unique_id = "concrete_block"
    name = "콘크리트 블록"
    category = "material"
    value = 3
    passive_props = {}
    actions = []


@register_item
class Plank(Item):
    """판자 — 바닥/벽면용"""
    unique_id = "plank"
    name = "판자"
    category = "material"
    value = 2
    passive_props = {}
    actions = []


@register_item
class Wire(Item):
    """전선 — 전기 배선용"""
    unique_id = "wire"
    name = "전선"
    category = "material"
    value = 4
    passive_props = {}
    actions = []
