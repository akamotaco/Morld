# assets/objects/__init__.py — 오브젝트 에셋 모듈 (S04)
#
# 인스턴스 캐시 제공 (focus/액션용).

# 오브젝트 모듈들을 import하여 @register_object 데코레이터 실행
# 현재는 등록할 오브젝트 없음 (dungeon_entrance 제거: on_reach 자동 입장으로 대체)

# 인스턴스 캐시: unit_id → Object 인스턴스
_instances = {}


def register_instance(unit_id, instance):
    """오브젝트 인스턴스 등록 (instantiate 시 호출)"""
    _instances[unit_id] = instance


def clear_instances():
    _instances.clear()


def get_instance(unit_id):
    return _instances.get(unit_id)
