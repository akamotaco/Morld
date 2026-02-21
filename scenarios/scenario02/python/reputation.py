# reputation.py - 평판 시스템 (간접 관계 전파)
#
# 직접 경험: 관계:{name}:호감 (기존 시스템, 0-100)
# 간접 전파: 평판:{name} (이 모듈, -100 ~ 100)
#
# 전파 시점: NPC-NPC 대화 완료 시 (social.py talking phase)
# 전파 대상: 화자가 아는 제3자 전원 (관계 prop 존재하는 대상)
# 전파 강도: 아키타입 기반
#
# 자연 감쇠: -0.3/h → 0 수렴 (소문이므로 빠르게 퇴색)

import morld

# 아키타입별 전파 강도 (화자가 말할 때 얼마나 영향력 있는지)
PROPAGATION_STRENGTH = {
    "stoic": 0.3,
    "gentle": 0.6,
    "cheerful": 1.0,
    "timid": 0.2,
    "cold": 0.4,
    "seductive": 0.7,
    "fierce": 0.8,
    "proud": 0.5,
    "innocent": 0.5,
    "devoted": 0.6,
}

DECAY_RATE = 0.3  # 시간당 0 방향 감쇠


# ========================================
# 조회 API
# ========================================

def get_reputation(unit_id, target_name):
    """평판 조회 (-100 ~ 100, 0 = 중립)"""
    return morld.get_unit_prop(unit_id, f"평판:{target_name}") or 0


# ========================================
# 전파
# ========================================

def _get_archetype(unit_id):
    """unit_id의 아키타입 조회"""
    from think import _agents
    agent = _agents.get(unit_id)
    if agent:
        profile = getattr(agent, 'REACTION_PROFILE', None)
        if profile:
            return profile.get("archetype", "stoic")
    return "stoic"


def _get_name(unit_id):
    """unit_id → 이름"""
    info = morld.get_unit_info(unit_id)
    return info.get("name", "") if info else ""


def propagate(speaker_id, listener_id):
    """화자의 관계 정보를 청자의 평판으로 전파

    화자가 아는 제3자에 대해, 화자의 호감(0-100)을
    중립 기준(50)으로 변환하여 청자 평판에 반영.
    """
    speaker_props = morld.get_unit_props(speaker_id)
    if not speaker_props:
        return

    archetype = _get_archetype(speaker_id)
    strength = PROPAGATION_STRENGTH.get(archetype, 0.5)

    listener_name = _get_name(listener_id)

    for key, val in speaker_props.items():
        if not key.startswith("관계:") or not key.endswith(":호감"):
            continue
        if not isinstance(val, (int, float)):
            continue
        third_name = key.split(":")[1]
        # 청자 자신은 스킵
        if third_name == listener_name:
            continue

        # 화자의 인식: 호감 0-100 → -50~+50 스케일
        speaker_view = val - 50

        # 청자의 기존 평판
        cur_rep = get_reputation(listener_id, third_name)

        # 전파: 기존 평판을 화자 관점으로 이동 (strength 비율만큼)
        delta = (speaker_view - cur_rep) * strength * 0.3
        new_rep = max(-100, min(100, cur_rep + delta))
        if abs(new_rep - cur_rep) > 0.01:
            morld.set_unit_prop(listener_id, f"평판:{third_name}", new_rep)


# ========================================
# 자연 감쇠
# ========================================

def decay_hourly(unit_id):
    """평판 자연 감쇠 — 시간당 DECAY_RATE만큼 0으로 수렴"""
    props = morld.get_unit_props(unit_id)
    if not props:
        return
    for key, val in props.items():
        if not key.startswith("평판:"):
            continue
        if not isinstance(val, (int, float)) or val == 0:
            continue
        if val > 0:
            new_val = max(0, val - DECAY_RATE)
        else:
            new_val = min(0, val + DECAY_RATE)
        if new_val != val:
            morld.set_unit_prop(unit_id, key, new_val)


# ========================================
# 리셋
# ========================================

def reset():
    """챕터 전환 시 리셋 (상태 없음 — prop 기반이므로 clear_world()로 자동 정리)"""
    pass
