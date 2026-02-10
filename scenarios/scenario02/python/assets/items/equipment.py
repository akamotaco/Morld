# assets/items/equipment.py - 장비 아이템
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명@context"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
#
# 사용법:
#   from assets.items.equipment import OldKnife, LeatherPouch
#   knife = OldKnife()
#   knife.instantiate(item_id)

import morld
import ui
from assets.base import Item
from assets.registry import register_item


# ========================================
# 날붙이 (Blade) 기본 클래스
# ========================================

class Blade(Item):
    """
    날붙이 기본 클래스

    소지 시 can:skin(박피) 능력 부여
    - 토끼 사체 등에서 가죽/고기 획득 가능
    - 장착 없이도 박피 가능 (도구 선택 UI 표시)
    """
    passive_props = {"can:skin": 1}
    equip_props = {"장착:손": 1}
    skin_time = 15  # 박피 소요 시간 (분) - 서브클래스에서 오버라이드
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """날붙이 살펴보기"""
        yield ui.dialog("날카로운 날이 달린 도구다.")


# ========================================
# 사냥꾼 장비
# ========================================

@register_item
class OldKnife(Blade):
    """낡은 칼 - 플레이어 초기 장비 (사냥꾼 선택 시)"""
    unique_id = "old_knife"
    name = "낡은 칼"
    passive_props = {"can:skin": 1}
    equip_props = {"공격": 2, "사냥": 1, "장착:손": 1}
    skin_time = 20  # 낡은 칼은 박피에 20분 소요
    value = 20

    def look(self):
        """낡은 칼 살펴보기"""
        yield ui.dialog([
            "오래되어 녹이 슨 칼이다.",
            "그래도 날은 아직 쓸만하다."
        ])


@register_item
class RusticDagger(Blade):
    """투박한 단검 - 세라 소유, 창고 도구함에 배치"""
    unique_id = "rustic_dagger"
    name = "투박한 단검"
    owner = "sera"
    passive_props = {"can:skin": 1}
    equip_props = {"공격": 3, "사냥": 2, "장착:손": 1}
    skin_time = 15  # 투박한 단검은 박피에 15분 소요
    value = 30

    def look(self):
        """투박한 단검 살펴보기"""
        yield ui.dialog([
            "투박하지만 튼튼한 단검이다.",
            "세라가 사냥할 때 쓰는 것 같다."
        ])


@register_item
class LeatherPouch(Item):
    unique_id = "leather_pouch"
    name = "가죽 주머니"
    passive_props = {"수납": 5}
    equip_props = {}
    value = 10
    actions = ["take@container"]


# ========================================
# 학자 장비
# ========================================

@register_item
class WritingTool(Item):
    unique_id = "writing_tool"
    name = "필기구"
    passive_props = {}
    equip_props = {"지능": 1}
    value = 5
    actions = ["take@container"]


@register_item
class OldBook(Item):
    unique_id = "old_book"
    name = "낡은 책"
    passive_props = {"지식": 1}
    equip_props = {}
    value = 15
    actions = ["take@container", "call:read:읽기@inventory"]

    def read(self):
        """낡은 책 읽기"""
        yield ui.dialog([
            "오래된 책을 펼쳐본다.",
            "손때 묻은 페이지에는 이 저택의 역사가 적혀 있다.",
            "흥미로운 내용이지만, 대부분의 글자는 바래져 읽기 어렵다."
        ], autofill="book")
        morld.advance_time_des(10 * 60_000)


# ========================================
# 장인 장비
# ========================================

