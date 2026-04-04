# morale.py - S04 사기 시스템
#
# 사기는 개인별 수치. 파티 사기 = 평균 + 분산.
# 플레이어도 사기 영향 받음.
#
# 사기 변동: 전투 결과, 분배, 동료 상태, 기벽 등에 의해 변동.
# 파티원 전원에게 공통 적용 (개인 수치에 각각 반영).

import morld
import math

# === 상수 ===
MORALE_MAX = 100
MORALE_DEFAULT = 70

MORALE_STABLE = 70      # 안정
MORALE_SHAKEN = 40      # 동요
MORALE_DANGER = 20      # 위험
MORALE_COLLAPSE = 0     # 붕괴


def reset():
    """챕터 전환 시 리셋"""
    pass  # 개인 사기는 prop 기반이므로 clear_world()로 초기화됨


def get_morale(unit_id: int) -> int:
    """개인 사기 조회"""
    val = morld.get_unit_prop(unit_id, "사기")
    return int(val) if val is not None else MORALE_DEFAULT


def set_morale(unit_id: int, value: int):
    """개인 사기 설정"""
    morld.set_unit_prop(unit_id, "사기", max(0, min(MORALE_MAX, value)))


def modify_morale(unit_id: int, delta: int):
    """개인 사기 변경"""
    current = get_morale(unit_id)
    set_morale(unit_id, current + delta)


def get_morale_state(unit_id: int) -> str:
    """개인 사기 상태"""
    m = get_morale(unit_id)
    if m >= MORALE_STABLE:
        return "안정"
    elif m >= MORALE_SHAKEN:
        return "동요"
    elif m >= MORALE_DANGER:
        return "위험"
    else:
        return "붕괴"


# === 파티 사기 (평균 + 분산) ===

def get_party_morale() -> dict:
    """
    파티 전체 사기 요약.

    Returns:
        {"average": float, "min": int, "max": int, "std": float, "warning": str}
    """
    import party

    members = party.get_members()
    if not members:
        return {"average": 0, "min": 0, "max": 0, "std": 0, "warning": "파티 없음"}

    morales = [get_morale(mid) for mid in members]
    avg = sum(morales) / len(morales)
    mn = min(morales)
    mx = max(morales)

    # 표준편차
    if len(morales) > 1:
        variance = sum((m - avg) ** 2 for m in morales) / len(morales)
        std = math.sqrt(variance)
    else:
        std = 0

    # 경고 판정
    if mn <= MORALE_DANGER:
        warning = "위험 — 반란/이탈 임박"
    elif std > 20:
        warning = "불온한 기운이 감지된다"
    else:
        warning = ""

    return {
        "average": round(avg, 1),
        "min": mn,
        "max": mx,
        "std": round(std, 1),
        "warning": warning,
    }


# === 파티 전체 사기 변동 ===

def modify_party_morale(delta: int):
    """파티원 전원에게 사기 변동 적용"""
    import party

    for mid in party.get_members():
        modify_morale(mid, delta)


# 편의 함수: 이벤트별

def on_battle_victory():
    modify_party_morale(5)

def on_battle_defeat():
    modify_party_morale(-8)

def on_treasure_found():
    modify_party_morale(3)

def on_ally_fainted(fainted_id: int):
    modify_party_morale(-10)

def on_food_shortage():
    modify_party_morale(-5)

def on_floor_cleared():
    modify_party_morale(7)

def on_twist_revealed():
    """꺾기 사실 인지"""
    modify_party_morale(-15)

def on_affliction(afflicted_id: int):
    """고질 발생 — 본인 + 파티 전원"""
    modify_morale(afflicted_id, -10)
    modify_party_morale(-3)

def on_awakening(awakened_id: int):
    """깨우침 발생"""
    modify_party_morale(5)
