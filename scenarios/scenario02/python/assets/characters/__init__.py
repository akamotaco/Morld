# assets/characters/__init__.py - 캐릭터 Asset 모듈
#
# describe_text/focus_text 시스템:
#   - describe_text: 장소에 있을 때 묘사 (get_describe_text)
#   - focus_text: Focus 상태일 때 묘사 (get_focus_text)
#   - C#에서 get_all_describe_texts() / get_focus_text() 호출

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


def get_focus_text(unit_id: int) -> str:
    """특정 캐릭터의 현재 상태에 맞는 focus text 반환 (C#에서 호출)"""
    instance = _instances.get(unit_id)
    if instance is None:
        return ""
    return instance.get_focus_text()


# 이벤트 핸들러 (인스턴스 메서드 방식)
def get_character_event_handler(unit_id: int):
    """특정 캐릭터의 이벤트 핸들러 (인스턴스) 반환

    이제 캐릭터 인스턴스 자체가 이벤트 핸들러 역할을 함.
    - on_meet_player(player_id) → 인스턴스 메서드
    - npc_talk(player_id) → 인스턴스 메서드
    """
    instance = _instances.get(unit_id)
    if instance is None:
        return None

    # Player는 이벤트 핸들러 없음
    if instance.unique_id == "player":
        return None

    return instance
