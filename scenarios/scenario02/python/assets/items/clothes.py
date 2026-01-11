# assets/items/clothes.py - 의류 아이템
#
# 의류 슬롯 시스템:
# - 착용:상의 - 상의 (셔츠, 블라우스)
# - 착용:하의 - 하의 (바지, 치마)
# - 착용:외투 - 외투 (코트, 자켓) - 상의/하의 위에 중복 가능
# - 착용:속옷상의 - 브라 등
# - 착용:속옷하의 - 팬티 등
# - 착용:양말 - 양말, 스타킹 등
# - 착용:신발 - 신발류
# - 착용:모자 - 모자류
# - 착용:안경 - 안경, 선글라스 등
# - 착용:망토 - 망토, 케이프 등
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
# - 분위기:섹시함 - 성적 매력이 있는 느낌
# - 분위기:귀여움 - 사랑스러운 느낌
# - 분위기:신비로움 - 신비로운 느낌
# - 분위기:멋짐 - 멋진 느낌
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


# ========================================
# 속옷 - 상의 (브라)
# ========================================

@register_item
class SimpleBra(Clothing):
    """단순한 브라"""
    unique_id = "simple_bra"
    name = "브라"
    equip_props = {"착용:속옷상의": 1}
    value = 8

    def look(self):
        yield morld.dialog("평범한 브라다.")


@register_item
class LaceBra(Clothing):
    """레이스 브라"""
    unique_id = "lace_bra"
    name = "레이스 브라"
    equip_props = {"착용:속옷상의": 1, "분위기:섹시함": 1, "분위기:우아함": 1}
    value = 20

    def look(self):
        yield morld.dialog("섬세한 레이스 장식의 브라다.")


@register_item
class SportsBra(Clothing):
    """스포츠 브라"""
    unique_id = "sports_bra"
    name = "스포츠 브라"
    equip_props = {"착용:속옷상의": 1, "분위기:활동적": 1}
    value = 15

    def look(self):
        yield morld.dialog("운동할 때 입는 스포츠 브라다.")


@register_item
class CuteBra(Clothing):
    """귀여운 브라"""
    unique_id = "cute_bra"
    name = "귀여운 브라"
    equip_props = {"착용:속옷상의": 1, "분위기:귀여움": 1}
    value = 15

    def look(self):
        yield morld.dialog("리본 장식이 달린 귀여운 브라다.")


# ========================================
# 속옷 - 하의 (팬티)
# ========================================

@register_item
class SimplePanties(Clothing):
    """단순한 팬티"""
    unique_id = "simple_panties"
    name = "팬티"
    equip_props = {"착용:속옷하의": 1}
    value = 5

    def look(self):
        yield morld.dialog("평범한 팬티다.")


@register_item
class LacePanties(Clothing):
    """레이스 팬티"""
    unique_id = "lace_panties"
    name = "레이스 팬티"
    equip_props = {"착용:속옷하의": 1, "분위기:섹시함": 1, "분위기:우아함": 1}
    value = 18

    def look(self):
        yield morld.dialog("섬세한 레이스 장식의 팬티다.")


@register_item
class CottonPanties(Clothing):
    """면 팬티"""
    unique_id = "cotton_panties"
    name = "면 팬티"
    equip_props = {"착용:속옷하의": 1, "분위기:깔끔함": 1}
    value = 8

    def look(self):
        yield morld.dialog("편안한 면 소재의 팬티다.")


@register_item
class CutePanties(Clothing):
    """귀여운 팬티"""
    unique_id = "cute_panties"
    name = "귀여운 팬티"
    equip_props = {"착용:속옷하의": 1, "분위기:귀여움": 1}
    value = 12

    def look(self):
        yield morld.dialog("리본 장식이 달린 귀여운 팬티다.")


# ========================================
# 양말류
# ========================================

@register_item
class SimpleSocks(Clothing):
    """단순한 양말"""
    unique_id = "simple_socks"
    name = "양말"
    equip_props = {"착용:양말": 1, "분위기:깔끔함": 1}
    value = 3

    def look(self):
        yield morld.dialog("평범한 양말이다.")


@register_item
class WoolSocks(Clothing):
    """울 양말"""
    unique_id = "wool_socks"
    name = "울 양말"
    equip_props = {"착용:양말": 1, "분위기:따뜻함": 1}
    value = 8

    def look(self):
        yield morld.dialog("따뜻한 울 소재의 양말이다.")


