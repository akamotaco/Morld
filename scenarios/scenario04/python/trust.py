# trust.py - S04 신뢰도 시스템
#
# 각 파티원은 플레이어에 대한 신뢰도를 가짐.
# 행동에 따라 변동. 낮으면 불복/배신/반란.

import morld

# === 상수 ===
TRUST_MAX = 100
TRUST_DEFAULT = 50
TRUST_LOYALTY_THRESHOLD = 70    # 충성
TRUST_DISCONTENT_THRESHOLD = 30  # 불만
TRUST_HOSTILE_THRESHOLD = 10     # 적대


def get_trust(unit_id: int) -> int:
    """신뢰도 조회"""
    val = morld.get_unit_prop(unit_id, "신뢰도")
    return int(val) if val is not None else TRUST_DEFAULT


def set_trust(unit_id: int, value: int):
    """신뢰도 설정"""
    morld.set_unit_prop(unit_id, "신뢰도", max(0, min(TRUST_MAX, value)))


def modify_trust(unit_id: int, delta: int):
    """신뢰도 변경"""
    current = get_trust(unit_id)
    set_trust(unit_id, current + delta)


def get_trust_state(unit_id: int) -> str:
    """신뢰도 상태 문자열"""
    trust = get_trust(unit_id)
    if trust >= TRUST_LOYALTY_THRESHOLD:
        return "충성"
    elif trust >= TRUST_DISCONTENT_THRESHOLD:
        return "보통"
    elif trust >= TRUST_HOSTILE_THRESHOLD:
        return "불만"
    else:
        return "적대"


# === 신뢰 변동 이벤트 ===

def on_protect_in_battle(unit_id: int):
    modify_trust(unit_id, 5)

def on_fair_distribution(unit_id: int):
    modify_trust(unit_id, 3)

def on_conversation(unit_id: int):
    modify_trust(unit_id, 2)

def on_rescue(unit_id: int):
    modify_trust(unit_id, 10)

def on_unfair_distribution(unit_id: int):
    modify_trust(unit_id, -5)

def on_abandoned_in_danger(unit_id: int):
    modify_trust(unit_id, -8)

def on_witnessed_cruelty(unit_id: int):
    """동료 탈락/납치/조교 목격"""
    modify_trust(unit_id, -15)
