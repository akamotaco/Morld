# injury.py — 부상 시스템 (sparse prop, 누적, 체력 저항)
#
# 차단 없음 — 페널티는 body_gate.get_*_factor 가 담당.
# 회복은 시나리오가 트리거 (구호소/치료 아이템) — engine은 reduce API만 제공.
#
# Prop schema:
#   부상:{part}:정도 = 1~∞   # 0 도달 시 prop 정리 (sparse)
#   부상:{part}:종류 = 자유 문자열

import morld


_PROP_DEGREE = "부상:{}:정도"
_PROP_KIND = "부상:{}:종류"


def add_injury(uid, part: str, severity: int, kind: str = None) -> int:
    """부상 누적. 체력 저항 적용 후 prop에 가산.

    체력 저항 곡선 (침식 패턴 동일):
      resistance = 스탯:체력 × 0.02   (체력 10 = 20% 감쇠, 50 = 100% clamp)
      actual = max(1, severity × max(0.1, 1 - resistance))
      → 최저 10% 적용, 최소 1.

    Args:
        uid: 대상 유닛
        part: 부위 (자유 문자열)
        severity: 기본 부상량 (저항 전)
        kind: 종류 (옵션, 자유 문자열)

    Returns:
        실제 적용된 정도 (0이면 추가 안 됨).
    """
    if severity <= 0:
        return 0

    vit = morld.get_unit_prop(uid, "스탯:체력") or 10
    resistance = vit * 0.02
    actual = max(1, int(severity * max(0.1, 1.0 - resistance)))

    cur = get_severity(uid, part)
    morld.set_unit_prop(uid, _PROP_DEGREE.format(part), cur + actual)
    if kind:
        morld.set_unit_prop(uid, _PROP_KIND.format(part), kind)

    name = morld.get_unit_name(uid) or f"id={uid}"
    kind_str = f" ({kind})" if kind else ""
    morld.add_action_log(f"[{name}]의 {part}에 부상{kind_str} +{actual}")
    return actual


def reduce_injury(uid, part: str, amount: int) -> int:
    """부상 감소. 0 도달 시 prop 정리 (sparse cleanup).

    Returns:
        실제 감소량.
    """
    if amount <= 0:
        return 0
    cur = get_severity(uid, part)
    if cur == 0:
        return 0
    new_val = max(0, cur - amount)
    if new_val == 0:
        morld.set_unit_prop(uid, _PROP_DEGREE.format(part), None)
        morld.set_unit_prop(uid, _PROP_KIND.format(part), None)
    else:
        morld.set_unit_prop(uid, _PROP_DEGREE.format(part), new_val)
    return cur - new_val


def get_severity(uid, part: str) -> int:
    """부상 정도. prop 없으면 0."""
    val = morld.get_unit_prop(uid, _PROP_DEGREE.format(part))
    return int(val) if val else 0


def get_kind(uid, part: str) -> str:
    """부상 종류 (자유 문자열). 없으면 빈 문자열."""
    return morld.get_unit_prop(uid, _PROP_KIND.format(part)) or ""


def has_injury(uid, part: str) -> bool:
    return get_severity(uid, part) > 0


def get_injuries(uid) -> list:
    """layout 부위 + 표준 부위 중 부상 있는 것만 반환.

    sparse 모델이라 전체 prop enumerate 어려움 — layout 기반 + 표준 anatomy 점검.
    Returns:
        [(part, severity, kind), ...]
    """
    from engine import body_state
    layout = body_state.get_body_layout(uid)
    seen = set()
    parts = []
    for ability_parts in layout.values():
        for p in ability_parts:
            if p not in seen:
                seen.add(p)
                parts.append(p)
    # 몸통: layout에 없어도 표준 부위로 점검
    if body_state.PART_TORSO not in seen:
        parts.append(body_state.PART_TORSO)

    result = []
    for p in parts:
        sev = get_severity(uid, p)
        if sev > 0:
            result.append((p, sev, get_kind(uid, p)))
    return result


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