@register_item
class Stockings(Clothing):
    """스타킹"""
    unique_id = "stockings"
    name = "스타킹"
    equip_props = {"착용:양말": 1, "분위기:우아함": 1}
    value = 12

    def look(self):
        yield morld.dialog("얇은 스타킹이다.")


@register_item
class BlackStockings(Clothing):
    """검은 스타킹"""
    unique_id = "black_stockings"
    name = "검은 스타킹"
    equip_props = {"착용:양말": 1, "분위기:우아함": 1, "분위기:섹시함": 1}
    value = 15

    def look(self):
        yield morld.dialog("검은색 스타킹이다.")


@register_item
class ThighHighSocks(Clothing):
    """사이하이삭스"""
    unique_id = "thigh_high_socks"
    name = "사이하이삭스"
    equip_props = {"착용:양말": 1, "분위기:귀여움": 1}
    value = 15

    def look(self):
        yield morld.dialog("허벅지까지 오는 긴 양말이다.")


@register_item
class WhiteThighHighSocks(Clothing):
    """흰 사이하이삭스"""
    unique_id = "white_thigh_high_socks"
    name = "흰 사이하이삭스"
    equip_props = {"착용:양말": 1, "분위기:귀여움": 1, "분위기:깔끔함": 1}
    value = 18

    def look(self):
        yield morld.dialog("흰색 사이하이삭스다. 청순해 보인다.")


@register_item
class StripedThighHighSocks(Clothing):
    """줄무늬 사이하이삭스"""
    unique_id = "striped_thigh_high_socks"
    name = "줄무늬 사이하이삭스"
    equip_props = {"착용:양말": 1, "분위기:귀여움": 1, "분위기:활동적": 1}
    value = 18

    def look(self):
        yield morld.dialog("줄무늬 패턴의 사이하이삭스다.")


# ========================================
# 신발류
# ========================================

@register_item
class SimpleShoes(Clothing):
    """단순한 신발"""
    unique_id = "simple_shoes"
    name = "신발"
    equip_props = {"착용:신발": 1, "분위기:깔끔함": 1}
    value = 20

    def look(self):
        yield morld.dialog("평범한 신발이다.")


@register_item
class LeatherBoots(Clothing):
    """가죽 부츠"""
    unique_id = "leather_boots"
    name = "가죽 부츠"
    equip_props = {"착용:신발": 1, "분위기:활동적": 1, "분위기:멋짐": 1}
    value = 40

    def look(self):
        yield morld.dialog("튼튼한 가죽 부츠다.")


@register_item
class HighHeels(Clothing):
    """하이힐"""
    unique_id = "high_heels"
    name = "하이힐"
    equip_props = {"착용:신발": 1, "분위기:우아함": 1, "분위기:섹시함": 1}
    value = 35

    def look(self):
        yield morld.dialog("굽이 높은 하이힐이다.")


@register_item
class Sandals(Clothing):
    """샌들"""
    unique_id = "sandals"
    name = "샌들"
    equip_props = {"착용:신발": 1, "분위기:활동적": 1}
    value = 15

    def look(self):
        yield morld.dialog("시원한 샌들이다.")


@register_item
class Slippers(Clothing):
    """슬리퍼"""
    unique_id = "slippers"
    name = "슬리퍼"
    equip_props = {"착용:신발": 1}
    value = 8

    def look(self):
        yield morld.dialog("편안한 실내용 슬리퍼다.")


@register_item
class WarmBoots(Clothing):
    """방한 부츠"""
    unique_id = "warm_boots"
    name = "방한 부츠"
    equip_props = {"착용:신발": 1, "분위기:따뜻함": 1, "보온": 1}
    value = 45

    def look(self):
        yield morld.dialog("따뜻한 털이 안에 달린 부츠다.")


# ========================================
# 모자류
# ========================================

@register_item
class StrawHat(Clothing):
    """밀짚모자"""
    unique_id = "straw_hat"
    name = "밀짚모자"
    equip_props = {"착용:모자": 1, "분위기:활동적": 1}
    value = 10

    def look(self):
        yield morld.dialog("햇빛을 가려주는 밀짚모자다.")


