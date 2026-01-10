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
#   loc.instantiate(12, REGION_ID)
#   loc.add_item_to_ground(herb)

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

def call_instance_method(instance_id: int, method_name: str, *args):
    """
    Asset 인스턴스의 메서드 호출 (call: 액션용)

    Objects, Items, Characters 레지스트리에서 순서대로 인스턴스를 찾아
    해당 메서드를 호출합니다.

    Args:
        instance_id: 인스턴스 ID (Unit ID 또는 Item ID)
        method_name: 호출할 메서드 이름
        *args: 메서드에 전달할 인자들

    Returns:
        메서드 반환값 (Generator 또는 dict)
    """
    # 1. Objects 레지스트리에서 찾기
    from assets import objects
    instance = objects.get_instance(instance_id)
    if instance is not None:
        method = getattr(instance, method_name, None)
        if method is not None:
            return method(*args)
        print(f"[assets] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    # 2. Items 레지스트리에서 찾기
    from assets import items
    instance = items.get_instance(instance_id)
    if instance is not None:
        method = getattr(instance, method_name, None)
        if method is not None:
            return method(*args)
        print(f"[assets] Method not found: {method_name} on {instance.__class__.__name__}")
        return None

    # 3. Characters 레지스트리에서 찾기
    from assets import characters
    instance = characters.get_instance(instance_id)
    if instance is not None:
        method = getattr(instance, method_name, None)
        if method is not None:
            return method(*args)
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
