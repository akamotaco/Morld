# inventory.py — S04 slim stub
#
# S04는 인벤토리 슬롯 제한 시스템을 쓰지 않음 (무제한 모드, S03 호환).
# describe_system.cs가 `import inventory`로 조회하지만 get_max_slots=None이면
# 슬롯 표시를 skip. ModuleNotFoundError 방지용 stub.

import morld


def get_max_slots(unit_id):
    """무제한 모드 — None 반환 시 describe_system이 슬롯 표시를 skip"""
    return None


def get_used_slots(unit_id):
    """사용 중 슬롯 수 (distinct item_id 개수)"""
    return morld.get_inventory_slot_count(unit_id)


def get_free_slots(unit_id):
    return None  # 무제한


def has_free_slot(unit_id, item_id=None):
    return True  # 항상 여유 있음
