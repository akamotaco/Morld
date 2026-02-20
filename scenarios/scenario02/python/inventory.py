# inventory.py - 슬롯 기반 인벤토리 용량 시스템
#
# 캐릭터(플레이어+NPC)는 제한된 인벤토리 슬롯을 가짐.
# 스택(같은 item_id) = 1슬롯. 총 슬롯 = 기본슬롯 + 근력 × 배율.
# 오브젝트/컨테이너는 무제한 (기존과 동일).
#
# Props:
#   인벤토리:기본슬롯 = base slots (default: 5)
#   인벤토리:배율     = strength multiplier (default: 1.0)
#   없으면 → 무제한 (시나리오03 호환)
#
# safe_give_item(): 인벤토리 추가 래퍼. 꽉 차면 바닥에 드롭.

import morld

# === 상수 ===

PROP_BASE_SLOTS = "인벤토리:기본슬롯"
PROP_MULTIPLIER = "인벤토리:배율"
DEFAULT_BASE_SLOTS = 5
DEFAULT_MULTIPLIER = 1.0


# ========================================
# 조회 API
# ========================================

def get_max_slots(unit_id):
    """
    캐릭터의 최대 인벤토리 슬롯 수.

    Returns:
        int (슬롯 수) 또는 None (무제한 — prop 미설정)
    """
    base = morld.get_unit_prop(unit_id, PROP_BASE_SLOTS)
    if not base:
        return None  # 무제한 (시나리오03 호환)

    base = int(base)
    multiplier = _get_multiplier(unit_id)
    strength = morld.get_unit_prop(unit_id, "근력") or 0
    return base + int(float(strength) * multiplier)


def get_used_slots(unit_id):
    """
    현재 사용 중인 슬롯 수 (distinct item_id 개수).

    Returns:
        int
    """
    return morld.get_inventory_slot_count(unit_id)


def get_free_slots(unit_id):
    """
    남은 슬롯 수.

    Returns:
        int 또는 None (무제한)
    """
    max_slots = get_max_slots(unit_id)
    if max_slots is None:
        return None
    used = get_used_slots(unit_id)
    return max(0, max_slots - used)


def has_free_slot(unit_id, item_id=None):
    """
    슬롯 여유가 있는지 확인.
    item_id가 주어지면 이미 인벤토리에 있는지(스택 추가) 체크.

    Returns:
        bool (True = 여유 있음 또는 무제한)
    """
    max_slots = get_max_slots(unit_id)
    if max_slots is None:
        return True  # 무제한

    # 이미 같은 아이템이 있으면 스택 추가이므로 슬롯 불필요
    if item_id is not None and morld.has_item(unit_id, item_id):
        return True

    used = get_used_slots(unit_id)
    return used < max_slots


# ========================================
# 실행 API
# ========================================

def safe_give_item(unit_id, item_id, count=1):
    """
    인벤토리에 아이템 추가. 용량 초과 시 바닥에 드롭.

    Returns:
        bool - True if added to inventory, False if dropped to ground
    """
    if has_free_slot(unit_id, item_id):
        morld.give_item(unit_id, item_id, count)
        return True

    # 용량 초과 → 바닥에 드롭
    import ground as ground_module
    ground_module.drop_item_at(unit_id, item_id, count)
    print(f"[inventory] overflow: unit={unit_id} item={item_id} x{count} → ground")
    return False


# ========================================
# 초기화
# ========================================

def init_character_slots(unit_id, base=DEFAULT_BASE_SLOTS, multiplier=DEFAULT_MULTIPLIER):
    """챕터 초기화에서 캐릭터 슬롯 prop 설정"""
    morld.set_unit_prop(unit_id, PROP_BASE_SLOTS, base)
    morld.set_unit_prop(unit_id, PROP_MULTIPLIER, int(multiplier * 100))
    # 배율은 정수 prop으로 저장 (1.0 → 100), 조회 시 /100


def _get_multiplier(unit_id):
    """배율 prop 읽기 (정수 → float 변환)"""
    val = morld.get_unit_prop(unit_id, PROP_MULTIPLIER)
    if not val:
        return DEFAULT_MULTIPLIER
    return float(val) / 100.0
