# equipment.py - 장비 시스템
#
# 아이템 장착/해제 처리
# C#의 InventorySystem.EquipItem/UnequipItem 호출
# equip_props 반영은 C# Unit.GetActualProps()에서 자동 처리

import morld


def equip_item(unit_id: int, item_id: int) -> bool:
    """
    아이템 장착

    Args:
        unit_id: 유닛 ID
        item_id: 아이템 ID

    Returns:
        성공 여부
    """
    result = morld.equip_item_internal(unit_id, item_id)
    if result:
        # 장착 시 put 액션 비활성화 (상대값 -1)
        # 원래 값이 0이면 -1, 1이면 0이 됨
        # Note: get_item_action_prop은 키가 없으면 0 반환 (prop은 항상 정수)
        current = morld.get_item_action_prop(item_id, "put")
        morld.set_item_action_prop(item_id, "put", current - 1)
    return result


def unequip_item(unit_id: int, item_id: int) -> bool:
    """
    아이템 장착 해제

    Args:
        unit_id: 유닛 ID
        item_id: 아이템 ID

    Returns:
        성공 여부
    """
    result = morld.unequip_item_internal(unit_id, item_id)
    if result:
        # 장착 해제 시 put 액션 복원 (상대값 +1)
        # -1이면 0, 0이면 1이 됨
        # Note: get_item_action_prop은 키가 없으면 0 반환 (prop은 항상 정수)
        current = morld.get_item_action_prop(item_id, "put")
        morld.set_item_action_prop(item_id, "put", current + 1)
    return result


def is_equipped(unit_id: int, item_id: int) -> bool:
    """
    아이템 장착 여부 확인

    Args:
        unit_id: 유닛 ID
        item_id: 아이템 ID

    Returns:
        장착 여부
    """
    return morld.is_equipped(unit_id, item_id)


def get_equipped_items(unit_id: int) -> list:
    """
    장착 중인 아이템 ID 목록

    Args:
        unit_id: 유닛 ID

    Returns:
        장착 아이템 ID 리스트
    """
    return morld.get_equipped_items(unit_id)