@register_item
class PortableCraftingKit(Item):
    """
    휴대용 제작 도구 (소형)

    소지 시 어디서나 간단한 아이템 제작 가능
    - 토끼 덫 등
    """
    unique_id = "small_toolbox"  # 호환성을 위해 unique_id 유지
    name = "휴대용 제작 도구"
    passive_props = {"수리": 1}
    equip_props = {"손재주": 2}
    value = 25
    actions = ["take@container", "call:craft:제작@inventory", "call:look:살펴보기@inventory"]

    def craft(self):
        """
        휴대용 제작 메뉴 열기 (다이얼로그 + 토글)

        variants가 있는 레시피는 토글로 재료 옵션 표시
        """
        from crafting_recipes import get_portable_recipes
        from crafting import check_materials, get_material_name, craft_item

        player_id = morld.get_player_id()
        portable_recipes = get_portable_recipes()

        # 상태 관리
        state = {"selected_variant": None, "recipe": None}

        def build_menu():
            """제작 메뉴 생성"""
            lines = ["[휴대 제작]", ""]

            for recipe in portable_recipes:
                name = recipe["name"]

                if "variants" in recipe:
                    # variants가 있으면 토글 형태
                    lines.append(f"▶ {name}")
                    for i, variant in enumerate(recipe["variants"]):
                        materials = variant["materials"]
                        craft_time = variant["craft_time"]

                        # 재료 보유 확인
                        temp_recipe = {"materials": materials}
                        can_craft, missing, have = check_materials(player_id, temp_recipe)

                        # 재료 텍스트 생성
                        mat_parts = []
                        for mat_uid, required in materials.items():
                            mat_name = get_material_name(mat_uid)
                            owned = have.get(mat_uid, 0)
                            if owned >= required:
                                mat_parts.append(f"{mat_name} {owned}/{required}")
                            else:
                                mat_parts.append(f"{mat_name} [color=red]{owned}/{required}[/color]")
                        mat_text = ", ".join(mat_parts)

                        if can_craft:
                            lines.append(f"    [url=@proc:{recipe['unique_id']}:{i}]{mat_text}[/url] [color=gray]({craft_time}분)[/color]")
                        else:
                            lines.append(f"    [color=gray]{mat_text} ({craft_time}분)[/color]")
                else:
                    # 단일 레시피
                    can_craft, missing, have = check_materials(player_id, recipe)
                    craft_time = recipe.get("craft_time", 10)

                    if can_craft:
                        lines.append(f"  [url=@proc:{recipe['unique_id']}]{name}[/url] [color=gray]({craft_time}분)[/color]")
                    else:
                        lines.append(f"  [color=gray]{name} ({craft_time}분)[/color]")

            lines.append("")
            lines.append("[url=@ret:cancel]돌아가기[/url]")
            return "\n".join(lines)

        def on_select(action):
            if action == "init":
                return None

            # 선택 파싱: "unique_id:variant_index" 또는 "unique_id"
            parts = action.split(":")
            unique_id = parts[0]

            for recipe in portable_recipes:
                if recipe["unique_id"] == unique_id:
                    state["recipe"] = recipe

                    if "variants" in recipe and len(parts) > 1:
                        variant_idx = int(parts[1])
                        state["selected_variant"] = recipe["variants"][variant_idx]
                    else:
                        state["selected_variant"] = None

                    return True  # 다이얼로그 종료

            return None

        result = yield ui.dialog(build_menu(), autofill="off", proc=on_select, result=state)

        # 제작 실행
        if result == "cancel" or not state["recipe"]:
            return

        recipe = state["recipe"]
        variant = state["selected_variant"]

        # variant가 있으면 재료와 시간을 오버라이드
        if variant:
            craft_recipe = {
                "unique_id": recipe["unique_id"],
                "name": recipe["name"],
                "materials": variant["materials"],
                "craft_time": variant["craft_time"],
                "result_count": recipe.get("result_count", 1),
            }
        else:
            craft_recipe = recipe

        # 최종 재료 확인
        can_craft, _, _ = check_materials(player_id, craft_recipe)
        if can_craft:
            yield from craft_item(player_id, craft_recipe)

    def look(self):
        """도구 살펴보기"""
        yield ui.dialog([
            "간단한 제작 도구가 담긴 작은 가방이다.",
            "이것만 있으면 어디서든 간단한 도구를 만들 수 있다."
        ])


