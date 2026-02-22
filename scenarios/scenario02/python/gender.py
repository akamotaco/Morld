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
# 성별 상수 (문자열 — 외부 인터페이스용)
# ============================================

MALE = "male"
FEMALE = "female"
FUTANARI = "futanari"
ASEXUAL = "asexual"

# 정수 인코딩 (prop 시스템은 정수만 지원)
_GENDER_TO_INT = {MALE: 1, FEMALE: 2, FUTANARI: 3, ASEXUAL: 4}
_INT_TO_GENDER = {v: k for k, v in _GENDER_TO_INT.items()}

def gender_to_int(gender_str):
    """문자열 성별 → 정수 (prop 저장용)"""
    return _GENDER_TO_INT.get(gender_str, 1)

def int_to_gender(gender_int):
    """정수 → 문자열 성별"""
    return _INT_TO_GENDER.get(gender_int, MALE)

# 생물체 성별 한글 표시
CREATURE_GENDER_DISPLAY = {
    MALE: "수컷",
    FEMALE: "암컷",
    ASEXUAL: "무성",
}


def get_creature_gender_display(unit_id):
    """생물체 성별 한글 표시"""
    g = get_gender(unit_id)
    return CREATURE_GENDER_DISPLAY.get(g, "무성")


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
    """유닛의 성별 반환 (prop "성별" 정수 디코딩)

    Returns:
        str: "male", "female", "futanari", "asexual" 중 하나

    Raises:
        ValueError: 캐릭터에 "성별" prop이 없을 때 (설정 누락은 반드시 수정 필요)
        (생물체(creature)는 예외 없이 ASEXUAL 반환)
    """
    val = morld.get_unit_prop(unit_id, "성별")
    if val:
        return int_to_gender(int(val))
    # 생물체: 성별 prop 없으면 무성 (ValueError 대신)
    info = morld.get_unit_info(unit_id)
    if info and info.get("type") == "creature":
        return ASEXUAL
    # 일반 캐릭터: 성별 prop 없음 → 에러로 조기 발견
    raise ValueError(
        f"get_gender(unit_id={unit_id}): '성별' prop이 0 또는 미설정. "
        f"Character.instantiate() 또는 persistence 복원 경로를 확인하세요."
    )


def has_anatomy(unit_id, category):
    """해당 감각 카테고리 보유 여부 (임시 해부학 포함)

    Args:
        unit_id: 대상 유닛 ID
        category: "M", "B", "A", "V", "C", "P" 중 하나

    Returns:
        bool: 해당 카테고리를 보유하면 True
    """
    if category in get_anatomy(unit_id):
        return True
    # 임시 해부학 (장비에 의한 — 예: 페니스밴드 → 임시해부학:P)
    if morld.get_unit_prop(unit_id, f"임시해부학:{category}"):
        return True
    return False


def has_natural_anatomy(unit_id, category):
    """장비 보정 없는 순수 해부학 카테고리 보유 여부

    사정 등 자연 기능 체크 시 사용 (페니스밴드는 사정 불가).

    Args:
        unit_id: 대상 유닛 ID
        category: "M", "B", "A", "V", "C", "P" 중 하나

    Returns:
        bool: 해당 카테고리를 자연적으로 보유하면 True
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

_ORIENT_TO_INT = {ORIENTATION_HETEROSEXUAL: 1, ORIENTATION_BISEXUAL: 2, ORIENTATION_HOMOSEXUAL: 3}
_INT_TO_ORIENT = {v: k for k, v in _ORIENT_TO_INT.items()}

def orientation_to_int(orient_str):
    """문자열 성적지향 → 정수 (prop 저장용)"""
    return _ORIENT_TO_INT.get(orient_str, 2)

def int_to_orientation(orient_int):
    """정수 → 문자열 성적지향"""
    return _INT_TO_ORIENT.get(orient_int, ORIENTATION_BISEXUAL)

def register_orientation(unit_id, orientation):
    """(deprecated) 호환성 유지용 no-op — props로 전환됨"""
    pass


def get_orientation(unit_id):
    """성적 지향 반환 (prop "성적지향" 정수 디코딩)"""
    val = morld.get_unit_prop(unit_id, "성적지향")
    if val:
        return int_to_orientation(val)
    return ORIENTATION_BISEXUAL


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
    """(deprecated) 호환성 유지용 no-op — props는 instantiate 시 자동 재설정"""
    pass


# ============================================
# 체격 / 음경 / 가슴 크기 시스템
# ============================================

BODY_SIZE_MAP = {"왜소": 1, "보통": 2, "장신": 3, "거구": 4}
PENIS_SIZE_MAP = {"작음": 1, "보통": 2, "큼": 3}
# 가슴 크기: 0=없음, 1=작음, 2=보통, 3=큼
BREAST_SIZE_DEFAULT = {MALE: 0, FEMALE: 2, FUTANARI: 2, ASEXUAL: 0}


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


def get_breast_size(unit_id):
    """가슴 크기 수치 반환 (0=없음, 1=작음, 2=보통, 3=큼)"""
    val = morld.get_unit_prop(unit_id, "가슴:크기")
    if val is not None:
        return val
    gender = get_gender(unit_id)
    return BREAST_SIZE_DEFAULT.get(gender, 0)


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
