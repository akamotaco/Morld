# assets/objects/__init__.py - 오브젝트 Asset 모듈
#
# 인스턴스 레지스트리 및 call: 패턴 지원
# - call: 액션을 위한 인스턴스 메서드 호출
# - instance_id → Object 인스턴스 매핑

from .furniture import (
    Fireplace, OldSofa, LivingSofa, Bookshelf,
    DiningTable, DiningChair,
    Stove, Cupboard, Kettle,
    Bathtub, Washbasin,
    CraftingTable,
    Bed, SmallDesk, Mirror,
    CorridorWindow, Vase,
    Wardrobe
)
from .outdoor import (
    GardenBench, Well, GardenPlot, DryingRack, FishingSpot
)
from .nature import (
    ResourceObject, AppleTree, BerryBush, MushroomPatch
)
from .grounds import (
    GroundWooden, GroundStone, GroundMarble, GroundTile,
    GroundDirt, GroundGrass, GroundForest, GroundRocky,
    GroundAsphalt, GroundConcrete
)
from .vehicles import (
    Bicycle, CarDriverSeat, CarPassengerSeat, CarTrunk
)

__all__ = [
    # furniture
    'Fireplace', 'OldSofa', 'LivingSofa', 'Bookshelf',
    'DiningTable', 'DiningChair',
    'Stove', 'Cupboard', 'Kettle',
    'Bathtub', 'Washbasin',
    'CraftingTable',
    'Bed', 'SmallDesk', 'Mirror',
    'CorridorWindow', 'Vase',
    'Wardrobe',
    # outdoor
    'GardenBench', 'Well', 'GardenPlot', 'DryingRack', 'FishingSpot',
    # nature (자원 생성)
    'ResourceObject', 'AppleTree', 'BerryBush', 'MushroomPatch',
    # grounds
    'GroundWooden', 'GroundStone', 'GroundMarble', 'GroundTile',
    'GroundDirt', 'GroundGrass', 'GroundForest', 'GroundRocky',
    'GroundAsphalt', 'GroundConcrete',
    # vehicles
    'Bicycle', 'CarDriverSeat', 'CarPassengerSeat', 'CarTrunk',
]


# ========================================
# 인스턴스 레지스트리 (instance_id → Object 인스턴스)
# ========================================

_instances = {}


def register_instance(instance_id: int, instance):
    """오브젝트 인스턴스 등록 (instantiate 시 호출)"""
    _instances[instance_id] = instance


def clear_instances():
    """모든 인스턴스 캐시 초기화 (챕터 전환 시 호출)"""
    global _instances
    _instances.clear()
    print("[assets.objects] Instances cleared.")


def get_instance(instance_id: int):
    """오브젝트 인스턴스 반환"""
    return _instances.get(instance_id)


def get_focus_text(unit_id: int) -> str:
    """특정 오브젝트의 현재 상태에 맞는 focus text 반환 (C#에서 호출)"""
    instance = _instances.get(unit_id)
    if instance is None:
        return ""
    return instance.get_focus_text()


def call_instance_method(instance_id: int, method_name: str):
    """
    오브젝트 인스턴스의 메서드 호출 (call: 액션용)

    Args:
        instance_id: 오브젝트 인스턴스 ID
        method_name: 호출할 메서드 이름

    Returns:
        메서드 반환값 (Generator 또는 dict)
    """
    instance = _instances.get(instance_id)
    if instance is None:
        print(f"[assets.objects] Instance not found: {instance_id}")
        return None

    method = getattr(instance, method_name, None)
    if method is None:
        print(f"[assets.objects] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    return method()
