# recipes.py - 조리 레시피 시스템
#
# 레시피 구조:
# - ingredients: {unique_id: count} - 재료 종류가 정확히 일치해야 함
# - result: (unique_id, count) - 결과물
# - cook_time: 조리 시간 (분)
#
# 현재 채집 가능한 재료:
# - food_wild_berry (산딸기) - 채집터, 강가
# - food_apple (사과) - 숲 깊은 곳
# - food_mushroom (버섯) - 채집터
# - food_fish (생선) - 강가 낚시
# - food_herb (약초) - 뒷마당 약초밭


# 레시피 정의
# ingredients의 키는 아이템 unique_id와 매칭
RECIPES = {
    # === 생선 요리 ===
    "food_cooked_fish": {
        "name": "구운 생선",
        "ingredients": {"food_fish": 1},
        "result": ("food_cooked_fish", 1),
        "cook_time": 10,
    },

    # === 버섯 요리 ===
    "food_mushroom_stew": {
        "name": "버섯 스튜",
        "ingredients": {"food_mushroom": 2},
        "result": ("food_mushroom_stew", 1),
        "cook_time": 20,
    },

    # === 과일/채소 요리 ===
    "food_fruit_salad": {
        "name": "과일 샐러드",
        "ingredients": {"food_apple": 1, "food_wild_berry": 2},
        "result": ("food_fruit_salad", 1),
        "cook_time": 5,
    },

    # === 허브 음료 ===
    "drink_herb_tea": {
        "name": "허브티",
        "ingredients": {"food_herb": 1},
        "result": ("drink_herb_tea", 1),
        "cook_time": 5,
    },
}


def find_matching_recipe(inventory_uniques: dict):
    """
    인벤토리의 재료 종류가 레시피와 정확히 일치하는지 확인

    Args:
        inventory_uniques: {unique_id: count} - 조리 도구에 있는 재료

    Returns:
        (recipe_id, recipe, max_count) 또는 None
        - recipe_id: 레시피 ID
        - recipe: 레시피 딕셔너리
        - max_count: 최대 조리 가능 횟수
    """
    inv_keys = set(inventory_uniques.keys())

    for recipe_id, recipe in RECIPES.items():
        recipe_keys = set(recipe["ingredients"].keys())

        # 재료 종류가 정확히 일치해야 함
        if inv_keys != recipe_keys:
            continue

        # 몇 번 조리 가능한지 계산
        max_count = float('inf')
        for unique_id, needed in recipe["ingredients"].items():
            available = inventory_uniques.get(unique_id, 0)
            max_count = min(max_count, available // needed)

        if max_count > 0:
            return recipe_id, recipe, int(max_count)

    return None


def get_recipe_by_id(recipe_id: str):
    """레시피 ID로 레시피 조회"""
    return RECIPES.get(recipe_id)


def list_all_recipes():
    """모든 레시피 목록 반환"""
    return list(RECIPES.items())
