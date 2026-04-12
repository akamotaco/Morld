# assets/__init__.py - S04 Asset 패키지
#
# base 클래스와 registry 함수 노출
# C#에서 호출하는 인터페이스 포함: get_available_actions, check_initiative_event

from .base import Asset, Character, Object, Item
from .registry import (
    register_item,
    register_object,
    register_character,
    instantiate_character,
    instantiate_object,
    get_instance_id,
    get_unique_id,
    get_or_create_item_id,
    clear,
)


# ========================================
# C# 호출 인터페이스
# ========================================

def get_available_actions(unit_id):
    """유닛의 사용 가능 액션 목록 (C#에서 호출)

    우선순위:
      1) 인스턴스가 get_available_actions()를 정의하면 그 결과
      2) 인스턴스에 actions 속성이 있으면 그 리스트
      3) 둘 다 없으면 빈 리스트
    """
    from assets import characters
    instance = characters.get_instance(unit_id)
    if instance is None:
        return []
    if hasattr(instance, 'get_available_actions'):
        return list(instance.get_available_actions())
    if hasattr(instance, 'actions') and instance.actions:
        return list(instance.actions)
    return []


def call_instance_method(instance_id: int, method_name: str, args=None, equipment=None):
    """Asset 인스턴스 메서드 호출 (call: 액션용).

    C# MetaActionHandler가 `action:call:methodName:...:unitId` URL을 처리할 때
    이 함수를 거쳐 Python 측 인스턴스 메서드를 실행한다.

    Args:
        instance_id: 대상 unit_id (또는 item_id)
        method_name: 호출할 메서드 이름
        args: 인자 리스트 (None=빈 리스트)
        equipment: can: prop을 제공한 장비 dict 또는 None

    Returns:
        메서드 반환값 (Generator/dict/None 등)
    """
    if args is None:
        args = []

    from assets import characters
    instance = characters.get_instance(instance_id)
    if instance is None:
        print(f"[assets] No instance for id={instance_id}, method={method_name}")
        return None

    method = getattr(instance, method_name, None)
    if method is None:
        print(f"[assets] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    # equipment 파라미터 지원 여부 확인 (간이)
    try:
        import inspect
        sig = inspect.signature(method)
        if equipment is not None and 'equipment' in sig.parameters:
            return method(*args, equipment=equipment)
    except (ValueError, TypeError):
        pass
    return method(*args)


def get_action_blocked_message(unit_id):
    """유닛의 상태 차단 메시지 (C#에서 호출)"""
    from assets import characters
    instance = characters.get_instance(unit_id)
    if instance is not None and hasattr(instance, 'get_action_blocked_message'):
        return instance.get_action_blocked_message()
    return None


def check_initiative_event(unit_id):
    """NPC 주도 이벤트 체크 (C#에서 focus 시 호출)

    Returns: Generator (이벤트 있음) 또는 None
    """
    from assets import characters
    instance = characters.get_instance(unit_id)
    if instance is None:
        return None

    # first meet 체크
    if hasattr(instance, 'is_first_meet'):
        import morld
        player_id = morld.get_player_id()
        if player_id is not None and instance.is_first_meet(player_id):
            if hasattr(instance, '_run_event_dialog'):
                return instance._run_event_dialog("first_meet", player_id)

    return None
