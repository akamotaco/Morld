# assets/characters/__init__.py - 캐릭터 Asset 모듈 (시나리오03)

from .secretary import Secretary
from .squad_member import SquadMember

# 캐릭터 클래스 매핑 (unique_id -> 클래스)
CHARACTER_CLASSES = {
    "secretary": Secretary,
    "squad_member": SquadMember,
}

# 인스턴스 캐시 (instance_id -> 인스턴스)
_instances = {}


def register_instance(instance_id, instance):
    """캐릭터 인스턴스 등록"""
    _instances[instance_id] = instance


def get_instance(instance_id):
    """캐릭터 인스턴스 조회"""
    return _instances.get(instance_id)


def get_character_event_handler(unit_id):
    """캐릭터별 이벤트 핸들러 반환"""
    instance = _instances.get(unit_id)
    if instance and hasattr(instance, 'event_handler'):
        return instance.event_handler
    return None
