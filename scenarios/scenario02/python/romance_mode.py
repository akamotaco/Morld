# romance_mode.py - 연애 행위 동작 모드 시스템
"""
연애 세션의 동작 모드 정의 및 관리

4가지 모드:
- consensual: 합의 (기본 - 상호 동의)
- forced: 강제 (의식 있는 대상, 저항 가능)
- unconscious: 무의식 (기절 대상, 각성 시 forced로 전이)
- frozen: 시간정지 (정지 대상, 효과 지연)
"""

import morld

# ============================================
# 모드 상수
# ============================================

MODE_CONSENSUAL = "consensual"
MODE_FORCED = "forced"
MODE_UNCONSCIOUS = "unconscious"
MODE_FROZEN = "frozen"


# ============================================
# 모드 컨텍스트 생성
# ============================================

def create_mode_context(mode, actor_id, target_id):
    """모드 컨텍스트 생성

    Args:
        mode: MODE_CONSENSUAL / MODE_FORCED / MODE_UNCONSCIOUS / MODE_FROZEN
        actor_id: 주도하는 쪽 (플레이어 or NPC)
        target_id: 대상

    Returns:
        dict: 모드별 상태 컨텍스트
    """
    ctx = {
        "mode": mode,
        "actor_id": actor_id,
        "target_id": target_id,
        "action_count": 0,      # 수행한 행위 횟수 (종료 시 패널티 계산용)
    }

    if mode == MODE_FORCED:
        ctx["resistance_meter"] = 0       # 대상 저항 축적 (100 도달 시 탈출)
        ctx["break_free_attempts"] = 0

    elif mode == MODE_UNCONSCIOUS:
        ctx["wake_check_accum"] = 0       # 각성 체크 누적 시간 (ms)

    elif mode == MODE_FROZEN:
        ctx["deferred_effects"] = []      # 해제 후 일괄 적용할 효과
        ctx["deferred_semen"] = {}        # 해제 후 적용할 정액 {부위: 양}
        ctx["deferred_internal_semen"] = {}  # 체내 정액 {부위: 양}
        ctx["deferred_climax_count"] = 0

    return ctx


# ============================================
# 모드별 동작 변경 훅 (순수 함수)
# ============================================

def get_affection_req(mode):
    """모드별 호감도 요구치 오버라이드

    Returns:
        int or None: None이면 정상 체크, 0이면 무조건 통과
    """
    if mode == MODE_CONSENSUAL:
        return None  # 정상 체크
    return 0  # forced/unconscious/frozen: 호감 무시


def get_effect_multipliers(mode):
    """모드별 효과 배율

    Returns:
        dict: {affection, desire, rebellion, submission, arousal, sensation_exp}
    """
    if mode == MODE_CONSENSUAL:
        return {
            "affection": 1.0, "desire": 1.0, "rebellion": 1.0,
            "submission": 1.0, "arousal": 1.0, "sensation_exp": 1.0,
        }
    elif mode == MODE_FORCED:
        return {
            "affection": 0.0,       # 호감 변화 없음
            "desire": 0.5,          # 욕망 절반
            "rebellion": 2.0,       # 반발 2배
            "submission": 2.0,      # 복종 2배 가속
            "arousal": 1.0,         # 성욕 정상
            "sensation_exp": 0.5,   # 경험치 절반
        }
    elif mode == MODE_UNCONSCIOUS:
        return {
            "affection": 0.0,       # 감정 효과 억제
            "desire": 0.0,
            "rebellion": 0.0,
            "submission": 0.0,
            "arousal": 0.5,         # 물리적 반사 (절반)
            "sensation_exp": 0.5,   # 경험치 절반
        }
    elif mode == MODE_FROZEN:
        return {
            # 관계 효과는 정상 계산 후 defer_effect로 축적
            # 실제 감쇠(30%)는 apply_deferred_effects에서 적용
            "affection": 1.0, "desire": 1.0, "rebellion": 1.0,
            "submission": 1.0, "arousal": 1.0,
            # 감각 경험치는 시간정지 중 미적용 (신경계 정지)
            "sensation_exp": 0.0,
        }
    return {}


