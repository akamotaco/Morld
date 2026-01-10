# assets/items/food.py - 음식 아이템
#
# 생존 시스템과 연동되는 음식 아이템들
# - food_satiety: 포만감 회복량
# - eat(): 먹기 액션 (Generator)
#
# 사용법:
#   from assets.items.food import Apple, WildBerry
#   apple = Apple()
#   apple.instantiate(item_id)

import morld
from assets.base import Item
from assets.registry import register_item


class FoodItem(Item):
    """
    음식 아이템 베이스 클래스

    Attributes:
        food_satiety: 포만감 회복량
        eat_message: 먹을 때 표시되는 메시지 (리스트)
        eat_time: 먹는데 걸리는 시간 (분)
    """
    food_satiety = 0
    eat_message = ["음식을 먹었다."]
    eat_time = 1

    def eat(self):
        """
        음식 먹기 - 포만감 회복 후 아이템 소비

        Generator 기반 액션
        """
        player_id = morld.get_player_id()

        # 포만감 최대치 확인
        import survival
        stats = survival.get_survival_stats(player_id)
        if stats["satiety"] >= stats["max_satiety"]:
            yield morld.dialog("배가 불러서 더 먹을 수 없다.")
            return

        # 포만감 회복
        survival.add_satiety(player_id, self.food_satiety)

        # 아이템 소비
        morld.lost_item(player_id, self.instance_id)

        # 메시지 표시
        yield morld.dialog(self.eat_message)

        # 시간 경과
        morld.advance_time(self.eat_time)


# ========================================
# 자연에서 채집 가능한 음식
# ========================================

@register_item
class WildBerry(FoodItem):
    """산딸기 - 산딸기 덤불에서 채집"""
    unique_id = "wild_berry"
    name = "산딸기"
    value = 2
    food_satiety = 10
    eat_message = [
        "산딸기를 먹었다.",
        "새콤달콤한 맛이 입안에 퍼진다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class Apple(FoodItem):
    """사과 - 사과나무에서 채집"""
    unique_id = "apple"
    name = "사과"
    value = 5
    food_satiety = 25
    eat_message = [
        "사과를 한입 베어 물었다.",
        "아삭한 식감과 달콤한 과즙이 느껴진다."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class Mushroom(FoodItem):
    """버섯 - 숲에서 채집"""
    unique_id = "mushroom"
    name = "버섯"
    value = 4
    food_satiety = 15
    eat_message = [
        "버섯을 먹었다.",
        "쫄깃한 식감이 좋다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:먹기@inventory"]


# ========================================
# 조리된 음식
# ========================================

@register_item
class CookedMeat(FoodItem):
    """구운 고기 - 조리 필요"""
    unique_id = "cooked_meat"
    name = "구운 고기"
    value = 20
    food_satiety = 50
    eat_message = [
        "구운 고기를 먹었다.",
        "든든하게 배가 차는 느낌이다."
    ]
    eat_time = 5
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class CookedFish(FoodItem):
    """구운 생선 - 조리 필요"""
    unique_id = "cooked_fish"
    name = "구운 생선"
    value = 15
    food_satiety = 35
    eat_message = [
        "구운 생선을 먹었다.",
        "담백하고 고소한 맛이다."
    ]
    eat_time = 4
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class HerbSalad(FoodItem):
    """허브 샐러드 - 조리 필요"""
    unique_id = "herb_salad"
    name = "허브 샐러드"
    value = 18
    food_satiety = 20
    eat_message = [
        "허브 샐러드를 먹었다.",
        "상쾌한 풀 향기가 입안에 퍼진다."
    ]
    eat_time = 3
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class MeatStew(FoodItem):
    """고기 스튜 - 조리 필요"""
    unique_id = "meat_stew"
    name = "고기 스튜"
    value = 30
    food_satiety = 70
    eat_message = [
        "따끈한 고기 스튜를 먹었다.",
        "든든하고 몸이 따뜻해진다."
    ]
    eat_time = 8
    actions = ["take@container", "call:eat:먹기@inventory"]
