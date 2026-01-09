# assets/items/tools.py - 도구 아이템
#
# 사용법:
#   from assets.items.tools import Torch, Rope
#   torch = Torch()
#   torch.instantiate(item_id)

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
    actions = ["take@container", "use@inventory", "equip@inventory"]


class Rope(Item):
    unique_id = "rope"
    name = "밧줄"
    passive_props = {}
    equip_props = {}
    value = 8
    actions = ["take@container", "use@inventory"]


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
    actions = ["take@container", "use@inventory", "equip@inventory"]


class AlarmClock(Item):
    """리나의 자명종"""
    unique_id = "alarm_clock"
    name = "자명종"
    owner = "lina"
    passive_props = {}
    equip_props = {}
    value = 20
    actions = ["take@container", "use@inventory"]


class FishingRod(Item):
    """세라의 낚시대"""
    unique_id = "fishing_rod"
    name = "낚시대"
    owner = "sera"
    passive_props = {}
    equip_props = {}
    value = 25
    actions = ["take@container", "use@inventory"]


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
    actions = ["take@container", "use@inventory"]


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
    actions = ["take@container", "script:read_book:읽기"]


class ManagementLedger(Item):
    """엘라의 관리 장부"""
    unique_id = "management_ledger"
    name = "관리 장부"
    owner = "ella"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "script:read_book:읽기"]


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
    actions = ["take@container", "use@inventory"]


class WaterBottle(Item):
    """물병"""
    unique_id = "water_bottle"
    name = "물병"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "use@inventory"]
