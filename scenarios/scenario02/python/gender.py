# gender.py - 성별 시스템
"""
성별 시스템 — 캐릭터의 성별과 해부학적 특성 관리

성별 종류:
- male: 남성 (M/B/A/P 감각)
- female: 여성 (M/B/A/V/C 감각)
- futanari: 후타나리 (M/B/A/V/C/P 감각)
- asexual: 무성 (M 감각만)
"""

import morld

# ============================================
# 성별 상수
# ============================================

MALE = "male"
FEMALE = "female"
FUTANARI = "futanari"
ASEXUAL = "asexual"

# 성별별 보유 감각 카테고리
ANATOMY = {
    MALE:     frozenset({"M", "B", "A", "P"}),
    FEMALE:   frozenset({"M", "B", "A", "V", "C"}),
    FUTANARI: frozenset({"M", "B", "A", "V", "C", "P"}),
    ASEXUAL:  frozenset({"M"}),
}


# ============================================
# API 함수
# ============================================

def get_gender(unit_id):
    """유닛의 성별 반환 (Character asset의 type 필드 기반)

    Returns:
        str: "male", "female", "futanari", "asexual" 중 하나
    """
    try:
        from assets.characters import get_instance
        instance = get_instance(unit_id)
        if instance:
            return getattr(instance, 'type', MALE)
    except Exception:
        pass

    # asset 없으면 unit_info에서 type 확인
    info = morld.get_unit_info(unit_id)
    if info:
        return info.get("type", MALE)
    return MALE


def has_anatomy(unit_id, category):
    """해당 감각 카테고리 보유 여부

    Args:
        unit_id: 대상 유닛 ID
        category: "M", "B", "A", "V", "C", "P" 중 하나

    Returns:
        bool: 해당 카테고리를 보유하면 True
    """
    return category in get_anatomy(unit_id)


def get_anatomy(unit_id):
    """보유 감각 카테고리 set 반환

    Returns:
        frozenset: 보유 감각 카테고리 집합
    """
    gender = get_gender(unit_id)
    return ANATOMY.get(gender, ANATOMY[MALE])


# ============================================
# 성적 지향 시스템
# ============================================

ORIENTATION_HETEROSEXUAL = "heterosexual"
ORIENTATION_BISEXUAL = "bisexual"
ORIENTATION_HOMOSEXUAL = "homosexual"

_orientation_cache = {}  # unit_id -> orientation


def register_orientation(unit_id, orientation):
    """NPC 성적 지향 등록 (Agent.__init__에서 호출)"""
    _orientation_cache[unit_id] = orientation


def get_orientation(unit_id):
    """성적 지향 반환 (기본: bisexual)"""
    return _orientation_cache.get(unit_id, ORIENTATION_BISEXUAL)


def get_orientation_multiplier(npc_id, partner_id):
    """성적 지향 호환성 배율

    Returns:
        float: 0.5(비호환) / 1.0(양성애) / 1.1(선호일치)
    """
    orientation = get_orientation(npc_id)
    if orientation == ORIENTATION_BISEXUAL:
        return 1.0

    npc_gender = get_gender(npc_id)
    partner_gender = get_gender(partner_id)
    # futanari는 female 기반으로 취급
    npc_base = FEMALE if npc_gender == FUTANARI else npc_gender
    partner_base = FEMALE if partner_gender == FUTANARI else partner_gender

    if orientation == ORIENTATION_HETEROSEXUAL:
        return 1.1 if npc_base != partner_base else 0.5
    elif orientation == ORIENTATION_HOMOSEXUAL:
        return 1.1 if npc_base == partner_base else 0.5
    return 1.0


def reset_orientation():
    """챕터 전환 시 리셋"""
    _orientation_cache.clear()


# ============================================
# 체격 / 음경 크기 시스템
# ============================================

BODY_SIZE_MAP = {"왜소": 1, "보통": 2, "장신": 3, "거구": 4}
PENIS_SIZE_MAP = {"작음": 1, "보통": 2, "큼": 3}


def get_body_size(unit_id):
    """체격 수치 반환 (1=왜소, 2=보통, 3=장신, 4=거구)"""
    val = morld.get_unit_prop(unit_id, "체격")
    if val is not None:
        return val
    # fallback: 신체:X prop에서 추론
    props = morld.get_unit_props(unit_id)
    if props:
        for key in ("왜소", "보통", "장신", "거구"):
            if props.get(f"신체:{key}"):
                return BODY_SIZE_MAP[key]
    return 2  # 기본 보통


def get_penis_size(unit_id):
    """음경 크기 수치 반환 (0=없음, 1=작음, 2=보통, 3=큼)"""
    gender = get_gender(unit_id)
    if gender not in (MALE, FUTANARI):
        return 0
    val = morld.get_unit_prop(unit_id, "음경:크기")
    if val is not None:
        return val
    return 2  # 기본 보통


def check_penetration_compatibility(actor_id, target_id):
    """삽입 호환성 체크

    Args:
        actor_id: 삽입하는 쪽 (P 보유자)
        target_id: 삽입받는 쪽

    Returns:
        dict: {needs_prep, pain, stim_mod}
        - needs_prep: 필요한 최소 stim 수치 (0이면 준비 불필요)
        - pain: True면 삽입 시 통증 발생
        - stim_mod: 자극 배율
    """
    penis = get_penis_size(actor_id)
    body = get_body_size(target_id)
    diff = penis - body

    if diff >= 2:
        return {"needs_prep": 60, "pain": True, "stim_mod": 1.3}
    elif diff == 1:
        return {"needs_prep": 30, "pain": False, "stim_mod": 1.1}
    elif diff == 0:
        return {"needs_prep": 0, "pain": False, "stim_mod": 1.0}
    elif diff == -1:
        return {"needs_prep": 0, "pain": False, "stim_mod": 0.85}
    else:  # diff <= -2
        return {"needs_prep": 0, "pain": False, "stim_mod": 0.7}
