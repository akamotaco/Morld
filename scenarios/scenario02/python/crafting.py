# crafting.py - 크래프팅 시스템
#
# 제작 레시피 관리 및 제작 UI
#
# 레시피 구조:
# - unique_id: 결과물 아이템 unique_id
# - name: 표시 이름
# - category: 카테고리 (무기, 도구, 채집 등)
# - materials: {재료_unique_id: 개수, ...}
# - result_count: 결과물 개수 (기본 1)
# - craft_time: 제작 시간 (분)
# - tool_required: 필요한 도구 (passive props 체크)
#
# 사용법:
#   from crafting import open_craft_menu
#   yield from open_craft_menu()

import morld
from assets.registry import get_item_class


# ========================================
# 레시피 정의
# ========================================

# 플레이어 휴대 제작 (간단한 아이템)
PLAYER_RECIPES = [
    {
        "unique_id": "arrow",
        "name": "화살",
        "category": "무기",
        "materials": {"plank": 1, "feather": 1},
        "result_count": 5,  # 한 번에 5개 생성
        "craft_time": 10,
        "tool_required": None,
    },
]

# 제작대 전용 레시피 (복잡한 아이템)
WORKBENCH_RECIPES = [
    {
        "unique_id": "hunting_bow",
        "name": "사냥용 활",
        "category": "무기",
        "materials": {"plank": 2, "cord": 1},
        "result_count": 1,
        "craft_time": 30,
        "tool_required": None,
    },
]

# 전체 레시피 (호환성 유지)
RECIPES = PLAYER_RECIPES + WORKBENCH_RECIPES

# 카테고리 목록 (순서 유지)
CATEGORIES = ["무기", "도구", "채집"]


# ========================================
# 레시피 조회 함수
# ========================================

def get_recipes_by_category(category: str, recipe_source: list = None) -> list:
    """카테고리별 레시피 목록 반환"""
    recipes = recipe_source if recipe_source is not None else RECIPES
    return [r for r in recipes if r["category"] == category]


def get_available_categories(recipe_source: list = None) -> list:
    """레시피가 존재하는 카테고리만 반환"""
    recipes = recipe_source if recipe_source is not None else RECIPES
    available = set()
    for recipe in recipes:
        available.add(recipe["category"])
    # 순서 유지
    return [c for c in CATEGORIES if c in available]


def get_recipe(unique_id: str, recipe_source: list = None) -> dict:
    """unique_id로 레시피 조회"""
    recipes = recipe_source if recipe_source is not None else RECIPES
    for recipe in recipes:
        if recipe["unique_id"] == unique_id:
            return recipe
    return None


# ========================================
# 재료 확인 함수
# ========================================

def check_materials(player_id: int, recipe: dict) -> tuple:
    """
    재료 보유 여부 확인

    Returns:
        (can_craft: bool, missing: dict, have: dict)
        - can_craft: 제작 가능 여부
        - missing: 부족한 재료 {unique_id: 부족 개수}
        - have: 보유 재료 {unique_id: 보유 개수}
    """
    inventory = morld.get_unit_inventory(player_id)
    missing = {}
    have = {}

    for mat_unique_id, required in recipe["materials"].items():
        # unique_id로 item_id 조회
        item_id = morld.get_item_id_by_unique(mat_unique_id)
        if item_id is None:
            # 아이템 자체가 게임에 없음
            missing[mat_unique_id] = required
            have[mat_unique_id] = 0
            continue

        # 인벤토리에서 개수 확인
        owned = 0
        if inventory:
            owned = inventory.get(str(item_id), 0)
            if isinstance(owned, str):
                owned = int(owned)

        have[mat_unique_id] = owned
        if owned < required:
            missing[mat_unique_id] = required - owned

    return len(missing) == 0, missing, have


def get_material_name(unique_id: str) -> str:
    """재료 unique_id → 한글 이름"""
    item_cls = get_item_class(unique_id)
    if item_cls:
        return item_cls.name
    # fallback
    names = {
        "plank": "나무판",
        "cord": "끈",
        "feather": "깃털",
        "branch": "나뭇가지",
        "log": "통나무",
    }
    return names.get(unique_id, unique_id)


# ========================================
# 제작 실행
# ========================================

def craft_item(player_id: int, recipe: dict):
    """
    아이템 제작 실행

    Args:
        player_id: 플레이어 ID
        recipe: 레시피 dict

    Returns:
        Generator (morld.dialog)
    """
    # 재료 소모
    for mat_unique_id, required in recipe["materials"].items():
        item_id = morld.get_item_id_by_unique(mat_unique_id)
        if item_id is not None:
            morld.lost_item(player_id, item_id, required)

    # 시간 경과
    morld.advance_time(recipe["craft_time"])

    # 결과물 생성
    result_unique_id = recipe["unique_id"]
    result_id = morld.get_item_id_by_unique(result_unique_id)

    if result_id is None:
        # 아이템이 없으면 동적 생성
        result_cls = get_item_class(result_unique_id)
        if result_cls:
            item = result_cls()
            result_id = morld.create_id("item")
            item.instantiate(result_id)
        else:
            yield morld.dialog("제작에 실패했다...")
            return

    # 결과물 지급
    result_count = recipe.get("result_count", 1)
    morld.give_item(player_id, result_id, result_count)

    # 완료 메시지
    result_name = recipe["name"]
    if result_count > 1:
        yield morld.dialog(f"{result_name} {result_count}개를 만들었다!")
    else:
        yield morld.dialog(f"{result_name}을(를) 만들었다!")