@register_item
class Beret(Clothing):
    """베레모"""
    unique_id = "beret"
    name = "베레모"
    equip_props = {"착용:모자": 1, "분위기:우아함": 1, "분위기:멋짐": 1}
    value = 20

    def look(self):
        yield morld.dialog("세련된 베레모다.")


@register_item
class WoolHat(Clothing):
    """털모자"""
    unique_id = "wool_hat"
    name = "털모자"
    equip_props = {"착용:모자": 1, "분위기:따뜻함": 1, "분위기:귀여움": 1, "보온": 1}
    value = 15

    def look(self):
        yield morld.dialog("따뜻한 털모자다.")


@register_item
class Ribbon(Clothing):
    """리본"""
    unique_id = "ribbon"
    name = "리본"
    equip_props = {"착용:모자": 1, "분위기:귀여움": 1}
    value = 8

    def look(self):
        yield morld.dialog("머리에 다는 리본이다.")


@register_item
class HuntingCap(Clothing):
    """사냥 모자"""
    unique_id = "hunting_cap"
    name = "사냥 모자"
    equip_props = {"착용:모자": 1, "분위기:활동적": 1, "분위기:멋짐": 1}
    value = 25

    def look(self):
        yield morld.dialog("사냥꾼들이 쓰는 모자다.")


@register_item
class MaidHeadband(Clothing):
    """메이드 머리띠"""
    unique_id = "maid_headband"
    name = "메이드 머리띠"
    equip_props = {"착용:모자": 1, "분위기:단정함": 1, "분위기:귀여움": 1}
    value = 12

    def look(self):
        yield morld.dialog("메이드복에 어울리는 머리띠다.")


# ========================================
# 안경류
# ========================================

@register_item
class Glasses(Clothing):
    """안경"""
    unique_id = "glasses"
    name = "안경"
    equip_props = {"착용:안경": 1, "분위기:단정함": 1}
    value = 25

    def look(self):
        yield morld.dialog("평범한 안경이다.")


@register_item
class RoundGlasses(Clothing):
    """둥근 안경"""
    unique_id = "round_glasses"
    name = "둥근 안경"
    equip_props = {"착용:안경": 1, "분위기:단정함": 1, "분위기:귀여움": 1}
    value = 28

    def look(self):
        yield morld.dialog("둥글둥글한 프레임의 안경이다.")


@register_item
class Sunglasses(Clothing):
    """선글라스"""
    unique_id = "sunglasses"
    name = "선글라스"
    equip_props = {"착용:안경": 1, "분위기:멋짐": 1}
    value = 30

    def look(self):
        yield morld.dialog("햇빛을 막아주는 선글라스다.")


@register_item
class FashionSunglasses(Clothing):
    """패션 선글라스"""
    unique_id = "fashion_sunglasses"
    name = "패션 선글라스"
    equip_props = {"착용:안경": 1, "분위기:멋짐": 1, "분위기:섹시함": 1}
    value = 40

    def look(self):
        yield morld.dialog("세련된 디자인의 패션 선글라스다.")


@register_item
class Monocle(Clothing):
    """모노클"""
    unique_id = "monocle"
    name = "모노클"
    equip_props = {"착용:안경": 1, "분위기:우아함": 1, "분위기:신비로움": 1}
    value = 50

    def look(self):
        yield morld.dialog("한쪽 눈에 끼는 모노클이다. 귀족적인 느낌이 난다.")


# ========================================
# 망토류
# ========================================

@register_item
class SimpleCape(Clothing):
    """단순한 망토"""
    unique_id = "simple_cape"
    name = "망토"
    equip_props = {"착용:망토": 1, "분위기:신비로움": 1}
    value = 30

    def look(self):
        yield morld.dialog("평범한 망토다.")


@register_item
class HoodedCloak(Clothing):
    """후드 달린 망토"""
    unique_id = "hooded_cloak"
    name = "후드 망토"
    equip_props = {"착용:망토": 1, "분위기:신비로움": 1, "분위기:따뜻함": 1, "보온": 1}
    value = 45

    def look(self):
        yield morld.dialog("후드가 달린 망토다. 얼굴을 숨기기 좋다.")


@register_item
class VelvetCape(Clothing):
    """벨벳 망토"""
    unique_id = "velvet_cape"
    name = "벨벳 망토"
    equip_props = {"착용:망토": 1, "분위기:우아함": 1, "분위기:멋짐": 1}
    value = 60

    def look(self):
        yield morld.dialog("부드러운 벨벳 소재의 고급스러운 망토다.")


