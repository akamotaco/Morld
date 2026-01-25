# crafting.py - 크래프팅 시스템
#
# 제작 UI 및 제작 실행 로직
# 레시피 데이터는 crafting_recipes.py에서 관리
#
# 사용법:
#   from crafting import open_craft_menu, craft_item
#   yield from open_craft_menu(get_portable_recipes(), "휴대 제작")

import morld
import ui
from assets.registry import get_item_class, get_or_create_item_id
from crafting_recipes import (
    CRAFTING_RECIPES,
    get_recipe,
    get_portable_recipes,
    get_workbench_recipes,
    get_recipes_by_category,
    get_available_categories,
)

# 레거시 호환성을 위한 export
PORTABLE_RECIPES = get_portable_recipes()
WORKBENCH_RECIPES = get_workbench_recipes()
RECIPES = list({"unique_id": uid, **r} for uid, r in CRAFTING_RECIPES.items())
PLAYER_RECIPES = PORTABLE_RECIPES


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

    # 인벤토리를 unique_id 기준으로 변환 (같은 unique_id 아이템 합산)
    inv_by_unique = {}
    if inventory:
        for item_id, count in inventory.items():
            item_info = morld.get_item_info(item_id)
            if item_info:
                unique_id = item_info.get("unique_id")
                if unique_id:
                    if isinstance(count, str):
                        count = int(count)
                    inv_by_unique[unique_id] = inv_by_unique.get(unique_id, 0) + count

    for mat_unique_id, required in recipe["materials"].items():
        # unique_id 기준으로 보유량 확인
        owned = inv_by_unique.get(mat_unique_id, 0)

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
    # 재료 소모 (unique_id 기준으로 인벤토리에서 찾아서 소모)
    inventory = morld.get_unit_inventory(player_id)
    for mat_unique_id, required in recipe["materials"].items():
        remaining = required
        if inventory:
            for item_id, count in list(inventory.items()):
                if remaining <= 0:
                    break
                item_info = morld.get_item_info(item_id)
                if item_info and item_info.get("unique_id") == mat_unique_id:
                    if isinstance(count, str):
                        count = int(count)
                    to_consume = min(count, remaining)
                    morld.lost_item(player_id, int(item_id), to_consume)
                    remaining -= to_consume

    # 시간 경과
    morld.advance_time(recipe["craft_time"])

    # 결과물 생성 (registry를 통해 싱글톤 ID 조회/생성)
    # result_id가 있으면 그것을 사용, 없으면 unique_id를 사용
    result_unique_id = recipe.get("result_id", recipe["unique_id"])
    result_id = get_or_create_item_id(result_unique_id)

    if result_id is None:
        yield ui.dialog("제작에 실패했다...")
        return

    # 결과물 지급
    result_count = recipe.get("result_count", 1)
    morld.give_item(player_id, result_id, result_count)

    # 완료 메시지
    result_name = recipe["name"]
    if result_count > 1:
        yield ui.dialog(f"{result_name} {result_count}개를 만들었다!")
    else:
        yield ui.dialog(f"{result_name}을(를) 만들었다!")


# ========================================
# 크래프팅 UI (카테고리 기반)
# ========================================

def open_craft_menu(recipe_source: list = None, title: str = "제작", preview: bool = True):
    """
    제작 메뉴 열기 (Generator) - 카테고리 기반 UI

    Args:
        recipe_source: 사용할 레시피 목록 (None이면 PLAYER_RECIPES 사용)
        title: 메뉴 제목 (기본: "제작")
        preview: True면 재료 부족해도 grey out으로 표시, False면 제작 가능한 것만 표시

    UI 흐름:
    1. 카테고리 선택
    2. 레시피 선택
    3. 재료 확인 + 제작 여부
    4. 제작 실행

    사용법:
        yield from open_craft_menu()  # 플레이어 제작
        yield from open_craft_menu(WORKBENCH_RECIPES, "제작대")  # 제작대
        yield from open_craft_menu(WORKBENCH_RECIPES, "제작대", preview=False)  # 제작 가능만 표시
    """
    recipes = recipe_source if recipe_source is not None else PLAYER_RECIPES

    player_id = morld.get_player_id()
    categories = get_available_categories(recipes)

    print(f"[crafting] recipes count: {len(recipes)}, categories: {categories}")
    if recipes:
        print(f"[crafting] first recipe: {recipes[0]}")

    if not categories:
        yield ui.dialog("제작할 수 있는 것이 없다.")
        return

    # 상태 관리
    state = {
        "category": None,
        "recipe": None,
        "done": False,
    }

    def _format_materials_short(materials):
        """재료를 짧은 텍스트로 포맷"""
        parts = []
        for mat_uid, required in materials.items():
            mat_name = get_material_name(mat_uid)
            parts.append(f"{mat_name} {required}개")
        return ", ".join(parts)

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
        """레시피 목록 메뉴 생성 - 재료 부족해도 표시 (grey out)"""
        cat_recipes = get_recipes_by_category(category, recipes)
        lines = [f"[{title} - {category}]\n"]

        for recipe in cat_recipes:
            name = recipe["name"]
            craft_time = recipe.get("craft_time", 10)
            can_craft, _, _ = check_materials(player_id, recipe)

            if can_craft:
                lines.append(f"[url=@proc:recipe:{recipe['unique_id']}]{name}[/url] [color=gray]({craft_time}분)[/color]")
            elif preview:
                # preview=True: 재료 부족해도 grey out으로 표시
                mat_text = _format_materials_short(recipe["materials"])
                lines.append(f"[color=gray]{name}[/color] [color=#666666]({mat_text})[/color]")
            # preview=False: 제작 불가능하면 표시하지 않음

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
            recipe = get_recipe(unique_id)
            if recipe:
                state["recipe"] = recipe
                return build_confirm_menu(recipe)
            return None

        if action == "craft":
            state["done"] = True
            return True  # 다이얼로그 종료 후 제작 진행

        return None

    # 메뉴 표시
    result = yield ui.dialog(
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