# ========================================
# 크래프팅 UI
# ========================================

def open_craft_menu(recipe_source: list = None, title: str = "제작"):
    """
    제작 메뉴 열기 (Generator)

    Args:
        recipe_source: 사용할 레시피 목록 (None이면 PLAYER_RECIPES 사용)
        title: 메뉴 제목 (기본: "제작")

    UI 흐름:
    1. 카테고리 선택 (토글 메뉴)
    2. 레시피 선택
    3. 재료 확인 + 제작 여부
    4. 제작 실행

    사용법:
        yield from open_craft_menu()  # 플레이어 제작
        yield from open_craft_menu(WORKBENCH_RECIPES, "제작대")  # 제작대
    """
    # 기본값: 플레이어 레시피
    recipes = recipe_source if recipe_source is not None else PLAYER_RECIPES

    player_id = morld.get_player_id()
    categories = get_available_categories(recipes)

    if not categories:
        yield morld.dialog("제작할 수 있는 것이 없다.")
        return

    # 상태 관리
    state = {
        "category": None,
        "recipe": None,
        "done": False,
    }

    def build_category_menu():
        """카테고리 선택 메뉴 생성"""
        lines = [f"[{title}]\n"]
        lines.append("무엇을 만들까?\n")

        for cat in categories:
            cat_recipes = get_recipes_by_category(cat, recipes)
            lines.append(f"[url=@proc:cat:{cat}]▶ {cat} ({len(cat_recipes)})[/url]")

        lines.append("")
        lines.append("[url=@ret:back]돌아가기[/url]")
        return "\n".join(lines)

    def build_recipe_menu(category):
        """레시피 목록 메뉴 생성"""
        cat_recipes = get_recipes_by_category(category, recipes)
        lines = [f"[{title} - {category}]\n"]

        for recipe in cat_recipes:
            name = recipe["name"]
            lines.append(f"[url=@proc:recipe:{recipe['unique_id']}]{name}[/url]")

        lines.append("")
        lines.append("[url=@proc:back]◀ 뒤로[/url]")
        return "\n".join(lines)

    def build_confirm_menu(recipe):
        """제작 확인 메뉴 생성"""
        can_craft, missing, have = check_materials(player_id, recipe)

        lines = [f"[{recipe['name']}]\n"]

        # 재료 표시
        lines.append("필요한 재료:")
        for mat_uid, required in recipe["materials"].items():
            mat_name = get_material_name(mat_uid)
            owned = have.get(mat_uid, 0)

            if owned >= required:
                lines.append(f"  {mat_name}: {owned}/{required} [color=lime]✓[/color]")
            else:
                lines.append(f"  {mat_name}: {owned}/{required} [color=red]✗[/color]")

        lines.append("")

        # 결과물 표시
        result_count = recipe.get("result_count", 1)
        if result_count > 1:
            lines.append(f"결과: {recipe['name']} x{result_count}")
        else:
            lines.append(f"결과: {recipe['name']}")

        lines.append(f"소요 시간: {recipe['craft_time']}분")
        lines.append("")

        if can_craft:
            lines.append("[url=@proc:craft]제작하기[/url]")
        else:
            lines.append("[color=gray]재료가 부족합니다[/color]")

        lines.append("[url=@proc:back]◀ 뒤로[/url]")
        return "\n".join(lines)

    def handle_action(action):
        """proc 콜백"""
        if action == "init":
            return None

        if action == "back":
            if state["recipe"]:
                state["recipe"] = None
                return build_recipe_menu(state["category"])
            elif state["category"]:
                state["category"] = None
                return build_category_menu()
            else:
                state["done"] = True
                return True  # 다이얼로그 종료

        if action.startswith("cat:"):
            category = action[4:]
            state["category"] = category
            return build_recipe_menu(category)

        if action.startswith("recipe:"):
            unique_id = action[7:]
            recipe = get_recipe(unique_id, recipes)
            if recipe:
                state["recipe"] = recipe
                return build_confirm_menu(recipe)
            return None

        if action == "craft":
            state["done"] = True
            return True  # 다이얼로그 종료 후 제작 진행

        return None

    # 메뉴 표시
    result = yield morld.dialog(
        build_category_menu(),
        autofill="off",
        proc=handle_action,
        result=state
    )

    # 제작 실행
    if state.get("recipe") and result != "back":
        recipe = state["recipe"]
        can_craft, _, _ = check_materials(player_id, recipe)
        if can_craft:
            yield from craft_item(player_id, recipe)


# ========================================
# 스크립트 등록
# ========================================

@morld.register_script
def craft(context_unit_id):
    """제작 메뉴 열기 스크립트"""
    yield from open_craft_menu()
