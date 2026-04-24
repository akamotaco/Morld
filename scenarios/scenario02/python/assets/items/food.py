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
import ui
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

    def on_eat_effect(self, player_id):
        """특수 섭취 효과 — 서브클래스에서 오버라이드"""
        pass

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
            yield ui.dialog("배가 불러서 더 먹을 수 없다.")
            return

        # 미약 첨가 여부 확인 (대사 발동용 — 효과는 apply_food_additive_effects)
        from romance_core import has_food_additive, is_status_active, apply_food_additive_effects
        had_aphrodisiac_before = (
            has_food_additive(self.instance_id, "미약")
            and not is_status_active(player_id, "미약")
        )

        # 포만감 회복
        survival.add_satiety(player_id, self.food_satiety)

        # 플레이어 통계: 음식 섭취 횟수
        morld.set_unit_prop(player_id, "통계:음식섭취",
                            (morld.get_unit_prop(player_id, "통계:음식섭취") or 0) + 1)

        # 아이템 소비
        morld.lost_item(player_id, self.instance_id)

        # 메시지 표시
        yield ui.dialog(self.eat_message)

        # 특수 섭취 효과 (서브클래스 오버라이드)
        self.on_eat_effect(player_id)

        # 모든 첨가물 효과 일괄 적용 (미약/배란유도제/정력제/취기/독주/마약/최면제)
        apply_food_additive_effects(player_id, self.instance_id)
        if had_aphrodisiac_before:
            yield ui.dialog("...뭔가 이상한 맛이 섞여 있던 것 같다.")

        # 시간 경과
        morld.advance_time_des(self.eat_time * 60_000)


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