def get_reaction_prefix(mode):
    """모드별 반응 키 접두사

    Returns:
        str: 반응 키 앞에 붙일 접두사 ("" = 일반, "forced_" = 강제 전용)
              None이면 반응 없음 (무반응 나레이션)
    """
    if mode == MODE_CONSENSUAL:
        return ""
    elif mode == MODE_FORCED:
        return "forced_"
    return None  # unconscious, frozen: 반응 없음


def should_advance_time(mode):
    """시간 경과 여부"""
    return mode != MODE_FROZEN


def should_emit_sound(mode):
    """소리 방출 여부"""
    return mode in (MODE_CONSENSUAL, MODE_FORCED)


def should_check_third_party(mode):
    """제3자 감지 체크 여부"""
    return mode != MODE_FROZEN


def can_switch_initiative(mode):
    """주도권 전환 가능 여부"""
    return mode == MODE_CONSENSUAL


def can_target_resist(mode):
    """대상이 저항 가능한지"""
    return mode == MODE_FORCED


def should_check_wakeup(mode):
    """각성 체크 필요 여부"""
    return mode == MODE_UNCONSCIOUS


# ============================================
# 진입 판정
# ============================================

def get_unit_power(unit_id):
    """유닛의 전투/제압 능력치 계산

    power = 근력 + 체격 + (현재체력/최대체력) × 3

    Returns:
        float: 종합 제압 능력치
    """
    props = morld.get_unit_props(unit_id) or {}
    strength = props.get("근력", 5)

    # 체격 (gender.py의 get_body_size와 동일 로직, 의존성 최소화)
    body_size = props.get("체격", 2)

    hp = props.get("생존:체력", 100)
    max_hp = props.get("생존:최대체력", 100)
    hp_ratio = hp / max_hp if max_hp > 0 else 1.0

    return strength + body_size + hp_ratio * 3


def calculate_force_chance(actor_id, target_id):
    """강제 제압 성공 확률

    Args:
        actor_id: 제압하는 쪽
        target_id: 제압당하는 쪽

    Returns:
        float: 성공 확률 (0.1 ~ 0.95)
    """
    actor_power = get_unit_power(actor_id)
    target_power = get_unit_power(target_id)
    base = 0.5 + (actor_power - target_power) * 0.05

    # 은신 보너스: 은신 상태에서 기습 시 +20%
    stealth = morld.get_unit_prop(actor_id, "status:stealth")
    if stealth == 1:
        base += 0.20

    return max(0.1, min(0.95, base))


def can_start_forced(actor_id, target_id):
    """강제 모드 진입 가능 여부

    조건: 1:1 상황 (같은 location에 다른 의식있는 NPC 없음)

    Returns:
        tuple: (bool, str or None) — (가능여부, 실패 사유)
    """
    actor_loc = morld.get_unit_location(actor_id)
    if not actor_loc:
        return False, "위치를 확인할 수 없습니다"

    target_loc = morld.get_unit_location(target_id)
    if actor_loc != target_loc:
        return False, "같은 장소에 있어야 합니다"

    # 같은 location의 다른 의식있는 유닛 확인
    import survival
    units = morld.get_units_at_location(actor_loc[0], actor_loc[1])
    for uid in units:
        if uid == actor_id or uid == target_id:
            continue
        if not survival.is_npc_fainted(uid):
            unit_info = morld.get_unit_info(uid)
            name = unit_info.get("name", "누군가") if unit_info else "누군가"
            return False, f"{name}(이)가 있습니다"

    return True, None


def can_start_unconscious(actor_id, target_id):
    """무의식 모드 진입 가능 여부

    조건: 대상이 기절 상태

    Returns:
        tuple: (bool, str or None)
    """
    import survival
    if not survival.is_npc_fainted(target_id):
        return False, "대상이 의식이 있습니다"
    return True, None


