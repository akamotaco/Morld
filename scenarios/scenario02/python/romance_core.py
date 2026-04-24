# romance_core.py - 애정 행위 공유 핵심 로직
"""
romance.py와 npc_initiative.py가 공유하는 핵심 함수 모음.

포함 영역:
- 관계 Prop 키 생성
- 감각 레벨 계산
- 가용/호환 판정
- 효과 계산 (경험치/감각/지향성 보정)
- 노출/탈의
- 정액 시스템
- 삽입/충돌 헬퍼
- 처녀(첫경험)
- 참기/질외사정
- 준비/윤활 체크
- 은신 판정
- 소리
- 절정 반응 키
"""

import math
import random
import morld
from romance_actions import (
    MILLIS_PER_MINUTE,
    SEMEN_PARTS, SEMEN_AMOUNT_BASE, SEMEN_AMOUNT_MIN, SEMEN_AMOUNT_MAX,
    INTERNAL_SEMEN_PARTS, INTERNAL_SEMEN_MAX,
    PULL_OUT_STIM_THRESHOLD, LUBRICATION_THRESHOLD,
    PREPARATION_THRESHOLD,
    EXPOSURE_BONUS, UNDRESS_UPPER_SLOTS, UNDRESS_LOWER_SLOTS,
    STEALTH_BASE_CHANCE, STEALTH_HIDING_BONUS,
    HOLD_BACK_P_THRESHOLD,
    SENSATION_MAP,
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    VIRGINITY_CLEARING_ACTIONS, VIRGINITY_BONUS_AFFECTION, VIRGINITY_BONUS_EXP,
    _THRUST_TOGGLE_IDS, _INSERTION_EXP_MAP,
)


# ============================================
# Asset 헬퍼
# ============================================

def get_character_asset(unit_id):
    """캐릭터(NPC/파트너)의 Python Asset 인스턴스 가져오기"""
    try:
        from assets.characters import get_instance
        return get_instance(unit_id)
    except Exception:
        return None


# ============================================
# 관계 Prop 키 생성
# ============================================

