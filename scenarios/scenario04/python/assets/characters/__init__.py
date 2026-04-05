# assets/characters/__init__.py — 캐릭터 에셋 모듈 (S04)
#
# C#에서 호출하는 인터페이스:
#   - get_all_describe_texts(unit_ids) → 묘사 텍스트 리스트
#   - get_describe_text(unit_id) → 개별 묘사 텍스트
#   - get_focus_text(unit_id) → Focus 상태 텍스트

from . import player
from . import npc_a
from . import npc_b
from . import npc_c
from . import npc_d
from . import creatures

# 인스턴스 캐시: unit_id → Character 인스턴스
_instances = {}


def register_instance(unit_id, instance):
    """캐릭터 인스턴스 등록 (instantiate 시 호출)"""
    _instances[unit_id] = instance


def clear_instances():
    """모든 인스턴스 캐시 초기화"""
    _instances.clear()


def get_instance(unit_id):
    """캐릭터 인스턴스 반환"""
    return _instances.get(unit_id)


def get_describe_text(unit_id):
    """특정 캐릭터의 describe text 반환"""
    instance = _instances.get(unit_id)
    if instance is None:
        return ""
    return instance.get_describe_text()


def get_all_describe_texts(unit_ids):
    """여러 캐릭터의 describe text를 한 번에 반환 (C#에서 호출)"""
    import stealth as stealth_mod
    result = []
    for unit_id in unit_ids:
        # 은신 NPC는 describe에서 제외
        if stealth_mod.is_unit_stealthed(unit_id):
            continue
        text = get_describe_text(unit_id)
        if text:
            result.append(text)
    return result


def get_focus_text(unit_id):
    """특정 캐릭터의 focus text 반환 (C#에서 호출)"""
    instance = _instances.get(unit_id)
    if instance is None:
        return ""
    return instance.get_focus_text()
