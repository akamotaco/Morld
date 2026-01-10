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
# 채집 가능한 재료
# ========================================

@register_item
class Herb(FoodItem):
    """
    약초 - 뒷마당 약초밭에서 채집 (음료 재료)

    사용법:
    - 그냥 먹기: 포만감 5 + 치료 효과
    - 주전자에 넣고 끓이기: 허브티로 제조
    """
    unique_id = "food_herb"
    name = "약초"
    category = "drink_ingredient"  # 음료 재료 (주전자용)
    value = 8
    food_satiety = 5
    eat_message = [
        "약초를 씹어 먹었다.",
        "쓴맛이 입안에 퍼지지만, 몸에 좋은 느낌이다.",
        "상처가 조금 나아진 것 같다.",
        "(테스트 중으로 실제 치료 효과는 없습니다.)"
    ]
    eat_time = 1
    # passive_props = {"치료": 1}  # 소지 시 치료 효과 # 섭취시에만 치료 효과 (미구현)
    actions = ["take@container", "call:eat:먹기@inventory"]


# ========================================
# 자연에서 채집 가능한 음식
# ========================================

@register_item
class WildBerry(FoodItem):
    """산딸기 - 산딸기 덤불에서 채집"""
    unique_id = "food_wild_berry"
    name = "산딸기"
    category = "food_ingredient"  # 음식 재료 (아궁이용)
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
    unique_id = "food_apple"
    name = "사과"
    category = "food_ingredient"  # 음식 재료 (아궁이용)
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
    unique_id = "food_mushroom"
    name = "버섯"
    category = "food_ingredient"  # 음식 재료 (아궁이용)
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
    unique_id = "food_cooked_meat"
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
class Fish(FoodItem):
    """생선 - 낚시로 획득"""
    unique_id = "food_fish"
    name = "생선"
    category = "food_ingredient"  # 음식 재료 (아궁이용)
    value = 8
    food_satiety = 20
    eat_message = [
        "날 생선을 먹었다.",
        "비릿한 맛이 난다..."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class CookedFish(FoodItem):
    """구운 생선 - 조리 필요"""
    unique_id = "food_cooked_fish"
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
class MushroomStew(FoodItem):
    """버섯 스튜 - 조리 필요 (버섯 2개)"""
    unique_id = "food_mushroom_stew"
    name = "버섯 스튜"
    value = 25
    food_satiety = 45
    eat_message = [
        "따끈한 버섯 스튜를 먹었다.",
        "진한 버섯 향과 함께 몸이 따뜻해진다."
    ]
    eat_time = 6
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class FruitSalad(FoodItem):
    """과일 샐러드 - 조리 필요 (사과 1 + 산딸기 2)"""
    unique_id = "food_fruit_salad"
    name = "과일 샐러드"
    value = 18
    food_satiety = 40
    eat_message = [
        "과일 샐러드를 먹었다.",
        "달콤하고 상큼한 맛이 입안에 퍼진다."
    ]
    eat_time = 3
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class HerbTea(FoodItem):
    """허브티 - 조리 필요 (약초 1개)"""
    unique_id = "drink_herb_tea"
    name = "허브티"
    value = 15
    food_satiety = 15
    eat_message = [
        "따뜻한 허브티를 마셨다.",
        "은은한 허브 향이 마음을 편안하게 한다."
    ]
    eat_time = 3
    actions = ["take@container", "call:eat:마시기@inventory"]
