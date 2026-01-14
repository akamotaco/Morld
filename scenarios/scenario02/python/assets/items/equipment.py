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
from assets.base import Item
from assets.registry import register_item


# ========================================
# 날붙이 (Blade) 기본 클래스
# ========================================

class Blade(Item):
    """
    날붙이 기본 클래스

    장착 시 can:skin(박피) 능력 부여
    - 토끼 사체 등에서 가죽/고기 획득 가능
    """
    passive_props = {}
    equip_props = {"장착:손": 1, "can:skin": 1}
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """날붙이 살펴보기"""
        yield morld.dialog("날카로운 날이 달린 도구다.")


# ========================================
# 사냥꾼 장비
# ========================================

@register_item
class OldKnife(Blade):
    """낡은 칼 - 플레이어 초기 장비 (사냥꾼 선택 시)"""
    unique_id = "old_knife"
    name = "낡은 칼"
    passive_props = {}
    equip_props = {"공격": 2, "사냥": 1, "장착:손": 1, "can:skin": 1}
    value = 20

    def look(self):
        """낡은 칼 살펴보기"""
        yield morld.dialog([
            "오래되어 녹이 슨 칼이다.",
            "그래도 날은 아직 쓸만하다."
        ])


@register_item
class RusticDagger(Blade):
    """투박한 단검 - 세라 소유, 창고 도구함에 배치"""
    unique_id = "rustic_dagger"
    name = "투박한 단검"
    owner = "sera"
    passive_props = {}
    equip_props = {"공격": 3, "사냥": 2, "장착:손": 1, "can:skin": 1}
    value = 30

    def look(self):
        """투박한 단검 살펴보기"""
        yield morld.dialog([
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
        yield morld.dialog([
            "오래된 책을 펼쳐본다.",
            "손때 묻은 페이지에는 이 저택의 역사가 적혀 있다.",
            "흥미로운 내용이지만, 대부분의 글자는 바래져 읽기 어렵다."
        ], autofill="book")
        morld.advance_time(10)


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
        """휴대용 제작 메뉴 열기"""
        from crafting import open_craft_menu, PORTABLE_RECIPES
        yield from open_craft_menu(PORTABLE_RECIPES, "휴대 제작")

    def look(self):
        """도구 살펴보기"""
        yield morld.dialog([
            "간단한 제작 도구가 담긴 작은 가방이다.",
            "이것만 있으면 어디서든 간단한 도구를 만들 수 있다."
        ])


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
        yield morld.dialog([
            "나무를 깎아 만든 목검이다.",
            "진짜 검보다는 약하지만, 없는 것보다는 낫다."
        ])
