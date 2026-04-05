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

    Returns: 필터링된 액션 리스트 또는 None (필터링 없음)
    """
    import morld

    # 등록된 캐릭터 인스턴스 확인
    from assets import characters
    instance = characters.get_instance(unit_id)
    if instance is not None and hasattr(instance, 'get_available_actions'):
        return instance.get_available_actions()

    # 인스턴스가 없는 NPC (npc_generator 생성 등) — prop 기반 액션
    actions = []

    # 파티 관련 액션
    import party
    if party.is_member(unit_id) and unit_id != party.get_leader():
        # 파티원 → 이탈 액션
        actions.append(f"[url=dismiss:{unit_id}]파티 이탈[/url]")
    elif not party.is_member(unit_id):
        # 비파티원 → 초대 액션
        can_recruit = morld.get_unit_prop(unit_id, "파티후보")
        if can_recruit and not party.is_full():
            actions.append(f"[url=recruit:{unit_id}]파티 초대[/url]")

    # 대화 (모든 NPC)
    info = morld.get_unit_info(unit_id)
    if info and not info.get("is_object", False):
        actions.append(f"[url=talk:{unit_id}]대화하기[/url]")

    return actions if actions else None


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
