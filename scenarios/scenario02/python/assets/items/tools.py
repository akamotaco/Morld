# assets/items/tools.py - 도구 아이템
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명@context"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
# - 동일한 액션명(read, use)도 클래스별로 다른 동작 구현
#
# 사용법:
#   from assets.items.tools import Torch, Rope
#   torch = Torch()
#   torch.instantiate(item_id)

import morld
from assets.base import Item


# ========================================
# 기타 도구
# ========================================

class Torch(Item):
    unique_id = "torch"
    name = "횃불"
    passive_props = {}
    equip_props = {"밝기": 3}
    value = 5
    actions = ["take@container", "call:use:사용하기@inventory", "equip@inventory"]

    def use(self):
        """횃불 사용 - 불 켜기"""
        yield morld.dialog([
            "횃불에 불을 붙였다.",
            "주변이 환하게 밝아졌다."
        ])
        morld.advance_time(1)


class Rope(Item):
    unique_id = "rope"
    name = "밧줄"
    passive_props = {}
    equip_props = {}
    value = 8
    actions = ["take@container", "call:use:살펴보기@inventory"]

    def use(self):
        """밧줄 살펴보기"""
        yield morld.dialog([
            "튼튼한 밧줄이다.",
            "오르거나 묶는 데 쓸 수 있겠다."
        ])


# ========================================
# 소유자가 있는 개인 물품
# ========================================

class KitchenKnife(Item):
    """밀라의 부엌칼"""
    unique_id = "kitchen_knife"
    name = "부엌칼"
    owner = "mila"
    passive_props = {}
    equip_props = {"공격력": 2}
    value = 15
    actions = ["take@container", "call:use:살펴보기@inventory", "equip@inventory"]

    def use(self):
        """부엌칼 살펴보기"""
        yield morld.dialog([
            "날이 잘 서있는 부엌칼이다.",
            "밀라가 소중히 관리하는 것 같다."
        ])


class AlarmClock(Item):
    """리나의 자명종"""
    unique_id = "alarm_clock"
    name = "자명종"
    owner = "lina"
    passive_props = {}
    equip_props = {}
    value = 20
    actions = ["take@container", "call:use:살펴보기@inventory"]

    def use(self):
        """자명종 살펴보기"""
        yield morld.dialog([
            "째깍째깍 소리를 내는 자명종이다.",
            "리나가 아끼는 물건 같다."
        ])


class FishingRod(Item):
    """
    세라의 낚시대

    장착 시 can:fish 부여 → 물가에서 "낚시" 액션 활성화
    """
    unique_id = "fishing_rod"
    name = "낚시대"
    owner = "sera"
    passive_props = {}
    equip_props = {"can:fish": 1}  # 장착 시 낚시 가능
    value = 25
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """낚시대 살펴보기"""
        yield morld.dialog([
            "세라의 낚시대다.",
            "장착하면 물가에서 낚시를 할 수 있다."
        ])


class HuntingBow(Item):
    """세라의 사냥용 활"""
    unique_id = "hunting_bow"
    name = "사냥용 활"
    owner = "sera"
    passive_props = {}
    equip_props = {"공격력": 5, "사거리": 3}
    value = 50
    actions = ["take@container", "equip@inventory"]


class HerbPouch(Item):
    """리나의 약초 주머니"""
    unique_id = "herb_pouch"
    name = "약초 주머니"
    owner = "lina"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "call:use:살펴보기@inventory"]

    def use(self):
        """약초 주머니 살펴보기"""
        yield morld.dialog([
            "리나의 약초 주머니다.",
            "안에는 말린 약초들이 가득하다.",
            "치료에 쓸 수 있는 것들이 많아 보인다."
        ])


class CookingPot(Item):
    """밀라의 냄비"""
    unique_id = "cooking_pot"
    name = "냄비"
    owner = "mila"
    passive_props = {}
    equip_props = {}
    value = 30
    actions = ["take@container"]


class Diary(Item):
    """유키의 일기장"""
    unique_id = "diary"
    name = "일기장"
    owner = "yuki"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:read:읽기@inventory"]

    def read(self):
        """유키의 일기장 읽기"""
        yield morld.dialog([
            "유키의 일기장을 펼쳐본다.",
            "\"오늘도 언니들과 함께 저택 청소를 했다.\"",
            "\"저녁에는 밀라 언니가 맛있는 저녁을 해줬다.\"",
            "\"...모두가 행복해 보여서 나도 기분이 좋다.\""
        ], autofill="book")
        morld.advance_time(5)


class ManagementLedger(Item):
    """엘라의 관리 장부"""
    unique_id = "management_ledger"
    name = "관리 장부"
    owner = "ella"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "call:read:읽기@inventory"]

    def read(self):
        """엘라의 관리 장부 읽기"""
        yield morld.dialog([
            "엘라의 관리 장부를 펼쳐본다.",
            "저택의 식량, 자금, 일정 등이 꼼꼼하게 기록되어 있다.",
            "엘라의 정리 능력에 감탄하지 않을 수 없다."
        ], autofill="book")
        morld.advance_time(5)


# ========================================
# 공용 아이템 (소유자 없음)
# ========================================

class Candle(Item):
    """촛불"""
    unique_id = "candle"
    name = "촛불"
    passive_props = {}
    equip_props = {"밝기": 1}
    value = 3
    actions = ["take@container", "call:use:불 켜기@inventory"]

    def use(self):
        """촛불 사용 - 불 켜기"""
        yield morld.dialog([
            "촛불에 불을 붙였다.",
            "은은한 빛이 주변을 비춘다."
        ])
        morld.advance_time(1)


class WaterBottle(Item):
    """물병"""
    unique_id = "water_bottle"
    name = "물병"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:use:물 마시기@inventory"]

    def use(self):
        """물병 사용 - 물 마시기"""
        yield morld.dialog([
            "물병의 물을 마셨다.",
            "시원하고 상쾌하다."
        ])
        morld.advance_time(1)
