# assets/__init__.py - Asset 시스템 (scenario02)
#
# 인스턴스 기반 Asset 구조:
#   Asset (base)
#   ├── Unit
#   │   ├── Character
#   │   └── Object
#   ├── Item
#   └── Location
#
# 사용법:
#   loc = BackYard()
#   loc.instantiate(location_id, REGION_ID)  # location_id는 수동 지정
#
#   npc = Sera()
#   npc_id = morld.create_id("unit")         # ID 자동 생성
#   npc.instantiate(npc_id, REGION_ID, loc_id)

# 베이스 클래스 export
from assets.base import Asset, Unit, Character, Object, Item, Location

# 레지스트리 함수 export (ID 조회용)
from assets.registry import (
    get_instance_id,
    get_unique_id,
    require_instance_id,
    clear,
)


# ========================================
# call: 액션 지원 - 인스턴스 메서드 호출 API
# ========================================

def _method_accepts_equipment(method) -> bool:
    """메서드가 equipment 키워드 인자를 받는지 확인"""
    # sharpPy는 inspect 모듈을 지원하지 않으므로 간단한 방법 사용
    # method의 __code__ 속성으로 파라미터 이름 확인
    try:
        code = getattr(method, "__code__", None)
        if code is None:
            return False
        varnames = code.co_varnames[:code.co_argcount]
        return "equipment" in varnames
    except Exception:
        return False


def _update_errand_visibility(player_id: int, partner_id: int):
    """
    NPC에게 제안 가능한 퀘스트가 있는지 확인하여 can:errand 설정

    Args:
        player_id: 플레이어 ID
        partner_id: NPC instance ID
    """
    try:
        import morld
        from assets import characters
        from quest import quest_manager

        # NPC의 unique_id 조회
        instance = characters.get_instance(partner_id)
        if instance is None:
            return

        npc_unique_id = instance.unique_id
        if not npc_unique_id:
            return

        # 이 NPC에게서 받을 수 있는 퀘스트가 있는지 확인
        available_quests = quest_manager.get_available_quests_from(npc_unique_id)

        # can:errand 설정
        can_errand = 1 if available_quests else 0
        morld.set_unit_prop(player_id, "can:errand", can_errand)
    except Exception as e:
        print(f"[assets] Failed to update errand visibility: {e}")


def _update_affection_visibility_if_needed(partner_id: int):
    """
    캐릭터 액션 호출 시 애정 표현 및 심부름 visibility 업데이트

    date.py의 update_affection_action_visibility()를 호출하여
    데이트 중/일상 상태에 따라 can:hold_hands 등의 prop을 설정.

    또한 심부름 가능 여부도 업데이트.
    """
    try:
        import morld
        from date import update_affection_action_visibility
        player_id = morld.get_player_id()
        if player_id is not None:
            update_affection_action_visibility(player_id, partner_id)
            _update_errand_visibility(player_id, partner_id)
    except Exception as e:
        print(f"[assets] Failed to update affection visibility: {e}")


