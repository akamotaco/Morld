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
    ResourceObject, AppleTree, BerryBush, MushroomPatch,
    WildBerryBush, WildHerbPatch
)
from .grounds import (
    GroundWooden, GroundStone, GroundMarble, GroundTile,
    GroundDirt, GroundGrass, GroundForest, GroundRocky,
    GroundAsphalt, GroundConcrete,
    DynamicGround
)
from .scavenge import (
    ScavengeableObject, GasStationStand, PharmacyShelf, BrokenVendingMachine
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
    'WildBerryBush', 'WildHerbPatch',
    # grounds
    'GroundWooden', 'GroundStone', 'GroundMarble', 'GroundTile',
    'GroundDirt', 'GroundGrass', 'GroundForest', 'GroundRocky',
    'GroundAsphalt', 'GroundConcrete', 'DynamicGround',
    # scavenge (비충전 수집)
    'ScavengeableObject', 'GasStationStand', 'PharmacyShelf', 'BrokenVendingMachine',
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
    _location_objects.clear()
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


# ========================================
# Location 오브젝트 인덱스 (NPC 행동용)
# ========================================

_location_objects = {}  # (region_id, location_id) -> [instance_id, ...]


def register_location_object(region_id: int, location_id: int, instance_id: int):
    """오브젝트를 location 인덱스에 등록 (add_object 시 호출)"""
    key = (region_id, location_id)
    if key not in _location_objects:
        _location_objects[key] = []
    _location_objects[key].append(instance_id)


def get_location_objects(region_id: int, location_id: int) -> list:
    """특정 location의 오브젝트 ID 목록 반환"""
    return _location_objects.get((region_id, location_id), [])


def clear_location_objects():
    """location 인덱스 초기화 (챕터 전환 시)"""
    _location_objects.clear()


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
