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
