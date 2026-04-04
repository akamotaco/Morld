# corrosion.py - S04 부식 시스템 (장비/아이템)
#
# location 오염도에 비례하여 장비 내구도 감소.
# 부식된 장비: 성능 하락 → 최종 파괴.
# 대장간에서 수리 가능.

import morld
from events import subscribe_time_elapsed

# === 상수 ===
DURABILITY_MAX = 100
CORROSION_PER_POLLUTION_PER_HOUR = 0.3  # 오염도 1당 시간당 내구도 감소

# 부식 상태 임계치
CORROSION_WORN = 70      # 해짐 (성능 소폭 하락)
CORROSION_DAMAGED = 40   # 손상 (성능 중간 하락)
CORROSION_BROKEN = 10    # 파손 직전
CORROSION_DESTROYED = 0  # 파괴

# === 상태 ===
_accumulated_millis = 0


def reset():
    global _accumulated_millis
    _accumulated_millis = 0


def get_durability(item_id: int) -> int:
    val = morld.get_unit_prop(item_id, "내구도")
    return int(val) if val is not None else DURABILITY_MAX


def set_durability(item_id: int, value: int):
    morld.set_unit_prop(item_id, "내구도", max(0, min(DURABILITY_MAX, value)))


def get_corrosion_state(item_id: int) -> str:
    d = get_durability(item_id)
    if d <= CORROSION_DESTROYED:
        return "파괴"
    elif d <= CORROSION_BROKEN:
        return "파손"
    elif d <= CORROSION_DAMAGED:
        return "손상"
    elif d <= CORROSION_WORN:
        return "해짐"
    else:
        return "깨끗"


def get_performance_modifier(item_id: int) -> float:
    """부식에 따른 성능 보정 (1.0 = 정상)"""
    d = get_durability(item_id)
    if d <= CORROSION_DESTROYED:
        return 0.0
    elif d <= CORROSION_BROKEN:
        return 0.3
    elif d <= CORROSION_DAMAGED:
        return 0.6
    elif d <= CORROSION_WORN:
        return 0.85
    return 1.0


def repair(item_id: int, amount: int = None):
    """수리 (대장간)"""
    if amount is None:
        amount = DURABILITY_MAX
    current = get_durability(item_id)
    set_durability(item_id, min(DURABILITY_MAX, current + amount))


def apply_corrosion(item_id: int, amount: float):
    """부식 적용"""
    current = get_durability(item_id)
    new_val = max(0, current - amount)
    set_durability(item_id, int(new_val))

    if new_val <= 0 and current > 0:
        print(f"[corrosion] Item {item_id} destroyed by corrosion!")
        # 아이템 상태 prop
        morld.set_unit_prop(item_id, "상태:파괴", 1)


# === 아이템 상태 prop (피묻음/해짐/부식) ===

def set_bloody(item_id: int):
    morld.set_unit_prop(item_id, "상태:피묻음", 1)


def set_clean(item_id: int):
    morld.set_unit_prop(item_id, "상태:피묻음", 0)
    morld.set_unit_prop(item_id, "상태:부식흔적", 0)


def is_bloody(item_id: int) -> bool:
    return bool(morld.get_unit_prop(item_id, "상태:피묻음"))


# === 시간 경과: 파티원 장비 부식 ===

def _on_time_elapsed(millis: int):
    global _accumulated_millis
    _accumulated_millis += millis

    hours = _accumulated_millis // 3600000
    if hours < 1:
        return
    _accumulated_millis %= 3600000

    import party, pollution

    for mid in party.get_members():
        loc = morld.get_unit_location(mid)
        if not loc:
            continue
        region_id, loc_id = loc
        poll = pollution.get_pollution(region_id, loc_id)

        if poll > 0:
            # 장착 중인 장비에 부식 적용
            equipped = morld.get_equipped_items(mid) if hasattr(morld, 'get_equipped_items') else []
            for item_id in equipped:
                amount = poll * CORROSION_PER_POLLUTION_PER_HOUR * hours
                apply_corrosion(item_id, amount)


subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
