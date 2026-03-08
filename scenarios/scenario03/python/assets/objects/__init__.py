# assets/objects/__init__.py - 오브젝트 Asset 모듈 (시나리오03)

from .train import SubwayTrain, CRTConsole

# 인스턴스 캐시 (instance_id -> 인스턴스)
_instances = {}


def register_instance(instance_id, instance):
    """오브젝트 인스턴스 등록"""
    _instances[instance_id] = instance


def get_instance(instance_id):
    """오브젝트 인스턴스 조회"""
    return _instances.get(instance_id)
