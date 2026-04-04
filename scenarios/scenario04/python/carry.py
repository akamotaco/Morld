# carry.py - S04 운반/납치 시스템
#
# S02 carry.py 기반 경량화.
# 실신 NPC를 물리적으로 운반.
# 무게 시스템 연동 (운반 대상 체중 추가).
# 운반 중 디스어드밴티지 (이동속도↓, 함정감지↓, 회피↓).
# 파티원에게 운반 지시 가능.

import morld

# === 상태 ===
# carrier_id -> carried_id
_carry_map = {}
# carried_id -> carrier_id (역방향)
_reverse_map = {}


def reset():
    _carry_map.clear()
    _reverse_map.clear()


def is_carrying(carrier_id: int) -> bool:
    return carrier_id in _carry_map


def is_being_carried(unit_id: int) -> bool:
    return unit_id in _reverse_map


def get_carried(carrier_id: int) -> int:
    """운반 중인 대상 ID (없으면 None)"""
    return _carry_map.get(carrier_id)


def get_carrier(unit_id: int) -> int:
    """운반하는 자 ID (없으면 None)"""
    return _reverse_map.get(unit_id)


def can_pick_up(carrier_id: int, target_id: int) -> tuple:
    """
    운반 가능 여부 체크.

    Returns:
        (bool, str): (가능 여부, 사유)
    """
    if is_carrying(carrier_id):
        return False, "이미 누군가를 운반 중입니다."

    if is_being_carried(target_id):
        return False, "이미 운반되고 있습니다."

    # 실신 상태만 운반 가능
    if not morld.get_unit_prop(target_id, "상태:실신") and \
       not morld.get_unit_prop(target_id, "상태:감금"):
        return False, "의식이 있는 대상은 운반할 수 없습니다."

    # 무게 체크
    carrier_str = morld.get_unit_prop(carrier_id, "스탯:근력") or 10
    target_weight = morld.get_unit_prop(target_id, "무게") or 60  # 기본 60kg
    max_carry_weight = carrier_str * 8  # 근력 10 = 80kg

    if target_weight > max_carry_weight:
        return False, "너무 무거워서 들 수 없습니다."

    return True, "운반 가능"


def pick_up(carrier_id: int, target_id: int) -> bool:
    """운반 시작"""
    ok, reason = can_pick_up(carrier_id, target_id)
    if not ok:
        print(f"[carry] Cannot pick up: {reason}")
        return False

    _carry_map[carrier_id] = target_id
    _reverse_map[target_id] = carrier_id

    morld.set_unit_prop(carrier_id, "상태:운반중", 1)
    morld.set_unit_prop(target_id, "상태:운반됨", 1)

    # 운반 대상을 운반자와 같은 위치로
    loc = morld.get_unit_location(carrier_id)
    if loc:
        region_id, loc_id = loc
        carrier_info = morld.get_unit_info(carrier_id)
        x = carrier_info.get("x", 0) if carrier_info else 0
        morld.set_unit_location(target_id, region_id, loc_id, x=x)

    name_carrier = ""
    name_target = ""
    info = morld.get_unit_info(carrier_id)
    if info:
        name_carrier = info.get("name", "???")
    info = morld.get_unit_info(target_id)
    if info:
        name_target = info.get("name", "???")
    print(f"[carry] {name_carrier} picked up {name_target}")
    return True


def put_down(carrier_id: int) -> int:
    """
    운반 대상 내려놓기.

    Returns:
        내려놓은 unit_id (없으면 None)
    """
    target_id = _carry_map.pop(carrier_id, None)
    if target_id is None:
        return None

    _reverse_map.pop(target_id, None)

    morld.set_unit_prop(carrier_id, "상태:운반중", 0)
    morld.set_unit_prop(target_id, "상태:운반됨", 0)

    print(f"[carry] Put down unit {target_id}")
    return target_id


# === 디스어드밴티지 ===

def get_carry_penalties(carrier_id: int) -> dict:
    """
    운반 중 패널티 조회.

    Returns:
        {"speed_mult": float, "detection_mult": float, "evasion_mult": float}
    """
    if not is_carrying(carrier_id):
        return {"speed_mult": 1.0, "detection_mult": 1.0, "evasion_mult": 1.0}

    return {
        "speed_mult": 0.5,       # 이동속도 50%
        "detection_mult": 0.3,   # 함정감지 30%
        "evasion_mult": 0.5,     # 회피 50%
    }


# === 운반 중 이동 동기화 ===

def sync_carried_position(carrier_id: int):
    """운반자 이동 시 대상도 같은 위치로"""
    target_id = get_carried(carrier_id)
    if target_id is None:
        return

    loc = morld.get_unit_location(carrier_id)
    if loc:
        region_id, loc_id = loc
        carrier_info = morld.get_unit_info(carrier_id)
        x = carrier_info.get("x", 0) if carrier_info else 0
        morld.set_unit_location(target_id, region_id, loc_id, x=x)
