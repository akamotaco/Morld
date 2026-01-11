# assets/items/materials.py - 자재 아이템
#
# 크래프팅에 사용되는 기본 재료들
# - Log: 통나무 (나무 벌목) → 도끼로 나무판 가공 가능
# - Branch: 나뭇가지 (나무에서 줍기)
# - Plank: 나무판 (통나무 가공)
# - Cord: 끈 (풀 등에서 채집)
# - Feather: 깃털 (새 사냥 등)

import morld
from assets.base import Item
from assets.registry import register_item, get_item_class


@register_item
class Log(Item):
    """
    통나무 - 크래프팅 재료

    도끼(passive) 보유 시 "나무판으로 가공" 액션 활성화
    통나무 1개 → 나무판 3개
    """
    unique_id = "log"
    name = "통나무"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = [
        "take@container",
        "call:look:살펴보기@inventory",
    ]

    def look(self):
        """통나무 살펴보기"""
        yield morld.dialog([
            "단단한 통나무다.",
            "제작대에서 나무판으로 가공할 수 있을 것 같다."
        ])


@register_item
class Branch(Item):
    """나뭇가지 - 크래프팅 재료"""
    unique_id = "branch"
    name = "나뭇가지"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 2
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """나뭇가지 살펴보기"""
        yield morld.dialog([
            "마른 나뭇가지다.",
            "불쏘시개나 간단한 도구 재료로 쓸 수 있다."
        ])


@register_item
class Plank(Item):
    """나무판 - 크래프팅 재료 (통나무 가공)"""
    unique_id = "plank"
    name = "나무판"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """나무판 살펴보기"""
        yield morld.dialog([
            "반듯하게 다듬어진 나무판이다.",
            "건축이나 도구 제작에 쓸 수 있다."
        ])


@register_item
class Cord(Item):
    """끈 - 크래프팅 재료 (활, 덫 등 제작용)"""
    unique_id = "cord"
    name = "끈"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 3
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """끈 살펴보기"""
        yield morld.dialog([
            "질긴 식물 줄기로 엮은 끈이다.",
            "활이나 덫을 만드는 데 쓸 수 있다."
        ])


@register_item
class Feather(Item):
    """깃털 - 크래프팅 재료 (화살 등 제작용)"""
    unique_id = "feather"
    name = "깃털"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 2
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """깃털 살펴보기"""
        yield morld.dialog([
            "새의 깃털이다.",
            "화살 깃으로 쓸 수 있겠다."
        ])
