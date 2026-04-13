# assets/objects/__init__.py — 오브젝트 에셋 모듈 (S04)
#
# 인스턴스 캐시 제공 (focus/액션용).

from . import dungeon_entrance  # noqa: F401

# 인스턴스 캐시: unit_id → Object 인스턴스
_instances = {}


def register_instance(unit_id, instance):
    """오브젝트 인스턴스 등록 (instantiate 시 호출)"""
    _instances[unit_id] = instance


def clear_instances():
    _instances.clear()


def get_instance(unit_id):
    return _instances.get(unit_id)
