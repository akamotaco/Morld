# obedience.py - S04 복종도 시스템
#
# 파티원이 플레이어 결정을 얼마나 따르는지. 신뢰(호감)와 분리.
# - 신뢰: "너를 믿는다" (감정/관계)
# - 복종: "너의 지시를 따른다" (위계/충성)
#
# 다수결 flip 판정에서 MAX(신뢰, 복종) 기반 roll.
# 낮은 신뢰여도 높은 복종이면 따름 (군대/계약 모델).

import morld


# === 상수 ===
OBEDIENCE_MAX = 100
OBEDIENCE_DEFAULT = 0  # 기본 0 — 복종은 축적해야 함 (신뢰와 달리 initial 중립 없음)


def reset():
    """챕터 전환 시 리셋"""
    pass  # prop 기반이므로 clear_world()로 초기화됨


def get_obedience(unit_id: int) -> int:
    val = morld.get_unit_prop(unit_id, "복종도")
    return int(val) if val is not None else OBEDIENCE_DEFAULT


def set_obedience(unit_id: int, value: int):
    morld.set_unit_prop(unit_id, "복종도", max(0, min(OBEDIENCE_MAX, value)))


def modify_obedience(unit_id: int, delta: int):
    set_obedience(unit_id, get_obedience(unit_id) + delta)


# === 복종 변동 이벤트 (차후 확장) ===

def on_order_followed(unit_id: int):
    """지시를 따랐을 때 — 복종 상승"""
    modify_obedience(unit_id, 2)


def on_order_defied(unit_id: int):
    """지시를 거부했을 때 — 복종 감소"""
    modify_obedience(unit_id, -5)
