# assets/characters/__init__.py - 캐릭터 Asset 모듈
#
# describe_text 시스템:
#   - 각 캐릭터 클래스의 describe_text 속성 사용
#   - get_describe_text(unit_id) 함수로 호출
#   - C#에서 get_all_describe_texts() 호출

from .player import Player
from .lina import Lina
from .sera import Sera
from .mila import Mila
from .yuki import Yuki
from .ella import Ella

# 캐릭터 클래스 매핑 (unique_id → 클래스)
CHARACTER_CLASSES = {
    "player": Player,
    "lina": Lina,
    "sera": Sera,
    "mila": Mila,
    "yuki": Yuki,
    "ella": Ella,
}

# 인스턴스 캐시 (instance_id → 인스턴스)
_instances = {}


def register_instance(instance_id: int, instance):
    """캐릭터 인스턴스 등록 (instantiate 시 호출)"""
    _instances[instance_id] = instance


def get_instance(instance_id: int):
    """캐릭터 인스턴스 반환"""
    return _instances.get(instance_id)


def get_describe_text(unit_id: int) -> str:
    """특정 캐릭터의 현재 상태에 맞는 describe text 반환"""
    instance = _instances.get(unit_id)
    if instance is None:
        return ""
    return instance.get_describe_text()


def get_all_describe_texts(unit_ids: list) -> list:
    """여러 캐릭터의 describe text를 한 번에 반환 (C#에서 호출)"""
    result = []
    for unit_id in unit_ids:
        text = get_describe_text(unit_id)
        if text:
            result.append(text)
    return result


# 이벤트 핸들러 (기존 호환성)
def get_character_event_handler(unit_id: int):
    """특정 캐릭터의 이벤트 핸들러 모듈 반환"""
    from . import lina, sera, mila, yuki, ella

    # unique_id로 매핑
    instance = _instances.get(unit_id)
    if instance is None:
        return None

    unique_id = instance.unique_id
    module_map = {
        "lina": lina,
        "sera": sera,
        "mila": mila,
        "yuki": yuki,
        "ella": ella,
    }

    module = module_map.get(unique_id)
    if module and hasattr(module, 'events'):
        return module.events

    return None