def can_start_frozen(actor_id, target_id):
    """시간정지 모드 진입 가능 여부

    조건: 시간이 정지된 상태

    Returns:
        tuple: (bool, str or None)
    """
    if not morld.is_time_frozen():
        return False, "시간이 흐르고 있습니다"
    return True, None


# ============================================
# 저항 메카닉 (FORCED 모드)
# ============================================

def check_resistance(mode_ctx, target_id):
    """NPC 저항 체크 (매 행위 후 호출)

    Args:
        mode_ctx: 모드 컨텍스트
        target_id: 저항하는 NPC

    Returns:
        dict: {"escaped": bool, "resistance_delta": int}
    """
    if mode_ctx["mode"] != MODE_FORCED:
        return {"escaped": False, "resistance_delta": 0}

    props = morld.get_unit_props(target_id) or {}
    strength = props.get("근력", 5)
    rebellion_key = None

    # 반발 수치 찾기
    for key in props:
        if key.startswith("관계:") and key.endswith(":반발"):
            rebellion_key = key
            break
    rebellion = props.get(rebellion_key, 0) if rebellion_key else 0

    # 저항 확률: 기본 10% + 근력 2% + 반발 0.3%
    import random
    resistance_chance = 0.10 + strength * 0.02 + rebellion * 0.003
    resistance_chance = min(0.5, resistance_chance)  # 최대 50%

    mode_ctx["break_free_attempts"] += 1

    if random.random() < resistance_chance:
        return {"escaped": True, "resistance_delta": 0}

    # 저항 실패 — 저항 게이지 소폭 축적
    delta = max(3, int(strength * 1.5))
    mode_ctx["resistance_meter"] += delta
    if mode_ctx["resistance_meter"] >= 100:
        return {"escaped": True, "resistance_delta": delta}

    return {"escaped": False, "resistance_delta": delta}


# ============================================
# 각성 체크 (UNCONSCIOUS 모드)
# ============================================

def check_wakeup(mode_ctx, target_id, elapsed_ms):
    """무의식 NPC 각성 체크

    Args:
        mode_ctx: 모드 컨텍스트
        target_id: 기절한 NPC
        elapsed_ms: 이번 행위의 시간 경과 (ms)

    Returns:
        bool: True면 각성 (→ FORCED로 전이 필요)
    """
    if mode_ctx["mode"] != MODE_UNCONSCIOUS:
        return False

    import survival
    remaining = survival.get_faint_remaining_millis(target_id)
    if remaining <= 0:
        # 기절 시간 만료 — 각성
        return True

    return False


# ============================================
# 모드 전이
# ============================================

def transition_to_forced(mode_ctx):
    """UNCONSCIOUS → FORCED 전이 (NPC 각성)

    Args:
        mode_ctx: 기존 모드 컨텍스트 (in-place 수정)
    """
    mode_ctx["mode"] = MODE_FORCED
    mode_ctx["resistance_meter"] = 30  # 각성 직후 높은 초기 저항
    mode_ctx["break_free_attempts"] = 0
    # unconscious 전용 필드 정리
    mode_ctx.pop("wake_check_accum", None)


# ============================================
# 지연 효과 (FROZEN 모드)
# ============================================

def defer_effect(mode_ctx, stat, value):
    """시간정지 중 효과를 지연 목록에 축적

    Args:
        mode_ctx: 모드 컨텍스트
        stat: 효과 종류 (호감/욕망/반발/복종/성욕 등)
        value: 효과 수치
    """
    if mode_ctx["mode"] != MODE_FROZEN:
        return
    mode_ctx["deferred_effects"].append({"stat": stat, "value": value})


def defer_semen(mode_ctx, part, amount, internal=False):
    """시간정지 중 정액 효과를 지연

    Args:
        mode_ctx: 모드 컨텍스트
        part: 부위명
        amount: 정액량
        internal: True면 체내 정액
    """
    if mode_ctx["mode"] != MODE_FROZEN:
        return
    target = mode_ctx["deferred_internal_semen"] if internal else mode_ctx["deferred_semen"]
    target[part] = target.get(part, 0) + amount


