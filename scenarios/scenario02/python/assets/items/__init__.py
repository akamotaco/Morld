# assets/items/__init__.py - 아이템 Asset 모듈
#
# 인스턴스 레지스트리 및 call: 패턴 지원
# - call: 액션을 위한 인스턴스 메서드 호출
# - instance_id → Item 인스턴스 매핑

from .equipment import (
    OldKnife, LeatherPouch, WritingTool, OldBook, SmallToolbox
)
from .tools import (
    Torch, Rope,
    KitchenKnife, AlarmClock, FishingRod, HuntingBow, HerbPouch, CookingPot,
    Diary, ManagementLedger,
    Lantern, WaterBottle
)
from .resources import (
    Flour, Rice, Water, Bread, Berry, Meat,
    Wood, Cloth
)
from .food import (
    FoodItem, WildBerry, Apple, Mushroom, CookedMeat, CookedFish,
    Fish, Herb, HerbTea, FruitSalad, MushroomStew
)
from .clothes import (
    Clothing, RaggedClothes, SimpleShirt, LinenShirt, Blouse, WhiteBlouse,
    SimplePants, LinenPants, LongSkirt, Shorts,
    Sundress, MaidDress, WorkDress,
    LightJacket, HuntingVest, Apron, WarmCoat,
    SeraHuntingOutfit, MilaApron
)

__all__ = [
    # equipment
    'OldKnife', 'LeatherPouch', 'WritingTool', 'OldBook', 'SmallToolbox',
    # tools
    'Torch', 'Rope',
    'KitchenKnife', 'AlarmClock', 'FishingRod', 'HuntingBow', 'HerbPouch', 'CookingPot',
    'Diary', 'ManagementLedger',
    'Lantern', 'WaterBottle',
    # resources
    'Flour', 'Rice', 'Water', 'Bread', 'Berry', 'Meat',
    'Wood', 'Cloth',
    # food
    'FoodItem', 'WildBerry', 'Apple', 'Mushroom', 'CookedMeat', 'CookedFish',
    'Fish', 'Herb', 'HerbTea', 'FruitSalad', 'MushroomStew',
    # clothes
    'Clothing', 'RaggedClothes', 'SimpleShirt', 'LinenShirt', 'Blouse', 'WhiteBlouse',
    'SimplePants', 'LinenPants', 'LongSkirt', 'Shorts',
    'Sundress', 'MaidDress', 'WorkDress',
    'LightJacket', 'HuntingVest', 'Apron', 'WarmCoat',
    'SeraHuntingOutfit', 'MilaApron',
]


# ========================================
# 인스턴스 레지스트리 (instance_id → Item 인스턴스)
# ========================================

_instances = {}


def register_instance(instance_id: int, instance):
    """아이템 인스턴스 등록 (instantiate 시 호출)"""
    _instances[instance_id] = instance


def clear_instances():
    """모든 인스턴스 캐시 초기화 (챕터 전환 시 호출)"""
    global _instances
    _instances.clear()
    print("[assets.items] Instances cleared.")


def get_instance(instance_id: int):
    """아이템 인스턴스 반환"""
    return _instances.get(instance_id)


def get_focus_text(item_id: int) -> str:
    """특정 아이템의 현재 상태에 맞는 focus text 반환 (C#에서 호출)"""
    instance = _instances.get(item_id)
    if instance is None:
        return ""
    return instance.get_focus_text()


def call_instance_method(instance_id: int, method_name: str):
    """
    아이템 인스턴스의 메서드 호출 (call: 액션용)

    Args:
        instance_id: 아이템 인스턴스 ID
        method_name: 호출할 메서드 이름

    Returns:
        메서드 반환값 (Generator 또는 dict)
    """
    instance = _instances.get(instance_id)
    if instance is None:
        print(f"[assets.items] Instance not found: {instance_id}")
        return None

    method = getattr(instance, method_name, None)
    if method is None:
        print(f"[assets.items] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    return method()
