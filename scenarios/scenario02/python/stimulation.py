# stimulation.py - 자극 시스템
"""
자극 (Stimulation) 시스템 — 애정 행위 중 부위별 자극 관리

핵심 특성:
- 세션 스코프: romance 세션 state dict 안에만 존재, prop 아님
- 부위별 자극: FMBAVCP 카테고리별 독립 자극 수치 (0-100)
- 절정 게이지: 자극과 분리된 단일 게이지 (0-100)
  - 자극 적용 시 게이지도 상승 (peaked 부위 수에 따라 가속)
  - 게이지 만충 + peaked 부위 존재 시 절정
- 동시 절정: peaked 부위 전부 동시 절정, 다중 부위 배율
- 트랜스: NPC 비-P 부위 peaked + 게이지 미충족
- 참기: 확률 기반 성공/실패 + 감쇠형
- 사정하기: P 강제 peaked + 게이지 만충 → 절정
"""

import random

# ============================================
# 상수
# ============================================

STIM_MAX = 100                  # 자극 최대치 (peaked)
AFTERGLOW_INITIAL = 50          # 절정 시 부여되는 여운 초기값
AFTERGLOW_DECAY = 10            # 행위 1회당 여운 감소량
CHAIN_AMPLIFIER = 1.5           # 연쇄 절정 시 자극 배율
CHAIN_RAPID_BONUS = 0.5         # 짧은 간격 연쇄 시 추가 배율
CLIMAX_AROUSAL_REDUCTION = 30   # 절정 시 성욕 감소량
CLIMAX_SENSATION_GAIN = 3       # 절정 부위 경험치 보너스
REFRACTORY_INITIAL = 60         # 불응기 초기값 (남성 절정 후)
REFRACTORY_DECAY = 10           # 행위 1회당 불응기 감소량
REFRACTORY_GAIN_FACTOR = 0.1   # 불응기 중 자극 gain 배율 (90% 감소)

# 절정 게이지
CLIMAX_GAUGE_RATIO = 0.4       # 자극 → 게이지 전환 비율
PEAKED_GAUGE_BONUS = 0.3       # peaked 부위당 게이지 가속 보너스
CLIMAX_GAUGE_MAX = 100         # 절정 게이지 최대치
SIMULTANEOUS_BONUS = 0.2       # 동시 절정 부위당 추가 배율

# 참기 (hold_back)
HOLD_BACK_BASE_CHANCE = 70     # 참기 기본 성공 확률 (%)
HOLD_BACK_CHANCE_DECAY = 10    # 참기 횟수당 확률 감쇠 (%)
HOLD_BACK_MIN_CHANCE = 10      # 참기 최소 성공 확률 (%)
HOLD_BACK_REDUCTION = 25       # 성공 시 게이지 감소량
HOLD_BACK_REDUCTION_DECAY = 5  # 횟수당 감소량 감쇠
HOLD_BACK_REDUCTION_MIN = 5    # 최소 감소량
HOLD_BACK_FAIL_PENALTY = 10    # 실패 시 게이지 증가량

# P 감각 영향력
P_SENSATION_GAIN_REDUCTION = 0.07  # P 감각 1당 P 자극 상승 감소율
P_SENSATION_GAIN_MIN = 0.3         # P 자극 상승 최소 배율 (감각 10일 때)
EJACULATE_BASE_THRESHOLD = 70      # 사정하기 기본 P 자극 요구치
EJACULATE_SENSATION_REDUCTION = 4  # P 감각 1당 사정하기 요구치 감소
EJACULATE_MIN_THRESHOLD = 30       # 사정하기 최소 P 자극 요구치


# ============================================
# 세션 상태 관리
# ============================================

def create_state(male_mode=False):
    """세션용 자극 상태 생성

    romance 세션 시작 시 state["stim"]에 할당.
    세션 종료 시 자동 폐기 (prop 저장 안 함).

    Args:
        male_mode: True이면 남성 모드 (절정=불응기, 연쇄 불가)

    Returns:
        dict: 자극 상태
    """
    return {
        "stim": {"F": 0, "M": 0, "B": 0, "A": 0, "V": 0, "C": 0, "P": 0},
        "climax_gauge": 0,      # 절정 게이지 (0-100)
        "afterglow": 0,         # 0=통상, >0=여운 상태
        "chain_count": 0,       # 현재 연쇄 절정 횟수 (여운 종료 시 리셋)
        "climax_total": 0,      # 이번 세션 총 절정 횟수
        "refractory": 0,        # 0=통상, >0=불응기 (남성 전용)
        "male_mode": male_mode, # 남성 모드 플래그 (세션 중 불변)
        "hold_back_count": 0,   # 참기 횟수 (감쇠 추적)
        "_seen_reactions": set(),  # 1회성(once) 반응 소모 추적 (세션 내 휘발)
    }


# ============================================
# 자극 계산
# ============================================