@register_item
class TravelCloak(Clothing):
    """여행용 망토"""
    unique_id = "travel_cloak"
    name = "여행용 망토"
    equip_props = {"착용:망토": 1, "분위기:활동적": 1, "분위기:따뜻함": 1}
    value = 35

    def look(self):
        yield morld.dialog("여행할 때 입기 좋은 튼튼한 망토다.")


# ========================================
# 추가 상의
# ========================================

@register_item
class TankTop(Clothing):
    """탱크탑"""
    unique_id = "tank_top"
    name = "탱크탑"
    equip_props = {"착용:상의": 1, "분위기:활동적": 1}
    value = 10

    def look(self):
        yield morld.dialog("민소매 탱크탑이다.")


@register_item
class Sweater(Clothing):
    """스웨터"""
    unique_id = "sweater"
    name = "스웨터"
    equip_props = {"착용:상의": 1, "분위기:따뜻함": 1, "분위기:귀여움": 1, "보온": 1}
    value = 30

    def look(self):
        yield morld.dialog("따뜻한 스웨터다.")


@register_item
class TurtleneckSweater(Clothing):
    """터틀넥 스웨터"""
    unique_id = "turtleneck_sweater"
    name = "터틀넥 스웨터"
    equip_props = {"착용:상의": 1, "분위기:따뜻함": 1, "분위기:단정함": 1, "보온": 2}
    value = 35

    def look(self):
        yield morld.dialog("목을 감싸는 터틀넥 스웨터다.")


@register_item
class CropTop(Clothing):
    """크롭탑"""
    unique_id = "crop_top"
    name = "크롭탑"
    equip_props = {"착용:상의": 1, "분위기:활동적": 1, "분위기:섹시함": 1}
    value = 18

    def look(self):
        yield morld.dialog("배가 드러나는 짧은 상의다.")


# ========================================
# 추가 하의
# ========================================

@register_item
class MiniSkirt(Clothing):
    """미니스커트"""
    unique_id = "mini_skirt"
    name = "미니스커트"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1, "분위기:섹시함": 1}
    value = 18

    def look(self):
        yield morld.dialog("짧은 미니스커트다.")


@register_item
class PleatedSkirt(Clothing):
    """플리츠 스커트"""
    unique_id = "pleated_skirt"
    name = "플리츠 스커트"
    equip_props = {"착용:하의": 1, "분위기:단정함": 1, "분위기:귀여움": 1}
    value = 22

    def look(self):
        yield morld.dialog("주름이 잡힌 플리츠 스커트다.")


@register_item
class HotPants(Clothing):
    """핫팬츠"""
    unique_id = "hot_pants"
    name = "핫팬츠"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1, "분위기:섹시함": 1}
    value = 15

    def look(self):
        yield morld.dialog("짧은 핫팬츠다.")


@register_item
class LeggingsClothing(Clothing):
    """레깅스"""
    unique_id = "leggings"
    name = "레깅스"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1}
    value = 18

    def look(self):
        yield morld.dialog("몸에 딱 맞는 레깅스다.")


# ========================================
# 추가 일체형 의류
# ========================================

@register_item
class EveningDress(Clothing):
    """이브닝 드레스"""
    unique_id = "evening_dress"
    name = "이브닝 드레스"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:우아함": 1, "분위기:섹시함": 1
    }
    value = 80

    def look(self):
        yield morld.dialog("파티에 입기 좋은 화려한 드레스다.")


@register_item
class NightGown(Clothing):
    """나이트가운"""
    unique_id = "night_gown"
    name = "나이트가운"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:우아함": 1, "분위기:섹시함": 1
    }
    value = 35

    def look(self):
        yield morld.dialog("잠옷으로 입는 나이트가운이다.")


@register_item
class Pajamas(Clothing):
    """잠옷"""
    unique_id = "pajamas"
    name = "잠옷"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:귀여움": 1, "분위기:따뜻함": 1
    }
    value = 25

    def look(self):
        yield morld.dialog("편안한 잠옷이다.")


@register_item
class Swimsuit(Clothing):
    """수영복"""
    unique_id = "swimsuit"
    name = "수영복"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:활동적": 1, "분위기:섹시함": 1
    }
    value = 30

    def look(self):
        yield morld.dialog("수영할 때 입는 수영복이다.")


