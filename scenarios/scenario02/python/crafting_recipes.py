# crafting_recipes.py - 크래프팅 레시피 데이터 정의
#
# 모든 크래프팅 레시피를 중앙에서 관리
# 각 시스템(휴대용 제작 도구, 제작대 등)에서 필요한 레시피를 가져다 사용
#
# 레시피 구조:
# - name: 표시 이름
# - category: 카테고리 (재료, 무기, 도구 등)
# - materials: {재료_unique_id: 개수}
# - result_count: 결과물 개수 (기본 1)
# - craft_time: 제작 시간 (분)


# ========================================
# 레시피 정의 (unique_id를 키로 사용)
# ========================================

CRAFTING_RECIPES = {
    # === 재료 가공 ===
    "plank": {
        "name": "나무판",
        "category": "재료",
        "materials": {"log": 1},
        "result_count": 3,
        "craft_time": 10,
    },

    # === 무기 ===
    "wooden_sword": {
        "name": "목검",
        "category": "무기",
        "materials": {"plank": 2},
        "result_count": 1,
        "craft_time": 20,
    },

    # === 도구 ===
    "rabbit_trap_branch": {
        "name": "토끼 덫",
        "category": "도구",
        "materials": {"branch": 3},
        "result_id": "rabbit_trap",
        "result_count": 1,
        "craft_time": 15,
    },
    "rabbit_trap_plank": {
        "name": "토끼 덫",
        "category": "도구",
        "materials": {"plank": 1},
        "result_id": "rabbit_trap",
        "result_count": 1,
        "craft_time": 10,
    },
}


# ========================================
# 장소별 레시피 목록
# ========================================

PORTABLE_RECIPE_LIST = [
    "rabbit_trap_branch",
    "rabbit_trap_plank",
]

WORKBENCH_RECIPE_LIST = [
    "plank",
    "wooden_sword",
    "rabbit_trap_branch",
    "rabbit_trap_plank",
]


# ========================================
# 레시피 조회 함수
# ========================================

def get_recipe(unique_id: str) -> dict:
    """unique_id로 레시피 조회"""
    recipe = CRAFTING_RECIPES.get(unique_id)
    if recipe:
        return {"unique_id": unique_id, **recipe}
    return None


def get_portable_recipes() -> list:
    """휴대용 제작 도구로 만들 수 있는 레시피 목록"""
    return [{"unique_id": uid, **CRAFTING_RECIPES[uid]} for uid in PORTABLE_RECIPE_LIST if uid in CRAFTING_RECIPES]


def get_workbench_recipes() -> list:
    """제작대에서 만들 수 있는 레시피 목록"""
    return [{"unique_id": uid, **CRAFTING_RECIPES[uid]} for uid in WORKBENCH_RECIPE_LIST if uid in CRAFTING_RECIPES]


def get_recipes_by_category(category: str, recipe_list: list = None) -> list:
    """카테고리별 레시피 목록 반환"""
    if recipe_list is None:
        recipe_list = [{"unique_id": uid, **r} for uid, r in CRAFTING_RECIPES.items()]
    return [r for r in recipe_list if r.get("category") == category]


def get_available_categories(recipe_list: list = None) -> list:
    """레시피가 존재하는 카테고리만 반환 (순서 유지)"""
    CATEGORY_ORDER = ["재료", "무기", "도구", "채집"]

    if recipe_list is None:
        recipe_list = [{"unique_id": uid, **r} for uid, r in CRAFTING_RECIPES.items()]

    available = set(r.get("category") for r in recipe_list)
    return [c for c in CATEGORY_ORDER if c in available]