def call_instance_method(instance_id: int, method_name: str, args=None, equipment=None):
    """
    Asset 인스턴스의 메서드 호출 (call: 액션용)

    Objects, Items, Characters 레지스트리에서 순서대로 인스턴스를 찾아
    해당 메서드를 호출합니다.

    Args:
        instance_id: 인스턴스 ID (Unit ID 또는 Item ID)
        method_name: 호출할 메서드 이름
        args: 메서드에 전달할 인자 리스트 (None이면 빈 리스트)
        equipment: 장비 정보 dict (can: prop을 제공한 장비)
                   {"item_id": int, "unique_id": str, "name": str} 또는 None

    Returns:
        메서드 반환값 (Generator 또는 dict)
    """
    if args is None:
        args = []

    def _call_method(instance, method):
        """equipment 파라미터 지원 여부에 따라 메서드 호출"""
        accepts = _method_accepts_equipment(method)
        if equipment is not None and accepts:
            return method(*args, equipment=equipment)
        else:
            return method(*args)

    # 1. Objects 레지스트리에서 찾기
    from assets import objects
    instance = objects.get_instance(instance_id)
    if instance is not None:
        method = getattr(instance, method_name, None)
        if method is not None:
            return _call_method(instance, method)
        print(f"[assets] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    # 2. Items 레지스트리에서 찾기
    from assets import items
    instance = items.get_instance(instance_id)
    if instance is not None:
        method = getattr(instance, method_name, None)
        if method is not None:
            return _call_method(instance, method)
        print(f"[assets] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    # 3. Characters 레지스트리에서 찾기
    from assets import characters
    instance = characters.get_instance(instance_id)
    if instance is not None:
        # 애정 표현 액션 visibility 업데이트 (focus 시점)
        _update_affection_visibility_if_needed(instance_id)

        method = getattr(instance, method_name, None)
        if method is not None:
            return _call_method(instance, method)
        print(f"[assets] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    print(f"[assets] Instance not found: {instance_id}")
    return None


# ========================================
# ID 중복 검사 (챕터 로드 후 호출)
# ========================================

def validate_instance_ids():
    """
    모든 레지스트리의 인스턴스 ID 중복 검사

    Objects, Items, Characters 레지스트리 간에 동일한 ID가
    사용되었는지 확인하고, 중복 발견 시 에러 발생.

    Raises:
        ValueError: 중복 ID가 발견된 경우
    """
    from assets import objects, items, characters

    # 각 레지스트리의 ID 수집
    object_ids = set(objects._instances.keys())
    item_ids = set(items._instances.keys())
    character_ids = set(characters._instances.keys())

    errors = []

    # Objects 내부 중복 체크 (register 시점에서 덮어쓰므로 여기선 체크 불가)
    # 대신 레지스트리 간 중복 체크

    # Objects vs Items
    overlap_obj_item = object_ids & item_ids
    if overlap_obj_item:
        for dup_id in overlap_obj_item:
            obj = objects.get_instance(dup_id)
            itm = items.get_instance(dup_id)
            errors.append(
                f"ID {dup_id} 중복: Object '{obj.__class__.__name__}' vs Item '{itm.__class__.__name__}'"
            )

    # Objects vs Characters
    overlap_obj_char = object_ids & character_ids
    if overlap_obj_char:
        for dup_id in overlap_obj_char:
            obj = objects.get_instance(dup_id)
            char = characters.get_instance(dup_id)
            errors.append(
                f"ID {dup_id} 중복: Object '{obj.__class__.__name__}' vs Character '{char.__class__.__name__}'"
            )

    # Items vs Characters
    overlap_item_char = item_ids & character_ids
    if overlap_item_char:
        for dup_id in overlap_item_char:
            itm = items.get_instance(dup_id)
            char = characters.get_instance(dup_id)
            errors.append(
                f"ID {dup_id} 중복: Item '{itm.__class__.__name__}' vs Character '{char.__class__.__name__}'"
            )

    if errors:
        error_msg = "[assets] Instance ID 중복 검사 실패:\n" + "\n".join(f"  - {e}" for e in errors)
        print(error_msg)
        raise ValueError(error_msg)

    # 성공 로그
    total = len(object_ids) + len(item_ids) + len(character_ids)
    print(f"[assets] Instance ID 검사 완료: {total}개 (Objects: {len(object_ids)}, Items: {len(item_ids)}, Characters: {len(character_ids)})")


# ========================================
# 상태 기반 액션 필터링 API (C#에서 호출)
# ========================================

def get_available_actions(unit_id: int):
    """
    유닛의 현재 상태에서 사용 가능한 액션 목록 반환

    Character의 get_available_actions() 메서드를 호출하여
    activity/mood에 따라 필터링된 액션 목록을 반환합니다.

    또한 NPC Focus 시점에서 심부름(errand) 버튼 visibility를 업데이트합니다.

    Args:
        unit_id: 유닛 ID

    Returns:
        필터링된 액션 문자열 리스트 또는 None (필터링 없음)
    """
    from assets import characters
    import morld

    instance = characters.get_instance(unit_id)
    if instance is None:
        return None  # 캐릭터가 아니면 필터링 없음

    # NPC Focus 시 심부름 visibility 업데이트
    player_id = morld.get_player_id()
    if player_id is not None:
        _update_errand_visibility(player_id, unit_id)

    if hasattr(instance, 'get_available_actions'):
        return instance.get_available_actions()

    return None


def get_action_blocked_message(unit_id: int):
    """
    유닛의 현재 상태 차단 메시지 반환

    Args:
        unit_id: 유닛 ID

    Returns:
        차단 메시지 문자열 또는 None
    """
    from assets import characters

    instance = characters.get_instance(unit_id)
    if instance is None:
        return None

    if hasattr(instance, 'get_action_blocked_message'):
        return instance.get_action_blocked_message()

    return None
