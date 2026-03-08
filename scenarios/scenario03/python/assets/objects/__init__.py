# assets/objects/__init__.py - 오브젝트 Asset 모듈 (시나리오03)

from .train import SubwayTrain, CRTConsole

# 인스턴스 캐시 (instance_id -> 인스턴스)
_instances = {}

# Location별 오브젝트 ID 목록 ((region_id, location_id) -> [unit_id, ...])
_location_objects = {}


def register_instance(instance_id, instance):
    """오브젝트 인스턴스 등록"""
    _instances[instance_id] = instance


def get_instance(instance_id):
    """오브젝트 인스턴스 조회"""
    return _instances.get(instance_id)


def register_location_object(region_id, location_id, instance_id):
    """Location에 오브젝트 ID 등록"""
    key = (region_id, location_id)
    if key not in _location_objects:
        _location_objects[key] = []
    _location_objects[key].append(instance_id)
