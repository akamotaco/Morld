# restraint.py — 결박 상태 조회 (엔진 공용)
#
# 결박 prop 기반 pure 상태 조회. 변경 액션 (장착/해제/저항)은 시나리오 책임 (S02 restraint.py).
#
# Prop schema (S02 호환 — 기존 prop 그대로):
#   결박:상체 = 1   # 팔/손 결박 (장비 해제 불가, 저항 불가, 이동 가능)
#   결박:하체 = 1   # 다리 결박 (이동 불가)
#   결박:입   = 1   # 말하기/구강/식사/소리 차단
#   결박:눈   = 1   # 시각 차단
#   결박:강도 = N   # 자력 해제 난이도
#   결박:자가 = 1   # 자가 결박 (S02 플레이어 전용)
#
# 통합 진입점은 body_gate (결박 + 결손 + 부상 multiplier 합산).

import morld


def is_upper_restrained(unit_id) -> bool:
    return bool(morld.get_unit_prop(unit_id, "결박:상체"))


def is_lower_restrained(unit_id) -> bool:
    return bool(morld.get_unit_prop(unit_id, "결박:하체"))


def is_restrained(unit_id) -> bool:
    """상체 또는 하체 결박."""
    return is_upper_restrained(unit_id) or is_lower_restrained(unit_id)


def is_fully_restrained(unit_id) -> bool:
    """상체+하체 동시 결박 — 탈출 불가."""
    return is_upper_restrained(unit_id) and is_lower_restrained(unit_id)


def is_gagged(unit_id) -> bool:
    return bool(morld.get_unit_prop(unit_id, "결박:입"))


def is_blindfolded(unit_id) -> bool:
    return bool(morld.get_unit_prop(unit_id, "결박:눈"))


def is_any_restrained(unit_id) -> bool:
    """상체/하체/입/눈 중 하나라도 결박."""
    return is_restrained(unit_id) or is_gagged(unit_id) or is_blindfolded(unit_id)


def is_self_restrained(unit_id) -> bool:
    """자가 결박 (S02 플레이어 전용 식별)."""
    return bool(morld.get_unit_prop(unit_id, "결박:자가"))


def get_restraint_strength(unit_id) -> int:
    """결박 강도 (자력 해제 난이도)."""
    return morld.get_unit_prop(unit_id, "결박:강도") or 0


def can_use_hands(unit_id) -> bool:
    """손 사용 가능 — 상체 결박 시 불가.

    주의: 결손/부상은 고려 안 함. 통합 판정은 body_gate.can_use_hands 사용.
    """
    return not is_upper_restrained(unit_id)


def can_escape_romance(unit_id) -> bool:
    """로맨스 탈출 가능 — 상체+하체 동시 결박 시 불가."""
    return not is_fully_restrained(unit_id)


def get_escape_multiplier(unit_id) -> float:
    """탈출 확률 배율 — 전신 0.0, 부분 0.3, 없음 1.0."""
    if is_fully_restrained(unit_id):
        return 0.0
    if is_upper_restrained(unit_id) or is_lower_restrained(unit_id):
        return 0.3
    return 1.0


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