@register_item
class Bikini(Clothing):
    """비키니"""
    unique_id = "bikini"
    name = "비키니"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:섹시함": 1, "분위기:활동적": 1
    }
    value = 35

    def look(self):
        yield morld.dialog("노출이 많은 비키니다.")


# ========================================
# 남성용 상의
# ========================================

@register_item
class MensDressShirt(Clothing):
    """남성용 드레스셔츠"""
    unique_id = "mens_dress_shirt"
    name = "드레스셔츠"
    equip_props = {"착용:상의": 1, "분위기:단정함": 1, "분위기:깔끔함": 1}
    value = 25

    def look(self):
        yield morld.dialog("격식있는 자리에 어울리는 드레스셔츠다.")


@register_item
class MensCasualShirt(Clothing):
    """남성용 캐주얼 셔츠"""
    unique_id = "mens_casual_shirt"
    name = "캐주얼 셔츠"
    equip_props = {"착용:상의": 1, "분위기:깔끔함": 1}
    value = 18

    def look(self):
        yield morld.dialog("편하게 입을 수 있는 캐주얼 셔츠다.")


@register_item
class MensVest(Clothing):
    """남성용 조끼"""
    unique_id = "mens_vest"
    name = "조끼"
    equip_props = {"착용:외투": 1, "분위기:단정함": 1, "분위기:멋짐": 1}
    value = 30

    def look(self):
        yield morld.dialog("셔츠 위에 입는 멋스러운 조끼다.")


@register_item
class MensTShirt(Clothing):
    """남성용 티셔츠"""
    unique_id = "mens_tshirt"
    name = "티셔츠"
    equip_props = {"착용:상의": 1, "분위기:활동적": 1}
    value = 12

    def look(self):
        yield morld.dialog("편한 티셔츠다.")


@register_item
class MensHoodie(Clothing):
    """남성용 후드티"""
    unique_id = "mens_hoodie"
    name = "후드티"
    equip_props = {"착용:상의": 1, "분위기:활동적": 1, "분위기:따뜻함": 1, "보온": 1}
    value = 28

    def look(self):
        yield morld.dialog("후드가 달린 편한 상의다.")


@register_item
class MensKnit(Clothing):
    """남성용 니트"""
    unique_id = "mens_knit"
    name = "니트"
    equip_props = {"착용:상의": 1, "분위기:따뜻함": 1, "분위기:단정함": 1, "보온": 1}
    value = 32

    def look(self):
        yield morld.dialog("따뜻한 니트 스웨터다.")


# ========================================
# 남성용 하의
# ========================================

@register_item
class MensSlacks(Clothing):
    """남성용 슬랙스"""
    unique_id = "mens_slacks"
    name = "슬랙스"
    equip_props = {"착용:하의": 1, "분위기:단정함": 1, "분위기:깔끔함": 1}
    value = 28

    def look(self):
        yield morld.dialog("격식있는 슬랙스다.")


@register_item
class MensJeans(Clothing):
    """남성용 청바지"""
    unique_id = "mens_jeans"
    name = "청바지"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1, "분위기:멋짐": 1}
    value = 25

    def look(self):
        yield morld.dialog("튼튼한 청바지다.")


@register_item
class MensCargoPants(Clothing):
    """남성용 카고바지"""
    unique_id = "mens_cargo_pants"
    name = "카고바지"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1, "수납": 1}
    value = 30

    def look(self):
        yield morld.dialog("주머니가 많은 카고바지다.")


@register_item
class MensShorts(Clothing):
    """남성용 반바지"""
    unique_id = "mens_shorts"
    name = "남성용 반바지"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1}
    value = 15

    def look(self):
        yield morld.dialog("활동하기 편한 남성용 반바지다.")


@register_item
class MensSweatpants(Clothing):
    """남성용 트레이닝복 하의"""
    unique_id = "mens_sweatpants"
    name = "트레이닝 바지"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1}
    value = 18

    def look(self):
        yield morld.dialog("운동하거나 편하게 입는 트레이닝 바지다.")


# ========================================
# 남성용 속옷
# ========================================

@register_item
class MensUnderwear(Clothing):
    """남성용 속옷"""
    unique_id = "mens_underwear"
    name = "남성 속옷"
    equip_props = {"착용:속옷하의": 1}
    value = 5

    def look(self):
        yield morld.dialog("평범한 남성용 속옷이다.")


