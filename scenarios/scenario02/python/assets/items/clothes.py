# assets/items/clothes.py - 의류 아이템
#
# 의류 슬롯 시스템:
# - 착용:상의 - 상의 (셔츠, 블라우스)
# - 착용:하의 - 하의 (바지, 치마)
# - 착용:외투 - 외투 (코트, 자켓) - 상의/하의 위에 중복 가능
# - 일체형 드레스: 착용:상의 + 착용:하의 둘 다 가짐
#
# 분위기 시스템 (equip_props):
# - 분위기:깔끔함 - 깨끗하고 정돈된 느낌
# - 분위기:단정함 - 반듯하고 예의바른 느낌
# - 분위기:활동적 - 움직임이 편한 느낌
# - 분위기:우아함 - 고급스럽고 세련된 느낌
# - 분위기:더러움 - 지저분한 느낌
# - 분위기:냄새남 - 악취가 나는 느낌
# - 분위기:따뜻함 - 포근하고 따뜻한 느낌
#
# 액션:
# - equip@inventory: 입기/벗기 (기존 equip 핸들러 사용, 라벨은 슬롯 타입으로 자동 결정)
#
# 사용법:
#   from assets.items.clothes import Shirt, Pants
#   shirt = Shirt()
#   shirt.instantiate(item_id)

import morld
from assets.base import Item
from assets.registry import register_item


# ========================================
# 기본 의류 클래스
# ========================================

class Clothing(Item):
    """의류 기본 클래스"""
    category = "clothing"
    passive_props = {}
    equip_props = {}  # 착용:상의, 착용:하의, 착용:외투 등
    action_props = {"put": 1}
    value = 10
    # 기본 액션: 입기/벗기 (equip 핸들러 재사용, 라벨은 C#에서 슬롯 타입으로 결정)
    actions = [
        "take@container",
        "equip@inventory",
        "call:look:살펴보기@inventory"
    ]

    def look(self):
        """의류 살펴보기 - 서브클래스에서 오버라이드"""
        yield morld.dialog(f"{self.name}이다.")


# ========================================
# 누더기 (챕터 0 전용)
# ========================================

@register_item
class RaggedClothes(Clothing):
    """
    누더기 옷 - 챕터 0에서 플레이어가 입고 시작

    일체형 (상의+하의)
    """
    unique_id = "ragged_clothes"
    name = "누더기"
    action_props = {} # 못버림
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,  # 일체형
        "분위기:더러움": 1, "분위기:냄새남": 1
    }
    value = 1
    def look(self):
        yield morld.dialog([
            "낡고 해진 옷이다.",
            "여기저기 구멍이 나 있다."
        ])


# ========================================
# 일반 상의
# ========================================

@register_item
class SimpleShirt(Clothing):
    """단순한 셔츠"""
    unique_id = "simple_shirt"
    name = "셔츠"
    equip_props = {"착용:상의": 1, "분위기:깔끔함": 1}
    value = 15

    def look(self):
        yield morld.dialog("평범한 셔츠다.")


@register_item
class LinenShirt(Clothing):
    """린넨 셔츠"""
    unique_id = "linen_shirt"
    name = "린넨 셔츠"
    equip_props = {"착용:상의": 1, "분위기:깔끔함": 1, "분위기:활동적": 1}
    value = 20

    def look(self):
        yield morld.dialog("시원한 린넨 소재의 셔츠다.")


@register_item
class Blouse(Clothing):
    """블라우스 (여성용)"""
    unique_id = "blouse"
    name = "블라우스"
    equip_props = {"착용:상의": 1, "분위기:단정함": 1, "분위기:우아함": 1}
    value = 25

    def look(self):
        yield morld.dialog("깔끔한 블라우스다.")


@register_item
class WhiteBlouse(Clothing):
    """흰 블라우스"""
    unique_id = "white_blouse"
    name = "흰 블라우스"
    equip_props = {"착용:상의": 1, "분위기:깔끔함": 1, "분위기:단정함": 1}
    value = 25

    def look(self):
        yield morld.dialog("깨끗한 흰 블라우스다.")


# ========================================
# 일반 하의
# ========================================

@register_item
class SimplePants(Clothing):
    """단순한 바지"""
    unique_id = "simple_pants"
    name = "바지"
    equip_props = {"착용:하의": 1, "분위기:깔끔함": 1}
    value = 15

    def look(self):
        yield morld.dialog("평범한 바지다.")


