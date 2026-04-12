# judge_reaction.py — S04 목격자 반응 판정
#
# 3자 상황(공격자 aggressor, 피해자 victim, 목격자 witness)에서
# 목격자가 어떻게 반응할지 결정.
#
# 대칭 구조: 플레이어가 공격자/피해자/목격자 어느 역할이든 같은 규칙이 적용된다.
#
# 설계: docs/advanced-systems.md §4.6

import morld
import trust as trust_module


# 반응 4종
REACTION_HELP_VICTIM = "help_victim"      # 피해자 편에 가담 (공격자 저지)
REACTION_JOIN_AGGRESSOR = "join_aggressor"  # 공격자 편에 가담 (약탈/추가 공격)
REACTION_WATCH = "watch"                    # 방관
REACTION_FLEE = "flee"                      # 도주


# 맥락 타입
CONTEXT_ATTACK = "attack"
CONTEXT_SEXUAL = "sexual"
CONTEXT_THEFT = "theft"
CONTEXT_KILL = "kill"


# 임계값
THRESHOLD_FLEE_POWER_RATIO = 0.3   # 승산이 이 비율 미만 → 도주 고려
THRESHOLD_ACTION = 0.3             # help/join 최소 점수 (미만이면 watch)


# ========================================
# NPC 성향 prop
# ========================================

def _get_float_prop(unit_id: int, key: str, default: float) -> float:
    val = morld.get_unit_prop(unit_id, key)
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def get_aggression(unit_id: int) -> float:
    """-1.0 (방어적) ~ +1.0 (공격적)"""
    return _get_float_prop(unit_id, "성향:공격성", 0.0)


def get_greed(unit_id: int) -> float:
    """0.0 (무욕) ~ 1.0 (탐욕)"""
    return _get_float_prop(unit_id, "성향:탐욕", 0.3)


def get_loyalty_tendency(unit_id: int) -> float:
    """0.0 (배신 쉬움) ~ 1.0 (끝까지 따름)"""
    return _get_float_prop(unit_id, "성향:충성성향", 0.5)


def get_npc_morality(unit_id: int) -> float:
    """-100 (악) ~ +100 (선). 플레이어 도덕성과 동일 스케일."""
    return _get_float_prop(unit_id, "성향:도덕성", 0.0)


def get_independence(unit_id: int) -> float:
    """0.0 (순종) ~ 1.0 (독립). 높으면 자기 판단으로 도주/이탈."""
    return _get_float_prop(unit_id, "성향:독립성", 0.5)


# ========================================
# 신뢰 / 연인 관계
# ========================================

def _trust_between(observer_id: int, target_id: int) -> int:
    """observer가 target에게 가진 신뢰 (0~100).

    현재 구현: target이 플레이어면 trust 모듈의 신뢰도 반환 (NPC→플레이어).
    그 외는 TRUST_DEFAULT. NPC↔NPC 신뢰 테이블 도입 시 교체.
    """
    player_id = morld.get_player_id()
    if target_id == player_id:
        return trust_module.get_trust(observer_id)
    return trust_module.TRUST_DEFAULT


def _trust_score(observer_id: int, target_id: int) -> float:
    """신뢰도 정규화: TRUST_DEFAULT(중립) 기준 -1.0 ~ +1.0.

    기본값 50이 0.0이 되도록 정규화하여, 정보 없는 관계가 판정 점수에
    편향을 주지 않게 한다.
    """
    raw = _trust_between(observer_id, target_id)
    return (raw - trust_module.TRUST_DEFAULT) / trust_module.TRUST_DEFAULT


def _has_romance_bond(a_id: int, b_id: int) -> bool:
    """연인 관계 여부. S04 romance 시스템은 미구현 → placeholder.

    향후 romance 모듈 추가 시 여기서 위임.
    """
    return False


# ========================================
# 위협 평가
# ========================================

def _power_score(unit_id: int) -> float:
    """단순 능력 평가 (현재 HP × 근력 / 100).

    정교한 전투력 계산은 encounter 모듈에 있지만, judge_reaction은
    "승산 평가" 수준의 근사치만 필요 → 경량 계산으로 충분.
    """
    hp = morld.get_unit_prop(unit_id, "생존:체력") or 100
    attack = morld.get_unit_prop(unit_id, "스탯:근력") or 10
    return float(hp) * float(attack) / 100.0


def _power_ratio(witness_id: int, aggressor_id: int) -> float:
    """witness / aggressor 능력 비율. 1.0=호각, <1.0=불리."""
    w = _power_score(witness_id)
    a = _power_score(aggressor_id)
    if a <= 0:
        return 2.0
    return w / a


# ========================================
# 판정
# ========================================

def judge_reaction(
    witness_id: int,
    aggressor_id: int,
    victim_id: int,
    context_type: str = CONTEXT_ATTACK,
    *,
    is_sleeping: bool = False,
) -> str:
    """목격자 반응 판정.

    Args:
        witness_id: 목격자 (NPC 또는 플레이어)
        aggressor_id: 공격자
        victim_id: 피해자
        context_type: CONTEXT_* 중 하나
        is_sleeping: 피해자가 수면 중인지 (무방비 상태)

    Returns:
        REACTION_HELP_VICTIM | REACTION_JOIN_AGGRESSOR | REACTION_WATCH | REACTION_FLEE
    """
    # 1. 연인 관계 우선 (치정 트리거)
    if _has_romance_bond(witness_id, victim_id):
        return REACTION_HELP_VICTIM
    if _has_romance_bond(witness_id, aggressor_id) and context_type != CONTEXT_SEXUAL:
        return REACTION_JOIN_AGGRESSOR

    # 2. 위협 평가 → 독립적 목격자의 도주 판정
    if _power_ratio(witness_id, aggressor_id) < THRESHOLD_FLEE_POWER_RATIO:
        if get_independence(witness_id) > 0.5:
            return REACTION_FLEE

    # 3. 가중합 점수 (신뢰도는 TRUST_DEFAULT 기준 정규화된 -1.0~+1.0)
    morality = get_npc_morality(witness_id) / 100.0   # -1.0 ~ +1.0
    aggression = get_aggression(witness_id)
    greed = get_greed(witness_id)
    trust_victim = _trust_score(witness_id, victim_id)
    trust_aggressor = _trust_score(witness_id, aggressor_id)

    help_score = morality + trust_victim - trust_aggressor
    if is_sleeping:
        help_score += 0.3
    if context_type == CONTEXT_KILL:
        help_score += 0.3

    join_score = aggression + trust_aggressor - trust_victim - morality
    if context_type == CONTEXT_THEFT:
        join_score += greed

    # 4. 결정 — help/join 중 높은 쪽, 임계 미달이면 watch
    if help_score > join_score and help_score > THRESHOLD_ACTION:
        return REACTION_HELP_VICTIM
    if join_score > THRESHOLD_ACTION:
        return REACTION_JOIN_AGGRESSOR
    return REACTION_WATCH