@register_item
class MensBoxers(Clothing):
    """남성용 박서"""
    unique_id = "mens_boxers"
    name = "박서"
    equip_props = {"착용:속옷하의": 1, "분위기:깔끔함": 1}
    value = 8

    def look(self):
        yield morld.dialog("편안한 박서 팬츠다.")


@register_item
class MensUndershirt(Clothing):
    """남성용 속셔츠"""
    unique_id = "mens_undershirt"
    name = "속셔츠"
    equip_props = {"착용:속옷상의": 1}
    value = 6

    def look(self):
        yield morld.dialog("셔츠 안에 입는 속셔츠다.")


# ========================================
# 남성용 외투
# ========================================

@register_item
class MensSuit(Clothing):
    """남성용 정장 자켓"""
    unique_id = "mens_suit"
    name = "정장 자켓"
    equip_props = {"착용:외투": 1, "분위기:단정함": 1, "분위기:멋짐": 1}
    value = 60

    def look(self):
        yield morld.dialog("격식있는 정장 자켓이다.")


@register_item
class MensLeatherJacket(Clothing):
    """남성용 가죽 자켓"""
    unique_id = "mens_leather_jacket"
    name = "가죽 자켓"
    equip_props = {"착용:외투": 1, "분위기:멋짐": 1, "분위기:활동적": 1}
    value = 55

    def look(self):
        yield morld.dialog("멋스러운 가죽 자켓이다.")


@register_item
class MensBomberJacket(Clothing):
    """남성용 항공 자켓"""
    unique_id = "mens_bomber_jacket"
    name = "항공 자켓"
    equip_props = {"착용:외투": 1, "분위기:멋짐": 1, "분위기:따뜻함": 1, "보온": 1}
    value = 50

    def look(self):
        yield morld.dialog("따뜻하고 멋진 항공 자켓이다.")


@register_item
class MensWindbreaker(Clothing):
    """남성용 바람막이"""
    unique_id = "mens_windbreaker"
    name = "바람막이"
    equip_props = {"착용:외투": 1, "분위기:활동적": 1}
    value = 35

    def look(self):
        yield morld.dialog("바람을 막아주는 가벼운 자켓이다.")


# ========================================
# 남성용 신발
# ========================================

@register_item
class MensDressShoes(Clothing):
    """남성용 구두"""
    unique_id = "mens_dress_shoes"
    name = "구두"
    equip_props = {"착용:신발": 1, "분위기:단정함": 1, "분위기:멋짐": 1}
    value = 45

    def look(self):
        yield morld.dialog("광이 나는 구두다.")


@register_item
class MensSneakers(Clothing):
    """남성용 운동화"""
    unique_id = "mens_sneakers"
    name = "운동화"
    equip_props = {"착용:신발": 1, "분위기:활동적": 1}
    value = 30

    def look(self):
        yield morld.dialog("편하게 신을 수 있는 운동화다.")


@register_item
class MensWorkBoots(Clothing):
    """남성용 작업화"""
    unique_id = "mens_work_boots"
    name = "작업화"
    equip_props = {"착용:신발": 1, "분위기:활동적": 1, "분위기:멋짐": 1}
    value = 50

    def look(self):
        yield morld.dialog("튼튼한 작업화다.")


# ========================================
# 남성용 모자
# ========================================

@register_item
class MensFedora(Clothing):
    """남성용 페도라"""
    unique_id = "mens_fedora"
    name = "페도라"
    equip_props = {"착용:모자": 1, "분위기:멋짐": 1, "분위기:우아함": 1}
    value = 30

    def look(self):
        yield morld.dialog("클래식한 페도라 모자다.")


@register_item
class MensCap(Clothing):
    """남성용 캡모자"""
    unique_id = "mens_cap"
    name = "캡모자"
    equip_props = {"착용:모자": 1, "분위기:활동적": 1}
    value = 15

    def look(self):
        yield morld.dialog("캐주얼한 캡모자다.")


@register_item
class MensBeanie(Clothing):
    """남성용 비니"""
    unique_id = "mens_beanie"
    name = "비니"
    equip_props = {"착용:모자": 1, "분위기:활동적": 1, "분위기:따뜻함": 1, "보온": 1}
    value = 12

    def look(self):
        yield morld.dialog("따뜻한 비니다.")


