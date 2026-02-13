# stimulation.py - 자극 시스템
"""
자극 (Stimulation) 시스템 — 애정 행위 중 부위별 자극 관리

핵심 특성:
- 세션 스코프: romance 세션 state dict 안에만 존재, prop 아님
- 부위별 자극: MBAVCP 카테고리별 독립 자극 수치
- 절정 (climax): 자극이 최대치 도달 시 발생
- 여운 (afterglow): 절정 후 일시적 상태
- 연쇄 절정 (chain climax): 여운 중 재절정 시 자극 증폭
"""

# ============================================
# 상수
# ============================================

STIM_MAX = 100                  # 절정 발생 임계값
AFTERGLOW_INITIAL = 50          # 절정 시 부여되는 여운 초기값
AFTERGLOW_DECAY = 10            # 행위 1회당 여운 감소량
CHAIN_AMPLIFIER = 1.5           # 연쇄 절정 시 자극 배율
CHAIN_RAPID_BONUS = 0.5         # 짧은 간격 연쇄 시 추가 배율
CLIMAX_AROUSAL_REDUCTION = 30   # 절정 시 성욕 감소량
CLIMAX_SENSATION_GAIN = 3       # 절정 부위 경험치 보너스
REFRACTORY_INITIAL = 60         # 불응기 초기값 (남성 절정 후)
REFRACTORY_DECAY = 10           # 행위 1회당 불응기 감소량
REFRACTORY_GAIN_FACTOR = 0.1   # 불응기 중 자극 gain 배율 (90% 감소)


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
        "afterglow": 0,         # 0=통상, >0=여운 상태
        "chain_count": 0,       # 현재 연쇄 절정 횟수 (여운 종료 시 리셋)
        "climax_total": 0,      # 이번 세션 총 절정 횟수
        "refractory": 0,        # 0=통상, >0=불응기 (남성 전용)
        "male_mode": male_mode, # 남성 모드 플래그 (세션 중 불변)
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

    Args:
        state: create_state()로 생성된 자극 상태
        category: 감각 카테고리 ("M", "B", "A", "V", "C", "P")
        amount: 자극 증가량

    Returns:
        dict or None: 절정 발생 시 climax info, 아니면 None
    """
    if category not in state["stim"]:
        return None
    if amount <= 0:
        return None

    state["stim"][category] = min(STIM_MAX, state["stim"][category] + amount)

    if state["stim"][category] >= STIM_MAX:
        return _trigger_climax(state, category)

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


def get_climax_sensation_gain(rebellion):
    """절정 시 감각 경험치 보너스 (반발에 의해 억제 가능)

    Args:
        rebellion: 반발 수치 (0-100)

    Returns:
        int: 경험치 증가량 (0 이상)
    """
    return max(0, CLIMAX_SENSATION_GAIN - rebellion // 25)


# ============================================
# 내부 함수
# ============================================

def _trigger_climax(state, category):
    """절정 처리 (내부)

    남성 모드: 불응기 진입, 연쇄 불가
    여성 모드: 여운 진입/갱신, 연쇄 가능

    Returns:
        dict: {"category", "is_chain", "chain_count", "climax_total"}
    """
    # 자극 리셋
    state["stim"][category] = 0

    is_chain = False

    if state.get("male_mode"):
        # 남성: 불응기 진입, 연쇄 불가
        state["afterglow"] = 0
        state["chain_count"] = 0
        state["refractory"] = REFRACTORY_INITIAL
    else:
        # 여성: 연쇄 판정 + 여운 진입
        is_chain = state["afterglow"] > 0
        if is_chain:
            state["chain_count"] += 1
        else:
            state["chain_count"] = 0
        state["afterglow"] = AFTERGLOW_INITIAL

    # 총 절정 횟수
    state["climax_total"] += 1

    return {
        "category": category,
        "is_chain": is_chain,
        "chain_count": state["chain_count"],
        "climax_total": state["climax_total"],
    }


def force_climax(state, category):
    """강제 절정 발동 (질외사정 등)"""
    return _trigger_climax(state, category)