def apply_deferred_effects(target_id, mode_ctx, actor_id):
    """시간정지 해제 후 지연 효과 일괄 적용 (30% 감쇠)

    Args:
        target_id: 효과 대상 NPC
        mode_ctx: 모드 컨텍스트
        actor_id: 행위자 (플레이어)
    """
    if mode_ctx["mode"] != MODE_FROZEN:
        return

    from romance_core import (
        get_affection_key, _apply_semen, _apply_internal_semen,
    )

    DAMPENING = 0.3  # 지연 효과 감쇠율

    # 관계 효과 적용 (30%만)
    affection_key = get_affection_key(actor_id)
    for eff in mode_ctx["deferred_effects"]:
        stat = eff["stat"]
        value = round(eff["value"] * DAMPENING)
        if value == 0:
            continue
        if stat in ("성욕", "성적절정"):
            prop_key = f"상태:{stat}"
        else:
            prop_key = affection_key.replace(":호감", f":{stat}")
        morld.modify_prop(target_id, prop_key, value)

    # 외부 정액 적용 (100% — 물리적 흔적)
    for part, amount in mode_ctx["deferred_semen"].items():
        _apply_semen(target_id, part, amount)

    # 체내 정액 적용 (100%)
    for part, amount in mode_ctx["deferred_internal_semen"].items():
        _apply_internal_semen(target_id, part, amount)

    # 상태 prop 설정 (후속 이벤트 트리거용)
    morld.set_unit_prop(target_id, "상태:시간정지피해", 1)
    climax_count = mode_ctx["deferred_climax_count"]
    if climax_count > 0:
        morld.set_unit_prop(target_id, "상태:시간정지절정횟수", climax_count)


# ============================================
# 강제 모드 종료 패널티
# ============================================

def apply_forced_end_penalty(target_id, mode_ctx, actor_id):
    """강제 모드 종료 시 패널티 적용

    - 반발 +10~20 (행위 수 비례)
    - 호감 -5~15 (행위 수 비례)

    Args:
        target_id: 피해 NPC
        mode_ctx: 모드 컨텍스트
        actor_id: 강제 행위자
    """
    from romance_core import get_affection_key, get_rebellion_key

    action_count = mode_ctx.get("action_count", 0)
    affection_key = get_affection_key(actor_id)
    rebellion_key = get_rebellion_key(actor_id)

    # 반발 증가: 10 + 행위 수 (최대 20)
    rebellion_penalty = min(20, 10 + action_count)
    morld.modify_prop(target_id, rebellion_key, rebellion_penalty)

    # 호감 감소: -5 - 행위 수 (최대 -15)
    affection_penalty = max(-15, -5 - action_count)
    morld.modify_prop(target_id, affection_key, affection_penalty)

    # 상태 prop 설정 (후속 이벤트 트리거용)
    morld.set_unit_prop(target_id, "상태:강제피해", 1)


def apply_unconscious_end_state(target_id, mode_ctx):
    """무의식 모드 종료 시 상태 설정

    감정 변화 없음, 물리적 상태만 유지.
    NPC 각성 후 on_meet에서 발견 이벤트 트리거.
    """
    morld.set_unit_prop(target_id, "상태:무의식피해", 1)


# ============================================
# 나레이션 (반응 없는 모드)
# ============================================

def get_silent_narration(mode):
    """반응 없는 모드의 나레이션 텍스트"""
    if mode == MODE_UNCONSCIOUS:
        return "(반응 없이 축 늘어져 있다.)"
    elif mode == MODE_FROZEN:
        return "(시간이 멈춘 채 굳어 있다.)"
    return None


def get_silent_climax_narration(mode):
    """반응 없는 모드의 절정 나레이션"""
    if mode == MODE_UNCONSCIOUS:
        return "(무의식 중에도 몸이 떨리며 절정에 달했다.)"
    elif mode == MODE_FROZEN:
        return "(정지된 채로... 절정의 흔적이 남았다.)"
    return None
