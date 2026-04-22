# romance_dynamics.py — 관계 수치 동역학 + 라벨/파생
"""
호감/복종/애정/반발 스탯의 라벨 alias 및 애정 티어 도입.

- 라벨 alias: 수치 → 네이밍 (호감 80 → "친애")
- 애정 티어: 호감 상위 스탯. 복종 ≥ LOVE_BLOCK_SUBMISSION 이면 상승 차단
- 관계 라벨 파생: 호감/복종/애정/반발 조합 → "연인"/"종복"/"타인" 등 (저장 X)

설계 배경:
- era 시리즈 참고: 호감(好感)과 복종(隷属)은 독립 축, 애정(愛情)이 상위 티어
- romance-trajectory 31 아크타입의 endpoint 분리 (연인 vs 노예)
- "복종 높으면 사랑 안 생김" 직관을 애정 상승 게이트로 흡수
"""

import morld
from romance_core import (
    get_affection_key,
    get_rebellion_key,
    get_submission_key,
    _get_relationship_key,
)


# ============================================
# 상수
# ============================================

AFFECTION_MIN = 0
AFFECTION_MAX = 100
LOVE_MIN = 0
LOVE_MAX = 100

# 애정 상승 차단 임계: 복종이 이 이상이면 modify_love 의 positive delta 차단
LOVE_BLOCK_SUBMISSION = 60


# ============================================
# 라벨 테이블 (내림차순 — 첫 매칭이 정답)
# ============================================

_AFFECTION_LABELS = [
    (80, "친애"),
    (60, "신뢰"),
    (40, "친구"),
    (20, "지인"),
    (0,  "무관심"),
]

_SUBMISSION_LABELS = [
    (100, "절대복종"),
    (80,  "복속"),
    (60,  "충성"),
    (30,  "순응"),
    (0,   "자유"),
]

_LOVE_LABELS = [
    (80, "헌신"),
    (60, "사랑"),
    (40, "애정"),
    (20, "호의"),
    (0,  "무"),
]


def _lookup_label(value, table):
    v = int(value or 0)
    for threshold, label in table:
        if v >= threshold:
            return label
    return table[-1][1]


def get_affection_label(value):
    return _lookup_label(value, _AFFECTION_LABELS)


def get_submission_label(value):
    return _lookup_label(value, _SUBMISSION_LABELS)


def get_love_label(value):
    return _lookup_label(value, _LOVE_LABELS)


# ============================================
# 애정 스탯 (`관계:{p}:애정`)
# ============================================

def get_love_key(player_id):
    return _get_relationship_key(player_id, "애정")


def get_love(target_id, player_id):
    return morld.get_unit_prop(target_id, get_love_key(player_id)) or 0


def modify_love(target_id, player_id, delta):
    """애정 변경. 복종 ≥ LOVE_BLOCK_SUBMISSION 이면 positive delta 차단.

    Returns: 실제 적용된 delta (차단/clamp 후).
    """
    if delta > 0:
        submission = morld.get_unit_prop(target_id, get_submission_key(player_id)) or 0
        if submission >= LOVE_BLOCK_SUBMISSION:
            return 0
    current = get_love(target_id, player_id)
    new_value = max(LOVE_MIN, min(LOVE_MAX, current + delta))
    actual = new_value - current
    if actual != 0:
        morld.set_unit_prop(target_id, get_love_key(player_id), new_value)
    return actual


# ============================================
# 관계 라벨 파생 (저장 X)
# ============================================

def get_relationship_label(target_id, player_id):
    """호감/복종/애정/반발 조합 → 관계 라벨 (파생)."""
    affection = morld.get_unit_prop(target_id, get_affection_key(player_id)) or 0
    submission = morld.get_unit_prop(target_id, get_submission_key(player_id)) or 0
    love = get_love(target_id, player_id)
    rebellion = morld.get_unit_prop(target_id, get_rebellion_key(player_id)) or 0

    if rebellion >= 60:
        return "적대"
    if love >= 80 and affection >= 60:
        return "배우자"
    if love >= 60 and affection >= 60 and submission < 60:
        return "연인"
    if submission >= 60 and love >= 40:
        return "헌신적 종자"
    if submission >= 60:
        return "종복"
    if affection >= 40:
        return "친구"
    if affection >= 20:
        return "지인"
    return "타인"