def calc_gain(base, sensation_level, rebellion, afterglow, refractory=0):
    """자극 증가량 계산

    Args:
        base: 행위의 기본 성욕 효과 (effects에서 "성욕" 값)
        sensation_level: 해당 부위 감각 레벨 (0-10)
        rebellion: 반발 수치 (0-100)
        afterglow: 현재 여운 수치 (0=통상)
        refractory: 현재 불응기 수치 (0=통상, 남성 전용)

    Returns:
        int: 최종 자극 증가량
    """
    if base <= 0:
        return 0

    # 기본 × 감각 보정
    gain = base * (1.0 + sensation_level * 0.15)

    # 반발 감소 (반발 100이면 80% 감소, 최소 20%)
    rebellion_factor = max(0.2, 1.0 - rebellion * 0.008)
    gain *= rebellion_factor

    # 불응기 중 대폭 감소 (남성), 여운 중 연쇄 증폭 (여성)
    if refractory > 0:
        gain *= REFRACTORY_GAIN_FACTOR
    elif afterglow > 0:
        gain *= CHAIN_AMPLIFIER

    return max(1, round(gain))


def apply(state, category, amount):
    """자극을 적용하고, 절정 발생 시 climax info 반환

    자극 적용 → 게이지 상승 → 절정 판정의 3단계.
    - 자극 100 도달 = peaked (즉시 절정 아님)
    - 여운 중 + peaked 도달 → 연쇄 절정
    - 게이지 만충 + peaked 존재 → 절정

    Args:
        state: create_state()로 생성된 자극 상태
        category: 감각 카테고리 ("F", "M", "B", "A", "V", "C", "P")
        amount: 자극 증가량

    Returns:
        dict or None: 절정 발생 시 climax info, 아니면 None
    """
    if category not in state["stim"]:
        return None
    if amount <= 0:
        return None

    # 1. 자극 적용
    state["stim"][category] = min(STIM_MAX, state["stim"][category] + amount)

    # 2. 절정 게이지 상승
    peaked_count = sum(1 for v in state["stim"].values() if v >= STIM_MAX)
    gauge_gain = amount * CLIMAX_GAUGE_RATIO * (1.0 + peaked_count * PEAKED_GAUGE_BONUS)
    state["climax_gauge"] = min(CLIMAX_GAUGE_MAX, state["climax_gauge"] + gauge_gain)

    # 3. 여운 중 연쇄 절정 (stim 100 도달 + afterglow > 0)
    if state["stim"][category] >= STIM_MAX and state["afterglow"] > 0:
        return _trigger_climax(state)

    # 4. 절정 판정 (게이지 만충 + peaked 존재)
    if state["climax_gauge"] >= CLIMAX_GAUGE_MAX and peaked_count > 0:
        return _trigger_climax(state)

    return None


def tick_afterglow(state):
    """행위마다 호출 — 여운/불응기 감소

    여운이 0이 되면 연쇄 카운트도 리셋.
    """
    if state["afterglow"] > 0:
        state["afterglow"] = max(0, state["afterglow"] - AFTERGLOW_DECAY)
        if state["afterglow"] <= 0:
            state["chain_count"] = 0

    # 불응기 감소 (남성)
    if state.get("refractory", 0) > 0:
        state["refractory"] = max(0, state["refractory"] - REFRACTORY_DECAY)


