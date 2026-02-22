# assets/items/materials.py - 자재 아이템
#
# 크래프팅에 사용되는 기본 재료들
# - Log: 통나무 (나무 벌목) → 도끼로 나무판 가공 가능
# - Branch: 나뭇가지 (나무에서 줍기)
# - Plank: 나무판 (통나무 가공)
# - WoodChip: 나무조각 (통나무 가공) → 연료용
# - Cord: 끈 (풀 등에서 채집)
# - Feather: 깃털 (새 사냥 등)

import morld
import ui
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
        yield ui.dialog([
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
        yield ui.dialog([
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
        yield ui.dialog([
            "반듯하게 다듬어진 나무판이다.",
            "건축이나 도구 제작에 쓸 수 있다."
        ])


@register_item
class WoodChip(Item):
    """나무조각 - 연료용 재료 (통나무 가공)"""
    unique_id = "wood_chip"
    name = "나무조각"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 4
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """나무조각 살펴보기"""
        yield ui.dialog([
            "잘게 쪼갠 나무 조각이다.",
            "불쏘시개로 사용하기 좋다."
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
        yield ui.dialog([
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
        yield ui.dialog([
            "새의 깃털이다.",
            "화살 깃으로 쓸 수 있겠다."
        ])


@register_item
class SpiderVenom(Item):
    """거미독 — 거미 시체에서 수확 (날붙이 필요)"""
    unique_id = "spider_venom"
    name = "거미독"
    category = "material"
    value = 10
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "거미의 독낭에서 추출한 독이다.",
            "약품 제작에 쓸 수 있을지 모른다."
        ])


@register_item
class SpiderSilk(Item):
    """거미줄 — 거미 시체에서 수확"""
    unique_id = "spider_silk"
    name = "거미줄"
    category = "material"
    value = 5
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "질긴 거미줄이다.",
            "끈 대용으로 쓸 수 있을 것 같다."
        ])
