# body_gate.py — 부위 상태 → 능력 차단/페널티 통합 진입점
#
# 차단 (binary):
#   - 결박 (S02 결박:{부위} prop 직접 검사 — 향후 engine/restraint.py 통합 시 import 변경)
#   - 결손 (loss.is_part_lost — 보조구 없을 때만 죽은 부위로 간주)
# 부상은 차단 안 함 — multiplier 만 노출 (호출부에서 명중률/속도 등에 곱셈).
#
# 호출부는 can_* / get_*_factor 만 사용 — 내부 시스템(결박/결손/부상) 변경 시 영향 없음.
#
# 향후 작업 (현재 구조 단계에서는 효과 미적용):
#   - encounter.py 명중/데미지: get_hand_factor 곱셈
#   - move 시스템: get_mobility_factor 곱셈
#   - dialogue 발화: can_speak 가드

import morld

from engine import body_state, injury, loss


# === 차단 (binary) ===

def can_use_hands(uid) -> bool:
    if _restraint_bound_upper(uid):
        return False
    if _ability_lost(uid, "hands"):
        return False
    return True


def can_move(uid) -> bool:
    if _restraint_bound_lower(uid):
        return False
    if _ability_lost(uid, "mobility"):
        return False
    return True


def can_speak(uid) -> bool:
    if morld.get_unit_prop(uid, "결박:입"):
        return False
    if _ability_lost(uid, "speech"):
        return False
    return True


def can_see(uid) -> bool:
    if morld.get_unit_prop(uid, "결박:눈"):
        return False
    if _ability_lost(uid, "vision"):
        return False
    return True


def can_hear(uid) -> bool:
    if _ability_lost(uid, "hearing"):
        return False
    return True


# === Factor (0.0~1.0 multiplier — 부상 페널티) ===

def get_hand_factor(uid) -> float:
    """팔 능력 0.0~1.0. 명중률/공격력 곱셈용."""
    return _ability_factor(uid, "hands")


def get_mobility_factor(uid) -> float:
    """이동 능력 0.0~1.0. 이동 속도 곱셈용."""
    return _ability_factor(uid, "mobility")


def get_speech_factor(uid) -> float:
    return _ability_factor(uid, "speech")


def get_vision_factor(uid) -> float:
    return _ability_factor(uid, "vision")


def get_hearing_factor(uid) -> float:
    return _ability_factor(uid, "hearing")


# === 내부 ===

def _ability_lost(uid, ability: str) -> bool:
    """능력 차단 판정 — layout + aggregation 룰.

    "any" (default): 모든 부위 죽음 → 차단.
    "all":           한 부위라도 죽음 → 차단.
    """
    layout = body_state.get_body_layout(uid)
    parts = layout.get(ability, [])
    if not parts:
        return False
    losts = [loss.is_part_lost(uid, p) for p in parts]
    rule = body_state.get_aggregation(ability)
    if rule == "all":
        return any(losts)
    return all(losts)


def _ability_factor(uid, ability: str) -> float:
    """능력 multiplier — layout + aggregation 룰.

    "any": max(부위 factors) — 가장 멀쩡한 부위 기준.
    "all": min(부위 factors) — 가장 손상된 부위 기준.
    """
    layout = body_state.get_body_layout(uid)
    parts = layout.get(ability, [])
    if not parts:
        return 1.0
    factors = [_part_factor(uid, p) for p in parts]
    rule = body_state.get_aggregation(ability)
    if rule == "all":
        return min(factors)
    return max(factors)


def _part_factor(uid, part: str) -> float:
    """부위 단일 multiplier. 결손+보조구없음=0, 부상정도/100 차감."""
    if loss.is_part_lost(uid, part):
        return 0.0
    sev = injury.get_severity(uid, part)
    return max(0.0, 1.0 - sev / 100)


def _restraint_bound_upper(uid) -> bool:
    """결박:상체. 향후 engine/restraint.py 통합 시 import."""
    return bool(morld.get_unit_prop(uid, "결박:상체"))


def _restraint_bound_lower(uid) -> bool:
    return bool(morld.get_unit_prop(uid, "결박:하체"))