# ========================================
# 유니섹스/공용 의류
# ========================================

@register_item
class OversizedHoodie(Clothing):
    """오버사이즈 후드티"""
    unique_id = "oversized_hoodie"
    name = "오버사이즈 후드티"
    equip_props = {"착용:상의": 1, "분위기:귀여움": 1, "분위기:따뜻함": 1, "보온": 1}
    value = 30

    def look(self):
        yield morld.dialog("크고 편한 후드티다. 아늑하다.")


@register_item
class DenimJacket(Clothing):
    """청자켓"""
    unique_id = "denim_jacket"
    name = "청자켓"
    equip_props = {"착용:외투": 1, "분위기:활동적": 1, "분위기:멋짐": 1}
    value = 40

    def look(self):
        yield morld.dialog("데님 소재의 캐주얼 자켓이다.")


@register_item
class TrackSuit(Clothing):
    """트레이닝복 세트"""
    unique_id = "track_suit"
    name = "트레이닝복"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:활동적": 1
    }
    value = 35

    def look(self):
        yield morld.dialog("운동할 때 입는 트레이닝복 세트다.")


@register_item
class RainCoat(Clothing):
    """우비"""
    unique_id = "rain_coat"
    name = "우비"
    equip_props = {"착용:외투": 1, "분위기:활동적": 1}
    value = 25

    def look(self):
        yield morld.dialog("비를 막아주는 우비다.")


@register_item
class LabCoat(Clothing):
    """실험복"""
    unique_id = "lab_coat"
    name = "실험복"
    equip_props = {"착용:외투": 1, "분위기:단정함": 1, "분위기:깔끔함": 1}
    value = 40

    def look(self):
        yield morld.dialog("연구원이 입는 흰 실험복이다.")


# ========================================
# 황폐화된 의류 (도시 의류점용)
# ========================================

@register_item
class TornJeans(Clothing):
    """찢어진 청바지"""
    unique_id = "torn_jeans"
    name = "찢어진 청바지"
    equip_props = {"착용:하의": 1, "분위기:멋짐": 1}
    value = 15

    def look(self):
        yield morld.dialog("일부러 찢은 듯한 청바지다. 멋스럽다.")


@register_item
class DirtyShirt(Clothing):
    """더러운 셔츠"""
    unique_id = "dirty_shirt"
    name = "더러운 셔츠"
    equip_props = {"착용:상의": 1, "분위기:더러움": 1}
    value = 3

    def look(self):
        yield morld.dialog("얼룩이 많이 묻은 셔츠다.")


@register_item
class WornOutJacket(Clothing):
    """낡은 자켓"""
    unique_id = "worn_out_jacket"
    name = "낡은 자켓"
    equip_props = {"착용:외투": 1, "분위기:따뜻함": 1}
    value = 10

    def look(self):
        yield morld.dialog("많이 낡았지만 아직 입을 만한 자켓이다.")


@register_item
class FadedDress(Clothing):
    """빛바랜 드레스"""
    unique_id = "faded_dress"
    name = "빛바랜 드레스"
    equip_props = {
        "착용:상의": 1, "착용:하의": 1,
        "분위기:우아함": 1
    }
    value = 20

    def look(self):
        yield morld.dialog("한때는 화려했을 드레스다. 색이 많이 바랬다.")


@register_item
class MilitaryBoots(Clothing):
    """군용 부츠"""
    unique_id = "military_boots"
    name = "군용 부츠"
    equip_props = {"착용:신발": 1, "분위기:활동적": 1, "분위기:멋짐": 1}
    value = 55

    def look(self):
        yield morld.dialog("튼튼한 군용 부츠다.")


@register_item
class TacticalVest(Clothing):
    """전술 조끼"""
    unique_id = "tactical_vest"
    name = "전술 조끼"
    equip_props = {"착용:외투": 1, "분위기:활동적": 1, "수납": 3}
    value = 60

    def look(self):
        yield morld.dialog("여러 주머니가 달린 전술 조끼다.")


@register_item
class CamouflagePants(Clothing):
    """위장 바지"""
    unique_id = "camouflage_pants"
    name = "위장 바지"
    equip_props = {"착용:하의": 1, "분위기:활동적": 1}
    value = 25

    def look(self):
        yield morld.dialog("위장 무늬의 바지다.")
