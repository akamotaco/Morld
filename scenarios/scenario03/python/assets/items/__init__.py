# assets/items/__init__.py - 아이템 Asset 모듈 (시나리오03)

from .materials import MetalPipe, ConcreteBlock, Plank, Wire

# 인스턴스 캐시 (instance_id -> 인스턴스)
_instances = {}


def register_instance(instance_id, instance):
    """아이템 인스턴스 등록"""
    _instances[instance_id] = instance


def get_instance(instance_id):
    """아이템 인스턴스 조회"""
    return _instances.get(instance_id)


def get_unique_id(instance_id):
    """인스턴스 ID에서 unique_id 조회"""
    inst = _instances.get(instance_id)
    return inst.unique_id if inst else None


def get_item_class(unique_id):
    """unique_id로 아이템 클래스 조회"""
    ITEM_CLASSES = {
        "metal_pipe": MetalPipe,
        "concrete_block": ConcreteBlock,
        "plank": Plank,
        "wire": Wire,
    }
    return ITEM_CLASSES.get(unique_id)