def _get_relationship_key(player_id, suffix):
    """관계 prop 키 생성 헬퍼"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    return f"관계:{player_name}:{suffix}"


def get_affection_key(player_id):
    """플레이어에 대한 호감도 prop 키 생성"""
    return _get_relationship_key(player_id, "호감")


def get_rebellion_key(player_id):
    """플레이어에 대한 반발 prop 키 생성"""
    return _get_relationship_key(player_id, "반발")


def get_submission_key(player_id):
    """플레이어에 대한 복종 prop 키 생성"""
    return _get_relationship_key(player_id, "복종")


# ============================================
# 질투 (Phase 5 감정 스탯 — 최소 인프라)
# ============================================

JEALOUSY_MAX = 100
JEALOUSY_MIN = 0


def get_jealousy(observer_id, target_name):
    """`관계:{target_name}:질투` — observer가 target에 대해 갖는 질투 수치.

    target_name은 문자열(name). 0~100 clamp.
    """
    value = morld.get_unit_prop(observer_id, f"관계:{target_name}:질투") or 0
    return value


def modify_jealousy(observer_id, target_name, delta):
    """질투 변동 + clamp. 변동 후 값 반환.

    Why: Phase 5 감정 스탯 — NTR 관찰 시 제3자에 대한 적대/소유욕 수치화.
    """
    current = get_jealousy(observer_id, target_name)
    new_val = max(JEALOUSY_MIN, min(JEALOUSY_MAX, current + delta))
    morld.set_unit_prop(observer_id, f"관계:{target_name}:질투", new_val)
    return new_val


# ============================================
# 주도권 축 (NPC 주도 다이얼로그 개편 — Slice P1)
# ============================================
# era `주도종속.ERB` 패턴 포팅:
#   기존 `관계:{player}:복종` on NPC  ≡ era 종속도 (NPC → player 복종)
#   신규 `관계:{player}:지배` on NPC  ≡ era 주도도 (NPC → player 지배)
# 두 축은 상호 배타 — 한 축 가산 시 반대 축부터 상쇄.
DOMINANCE_MAX = 100
DOMINANCE_MIN = 0


def get_dominance(npc_id, player_id):
    """NPC가 player를 지배하는 정도 (0~100)."""
    key = _get_relationship_key(player_id, "지배")
    return morld.get_unit_prop(npc_id, key) or 0


def modify_dominance(npc_id, player_id, delta):
    """지배 변동 — era 패턴:
      delta > 0: 먼저 `복종`부터 상쇄, 남은 만큼 `지배` 가산
      delta < 0: 그냥 `지배` 감쇠 (0까지)
    반환값: 변동 후 `지배` 값.
    """
    sub_key = _get_relationship_key(player_id, "복종")
    dom_key = _get_relationship_key(player_id, "지배")
    current_sub = morld.get_unit_prop(npc_id, sub_key) or 0
    current_dom = morld.get_unit_prop(npc_id, dom_key) or 0
    if delta > 0 and current_sub > 0:
        if current_sub < delta:
            remaining = delta - current_sub
            morld.set_unit_prop(npc_id, sub_key, 0)
            new_dom = min(DOMINANCE_MAX, current_dom + remaining)
        else:
            morld.set_unit_prop(npc_id, sub_key, current_sub - delta)
            new_dom = current_dom
    else:
        new_dom = max(DOMINANCE_MIN, min(DOMINANCE_MAX, current_dom + delta))
    morld.set_unit_prop(npc_id, dom_key, new_dom)
    return new_dom


SWITCH_BLOCK_DOMINANCE = 70
SWITCH_FREE_DOMINANCE = 30


def calculate_switch_takeover_chance(npc_id, player_id):
    """NPC 주도 → 플레이어 주도 전환 성공 확률 (0.0~1.0).

    Slice P3: era 주도종속 패턴 기반 게이트.
      지배 ≥ 70 → 0.0 (차단, NPC가 놓지 않음)
      지배 ≤ 30 → 1.0 (자유 전환)
      30 < 지배 < 70 → 선형 감소 (지배 30 → 1.0, 69 → 0.025)

    Why: 지배 누적된 상태에서 플레이어가 주도권을 쉽게 되찾을 수 없도록.
         역전 경로 (탈출 / 합의 전환 P4)와 구분.
    """
    dominance = get_dominance(npc_id, player_id)
    if dominance >= SWITCH_BLOCK_DOMINANCE:
        return 0.0
    if dominance <= SWITCH_FREE_DOMINANCE:
        return 1.0
    span = SWITCH_BLOCK_DOMINANCE - SWITCH_FREE_DOMINANCE
    return max(0.0, 1.0 - (dominance - SWITCH_FREE_DOMINANCE) / span)


CONSENT_BLOCK_DOMINANCE = 70


def calculate_consent_success_chance(npc_id, player_id):
    """NPC 주도 세션 중 "합의 제안" 성공 확률 (0.0~1.0).

    Slice P4 — 플레이어가 NPC에게 합의 전환을 요청 (저항 아닌 평화 경로).
      지배 ≥ 70 → 0.0 (차단, 플레이어는 이미 NPC에게 끌려)
      기본: (호감/100) × (1 - 반발/100)
      호감 ≥ 70 → +0.2 보너스

    Why: 단순 저항/탈출과 구분되는 "합의 이끌어내기" 경로.
         관계 기반, 호감↑ + 반발↓ NPC에 효과적.
    """
    dominance = get_dominance(npc_id, player_id)
    if dominance >= CONSENT_BLOCK_DOMINANCE:
        return 0.0
    props = morld.get_unit_props(npc_id) or {}
    affection = props.get(get_affection_key(player_id), 0)
    rebellion = props.get(get_rebellion_key(player_id), 0)
    base = (affection / 100.0) * (1.0 - rebellion / 100.0)
    if affection >= 70:
        base += 0.2
    return max(0.0, min(1.0, base))


def modify_submission_mutex(npc_id, player_id, delta):
    """복종 변동 — era 패턴 대칭:
      delta > 0: 먼저 `지배`부터 상쇄, 남은 만큼 `복종` 가산
      delta < 0: 그냥 `복종` 감쇠
    기존 `복종` 직접 modify_prop 호출과 공존 — 주도권 의미 있는
    상호작용에서만 이 함수 사용.
    """
    sub_key = _get_relationship_key(player_id, "복종")
    dom_key = _get_relationship_key(player_id, "지배")
    current_sub = morld.get_unit_prop(npc_id, sub_key) or 0
    current_dom = morld.get_unit_prop(npc_id, dom_key) or 0
    if delta > 0 and current_dom > 0:
        if current_dom < delta:
            remaining = delta - current_dom
            morld.set_unit_prop(npc_id, dom_key, 0)
            new_sub = min(DOMINANCE_MAX, current_sub + remaining)
        else:
            morld.set_unit_prop(npc_id, dom_key, current_dom - delta)
            new_sub = current_sub
    else:
        new_sub = max(DOMINANCE_MIN, min(DOMINANCE_MAX, current_sub + delta))
    morld.set_unit_prop(npc_id, sub_key, new_sub)
    return new_sub


def get_effective_affection_req(req, arousal=0, submission=0):
    """유효 호감 요구치 (성욕/복종 할인 적용)

    각 요소: 최대 30% 할인
    합산: 최대 50% 할인
    절대 최소: 20
    """
    arousal_discount = min(req * 0.3, arousal * 0.3)
    submission_discount = min(req * 0.3, submission * 0.3)
    total = min(req * 0.5, arousal_discount + submission_discount)
    return max(20, req - total)


# ============================================
# 감각 레벨
# ============================================

def get_sensation_level(unit_id, category):
    """감각 카테고리의 현재 레벨 (경험치에서 산출)

    해당 카테고리에 매핑된 부위들의 경험치 합산 → 레벨 변환.

    Args:
        unit_id: 대상 유닛 ID
        category: "M", "B", "A", "V", "C", "P", "F"

    Returns:
        int: 감각 레벨 (0-10)
    """
    total_exp = 0
    for part, cat in SENSATION_MAP.items():
        if cat == category:
            total_exp += morld.get_unit_prop(unit_id, f"경험:{part}") or 0
    return min(10, int(math.floor(math.sqrt(total_exp / 3))))


# ============================================
# 가용 / 호환 판정
# ============================================

# ============================================
# Phase 1: 자제심/수치심 모디파이어 (내면/사회 억제)
# ============================================

# 자제심 페널티 계수 (자제심 1당 점수 -N)
RESTRAINT_PENALTY_FACTOR = 0.3
# 수치심 페널티 계수 (수치심 1당 점수 -N, 관객 있을 때만)
SHAME_PENALTY_FACTOR = 0.2

# 아키타입별 자제심 기본값 — 명시 prop 없을 때 fallback.
# 범위: 10(방종) ~ 80(순수/절제), 중립은 50 부근.
ARCHETYPE_RESTRAINT_DEFAULT = {
    "innocent":  80,  # 순진 — 성적 지식/경험 없음, 강한 내면 억제
    "timid":     70,  # 소심 — 수줍어 꺼림
    "cold":      70,  # 냉담 — 거리감/의심
    "proud":     65,  # 오만 — 자존심 억제
    "tsundere":  60,  # 츤데레 — 겉 억제 (속은 수용)
    "devoted":   55,  # 헌신 — 파트너에게만 개방
    "stoic":     50,  # 과묵 — 중립
    "gentle":    40,  # 온화 — 보통
    "fierce":    30,  # 격렬 — 욕구 강함
    "cheerful":  25,  # 활발 — 사교적/개방적
    "seductive": 10,  # 유혹 — 방종
}


# 아키타입별 성격 7 trait 기본값 — trinary (-1/0/1).
# 명시 `성격:{key}` prop 없을 때 fallback. Phase 2 탤런트 (§7.2 spec).
PERSONALITY_TRAITS = ("담력", "태도", "응답", "자존심", "츤데레", "정조", "명랑")

_DEFAULT_PERSONALITY = {k: 0 for k in PERSONALITY_TRAITS}

ARCHETYPE_PERSONALITY_DEFAULT = {
    "stoic":     {"담력": 1,  "태도": 0,  "응답": -1, "자존심": 0,  "츤데레": 0, "정조": 0,  "명랑": -1},
    "cheerful":  {"담력": 0,  "태도": -1, "응답": 0,  "자존심": 0,  "츤데레": 0, "정조": 0,  "명랑": 1},
    "timid":     {"담력": -1, "태도": -1, "응답": -1, "자존심": -1, "츤데레": 0, "정조": 1,  "명랑": 0},
    "fierce":    {"담력": 1,  "태도": 1,  "응답": 1,  "자존심": 1,  "츤데레": 0, "정조": 0,  "명랑": 0},
    "innocent":  {"담력": 0,  "태도": -1, "응답": -1, "자존심": 0,  "츤데레": 0, "정조": 1,  "명랑": 1},
    "cold":      {"담력": 1,  "태도": 1,  "응답": 1,  "자존심": 1,  "츤데레": 0, "정조": -1, "명랑": -1},
    "gentle":    {"담력": 0,  "태도": -1, "응답": -1, "자존심": 0,  "츤데레": 0, "정조": 0,  "명랑": 0},
    "seductive": {"담력": 1,  "태도": 0,  "응답": 0,  "자존심": 0,  "츤데레": 0, "정조": -1, "명랑": 0},
    "proud":     {"담력": 1,  "태도": 1,  "응답": 1,  "자존심": 1,  "츤데레": 0, "정조": 1,  "명랑": 0},
    "devoted":   {"담력": 0,  "태도": -1, "응답": -1, "자존심": 0,  "츤데레": 0, "정조": 0,  "명랑": 0},
    "tsundere":  {"담력": 0,  "태도": 1,  "응답": 0,  "자존심": 1,  "츤데레": 1, "정조": 1,  "명랑": 0},
}


def _get_partner_archetype(partner_id):
    """파트너 아키타입 조회 — prop / instance / 성격 매핑 순으로 fallback.

    None 반환 가능 (캐릭터 인스턴스 없는 테스트 등).
    """
    # 1. 명시 prop (고정 NPC가 설정)
    explicit_prop = morld.get_unit_prop(partner_id, "아키타입")
    if explicit_prop:
        return explicit_prop
    # 2. Instance 속성 (Character.archetype 또는 REACTION_PROFILE["archetype"])
    char = get_character_asset(partner_id)
    if char:
        direct = getattr(char, 'archetype', None)
        if direct:
            return direct
        profile = getattr(char, 'REACTION_PROFILE', None)
        if profile and profile.get("archetype"):
            return profile["archetype"]
    # 3. 성격 prop → PERSONALITY_TO_ARCHETYPE (S04 Tier-3 자동 유도)
    personality = morld.get_unit_prop(partner_id, "성격")
    if personality:
        try:
            from engine import persona
            return persona.PERSONALITY_TO_ARCHETYPE.get(personality)
        except Exception:
            return None
    return None


def get_restraint_value(partner_id):
    """자제심 수치 — 명시 prop 우선, 없으면 아키타입 기본값, 그것도 없으면 0.

    Why: 명시 `성격:자제심` prop으로 개별 오버라이드 가능.
         아키타입 기본값은 캐릭터 성격과 일관된 시작 수치 제공.
         프로덕션 캐릭터(sera/mila/lina 등)는 REACTION_PROFILE을 통해 자동 적용됨.
    """
    explicit = morld.get_unit_prop(partner_id, "성격:자제심")
    if explicit is not None:
        return explicit
    archetype = _get_partner_archetype(partner_id)
    if archetype:
        return ARCHETYPE_RESTRAINT_DEFAULT.get(archetype, 50)
    return 0  # 아키타입 미설정 시 페널티 없음 (테스트/레거시 호환)


# Phase 2 후반 — 성향 성애 8개 (§6.3 / §7.4 spec).
# 범위가 trait마다 다르다 (0-100 / -1~3 / -1/0/1 / 0/1) — caller가 적절한 clamp 적용.
DISPOSITION_SEXUAL_TRAITS = (
    "성별기호", "쾌감응답", "새드", "마조",
    "도착", "노출벽", "무관심", "감정결여",
)

_DEFAULT_DISPOSITION_SEXUAL = {k: 0 for k in DISPOSITION_SEXUAL_TRAITS}

ARCHETYPE_DISPOSITION_SEXUAL_DEFAULT = {
    "stoic":     {"성별기호": 0, "쾌감응답": 0,  "새드": 0,  "마조": 0,  "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "cheerful":  {"성별기호": 0, "쾌감응답": 1,  "새드": 0,  "마조": 0,  "도착": 10, "노출벽": 10, "무관심": 0, "감정결여": 0},
    "timid":     {"성별기호": 0, "쾌감응답": 0,  "새드": 0,  "마조": 10, "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "fierce":    {"성별기호": 0, "쾌감응답": 0,  "새드": 10, "마조": 0,  "도착": 10, "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "innocent":  {"성별기호": 0, "쾌감응답": 0,  "새드": 0,  "마조": 0,  "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "cold":      {"성별기호": 0, "쾌감응답": -1, "새드": 20, "마조": 0,  "도착": 20, "노출벽": 0,  "무관심": 0, "감정결여": 1},
    "gentle":    {"성별기호": 0, "쾌감응답": 0,  "새드": 0,  "마조": 10, "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "seductive": {"성별기호": 0, "쾌감응답": 1,  "새드": 10, "마조": 10, "도착": 30, "노출벽": 40, "무관심": 0, "감정결여": 0},
    "proud":     {"성별기호": 0, "쾌감응답": 0,  "새드": 20, "마조": 0,  "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "devoted":   {"성별기호": 0, "쾌감응답": 0,  "새드": 0,  "마조": 20, "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
    "tsundere":  {"성별기호": 0, "쾌감응답": -1, "새드": 0,  "마조": 10, "도착": 0,  "노출벽": 0,  "무관심": 0, "감정결여": 0},
}


def get_disposition_value(unit_id, key):
    """성향 성애 trait 값 — 명시 `성향:{key}` prop 우선, 없으면 아키타입 기본값, 0.

    Phase 2 §6.3 / §7.4 spec. 각 trait 범위 상이 — caller가 clamp/해석.

    Why: Phase 1/2 전반 fallback 패턴과 동일. trait별 range는 §6.3 참조.
    """
    if key not in DISPOSITION_SEXUAL_TRAITS:
        raise ValueError(f"Unknown disposition trait: {key!r}. "
                         f"Expected one of {DISPOSITION_SEXUAL_TRAITS}")
    explicit = morld.get_unit_prop(unit_id, f"성향:{key}")
    if explicit is not None:
        return explicit
    archetype = _get_partner_archetype(unit_id)
    if archetype:
        defaults = ARCHETYPE_DISPOSITION_SEXUAL_DEFAULT.get(
            archetype, _DEFAULT_DISPOSITION_SEXUAL)
        return defaults.get(key, 0)
    return 0


def get_personality_value(unit_id, key):
    """성격 trait 값 — 명시 `성격:{key}` prop 우선, 없으면 아키타입 기본값, 없으면 0.

    Phase 2 §7.2 spec 구현. trinary (-1/0/1).

    Why: Phase 1 `get_restraint_value` 패턴 재사용 — 신규 네임드 NPC는 명시,
         레거시/테스트는 아키타입 기본값 자동 적용.
    """
    if key not in PERSONALITY_TRAITS:
        raise ValueError(f"Unknown personality trait: {key!r}. "
                         f"Expected one of {PERSONALITY_TRAITS}")
    explicit = morld.get_unit_prop(unit_id, f"성격:{key}")
    if explicit is not None:
        return explicit
    archetype = _get_partner_archetype(unit_id)
    if archetype:
        defaults = ARCHETYPE_PERSONALITY_DEFAULT.get(archetype, _DEFAULT_PERSONALITY)
        return defaults.get(key, 0)
    return 0


def get_restraint_modifier(partner_id):
    """자제심 → 점수 페널티 (영구 억제, 내면)

    자제심 100 → -30점 (호감 요구치 30 상승과 동등).
    아키타입별 기본값 자동 적용 (innocent=80 → -24 / seductive=10 → -3).

    **Phase 1.9**: 실질 자제심 사용 — 복종 누적 시 페널티도 감소
    (함락되면 허들 자연히 낮아짐).

    Why: era TW의 자제심(自制心) Talent 20 — "성적욕망 억제, 매각 요구 높음".
         morld에선 점수 합산 모델에 모디파이어로 반영.
    """
    from romance_dynamics import get_effective_restraint
    return -get_effective_restraint(partner_id) * RESTRAINT_PENALTY_FACTOR


# 관객계수 세부 상수
OUTDOOR_VISIBILITY_MULT = 1.2    # 야외: 개방된 시야로 감지 범위 ↑
INDOOR_VISIBILITY_MULT = 1.0     # 실내: 벽이 시각 차단 (소리만)


def _count_third_parties(partner_id):
    """같은 location의 의식 있는 제3자 수 (플레이어/파트너/기절·수면 제외)."""
    location = morld.get_unit_location(partner_id)
    if not location:
        return 0
    chars = morld.get_characters_at_location(location[0], location[1]) or []
    player_id = morld.get_player_id()

    try:
        import survival
        _is_out = lambda cid: (survival.is_npc_fainted(cid)
                               or survival.is_npc_sleeping(cid))
    except Exception:
        _is_out = lambda _cid: False

    count = 0
    for cid in chars:
        if cid == partner_id or cid == player_id:
            continue
        if _is_out(cid):
            continue
        count += 1
    return count


def _global_stealth_chance():
    """사전 평가용 은신 성공 확률 (세션 내부 state 없이 prop 기반 추정).

    romance_core.calculate_stealth_chance는 session state["hiding"] 기반.
    이 헬퍼는 세션 외부 — status:stealth prop으로만 판단.
    """
    chance = STEALTH_BASE_CHANCE  # 0.3
    player_id = morld.get_player_id()
    if morld.get_unit_prop(player_id, "status:stealth") == 1:
        chance += STEALTH_HIDING_BONUS  # +0.4
    return min(chance, 0.9)


def get_audience_factor(partner_id):
    """관객 계수 — 효과적 감지 가능성 (0.0 ~ 1.0).

    공식:
        density = min(1.0, audience_count / location_length)
        visibility_mult = 1.2(야외) / 1.0(실내)
        factor = density × visibility_mult × (1 - 은신_성공률)

    의미:
    - 좁은 공간일수록 밀도↑ (같은 관객 수라도 factor 상승)
    - 야외 +20% 보정 (탁 트인 시야)
    - 은신 성공 확률만큼 factor 감소 (은신 중이면 덜 부끄러움)

    플레이어/파트너/기절·수면 NPC는 관객 아님.

    TODO (향후): 관객별 친밀도/관계 가중치, 소음(stance) 영향.
    """
    audience = _count_third_parties(partner_id)
    if audience == 0:
        return 0.0

    loc = morld.get_unit_location(partner_id)
    loc_info = morld.get_location_info(loc[0], loc[1]) or {}
    length = max(1, loc_info.get("length", 1))
    is_indoor = loc_info.get("is_indoor", True)

    density = min(1.0, audience / length)
    visibility_mult = INDOOR_VISIBILITY_MULT if is_indoor else OUTDOOR_VISIBILITY_MULT
    stealth = _global_stealth_chance()

    factor = density * visibility_mult * (1.0 - stealth)
    return max(0.0, min(1.0, factor))


def get_shame_modifier(partner_id):
    """수치심 × 관객 계수 → 점수 페널티 (상황적 억제, 사회)

    수치심 100 + 관객 있음 → -20점.
    관객이 없으면 효과 0 (단둘이면 수치심 덜 작용).

    Phase 2 후반: 노출벽/도착 성향이 수치심 페널티를 상쇄한다.
      relief = (노출벽 + 도착) / 200 (0~1)
      최종 페널티 × (1 - relief)
    """
    props = morld.get_unit_props(partner_id) or {}
    shame = props.get("상태:수치심", 0)
    audience = get_audience_factor(partner_id)
    raw_penalty = -shame * SHAME_PENALTY_FACTOR * audience
    # 노출벽/도착 상쇄 (0~100 각)
    exhib = get_disposition_value(partner_id, "노출벽")
    pervert = get_disposition_value(partner_id, "도착")
    relief = min(1.0, (exhib + pervert) / 200.0)
    return raw_penalty * (1.0 - relief)


# ============================================
# 수치심 상태 변동 — 이벤트 훅
# ============================================

SHAME_MAX = 100
SHAME_MIN = 0

# 이벤트별 수치심 증가량 (양수)
SHAME_GAIN_ROMANCE_DISCOVERED = 20  # 행위 중 제3자에게 들킴
SHAME_GAIN_NUDE_DISCOVERED = 10     # 나체 상태 추가 페널티
SHAME_GAIN_NEAR_MISS = 3            # 은신 성공 스릴 (들킬 뻔)
SHAME_GAIN_MASTURBATION_SEEN = 25   # 자위 목격
SHAME_GAIN_NUDE_IN_PUBLIC = 5       # 공공장소 노출 상태 진입

# 외부 사정 수치심 — 부위별 가시성/치부 노출도 기반
SHAME_GAIN_EXTERNAL_CUMSHOT = {
    "얼굴": 15,
    "가슴": 10,
    "배": 6,
    "엉덩이": 5,
    "음부": 3,
}

# NPC↔NPC 정사 상태 — 단일 문자열 prop으로 통합 (Phase 2.6)
# 값: "합의" / "피해" / "가해" / None. 기존 3개 플래그 교체.
NPC_SEX_ROLE_KEY = "상태:NPC정사"
NPC_SEX_CONSENSUAL = "합의"
NPC_SEX_VICTIM = "피해"
NPC_SEX_AGGRESSOR = "가해"
NPC_SEX_ROLES = (NPC_SEX_CONSENSUAL, NPC_SEX_VICTIM, NPC_SEX_AGGRESSOR)


def get_npc_sex_role(unit_id):
    """현재 NPC 정사 역할 반환 — 미정사 시 None."""
    return morld.get_unit_prop(unit_id, NPC_SEX_ROLE_KEY)


def is_in_npc_sex(unit_id):
    """NPC↔NPC 정사 중 여부 (역할 무관)."""
    return get_npc_sex_role(unit_id) is not None


def is_npc_sex_victim(unit_id):
    return get_npc_sex_role(unit_id) == NPC_SEX_VICTIM


def is_npc_sex_aggressor(unit_id):
    return get_npc_sex_role(unit_id) == NPC_SEX_AGGRESSOR


def set_npc_sex_role(unit_id, role):
    """NPC 정사 역할 설정. role ∈ {'합의', '피해', '가해'}."""
    if role not in NPC_SEX_ROLES:
        raise ValueError(f"Invalid NPC sex role: {role!r}")
    morld.set_unit_prop(unit_id, NPC_SEX_ROLE_KEY, role)


def clear_npc_sex_role(unit_id):
    morld.clear_prop(unit_id, NPC_SEX_ROLE_KEY)


# 음식 첨가물 — 개별 `상태:{name}첨가` 플래그 대신 중앙 registry 기반 일괄 적용
# (Phase 2.6). 3 먹기 경로(플레이어/NPC 자율/NPC 선물)에서 공용.
FOOD_ADDITIVES = ("미약", "취기", "독주", "마약", "최면제", "배란유도제", "정력제")


def _food_additive_prop_key(name):
    return f"상태:{name}첨가"


def has_food_additive(item_id, name):
    """음식 item에 특정 첨가물 유무."""
    return morld.get_unit_prop(item_id, _food_additive_prop_key(name)) == 1


def add_food_additive(item_id, name):
    """음식 item에 첨가물 마킹."""
    morld.set_unit_prop(item_id, _food_additive_prop_key(name), 1)


def apply_food_additive_effects(eater_id, item_id):
    """음식 첨가물 효과 일괄 적용 — 활성 미약/배란유도/정력제는 스택 방지.

    각 첨가물 고정 효과:
      미약     → 상태:미약 6h 타이머 + 트랜스:외부 +30
      취기     → 상태:취기 +15 (누적, cap 100)
      독주     → 상태:취기 +30 (누적, cap 100)
      마약     → 트랜스:외부 +50 (누적)
      최면제   → 트랜스:외부 +40 (누적)
      배란유도제 → 상태:배란유도 24h 타이머
      정력제   → 상태:정력제 6h 타이머
    """
    # 미약
    if has_food_additive(item_id, "미약") and not is_status_active(eater_id, "미약"):
        apply_timed_status(eater_id, "미약")
        morld.modify_prop(eater_id, "트랜스:외부", 30)
    # 취기 누적
    drunk_gain = 0
    if has_food_additive(item_id, "취기"):
        drunk_gain += 15
    if has_food_additive(item_id, "독주"):
        drunk_gain += 30
    if drunk_gain > 0:
        cur = morld.get_unit_prop(eater_id, "상태:취기") or 0
        morld.set_unit_prop(eater_id, "상태:취기", min(100, cur + drunk_gain))
    # 트랜스 누적
    if has_food_additive(item_id, "마약"):
        morld.modify_prop(eater_id, "트랜스:외부", 50)
    if has_food_additive(item_id, "최면제"):
        morld.modify_prop(eater_id, "트랜스:외부", 40)
    # 타이머 기반
    if has_food_additive(item_id, "배란유도제") and not is_status_active(eater_id, "배란유도"):
        apply_timed_status(eater_id, "배란유도")
    if has_food_additive(item_id, "정력제") and not is_status_active(eater_id, "정력제"):
        apply_timed_status(eater_id, "정력제")

# 시간 감쇠
SHAME_DECAY_PER_HOUR = 5            # 1시간당 감소량 (자연 감쇠)

# 수치심 > 0인 유닛 추적 — 감쇠 tick에서 iterate
_SHAME_REGISTRY = set()


def apply_shame(unit_id, delta, reason=None):
    """수치심 변동 + SHAME_MIN/MAX clamp + 레지스트리 관리.

    Args:
        unit_id: 대상 NPC
        delta: 변동량 (+증가 / -감소)
        reason: 디버그 로그용 문자열 (optional)

    Returns:
        int: clamp 후 최종 수치심 값
    """
    current = morld.get_unit_prop(unit_id, "상태:수치심") or 0
    new_val = max(SHAME_MIN, min(SHAME_MAX, current + delta))
    morld.set_unit_prop(unit_id, "상태:수치심", new_val)
    if new_val > 0:
        _SHAME_REGISTRY.add(unit_id)
    else:
        _SHAME_REGISTRY.discard(unit_id)
    return new_val


def _decay_shame_tick():
    """시간 감쇠 — 레지스트리 전체 -SHAME_DECAY_PER_HOUR.

    1시간 간격으로 호출 (subscribe_time_elapsed 핸들러).
    """
    for uid in list(_SHAME_REGISTRY):
        current = morld.get_unit_prop(uid, "상태:수치심") or 0
        if current <= 0:
            _SHAME_REGISTRY.discard(uid)
            continue
        new_val = max(SHAME_MIN, current - SHAME_DECAY_PER_HOUR)
        morld.set_unit_prop(uid, "상태:수치심", new_val)
        if new_val <= 0:
            _SHAME_REGISTRY.discard(uid)


def on_romance_discovered(partner_id):
    """행위 중 제3자에게 들킴 → 수치심 대폭 상승 (나체면 추가)."""
    exposure = get_exposure_state(partner_id)
    delta = SHAME_GAIN_ROMANCE_DISCOVERED
    if exposure.get("upper_exposed") or exposure.get("lower_exposed"):
        delta += SHAME_GAIN_NUDE_DISCOVERED
    return apply_shame(partner_id, delta, reason="romance_discovered")


def on_stealth_near_miss(partner_id):
    """은신 성공으로 아슬아슬하게 안 들킴 → 약한 수치심 (스릴)."""
    return apply_shame(partner_id, SHAME_GAIN_NEAR_MISS, reason="near_miss")


def on_masturbation_witnessed(unit_id):
    """자위 중 목격됨 → 강한 수치심."""
    return apply_shame(unit_id, SHAME_GAIN_MASTURBATION_SEEN,
                       reason="masturbation_witnessed")


# ============================================
# 자위 목격자 성욕 증가 (공통 훅)
# ============================================

_MASTURBATION_OBSERVER_AROUSAL_BASE = 15
_MASTURBATION_OBSERVER_AROUSAL_AFFECTION_BONUS = 10  # 호감 ≥ 40 추가


def on_masturbation_observed_arousal(witness_id, masturbator_id):
    """자위 목격자 성욕 증가.

    발각자(witness) 관점 — 자위하는 상대에게 호감이 있으면 성욕 증가폭 증가.
    시나리오 1/2/3 공통 진입점. 무감한 관계(호감 < 0)는 아무 효과 없음.
    """
    target_info = morld.get_unit_info(masturbator_id)
    target_name = target_info.get("name", "") if target_info else ""
    affection = 0
    if target_name:
        affection = morld.get_unit_prop(
            witness_id, f"관계:{target_name}:호감") or 0

    if affection < 0:
        return morld.get_unit_prop(witness_id, "상태:성욕") or 0

    gain = _MASTURBATION_OBSERVER_AROUSAL_BASE
    if affection >= 40:
        gain += _MASTURBATION_OBSERVER_AROUSAL_AFFECTION_BONUS

    morld.modify_prop(witness_id, "상태:성욕", gain)
    return morld.get_unit_prop(witness_id, "상태:성욕") or 0


def on_nude_in_public(unit_id):
    """공공장소(관객 있는 location)에서 노출 상태 진입 → 수치심 증가."""
    return apply_shame(unit_id, SHAME_GAIN_NUDE_IN_PUBLIC,
                       reason="nude_in_public")


def on_external_cumshot(unit_id, target_part):
    """외부 사정 — 부위별 수치심 변동. SEMEN_PARTS 외는 0."""
    gain = SHAME_GAIN_EXTERNAL_CUMSHOT.get(target_part, 0)
    if gain == 0:
        return morld.get_unit_prop(unit_id, "상태:수치심") or 0
    return apply_shame(unit_id, gain, reason=f"external_cumshot:{target_part}")


def get_disposition_arousal_multiplier(partner_id):
    """성향 성애 기반 성욕 gain 배율.

    Phase 2 §7.13 — 쾌감응답이 반발 factor와 유사하게 배율 적용.
      쾌감응답 +1 (솔직) → ×1.3
      쾌감응답  0 (보통) → ×1.0
      쾌감응답 -1 (부정) → ×0.7
    """
    responsiveness = get_disposition_value(partner_id, "쾌감응답")
    return 1.0 + responsiveness * 0.3


def get_disposition_sm_multipliers(partner_id):
    """성향 마조 기반 복종/반발 배율 — 피가학 수용 성향.

    Phase 2 §7.13 — 마조 높을수록 강제/가해 행위에서 쾌락 수용 ↑.
    S02는 NPC가 주로 피해자 포지션이므로 마조를 통합 배율로 적용.
      마조 0   → 복종 ×1.0, 반발 ×1.0
      마조 50  → 복종 ×1.25, 반발 ×0.75
      마조 100 → 복종 ×1.5, 반발 ×0.5

    새드는 NPC가 가해 입장일 때만 유효 (npc_initiative 경로) — 현재 Slice
    에서는 단순화해 전체 배율에 반영하지 않음 (후속 확장 여지).
    """
    masochism = get_disposition_value(partner_id, "마조")
    # 0~100 선형: factor = 1 + (마조/200)
    factor = 1.0 + masochism * 0.005
    return {
        "복종": factor,
        "반발": max(0.1, 2.0 - factor),  # 배율 합이 2에 가까움
    }


def get_personality_effect_multipliers(partner_id):
    """성격 trait 기반 복종/반발 gain 배율 (양수 변동에만 적용).

    Phase 2 §6.8.2 공식:
    - 복종 증가: 자존심 -1 → ×1.5 / +1 → ×0.5 / 0 → ×1.0
    - 반발 증가: 담력 -1 → ×0.7 / +1 → ×1.3 / 0 → ×1.0

    Returns:
        dict {"복종": float, "반발": float}
    """
    pride = get_personality_value(partner_id, "자존심")
    boldness = get_personality_value(partner_id, "담력")
    sub_mult = 1.0 + (-pride) * 0.5       # -1 → 1.5, +1 → 0.5
    reb_mult = 1.0 + boldness * 0.3        # -1 → 0.7, +1 → 1.3
    return {"복종": sub_mult, "반발": reb_mult}


def get_player_address_form(npc_id, player_id):
    """Slice P7: NPC가 플레이어를 호칭하는 형태 반환 (지배/복종 연속 축 기반).

    반환값은 context["호칭"] 으로 주입되어 대사 템플릿 `{호칭}`에 사용.
    scalar `net = submission - dominance` 단일 축으로 해석:

      net ≥ 80   → "주인님"     (강한 자발 종속, 노예화 수준)
      net ≥ 40   → "{이름}님"   (존칭, 호감 깊음)
      -40~40     → "{이름}"     (이름 호칭, 대등)
      net ≤ -40  → "너"          (하대, 지배 누적)
      net ≤ -80  → "꼬마"        (경멸·조롱, 강한 지배)

    이름은 player_info에서 조회. 기본 "주인공".
    연속 값 구간화 — 기존 축 수치 변동이 호칭 전환으로 자연 연결.
    """
    sub_key = _get_relationship_key(player_id, "복종")
    dom_key = _get_relationship_key(player_id, "지배")
    submission = morld.get_unit_prop(npc_id, sub_key) or 0
    dominance = morld.get_unit_prop(npc_id, dom_key) or 0
    net = submission - dominance
    player_info = morld.get_unit_info(player_id)
    name = player_info.get("name", "주인공") if player_info else "주인공"
    if net >= 80:
        return "주인님"
    if net >= 40:
        return f"{name}님"
    if net <= -80:
        return "꼬마"
    if net <= -40:
        return "너"
    return name


def get_ownership_modifier(partner_id, player_id):
    """Slice P6: 주도권 축 기반 availability 선형 모디파이어.

    시뮬레이션 연속 함수 — 복종/지배 값 자체가 스펙트럼 지표.
    불연속 boolean 전환(era) 대신 점진적 효과.

      복종 × 0.3  → 복종 100 시 +30 (자발 수용)
      지배 × 0.15 → 지배 100 시 -15 (주인 권위로 행위 거부)
      선형이므로 중간값은 부드럽게 적용 (예: 복종 50 → +15)

    복종/지배는 상호 배타 축이라 동시에 큰 값 불가.
    기존 테스트/레거시 경로에서 복종이 SUBMISSION_MAX(100)을 초과하는
    경우가 있으므로 입력 값을 0-100으로 clamp (견고성).
    """
    sub_key = _get_relationship_key(player_id, "복종")
    dom_key = _get_relationship_key(player_id, "지배")
    submission = min(100, max(0, morld.get_unit_prop(partner_id, sub_key) or 0))
    dominance = min(100, max(0, morld.get_unit_prop(partner_id, dom_key) or 0))
    return submission * 0.3 - dominance * 0.15


def get_personality_gate_modifier(partner_id):
    """성격 7 trait 기반 게이트 모디파이어 (availability_score 페널티).

    Phase 2 §6.8.1 / §7.12 point 3 공식:
      threshold += 담력×5 + 자존심×8 + 정조×10 + 태도×3

    threshold 상승 = availability_score 감소 → 부호 반전하여 음수로 반환.

    Why: 담대/자존심/정조/태도는 수락 장벽. trinary (-1/0/1)이므로
         최대치 합 = (5+8+10+3) = 26, 최소치 = -26.
    """
    boldness = get_personality_value(partner_id, "담력")
    pride = get_personality_value(partner_id, "자존심")
    chastity = get_personality_value(partner_id, "정조")
    attitude = get_personality_value(partner_id, "태도")
    threshold_delta = (boldness * 5 + pride * 8
                       + chastity * 10 + attitude * 3)
    return -threshold_delta


def calculate_availability_score(partner_id, player_id, action_def):
    """액션 가용성 점수 — 베이스라인 + 모디파이어 합산

    Returns 0 이상 → 합의 가능, 미만 → 강제 필요 (또는 거부).

    모디파이어 (점수 가감):
    - 호감 (베이스라인)
    - 성욕/복종 할인 (get_effective_affection_req 경유)
    - 자제심 페널티 (영구 내면 억제)
    - 수치심 × 관객 페널티 (상황 억제)
    - 성격 게이트 (담력/자존심/정조/태도)

    Why: era TW GET_SUCCESS_RATE 패턴 — 모든 가감 요소를 점수로 통합.
         이후 성격/각인 추가 모디파이어가 더해질 여지를 열어둠.
    """
    props = morld.get_unit_props(partner_id) or {}
    affection = props.get(get_affection_key(player_id), 0)
    arousal = props.get("상태:성욕", 0)
    submission = props.get(get_submission_key(player_id), 0)
    eff_req = get_effective_affection_req(
        action_def.get("affection_req", 0), arousal, submission)
    baseline = affection - eff_req
    # Phase 1 모디파이어
    baseline += get_restraint_modifier(partner_id)
    baseline += get_shame_modifier(partner_id)
    # Phase 2 성격 게이트 (담력/자존심/정조/태도)
    baseline += get_personality_gate_modifier(partner_id)
    # Slice P6 — 소유 관계 보정 (노예 +30 / 주인 -15)
    baseline += get_ownership_modifier(partner_id, player_id)
    return baseline


def check_physical_req(action_def, partner_id, player_id):
    """물리 전제 체크 — 충족 시 (True, None), 불충족 시 (False, reason_str)

    action_def["physical_req"] 스키마 (모두 선택적):
    - strength_advantage: True  → 플레이어 근력 > 파트너 근력 필수 (강제 제압용)
    - min_strength: int         → 플레이어 근력 최소치
    (향후 확장: min_hp, requires_standing 등)

    Why: "근력 부족 등 조건이 안맞으면 greyed out". 호감 모디파이어와 달리
         물리 전제는 hard gate — 수치 합산 아니라 단순 충족/불충족.
    """
    req = action_def.get("physical_req")
    if not req:
        return True, None

    if req.get("strength_advantage"):
        from romance_mode import get_strength
        if get_strength(player_id) <= get_strength(partner_id):
            return False, "근력 부족"

    min_str = req.get("min_strength")
    if min_str is not None:
        from romance_mode import get_strength
        if get_strength(player_id) < min_str:
            return False, f"근력 {min_str} 필요"

    return True, None


def resolve_action_mode(partner_id, player_id, action_def):
    """액션 모드 해석 — 'consensual' / 'forced' / 'unavailable'

    - physical_req 불충족 → 'unavailable' (greyed out)
    - 점수 >= 0 → 'consensual' (합의)
    - 점수 < 0 → 'forced' (호감 미달, 강제 필요)
    """
    ok, _reason = check_physical_req(action_def, partner_id, player_id)
    if not ok:
        return "unavailable"
    score = calculate_availability_score(partner_id, player_id, action_def)
    if score >= 0:
        return "consensual"
    return "forced"


def is_action_available(partner_id, player_id, action_def):
    """합의 가능성 체크 (기존 shim) — resolve_action_mode == 'consensual'

    기존 호출부 호환용. 점수 >= 0 이면 True (수치적으로 이전 공식과 동등).
    """
    return resolve_action_mode(partner_id, player_id, action_def) == "consensual"


def is_lust_unlocked(affection, action_def, arousal, submission=0):
    """성욕/복종에 의한 해금인지 (정상 호감 미달이지만 성욕/복종으로 보완)"""
    return affection < action_def["affection_req"] and (arousal > 0 or submission > 0)


def is_anatomy_compatible(action_def, target_id, actor_id=None):
    """행위가 대상/행위자의 해부학적 구조와 호환되는지

    Args:
        action_def: 행위 정의 dict
        target_id: 대상(자극 받는 쪽) 유닛 ID
        actor_id: 행위자(수행하는 쪽) 유닛 ID (삽입 행위 체크용)
    """
    exp_part = action_def.get("exp_part")
    if exp_part:
        category = SENSATION_MAP.get(exp_part)
        if category is not None:
            import gender as gender_mod
            if not gender_mod.has_anatomy(target_id, category):
                return False
    # 행위자 해부학 체크 (삽입 행위: requires_player_anatomy)
    player_req = action_def.get("requires_player_anatomy")
    if player_req and actor_id is not None:
        import gender as gender_mod
        if not gender_mod.has_anatomy(actor_id, player_req):
            return False
    # 양쪽 해부학 체크 (tribadism 등: 양쪽 모두 V 보유 필요)
    both_req = action_def.get("requires_both_anatomy")
    if both_req and actor_id is not None:
        import gender as gender_mod
        if not gender_mod.has_anatomy(target_id, both_req):
            return False
        if not gender_mod.has_anatomy(actor_id, both_req):
            return False
    # 가슴 크기 체크
    breast_req = action_def.get("requires_breast_size")
    if breast_req is not None:
        import gender as gender_mod
        if gender_mod.get_breast_size(target_id) < breast_req:
            return False
    return True


def is_action_blocked_by_state(action_def, target_id):
    """결박/삽입물/기생체에 의한 행위 차단 체크

    Args:
        action_def: 행위 정의 dict
        target_id: 대상 유닛 ID (NPC)

    Returns:
        str or None: None이면 차단 아님, str이면 차단 사유
    """
    import restraint

    # 구강 차단: 입 결박 시 구강 행위 불가
    if action_def.get("uses_mouth") and restraint.is_gagged(target_id):
        return "입 결박"

    # 입 자유 필요: 강제 투여 등
    if action_def.get("requires_no_gag") and restraint.is_gagged(target_id):
        return "입 결박"

    # 삽입물/기생체 차단
    orifice = action_def.get("insertion_orifice")
    if orifice and action_def.get("is_insertion_attempt"):
        orifice_kr = "음부" if orifice == "vaginal" else "항문"
        if morld.get_unit_prop(target_id, f"삽입물:{orifice_kr}"):
            return f"{orifice_kr} 삽입물"
        parasite_slot = _ORIFICE_TO_PARASITE_SLOT.get(orifice)
        if parasite_slot and morld.get_unit_prop(target_id, parasite_slot):
            return "기생체 부착"

    return None


# 삽입 오리피스 → 기생 슬롯 매핑
_ORIFICE_TO_PARASITE_SLOT = {
    "vaginal": "기생:음부",
    "anal": "기생:항문",
}


# ============================================
# 효과 계산
# ============================================

def calculate_effects(action_def, partner_id, player_id=None):
    """경험치 + 감각 + 지향성 보정된 효과 계산"""
    base_effects = action_def["effects"].copy()
    exp_part = action_def.get("exp_part")

    if exp_part:
        exp_key = f"경험:{exp_part}"
        partner_props = morld.get_unit_props(partner_id)
        exp_value = partner_props.get(exp_key, 0)
        multiplier = 1.0 + (exp_value * 0.1)
        for stat, value in base_effects.items():
            base_effects[stat] = round(value * multiplier)

        # 감각 보너스
        category = SENSATION_MAP.get(exp_part)
        if category:
            sensation = get_sensation_level(partner_id, category)
            arousal_base = action_def["effects"].get("성욕", 0)
            if arousal_base > 0 and sensation > 0:
                bonus = round(arousal_base * sensation * 0.1)
                base_effects["성욕"] = base_effects.get("성욕", 0) + bonus

        # 수유 보너스: B 카테고리 + 수유 중 → ×1.3
        if category == "B":
            import pregnancy
            if pregnancy.is_lactating(partner_id):
                for stat in base_effects:
                    base_effects[stat] = round(base_effects[stat] * 1.3)

        # 경험치 +1 (트랜스 시 ×1.2 / ×1.5)
        exp_gain = 1
        try:
            from romance_dynamics import compute_trance_multipliers
            trance_mult = compute_trance_multipliers(partner_id).get("experience", 1.0)
            exp_gain = max(1, round(exp_gain * trance_mult))
        except Exception:
            pass
        morld.modify_prop(partner_id, exp_key, exp_gain)

    # 노출 보너스 (해당 부위 노출 시 ×1.5)
    bonus_area = action_def.get("exposure_bonus")
    if bonus_area:
        exposure = get_exposure_state(partner_id)
        if exposure.get(f"{bonus_area}_exposed"):
            for stat in base_effects:
                base_effects[stat] = round(base_effects[stat] * EXPOSURE_BONUS)

    # 성적 지향성 배율
    if player_id:
        import gender as gender_mod
        orientation_mult = gender_mod.get_orientation_multiplier(partner_id, player_id)
        if orientation_mult != 1.0:
            for stat in base_effects:
                base_effects[stat] = round(base_effects[stat] * orientation_mult)

    # Phase 2 성격 변동 계수 (양수 복종/반발 gain에만 적용)
    personality_mult = get_personality_effect_multipliers(partner_id)
    sm_mult = get_disposition_sm_multipliers(partner_id)
    for stat in ("복종", "반발"):
        val = base_effects.get(stat, 0)
        if val <= 0:
            continue
        combined = personality_mult.get(stat, 1.0) * sm_mult.get(stat, 1.0)
        if combined != 1.0:
            base_effects[stat] = round(val * combined)

    # Phase 2 후반 성향 쾌감응답 — 양수 성욕 gain에만 배율
    arousal_mult = get_disposition_arousal_multiplier(partner_id)
    if arousal_mult != 1.0:
        val = base_effects.get("성욕", 0)
        if val > 0:
            base_effects["성욕"] = round(val * arousal_mult)

    return base_effects


# ============================================
# 노출 / 탈의
# ============================================

def get_exposure_state(unit_id):
    """유닛의 상/하체 노출 상태 반환"""
    import equipment
    equipped = equipment.get_equipped_items(unit_id)
    has_top = False
    has_bra = False
    has_bottom = False
    has_panties = False
    for item_id in equipped:
        info = morld.get_item_info(item_id)
        if not info:
            continue
        ep = info.get("equip_props", {})
        if ep.get("착용:상의", 0) > 0:
            has_top = True
        if ep.get("착용:속옷상의", 0) > 0:
            has_bra = True
        if ep.get("착용:하의", 0) > 0:
            has_bottom = True
        if ep.get("착용:속옷하의", 0) > 0:
            has_panties = True
    return {
        "upper_exposed": not has_top and not has_bra,
        "lower_exposed": not has_bottom and not has_panties,
    }


def get_next_undress_item(unit_id, upper=True):
    """다음 탈의 대상 아이템 반환 (None이면 더 벗을 것 없음)"""
    import equipment
    equipped = equipment.get_equipped_items(unit_id)
    slots = UNDRESS_UPPER_SLOTS if upper else UNDRESS_LOWER_SLOTS
    for slot in slots:
        for item_id in equipped:
            info = morld.get_item_info(item_id)
            if info and info.get("equip_props", {}).get(slot, 0) > 0:
                return item_id
    return None


def perform_undress(unit_id, item_id):
    """아이템 1개 탈의 (unequip)"""
    import equipment
    return equipment.unequip_item(unit_id, item_id)


# ============================================
# 강탈
# ============================================

def get_next_loot_item(unit_id, upper=True):
    """다음 강탈 대상: 장착 중 우선, 없으면 미장착 인벤토리 의류

    Returns:
        tuple: (item_id, is_equipped) 또는 (None, False)
    """
    import equipment
    equipped = equipment.get_equipped_items(unit_id)
    slots = UNDRESS_UPPER_SLOTS if upper else UNDRESS_LOWER_SLOTS

    # 1차: 장착 중인 아이템 (undress 순서)
    for slot in slots:
        for item_id in equipped:
            info = morld.get_item_info(item_id)
            if info and info.get("equip_props", {}).get(slot, 0) > 0:
                return item_id, True

    # 2차: 인벤토리 내 미장착 의류
    equipped_set = set(equipped)
    inventory = morld.get_unit_inventory(unit_id)
    for item_id in inventory:
        if item_id in equipped_set:
            continue
        info = morld.get_item_info(item_id)
        if not info:
            continue
        ep = info.get("equip_props", {})
        if any(ep.get(s, 0) > 0 for s in slots):
            return item_id, False

    return None, False


def perform_loot(source_id, item_id, target_id, is_equipped=False):
    """의류 1개 강탈: 장착 중이면 해제 후 이동"""
    if is_equipped:
        import equipment
        equipment.unequip_item(source_id, item_id)
    morld.remove_item(source_id, item_id, 1)
    import inventory as inv_mod
    return inv_mod.safe_give_item(target_id, item_id, 1)


# ============================================
# 정액 시스템
# ============================================

def get_semen_total(unit_id):
    """전체 정액 오염 합산"""
    return sum(morld.get_unit_prop(unit_id, f"오염물:정액:{p}") or 0 for p in SEMEN_PARTS)


def _apply_semen(target_id, part, amount):
    """부위별 정액 적용"""
    prop = f"오염물:정액:{part}"
    current = morld.get_unit_prop(target_id, prop) or 0
    morld.set_unit_prop(target_id, prop, min(100, current + amount))
    try:
        import pollution
        current_poll = pollution.get_unit_pollution(target_id)
        pollution.set_unit_pollution(target_id, current_poll + 10)
    except Exception:
        pass


def clear_all_semen(unit_id):
    """전부위 정액 제거 (목욕 시) — 외부 + 체내"""
    for p in SEMEN_PARTS:
        morld.clear_prop(unit_id, f"오염물:정액:{p}")
    for p in INTERNAL_SEMEN_PARTS:
        morld.clear_prop(unit_id, f"체내:정액:{p}")


def get_internal_semen(unit_id, part):
    """체내 정액 조회"""
    return morld.get_unit_prop(unit_id, f"체내:정액:{part}") or 0


def get_internal_semen_total(unit_id):
    """체내 정액 전체 합산"""
    return sum(get_internal_semen(unit_id, p) for p in INTERNAL_SEMEN_PARTS)


_INTERNAL_TO_EXTERNAL_PART = {
    "음부": "음부",     # 질 내 overflow → 질 입구/허벅지 외부 오염
    "항문": "엉덩이",   # 항문 overflow → 엉덩이 외부 오염
    "구강": "얼굴",     # 구강 overflow → 턱·뺨 외부 오염
}


def _apply_internal_semen(target_id, part, amount):
    """체내 정액 적용 — overflow 시 초과분을 외부 오염으로 전이."""
    prop = f"체내:정액:{part}"
    current = morld.get_unit_prop(target_id, prop) or 0
    new_val = current + amount
    if new_val > INTERNAL_SEMEN_MAX:
        overflow = new_val - INTERNAL_SEMEN_MAX
        morld.set_unit_prop(target_id, prop, INTERNAL_SEMEN_MAX)
        ext_part = _INTERNAL_TO_EXTERNAL_PART.get(part)
        if ext_part:
            _apply_semen(target_id, ext_part, overflow)
    else:
        morld.set_unit_prop(target_id, prop, new_val)


def clear_all_internal_semen(unit_id):
    """전부위 체내 정액 제거"""
    for p in INTERNAL_SEMEN_PARTS:
        morld.clear_prop(unit_id, f"체내:정액:{p}")


def calculate_ejaculation_amount(unit_id, stamina, max_stamina=None):
    """사정량 계산 — P 감각 + 체력 기반

    Args:
        unit_id: P 보유자 unit_id
        stamina: 현재 세션 스태미나 (= 체력)
        max_stamina: 최대 체력 (None이면 기존 0-10 스케일 가정)

    Returns:
        int: 사정량 (10-100)
    """
    base = SEMEN_AMOUNT_BASE
    p_sensation = get_sensation_level(unit_id, "P")
    sensation_bonus = p_sensation * 3
    # HP 정규화 (max_stamina > 10이면 0-10 범위로 변환)
    if max_stamina and max_stamina > 10:
        normalized = (stamina / max(1, max_stamina)) * 10
    else:
        normalized = stamina
    stamina_bonus = normalized * 2
    amount = base + sensation_bonus + stamina_bonus
    # 정액 잔량에 따른 스케일링 (50% 미만 → 비례 감소)
    try:
        import semen as semen_mod
        current_semen = semen_mod.get_semen(unit_id)
        if current_semen < 50:
            amount = amount * (current_semen / 50)
    except ImportError:
        pass
    return max(SEMEN_AMOUNT_MIN, min(SEMEN_AMOUNT_MAX, round(amount)))


# ============================================
# 삽입 / 충돌 헬퍼
# ============================================

def _has_active_penetration(active_toggles):
    """활성 토글 중 삽입(허리흔들기) 행위가 있는지 확인"""
    return bool(active_toggles & _THRUST_TOGGLE_IDS)


def _has_active_intercourse_from_state(state):
    """삽입 상태에서 질 삽입 중인지 확인 (state 기반)"""
    insertion = state.get("insertion", {})
    return insertion.get("active") and insertion.get("orifice") == "vaginal"


def get_insertion_exp_part(state):
    """삽입 상태의 exp_part 반환"""
    insertion = state.get("insertion", {})
    if not insertion.get("active"):
        return None
    return _INSERTION_EXP_MAP.get(insertion.get("orifice"))


# ── 삽입 상태 헬퍼 (향후 multi-insertion 확장 대비) ──
# 현재: state["insertion"] = {"active": bool, "orifice": str, "who": str, ...}
# 향후: state["insertions"] = list of dicts 로 전환 시 이 함수만 수정

def is_insertion_active(state):
    """삽입 활성 여부 (향후 multi-insertion 확장 대비)"""
    ins = state.get("insertion", {})
    return ins.get("active", False)


def get_insertion_orifice(state):
    """현재 삽입 부위 (향후 list 반환으로 확장 가능)"""
    ins = state.get("insertion", {})
    return ins.get("orifice") if ins.get("active") else None


def get_insertion_who(state):
    """현재 삽입 주체 ("player" / "npc" / None)"""
    ins = state.get("insertion", {})
    return ins.get("who") if ins.get("active") else None


def get_action_exp_part(action_id, action_dict=None):
    """액션의 신체 부위(exp_part) 반환

    Args:
        action_id: 액션 ID
        action_dict: 액션 정의 dict (없으면 자동 조회)

    Returns:
        str: 신체 부위 또는 None
    """
    if action_dict:
        return action_dict.get("exp_part")
    if action_id in TOGGLE_ACTIONS:
        return TOGGLE_ACTIONS[action_id].get("exp_part")
    if action_id in INSTANT_ACTIONS:
        return INSTANT_ACTIONS[action_id].get("exp_part")
    return None


def get_conflicting_toggles(new_action_id, active_toggles, new_action_dict=None):
    """새 토글과 충돌하는 활성 토글 반환

    충돌 조건:
    1. 같은 exp_part (NPC쪽 부위 충돌)
    2. 같은 requires_player_anatomy (플레이어 신체 충돌)
    3. uses_mouth 충돌 (입/혀 행위는 동시에 하나만)
    exp_part가 None인 토글(껴안기 등)은 충돌하지 않습니다.
    """
    new_exp_part = get_action_exp_part(new_action_id, new_action_dict)
    new_def = new_action_dict or TOGGLE_ACTIONS.get(new_action_id) or {}
    new_player_req = new_def.get("requires_player_anatomy")
    new_uses_mouth = new_def.get("uses_mouth")

    conflicting = set()
    for toggle_id in active_toggles:
        if toggle_id == new_action_id:
            continue
        toggle_def = TOGGLE_ACTIONS.get(toggle_id)
        if not toggle_def:
            continue
        # exp_part 충돌 (NPC쪽 부위)
        if new_exp_part and toggle_def.get("exp_part") == new_exp_part:
            conflicting.add(toggle_id)
            continue
        # requires_player_anatomy 충돌 (플레이어 신체)
        if new_player_req and toggle_def.get("requires_player_anatomy") == new_player_req:
            conflicting.add(toggle_id)
            continue
        # uses_mouth 충돌 (입/혀 배타적)
        if new_uses_mouth and toggle_def.get("uses_mouth"):
            conflicting.add(toggle_id)
            continue
        # 허리흔들기 충돌 (requires_active_insertion 토글끼리 배타적)
        if (new_def.get("requires_active_insertion")
                and toggle_def.get("requires_active_insertion")):
            conflicting.add(toggle_id)

    return conflicting


def _remove_conflicting_toggles(new_action_id, active_toggles, new_action_dict=None):
    """새 토글과 충돌하는 토글들을 비활성화 (in-place)"""
    conflicting = get_conflicting_toggles(new_action_id, active_toggles, new_action_dict)
    for toggle_id in conflicting:
        active_toggles.discard(toggle_id)
    return conflicting


# ============================================
# 처녀(첫경험)
# ============================================

# 처녀 prop → 부위명 매핑
_VIRGINITY_TO_PART = {
    "처녀:음부": "음부",
    "처녀:항문": "항문",
    "처녀:구강": "구강",
}


def check_and_clear_virginity(target_id, player_id, action_id, exp_type="consensual"):
    """처녀 해제 체크. 해제 시 보너스 적용 + 부위별 첫경험 기록 + first 반응 키 반환."""
    virginity_prop = VIRGINITY_CLEARING_ACTIONS.get(action_id)
    if not virginity_prop:
        return None
    current = morld.get_unit_prop(target_id, virginity_prop)
    if not current:
        return None
    # 처녀 해제
    morld.set_unit_prop(target_id, virginity_prop, 0)
    # 부위별 첫경험 기록
    part = _VIRGINITY_TO_PART.get(virginity_prop)
    if part:
        record_first_experience(target_id, player_id, exp_type, part)
    # 보너스: 호감 +5
    affection_key = get_affection_key(player_id)
    morld.modify_prop(target_id, affection_key, VIRGINITY_BONUS_AFFECTION)
    # 보너스: 감각 경험치 +3
    action_def = INSTANT_ACTIONS.get(action_id) or TOGGLE_ACTIONS.get(action_id) or {}
    exp_part = action_def.get("exp_part")
    if exp_part:
        morld.modify_prop(target_id, f"경험:{exp_part}", VIRGINITY_BONUS_EXP)
    return f"first_{action_id}"


# ============================================
# 경험 기록 (첫경험 + 마지막경험)
# ============================================

def record_first_experience(target_id, partner_id, exp_type, part):
    """부위별 첫경험 기록 (최초 1회만). part = '음부'/'항문'/'구강'"""
    now = morld.get_game_time()
    # 부위별 첫경험
    part_key = f"기억:첫경험:{part}"
    if not morld.get_unit_prop(target_id, part_key):
        morld.set_unit_prop(target_id, part_key, 1)
        morld.set_unit_prop(target_id, f"{part_key}:유형", exp_type)
        morld.set_unit_prop(target_id, f"{part_key}:상대", partner_id)
        morld.set_unit_prop(target_id, f"{part_key}:시각", now)
    # 전체 첫경험 (최초 1회만)
    if not morld.get_unit_prop(target_id, "기억:첫경험"):
        morld.set_unit_prop(target_id, "기억:첫경험", 1)
        morld.set_unit_prop(target_id, "기억:첫경험:유형", exp_type)
        morld.set_unit_prop(target_id, "기억:첫경험:상대", partner_id)
        morld.set_unit_prop(target_id, "기억:첫경험:시각", now)


def record_last_experience(target_id, partner_id, exp_type):
    """마지막 경험 기록 (항상 갱신)"""
    now = morld.get_game_time()
    morld.set_unit_prop(target_id, "기억:마지막경험:유형", exp_type)
    morld.set_unit_prop(target_id, "기억:마지막경험:상대", partner_id)
    morld.set_unit_prop(target_id, "기억:마지막경험:시각", now)


# ============================================
# 참기 / 질외사정
# ============================================

def is_hold_back_available(state):
    """참기 가능 여부: peaked 부위 존재 + 절정 게이지 > 0"""
    stim = state.get("stim")
    if not stim:
        return False
    import stimulation as _stim_mod
    return (_stim_mod.get_peaked_count(stim) > 0
            and stim["climax_gauge"] > 0)


def is_ejaculate_available(state, player_id):
    """사정하기 가능 여부: P 해부학 + P stim >= threshold(감각 보정)"""
    stim = state.get("stim")
    if not stim:
        return False
    import gender as gender_mod
    if not gender_mod.has_anatomy(player_id, "P"):
        return False
    p_stim = stim["stim"].get("P", 0)
    p_sensation = get_sensation_level(player_id, "P")
    import stimulation as _stim_mod
    threshold = _stim_mod.get_ejaculate_threshold(p_sensation)
    return p_stim >= threshold


def is_pull_out_available(state):
    """질외사정 가능 여부: 삽입 상태 활성 + P 자극 ≥ 임계값"""
    insertion = state.get("insertion", {})
    if not insertion.get("active"):
        return False
    stim = state.get("stim")
    if not stim:
        return False
    return stim["stim"].get("P", 0) >= PULL_OUT_STIM_THRESHOLD


# ============================================
# 준비 / 윤활 체크
# ============================================

def check_preparation(stim_state, action_def):
    """강도 행위 준비 상태 확인

    intensity ≥ 3인 행위는 해당 부위 자극이 PREPARATION_THRESHOLD 이상이어야 함.

    Returns:
        True if 준비됨 or 비강도 행위, False if 미준비
    """
    intensity = action_def.get("intensity", 0)
    if intensity < 3:
        return True
    exp_part = action_def.get("exp_part")
    if not exp_part:
        return True
    category = SENSATION_MAP.get(exp_part)
    if not category:
        return True
    current_stim = stim_state["stim"].get(category, 0)
    return current_stim >= PREPARATION_THRESHOLD


def check_lubrication(partner_id, state):
    """윤활 체크 — V 보유자의 성욕이 임계치 이상인지 확인

    한번 충족되면 세션 동안 유지 (state["lubricated"] = True).
    Returns True if OK, False if too dry.
    """
    if state.get("lubricated"):
        return True
    import gender as gender_mod
    if not gender_mod.has_anatomy(partner_id, "V"):
        state["lubricated"] = True  # V 없으면 항상 OK
        return True
    arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
    if arousal >= LUBRICATION_THRESHOLD:
        state["lubricated"] = True
        return True
    return False


# ============================================
# 은신 판정
# ============================================

# ============================================
# 상태 묘사 (자극 수준 기반 자동 텍스트)
# ============================================

_STIM_HIGH_TEXTS = {
    "F": "얼굴이 달아오르고 있다.",
    "M": "입안의 감각이 뜨겁게 달아오른다.",
    "B": "가슴의 감각이 극에 달하고 있다.",
    "V": "깊은 곳에서 뜨거운 파도가 밀려온다.",
    "C": "클리토리스가 극도로 예민해져 있다.",
    "A": "항문의 자극이 강렬해지고 있다.",
    "P": "참을 수 없는 감각이 밀려온다.",
}

_STIM_MID_TEXTS = {
    "F": "얼굴이 상기되어 있다.",
    "M": "입안에서 감각이 퍼지고 있다.",
    "B": "가슴이 달아오르고 있다.",
    "V": "안에서 뜨거운 감각이 느껴진다.",
    "C": "클리토리스가 예민해지고 있다.",
    "A": "항문에서 낯선 감각이 느껴진다.",
    "P": "아래에서 욱신거리는 감각이 있다.",
}


def get_state_description(stim_state, anatomy_set):
    """자극 상태에 따른 자동 묘사 (최대 2줄)"""
    texts = []
    for cat in ("F", "M", "B", "A", "V", "C", "P"):
        if cat not in anatomy_set:
            continue
        val = stim_state["stim"].get(cat, 0)
        if val >= 80:
            t = _STIM_HIGH_TEXTS.get(cat)
            if t:
                texts.append(t)
        elif val >= 50:
            t = _STIM_MID_TEXTS.get(cat)
            if t:
                texts.append(t)

    # 절정 접근
    gauge = stim_state.get("climax_gauge", 0)
    if gauge >= 80:
        texts.append("절정이 가까워지고 있다.")
    elif gauge >= 50:
        texts.append("자극이 쌓이고 있다.")

    return texts[:2]  # 최대 2줄


def calculate_stealth_chance(state):
    """들키지 않을 확률 계산

    - 기본 확률: 30%
    - 은신 중(hiding=True): +40%

    Returns:
        float: 은신 성공 확률 (0.0 ~ 1.0)
    """
    chance = STEALTH_BASE_CHANCE
    if state.get("hiding"):
        chance += STEALTH_HIDING_BONUS
    return min(chance, 0.9)


def check_stealth_success(state):
    """은신 성공 여부 판정

    Returns:
        bool: True면 들키지 않음, False면 들킴
    """
    chance = calculate_stealth_chance(state)
    return random.random() < chance


# ============================================
# 소리
# ============================================

def get_excitement_level(npc_id):
    """NPC 흥분도 단계 (0=low, 1=mid, 2=high)"""
    props = morld.get_unit_props(npc_id)
    arousal = props.get("상태:성욕", 0)
    if arousal >= 70:
        return 2
    elif arousal >= 35:
        return 1
    return 0


def emit_romance_sound(partner_id):
    """파트너의 흥분도에 따른 소음 발생"""
    import sound
    partner_asset = get_character_asset(partner_id)
    if not partner_asset:
        return
    profile = getattr(partner_asset, 'ROMANCE_SOUND_PROFILE', None)
    if not profile:
        return
    level = get_excitement_level(partner_id)
    intensity = profile["levels"][level]
    if intensity > 0:
        sound.emit_sound(partner_id, "moan", intensity)


def emit_ecstasy_sound(partner_id):
    """절정 시 소음 (높은 강도)"""
    import sound
    partner_asset = get_character_asset(partner_id)
    if not partner_asset:
        return
    profile = getattr(partner_asset, 'ROMANCE_SOUND_PROFILE', None)
    intensity = profile["ecstasy"] if profile else 60
    sound.emit_sound(partner_id, "moan", intensity)


# ============================================
# 절정 반응 키
# ============================================

def get_climax_reaction_key(climax_info, active_toggles, toggle_actions, reactions, state=None):
    """절정 묘사 키 결정 (우선순위 기반)

    1. ecstasy_intercourse — 삽입 중 절정
    2. ecstasy_chain_3 — 3회차+ 연쇄 (chain_count >= 2)
    3. ecstasy_chain_2 — 2회차 연쇄 (chain_count >= 1)
    4. ecstasy_chain_{cat} — 부위별 연쇄
    5. ecstasy_chain — 범용 연쇄
    6. ecstasy_{category} — 카테고리별
    7. ecstasy — 기본 fallback
    """
    def _has_key(k):
        return f"{k}:start" in reactions or k in reactions

    # 1. 삽입 중 절정
    is_intercourse = False
    if state:
        is_intercourse = _has_active_intercourse_from_state(state)
    if is_intercourse:
        if _has_key("ecstasy_intercourse"):
            return "ecstasy_intercourse"

    is_chain = climax_info.get("is_chain")
    chain_count = climax_info.get("chain_count", 0)
    cat = climax_info.get("category")

    if is_chain:
        if chain_count >= 2 and _has_key("ecstasy_chain_3"):
            return "ecstasy_chain_3"
        if chain_count >= 1 and _has_key("ecstasy_chain_2"):
            return "ecstasy_chain_2"
        if cat and _has_key(f"ecstasy_chain_{cat}"):
            return f"ecstasy_chain_{cat}"
        if _has_key("ecstasy_chain"):
            return "ecstasy_chain"

    if cat and _has_key(f"ecstasy_{cat}"):
        return f"ecstasy_{cat}"

    return "ecstasy"


# ============================================
# 세션 보존 (공수 전환)
# ============================================

def calculate_npc_stamina_cost(base_cost: int, npc_id: int) -> int:
    """NPC 스태미나 소모량 계산

    체력(기본스탯) 높을수록 적게 소모, 만복도 낮을수록 많이 소모

    Args:
        base_cost: 기본 행동 비용 (action_def["stamina"] 합산)
        npc_id: NPC unit ID
    """
    # 체력 스탯 보정: 기준값 5, 체력 높으면 소모 감소
    constitution = morld.get_unit_prop(npc_id, "체력") or 5
    const_factor = 5.0 / max(1, constitution)

    # 만복도 보정: 50 이상이면 보정 없음, 0이면 +50% 소모
    satiety = morld.get_unit_prop(npc_id, "생존:포만감") or 0
    satiety_factor = 1.0 + max(0.0, (50 - satiety) / 100.0)

    return max(1, int(base_cost * const_factor * satiety_factor))


# 절정 시 체력 소모 기본값
CLIMAX_STAMINA_COST = 3


def calculate_climax_hp_cost(unit_id: int, is_exhausted: bool) -> int:
    """절정/사정 시 체력 소모량 계산

    비탈진: 기본 CLIMAX_STAMINA_COST × 체력 보정
    탈진: 1 (만복도 기반 확률 — 만복도 높으면 감소 확률 낮음)

    Returns:
        감소량 (0이면 감소 없음)
    """
    if is_exhausted:
        satiety = morld.get_unit_prop(unit_id, "생존:포만감") or 0
        # 만복도 0 → 100%, 만복도 50 → 67%, 만복도 100 → 33%
        probability = max(0.3, 1.0 - satiety / 150.0)
        if random.random() < probability:
            return 1
        return 0
    else:
        constitution = morld.get_unit_prop(unit_id, "체력") or 5
        const_factor = 5.0 / max(1, constitution)
        return max(1, int(CLIMAX_STAMINA_COST * const_factor))


def extract_preserved(state):
    """공수 전환 시 보존할 상태 추출"""
    preserved = {
        "stim": state["stim"],
        "stamina": state["stamina"],
        "initial_stamina": state.get("initial_stamina", state["stamina"]),
        "max_stamina": state.get("max_stamina", 100),
        "npc_stamina": state.get("npc_stamina"),
        "npc_initial_stamina": state.get("npc_initial_stamina"),
        "npc_max_stamina": state.get("npc_max_stamina"),
        "elapsed_time": state["elapsed_time"],
        "checked_npcs": state.get("checked_npcs", set()),
        "lubricated": state.get("lubricated", False),
        "schedule_pushed": True,
        "position": state.get("position", "missionary"),
        "condom_active": state.get("condom_active", False),
        "condom_punctured": state.get("condom_punctured", False),
        "condom_removed_in_trance": state.get("condom_removed_in_trance", False),
        "raw_vaginal_warned": state.get("raw_vaginal_warned", False),
    }
    if "mode_ctx" in state:
        preserved["mode_ctx"] = state["mode_ctx"]
    if "insertion" in state:
        preserved["insertion"] = state["insertion"].copy()
    return preserved


# ============================================
# 수치심 감쇠 이벤트 구독 (모듈 로드 시)
# ============================================

def _check_nude_in_public_tick():
    """1시간 간격 공공 노출 체크.

    플레이어 위치에 있는 NPC 중 노출 상태이고 주변에 타인(플레이어 포함)이
    있으면 수치심 증가. 전체 NPC 순회는 비용이 크므로 플레이어 주변으로 범위 한정.
    """
    try:
        player_id = morld.get_player_id()
        if player_id is None:
            return
        loc = morld.get_unit_location(player_id)
        if loc is None:
            return
        units = morld.get_characters_at_location(loc[0], loc[1])
        if not units or len(units) < 2:
            return  # 관객 없음 (혼자) — 노출 중이어도 공공 노출 아님
        for uid in units:
            if uid == player_id:
                continue
            try:
                exp = get_exposure_state(uid)
            except Exception:
                continue
            if exp.get("upper_exposed") or exp.get("lower_exposed"):
                on_nude_in_public(uid)
    except Exception:
        pass


def _decay_trance_external_tick():
    """1시간 간격 `트랜스:외부` 자연 감쇠 (절정 여운 회복).

    Phase 1.9.1: 절정 직후 +20 boost가 시간 지나며 -10씩 회복.
    _SHAME_REGISTRY 재활용 — 수치심 이벤트 겪은 NPC는 보통 트랜스 경험도 있음.
    """
    for uid in list(_SHAME_REGISTRY):
        try:
            cur = morld.get_unit_prop(uid, "트랜스:외부") or 0
            if cur > 0:
                morld.set_unit_prop(uid, "트랜스:외부", max(0, cur - 10))
        except Exception:
            pass


def _decay_drunk_tick():
    """1시간 간격 `상태:취기` 자연 감쇠 (알코올 분해).

    Phase 1.9.4: 술은 여운보다 천천히 빠짐 (-5/h vs 여운 -10/h).
    _SHAME_REGISTRY 재활용.
    """
    for uid in list(_SHAME_REGISTRY):
        try:
            cur = morld.get_unit_prop(uid, "상태:취기") or 0
            if cur > 0:
                morld.set_unit_prop(uid, "상태:취기", max(0, cur - 5))
        except Exception:
            pass


# 시간 제한 상태 효과 — 플래그 대신 `상태:{name}남은시간` 타이머로 파생
# (기존 `상태:{name}` 플래그는 제거됨, Phase 2.6)
TIMED_STATUS_DURATIONS = {
    "미약": 6,
    "배란유도": 24,
    "정력제": 6,
}

# 활성 타이머 유닛 추적 — apply_timed_status에서 등록, decay에서 iterate
_TIMED_STATUS_REGISTRY = set()


def is_status_active(unit_id, name):
    """시간 제한 상태 효과가 활성 중인지 — 타이머 > 0 파생."""
    timer = morld.get_unit_prop(unit_id, f"상태:{name}남은시간") or 0
    return timer > 0


def apply_timed_status(unit_id, name, duration=None):
    """시간 제한 상태 효과 적용. duration 미지정 시 TIMED_STATUS_DURATIONS 기본값 사용.

    타이머만 설정 — 기존 `상태:{name}` 플래그는 더 이상 쓰지 않음.
    is_status_active(uid, name)로 활성 여부 판정.
    """
    if duration is None:
        duration = TIMED_STATUS_DURATIONS.get(name, 6)
    morld.set_unit_prop(unit_id, f"상태:{name}남은시간", duration)
    _TIMED_STATUS_REGISTRY.add(unit_id)


def _decay_timed_status_tick():
    """1시간 간격 모든 타이머 감쇠 — 0 도달 시 clear_prop."""
    for uid in list(_TIMED_STATUS_REGISTRY):
        any_active = False
        for name in TIMED_STATUS_DURATIONS:
            try:
                key = f"상태:{name}남은시간"
                remaining = morld.get_unit_prop(uid, key) or 0
                if remaining > 0:
                    new_remaining = max(0, remaining - 1)
                    if new_remaining == 0:
                        morld.clear_prop(uid, key)
                    else:
                        morld.set_unit_prop(uid, key, new_remaining)
                        any_active = True
            except Exception:
                pass
        if not any_active:
            _TIMED_STATUS_REGISTRY.discard(uid)


def _on_time_elapsed_shame(millis):
    """1시간 간격 tick — 수치심/공공노출/트랜스외부/취기/약물 타이머 처리."""
    _decay_shame_tick()
    _check_nude_in_public_tick()
    _decay_trance_external_tick()
    _decay_drunk_tick()
    _decay_timed_status_tick()


try:
    from events import subscribe_time_elapsed as _sub_time_elapsed
    _MILLIS_PER_HOUR = 3_600_000
    _sub_time_elapsed(_on_time_elapsed_shame, min_interval=_MILLIS_PER_HOUR)
except Exception:
    # 테스트 환경/초기 로딩 순서 등으로 실패 시 무시
    pass