@register_item
class LinenPants(Clothing):
    """린넨 바지"""
    unique_id = "linen_pants"
    name = "린넨 바지"
    equip_props = {"착용:하의": 1, "분위기:깔끔함": 1, "분위기:활동적": 1}
    value = 20

    def look(self):
        yield morld.dialog("시원한 린넨 소재의 바지다.")


@register_item
class LongSkirt(Clothing):
    """긴 치마"""
    unique_id = "long_skirt"
    name = "긴 치마"
    equip_props = {"착용:하의": 1, "분위기:단정함": 1, "분위기:우아함": 1}
    value = 20

    def look(self):
        yield morld.dialog("발목까지 오는 긴 치마다.")


@register_item
class Shorts(Clothing):
    """반바지"""
    unique_id = "shorts"
    name = "반바지"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1}
    value = 12

    def look(self):
        yield morld.dialog("활동하기 편한 반바지다.")


# ========================================
# 일체형 의류 (드레스)
# ========================================

@register_item
class Sundress(Clothing):
    """선드레스 (일체형)"""
    unique_id = "sundress"
    name = "선드레스"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,  # 일체형
        "분위기:깔끔함": 1, "분위기:활동적": 1
    }
    value = 35

    def look(self):
        yield morld.dialog("가벼운 여름용 원피스다.")


@register_item
class MaidDress(Clothing):
    """메이드복 (일체형)"""
    unique_id = "maid_dress"
    name = "메이드복"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,  # 일체형
        "분위기:단정함": 1, "분위기:깔끔함": 1
    }
    value = 40

    def look(self):
        yield morld.dialog([
            "깔끔한 메이드복이다.",
            "흰 앞치마가 달려 있다."
        ])


@register_item
class WorkDress(Clothing):
    """작업복 원피스"""
    unique_id = "work_dress"
    name = "작업복"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:활동적": 1
    }
    value = 30

    def look(self):
        yield morld.dialog("튼튼한 작업용 원피스다.")


# ========================================
# 외투 (상의/하의 위에 중복 착용 가능)
# ========================================

@register_item
class LightJacket(Clothing):
    """가벼운 재킷"""
    unique_id = "light_jacket"
    name = "재킷"
    equip_props = {"착용:외투": 1, "분위기:깔끔함": 1}
    value = 30

    def look(self):
        yield morld.dialog("가벼운 재킷이다.")


@register_item
class HuntingVest(Clothing):
    """사냥용 조끼"""
    unique_id = "hunting_vest"
    name = "사냥용 조끼"
    equip_props = {"착용:외투": 1, "수납": 2, "분위기:활동적": 1}  # 추가 수납 공간
    value = 35

    def look(self):
        yield morld.dialog([
            "튼튼한 사냥용 조끼다.",
            "여러 주머니가 달려 있다."
        ])


@register_item
class Apron(Clothing):
    """앞치마"""
    unique_id = "apron"
    name = "앞치마"
    equip_props = {"착용:외투": 1, "분위기:단정함": 1}
    value = 10

    def look(self):
        yield morld.dialog("요리할 때 입는 앞치마다.")


@register_item
class WarmCoat(Clothing):
    """따뜻한 코트"""
    unique_id = "warm_coat"
    name = "코트"
    equip_props = {"착용:외투": 1, "보온": 2, "분위기:따뜻함": 1, "분위기:우아함": 1}
    value = 50

    def look(self):
        yield morld.dialog("따뜻한 겨울용 코트다.")


# ========================================
# NPC 전용 의류 (소유자 지정)
# ========================================

@register_item
class SeraHuntingOutfit(Clothing):
    """세라의 사냥복"""
    unique_id = "sera_hunting_outfit"
    name = "사냥복"
    owner = "sera"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:활동적": 1, "분위기:단정함": 1
    }
    value = 45

    def look(self):
        yield morld.dialog([
            "세라의 사냥복이다.",
            "움직이기 편하게 만들어졌다."
        ])


@register_item
class MilaApron(Clothing):
    """밀라의 앞치마"""
    unique_id = "mila_apron"
    name = "밀라의 앞치마"
    owner = "mila"
    equip_props = {"착용:외투": 1, "분위기:단정함": 1, "분위기:따뜻함": 1}
    value = 15

    def look(self):
        yield morld.dialog([
            "밀라가 항상 두르는 앞치마다.",
            "군데군데 얼룩이 있다."
        ])