def get_climax_sensation_gain(rebellion, chain_count=0):
    """절정 시 감각 경험치 보너스 (반발 억제 + 연쇄 절정 배율)

    Args:
        rebellion: 반발 수치 (0-100)
        chain_count: 연쇄 절정 횟수 (0=일반, 1+=연쇄)

    Returns:
        int: 경험치 증가량 (0 이상)
    """
    base = max(0, CLIMAX_SENSATION_GAIN - rebellion // 25)
    # 연쇄 절정 배율: chain 0=x1.0, 1=x1.5, 2=x2.0, 3+=x2.5
    chain_mult = 1.0 + min(chain_count, 3) * 0.5
    return max(0, round(base * chain_mult))


# ============================================
# 참기 (hold_back)
# ============================================

def hold_back(state):
    """참기 — 확률적 성공/실패 + 감쇠형

    횟수가 늘어날수록 성공 확률과 감소량 모두 감쇠.
    실패 시 게이지가 오히려 증가하여 절정 가속.

    Returns:
        dict: {"success": bool, "chance": int, "reduction": int, "gauge": float}
    """
    count = state["hold_back_count"]

    # 성공 확률 (횟수당 감쇠)
    chance = max(HOLD_BACK_MIN_CHANCE,
                 HOLD_BACK_BASE_CHANCE - count * HOLD_BACK_CHANCE_DECAY)

    state["hold_back_count"] += 1
    success = random.randint(1, 100) <= chance

    if success:
        # 성공: 게이지 감소 (감쇠형)
        reduction = max(HOLD_BACK_REDUCTION_MIN,
                        HOLD_BACK_REDUCTION - count * HOLD_BACK_REDUCTION_DECAY)
        state["climax_gauge"] = max(0, state["climax_gauge"] - reduction)
        return {"success": True, "chance": chance, "reduction": reduction,
                "gauge": state["climax_gauge"]}
    else:
        # 실패: 게이지 오히려 증가 → 절정 가속
        state["climax_gauge"] = min(CLIMAX_GAUGE_MAX,
                                     state["climax_gauge"] + HOLD_BACK_FAIL_PENALTY)
        return {"success": False, "chance": chance, "reduction": 0,
                "gauge": state["climax_gauge"]}


# ============================================
# P 감각 영향
# ============================================

def get_p_gain_multiplier(p_sensation):
    """P 감각에 따른 P 자극 상승 배율 (경험 ↑ → 지속력 ↑)

    sensation 0 → ×1.0, sensation 5 → ×0.65, sensation 10 → ×0.3
    """
    return max(P_SENSATION_GAIN_MIN, 1.0 - p_sensation * P_SENSATION_GAIN_REDUCTION)


def get_ejaculate_threshold(p_sensation):
    """P 감각에 따른 사정하기 P 자극 요구치 (경험 ↑ → 요구 ↓)

    sensation 0 → 70, sensation 5 → 50, sensation 10 → 30
    """
    return max(EJACULATE_MIN_THRESHOLD,
               EJACULATE_BASE_THRESHOLD - p_sensation * EJACULATE_SENSATION_REDUCTION)


# ============================================
# 트랜스 / 상태 조회
# ============================================

def is_trance(state):
    """NPC 트랜스 상태 (비-P 부위 peaked + 게이지 미충족)"""
    if state["climax_gauge"] >= CLIMAX_GAUGE_MAX:
        return False
    return any(v >= STIM_MAX for k, v in state["stim"].items() if k != "P")


def is_p_peaked(state):
    """P 자극 최대 (사정감)"""
    return state["stim"].get("P", 0) >= STIM_MAX


def get_peaked_count(state):
    """peaked 부위 수"""
    return sum(1 for v in state["stim"].values() if v >= STIM_MAX)


def get_peaked_parts(state):
    """peaked 부위 목록"""
    return [k for k, v in state["stim"].items() if v >= STIM_MAX]


# ============================================
# 강제 절정
# ============================================

def force_climax(state):
    """강제 절정 발동 (참기 실패 등)"""
    return _trigger_climax(state)


def force_ejaculate(state):
    """사정하기 — P를 peaked 상태로 만들고 절정 처리

    P를 STIM_MAX로 설정 + 게이지 만충 → _trigger_climax
    """
    state["stim"]["P"] = STIM_MAX
    state["climax_gauge"] = CLIMAX_GAUGE_MAX
    return _trigger_climax(state)


def apply_climax_reset_p(state):
    """P 자극 강제 리셋 (하위호환)"""
    state["stim"]["P"] = 0


# ============================================
# 내부 함수
# ============================================

def _trigger_climax(state):
    """절정 처리 — peaked 부위 모두 동시 절정

    Returns:
        dict: climax info (peaked_parts, simultaneous_mult, has_p, etc.)
    """
    peaked_parts = [k for k, v in state["stim"].items() if v >= STIM_MAX]
    peaked_count = len(peaked_parts)

    if peaked_count == 0:
        return None

    # 동시 절정 배율
    simultaneous_mult = 1.0 + max(0, peaked_count - 1) * SIMULTANEOUS_BONUS

    # 전체 peaked 부위 리셋
    for part in peaked_parts:
        state["stim"][part] = 0

    # 연쇄 판정
    is_chain = state["afterglow"] > 0
    if is_chain:
        state["chain_count"] += 1
    else:
        state["chain_count"] = 0

    # P 포함 여부에 따른 후처리
    has_p = "P" in peaked_parts
    non_p_parts = [p for p in peaked_parts if p != "P"]

    if has_p and state.get("male_mode"):
        state["refractory"] = REFRACTORY_INITIAL
    if non_p_parts:
        state["afterglow"] = AFTERGLOW_INITIAL

    # 게이지 리셋 (여운 초기값으로 — 여운 중 연쇄 가능)
    state["climax_gauge"] = state["afterglow"]

    state["climax_total"] += 1
    state["hold_back_count"] = 0  # 참기 카운트 리셋

    return {
        "peaked_parts": peaked_parts,
        "peaked_count": peaked_count,
        "simultaneous_mult": simultaneous_mult,
        "has_p": has_p,
        "non_p_parts": non_p_parts,
        "is_chain": is_chain,
        "chain_count": state["chain_count"],
        "climax_total": state["climax_total"],
        # 하위호환: 기존 코드가 사용하는 "category" 키
        "category": peaked_parts[0] if peaked_parts else "V",
    }