@register_item
class RoastedRabbit(FoodItem):
    """토끼 구이 - 조리 필요 (토끼 생고기 1개)"""
    unique_id = "food_roasted_rabbit"
    name = "토끼 구이"
    value = 30
    food_satiety = 55
    eat_message = [
        "토끼 구이를 먹었다.",
        "잘 익은 고기가 쫄깃하고 고소하다.",
        "든든하게 배가 찬다."
    ]
    eat_time = 5
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class AppleJam(FoodItem):
    """사과잼 - 조리 필요 (사과 2개)"""
    unique_id = "food_apple_jam"
    name = "사과잼"
    value = 20
    food_satiety = 30
    eat_message = [
        "사과잼을 먹었다.",
        "달콤하고 새콤한 맛이 입안에 퍼진다."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class VegetableSoup(FoodItem):
    """야채 수프 - 조리 필요 (버섯 2 + 산딸기 1)"""
    unique_id = "food_vegetable_soup"
    name = "야채 수프"
    value = 22
    food_satiety = 40
    eat_message = [
        "따끈한 야채 수프를 먹었다.",
        "버섯과 산딸기의 조화가 묘하게 좋다.",
        "속이 든든해진다."
    ]
    eat_time = 5
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class BerryJuice(FoodItem):
    """산딸기 주스 - 조리 필요 (산딸기 3개)"""
    unique_id = "food_berry_juice"
    name = "산딸기 주스"
    value = 12
    food_satiety = 25
    eat_message = [
        "산딸기 주스를 마셨다.",
        "새콤달콤한 맛이 온몸에 퍼진다."
    ]
    eat_time = 2
    actions = ["take@container", "call:eat:마시기@inventory"]


@register_item
class FishSetMeal(FoodItem):
    """생선정식 - 조리 필요 (생선 1 + 버섯 1)"""
    unique_id = "food_fish_set_meal"
    name = "생선정식"
    value = 28
    food_satiety = 55
    eat_message = [
        "생선정식을 먹었다.",
        "잘 구운 생선에 버섯 반찬까지, 풍성한 한 끼다.",
        "든든하게 배가 찬다."
    ]
    eat_time = 6
    actions = ["take@container", "call:eat:먹기@inventory"]


@register_item
class MixedStew(FoodItem):
    """종합 스튜 - 조리 필요 (사과 1 + 버섯 1 + 산딸기 1)"""
    unique_id = "food_mixed_stew"
    name = "종합 스튜"
    value = 25
    food_satiety = 50
    eat_message = [
        "종합 스튜를 먹었다.",
        "다양한 재료가 어우러져 깊은 맛을 낸다.",
        "몸이 따뜻해지는 느낌이다."
    ]
    eat_time = 6
    actions = ["take@container", "call:eat:먹기@inventory"]


# ========================================
# 캔/병 음료
# ========================================

@register_item
class CannedCola(FoodItem):
    """캔 콜라 - 편의점에서 발견"""
    unique_id = "drink_canned_cola"
    name = "캔 콜라"
    value = 5
    food_satiety = 15
    eat_message = [
        "캔을 따서 콜라를 마셨다.",
        "김이 다 빠졌지만 달콤한 맛은 남아있다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:마시기@inventory"]


@register_item
class CannedCoffee(FoodItem):
    """캔 커피 - 편의점에서 발견"""
    unique_id = "drink_canned_coffee"
    name = "캔 커피"
    value = 5
    food_satiety = 10
    eat_message = [
        "캔 커피를 마셨다.",
        "미지근하지만 쌉쌀한 맛이 정신을 깨운다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:마시기@inventory"]


@register_item
class EnergyDrink(FoodItem):
    """에너지 드링크 - 편의점에서 발견"""
    unique_id = "drink_energy"
    name = "에너지 드링크"
    value = 8
    food_satiety = 20
    eat_message = [
        "에너지 드링크를 벌컥 마셨다.",
        "인공적인 단맛과 함께 활력이 느껴진다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:마시기@inventory"]


@register_item
class WaterBottle(FoodItem):
    """생수병 - 편의점에서 발견"""
    unique_id = "drink_water"
    name = "생수병"
    value = 2
    food_satiety = 10
    eat_message = [
        "생수를 마셨다.",
        "목이 축축해지는 느낌이다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:마시기@inventory"]


@register_item
class SportsDrink(FoodItem):
    """스포츠 음료 - 편의점에서 발견"""
    unique_id = "drink_sports"
    name = "스포츠 음료"
    value = 6
    food_satiety = 18
    eat_message = [
        "스포츠 음료를 마셨다.",
        "약간 짠맛이 나지만 몸에 좋은 느낌이다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:마시기@inventory"]


@register_item
class GreenTea(FoodItem):
    """녹차 (페트병) - 편의점에서 발견"""
    unique_id = "drink_green_tea"
    name = "녹차"
    value = 4
    food_satiety = 12
    eat_message = [
        "녹차를 마셨다.",
        "은은한 차 향이 입안에 퍼진다."
    ]
    eat_time = 1
    actions = ["take@container", "call:eat:마시기@inventory"]


# ========================================
# 농사 작물 요리
# ========================================

@register_item
class RoastedSweetPotato(FoodItem):
    """구운 고구마 — 포만감 높음 + 온기 효과"""
    unique_id = "food_roasted_sweet_potato"
    name = "구운 고구마"
    category = "food"
    value = 12
    food_satiety = 55
    eat_message = [
        "구운 고구마를 먹었다.",
        "달콤하고 포근한 맛이다. 몸 속까지 따뜻해진다."
    ]
    eat_time = 5
    actions = ["take@ground", "take@container", "call:eat:먹기@inventory"]

    def on_eat_effect(self, player_id):
        """온기 효과 — 4시간"""
        remaining = morld.get_unit_prop(player_id, "상태:온기남은시간") or 0
        morld.set_unit_prop(player_id, "상태:온기", 1)
        morld.set_unit_prop(player_id, "상태:온기남은시간", max(remaining, 4))


@register_item
class CornSoup(FoodItem):
    """옥수수 스프 — 고소하고 든든"""
    unique_id = "food_corn_soup"
    name = "옥수수 스프"
    category = "food"
    value = 10
    food_satiety = 35
    eat_message = [
        "옥수수 스프를 마셨다.",
        "걸쭉하고 고소한 맛이다."
    ]
    eat_time = 4
    actions = ["take@ground", "take@container", "call:eat:먹기@inventory"]


@register_item
class GarlicSoup(FoodItem):
    """마늘 스프 — 독 저항 24시간"""
    unique_id = "food_garlic_soup"
    name = "마늘 스프"
    category = "food"
    value = 10
    food_satiety = 25
    eat_message = [
        "마늘 스프를 마셨다.",
        "진한 마늘 향이 온몸으로 퍼지며 생기가 돈다."
    ]
    eat_time = 3
    actions = ["take@ground", "take@container", "call:eat:먹기@inventory"]

    def on_eat_effect(self, player_id):
        """독 저항 효과 — 24시간"""
        remaining = morld.get_unit_prop(player_id, "상태:독저항남은시간") or 0
        morld.set_unit_prop(player_id, "상태:독저항", 1)
        morld.set_unit_prop(player_id, "상태:독저항남은시간", max(remaining, 24))


@register_item
class PumpkinPorridge(FoodItem):
    """호박 죽 — 포만감 최고"""
    unique_id = "food_pumpkin_porridge"
    name = "호박 죽"
    category = "food"
    value = 14
    food_satiety = 65
    eat_message = [
        "따뜻한 호박 죽을 먹었다.",
        "부드럽게 넘어가며 배가 가득 찬다."
    ]
    eat_time = 6
    actions = ["take@ground", "take@container", "call:eat:먹기@inventory"]


@register_item
class VegetableStirFry(FoodItem):
    """야채볶음 — 균형 잡힌 한 끼"""
    unique_id = "food_vegetable_stir_fry"
    name = "야채볶음"
    category = "food"
    value = 11
    food_satiety = 45
    eat_message = [
        "야채볶음을 먹었다.",
        "채소의 단맛과 고소한 맛이 어우러진다."
    ]
    eat_time = 4
    actions = ["take@ground", "take@container", "call:eat:먹기@inventory"]


@register_item
class OnionSoup(FoodItem):
    """양파 수프 — 따뜻하고 감칠맛"""
    unique_id = "food_onion_soup"
    name = "양파 수프"
    category = "food"
    value = 9
    food_satiety = 30
    eat_message = [
        "양파 수프를 마셨다.",
        "달콤하고 감칠맛 나는 국물이 속을 데운다."
    ]
    eat_time = 3
    actions = ["take@ground", "take@container", "call:eat:먹기@inventory"]