# 레거시 호환성을 위한 별칭
SmallToolbox = PortableCraftingKit


# ========================================
# 탐색 도구
# ========================================

@register_item
class Compass(Item):
    """
    나침반 - 소지 시 전체 지도 기능 활성화

    소지만 해도 can:map 능력 부여
    - Location focus에서 '지도' 액션 사용 가능
    - 모든 region의 장소들을 볼 수 있음 (지역 제한 없음)
    - 장거리 이동(path planning) 가능
    """
    unique_id = "compass"
    name = "나침반"
    passive_props = {"can:map": 1}
    value = 80
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """나침반 살펴보기"""
        text = "\n".join([
            "정교하게 만들어진 나침반이다.",
            "이것만 있으면 어디서든 방향을 잡을 수 있다.",
            "지도 기능을 사용할 수 있다.",
        ])
        yield ui.dialog(f"[!]{text}[/!]")


# 레거시 호환성을 위한 별칭
Map = Compass


@register_item
class MansionMap(Item):
    """
    저택 지도 - 저택 지역(Region 0)에서만 사용 가능

    소지 시 저택 지역에서 can:map:mansion 능력 부여
    - 저택 Region에서만 지도 기능 활성화
    """
    unique_id = "mansion_map"
    name = "저택 지도"
    passive_props = {"can:map:mansion": 1}
    value = 30
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """저택 지도 살펴보기"""
        text = "\n".join([
            "저택과 그 주변을 그린 지도다.",
            "저택 내부 구조가 상세하게 표시되어 있다.",
        ])
        yield ui.dialog(f"[!]{text}[/!]")


@register_item
class ForestMap(Item):
    """
    숲속 지도 - 숲 지역(Region 1)에서만 사용 가능

    소지 시 숲 지역에서 can:map:forest 능력 부여
    - 숲 Region에서만 지도 기능 활성화
    """
    unique_id = "forest_map"
    name = "숲속 지도"
    passive_props = {"can:map:forest": 1}
    value = 30
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """숲속 지도 살펴보기"""
        text = "\n".join([
            "숲의 길과 주요 장소를 그린 지도다.",
            "오두막, 늑대굴 등의 위치가 표시되어 있다.",
        ])
        yield ui.dialog(f"[!]{text}[/!]")


@register_item
class CityMap(Item):
    """
    도시 지도 - 도시 지역(Region 2)에서만 사용 가능

    소지 시 도시 지역에서 can:map:city 능력 부여
    - 도시 Region에서만 지도 기능 활성화
    """
    unique_id = "city_map"
    name = "도시 지도"
    passive_props = {"can:map:city": 1}
    value = 30
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """도시 지도 살펴보기"""
        text = "\n".join([
            "황폐화된 도시의 거리를 그린 지도다.",
            "편의점, 약국 등의 위치가 표시되어 있다.",
        ])
        yield ui.dialog(f"[!]{text}[/!]")


# ========================================
# 무기
# ========================================

@register_item
class WoodenSword(Item):
    """목검 - 나무판으로 제작하는 기본 무기"""
    unique_id = "wooden_sword"
    name = "목검"
    passive_props = {}
    equip_props = {"공격": 3, "장착:손": 1}
    value = 15
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """목검 살펴보기"""
        yield ui.dialog([
            "나무를 깎아 만든 목검이다.",
            "진짜 검보다는 약하지만, 없는 것보다는 낫다."
        ])


# ========================================
# 방수 장비
# ========================================

@register_item
class Umbrella(Item):
    """우산 — 장착 시 방수 효과"""
    unique_id = "umbrella"
    name = "우산"
    equip_props = {"방수": 1, "장착:손": 1}
    value = 15
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """우산 살펴보기"""
        yield ui.dialog("비를 막아주는 우산이다.")
