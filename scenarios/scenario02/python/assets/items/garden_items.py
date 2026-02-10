# assets/items/garden_items.py - 텃밭 관련 아이템
#
# 씨앗 (5종), 작물 (4종, 약초는 기존 food_herb 재사용), 비료, 물 아이템 (2종)

import morld
import ui
from assets.base import Item
from assets.items.food import FoodItem
from assets.registry import register_item


# ========================================
# 씨앗 아이템
# ========================================

class SeedItem(Item):
    """씨앗 베이스 클래스"""
    category = "seed"
    passive_props = {}
    equip_props = {}
    actions = ["take@container", "call:look:살펴보기@inventory"]

    seed_description = "씨앗이다."

    def look(self):
        yield ui.dialog(self.seed_description)


@register_item
class PotatoSeed(SeedItem):
    unique_id = "seed_potato"
    name = "감자 씨앗"
    value = 3
    seed_description = "감자를 키울 수 있는 씨앗이다. 텃밭에 심으면 자란다."


@register_item
class TomatoSeed(SeedItem):
    unique_id = "seed_tomato"
    name = "토마토 씨앗"
    value = 3
    seed_description = "토마토를 키울 수 있는 씨앗이다. 텃밭에 심으면 자란다."


@register_item
class CarrotSeed(SeedItem):
    unique_id = "seed_carrot"
    name = "당근 씨앗"
    value = 3
    seed_description = "당근을 키울 수 있는 씨앗이다. 텃밭에 심으면 자란다."


@register_item
class HerbSeed(SeedItem):
    unique_id = "seed_herb"
    name = "약초 씨앗"
    value = 5
    seed_description = "약초를 키울 수 있는 씨앗이다. 텃밭에 심으면 자란다."


@register_item
class CabbageSeed(SeedItem):
    unique_id = "seed_cabbage"
    name = "양배추 씨앗"
    value = 3
    seed_description = "양배추를 키울 수 있는 씨앗이다. 텃밭에 심으면 자란다."


# ========================================
# 작물 아이템 (수확물)
# ========================================
# 약초(food_herb)는 food.py에 이미 존재 → 재사용

@register_item
class Potato(FoodItem):
    unique_id = "food_potato"
    name = "감자"
    category = "food_ingredient"
    value = 6
    food_satiety = 30
    eat_message = [
        "감자를 먹었다.",
        "담백하고 든든한 맛이다."
    ]
    eat_time = 3
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class Tomato(FoodItem):
    unique_id = "food_tomato"
    name = "토마토"
    category = "food_ingredient"
    value = 5
    food_satiety = 15
    eat_message = [
        "토마토를 한입 베어 물었다.",
        "상큼하고 즙이 풍부하다."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class Carrot(FoodItem):
    unique_id = "food_carrot"
    name = "당근"
    category = "food_ingredient"
    value = 4
    food_satiety = 20
    eat_message = [
        "당근을 아삭아삭 먹었다.",
        "달콤한 맛이 입안에 퍼진다."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class Cabbage(FoodItem):
    unique_id = "food_cabbage"
    name = "양배추"
    category = "food_ingredient"
    value = 5
    food_satiety = 15
    eat_message = [
        "양배추 잎을 뜯어 먹었다.",
        "아삭한 식감이 좋다."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:먹기@inventory"]


# ========================================
# 비료
# ========================================

@register_item
class Fertilizer(Item):
    unique_id = "fertilizer"
    name = "비료"
    category = "garden_supply"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        yield ui.dialog([
            "식물의 성장을 촉진하는 비료다.",
            "텃밭에 뿌리면 작물이 더 빨리 자란다."
        ])


# ========================================
# 물 아이템
# ========================================

PROP_WATER_AMOUNT = "물:양"


class WaterContainer(Item):
    """물 용기 베이스 클래스"""
    category = "garden_tool"
    passive_props = {"can:water": 1}   # NPC 도구 탐색용
    equip_props = {}
    water_capacity = 1
    actions = [
        "take@container",
        "call:drink:물 마시기@inventory",
        "call:look:살펴보기@inventory",
    ]

    def _get_water(self):
        """현재 물 잔량"""
        return morld.get_unit_prop(self.instance_id, PROP_WATER_AMOUNT)

    def _set_water(self, amount):
        """물 잔량 설정"""
        morld.set_unit_prop(self.instance_id, PROP_WATER_AMOUNT, amount)

    def look(self):
        water = self._get_water()
        if water > 0:
            yield ui.dialog(f"{self.name} — 물이 {water}/{self.water_capacity}만큼 들어있다.")
        else:
            yield ui.dialog(f"{self.name} — 비어있다. 싱크대나 세면대에서 물을 받을 수 있다.")

    def drink(self):
        water = self._get_water()
        if water <= 0:
            yield ui.dialog("물이 비어있다. 싱크대나 세면대에서 물을 받아야 한다.")
            return

        player_id = morld.get_player_id()
        import survival
        stats = survival.get_survival_stats(player_id)
        if stats["satiety"] >= stats["max_satiety"]:
            yield ui.dialog("배가 불러서 더 마실 수 없다.")
            return

        survival.add_satiety(player_id, 5)
        self._set_water(water - 1)

        remaining = water - 1
        if remaining > 0:
            yield ui.dialog([
                f"{self.name}의 물을 마셨다.",
                f"남은 물: {remaining}/{self.water_capacity}"
            ])
        else:
            yield ui.dialog([
                f"{self.name}의 물을 마셨다.",
                "물이 다 떨어졌다."
            ])
        morld.advance_time_des(1 * 60_000)


@register_item
class WateringCan(WaterContainer):
    unique_id = "watering_can"
    name = "물뿌리개"
    water_capacity = 3
    value = 10


@register_item
class WaterBucket(WaterContainer):
    unique_id = "water_bucket"
    name = "물통"
    water_capacity = 5
    value = 8


@register_item
class SimpleWaterBottle(WaterContainer):
    unique_id = "simple_water_bottle"
    name = "간이 물병"
    water_capacity = 2
    value = 3
