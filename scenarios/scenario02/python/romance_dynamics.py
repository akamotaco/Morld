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
    get_restraint_value,
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
# 캐릭터 상호작용 게이트 임계값 (dialogue tier)
# ============================================
# 개별 캐릭터 파일이 `affection >= 20/50/80`을 각자 하드코딩하던 것을
# 단일 소스로 통합. 현재는 데이터 테이블 이전 단계로 상수만 공유.
# 추후 아키타입/캐릭터별 override가 필요해지면 dict 테이블로 확장.

AFFECTION_GATE_ACQUAINTANCE = 20  # 지인 수준: 기본 반응 해금
AFFECTION_GATE_FRIEND = 50        # 친구 수준: 스킨십/대화 확장 해금
AFFECTION_GATE_INTIMATE = 80      # 친밀 수준: 적극적 반응/허용 해금


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


def _love_damp_from_submission(submission):
    """복종 누적에 따른 애정 상승 감쇠 계수.

    기존: 복종 ≥ 60 일괄 차단 (경계에서 cliff).
    신규: 복종 60부터 선형 감쇠, 100에서 0 (연속 시뮬레이션).
    "몸이 먼저 굴복하고 정신이 뒤따른다" — 지배 누적 시 사랑이 점차 얼어붙는다.

    복종 0~60 : damp = 1.0 (영향 없음)
    복종 60~100: damp = (100 - submission) / (100 - LOVE_BLOCK_SUBMISSION)
    복종 ≥100  : damp = 0.0
    """
    if submission <= LOVE_BLOCK_SUBMISSION:
        return 1.0
    span = 100 - LOVE_BLOCK_SUBMISSION
    return max(0.0, (100 - submission) / span)


def modify_love(target_id, player_id, delta):
    """애정 변경. 복종 누적 시 positive delta 가 점진 감쇠.

    Returns: 실제 적용된 delta (감쇠/clamp 후).
    """
    if delta > 0:
        submission = morld.get_unit_prop(target_id, get_submission_key(player_id)) or 0
        damp = _love_damp_from_submission(submission)
        delta = int(delta * damp)
        if delta <= 0:
            return 0
    current = get_love(target_id, player_id)
    new_value = max(LOVE_MIN, min(LOVE_MAX, current + delta))
    actual = new_value - current
    if actual != 0:
        morld.set_unit_prop(target_id, get_love_key(player_id), new_value)
    return actual


# ============================================
# 실질 자제심 (복종 침잠 효과 — Phase 1.9)
# ============================================
# 복종 누적 시 자제심이 점차 무너짐 (함락 루트 서사 반영).
# "몸이 먼저 굴복하고 정신이 뒤따른다" — era 조교 메커니즘 정합.

RESTRAINT_EROSION_START = 60   # 복종 60부터 침잠 시작 ("충성" 구간 진입)
RESTRAINT_EROSION_RATE = 0.75  # 복종 초과분의 75%만큼 자제심 감쇠


def get_effective_restraint(unit_id):
    """복종 누적에 따른 실질 자제심 (함락 침잠 효과).

    raw = 성격:자제심 (아키타입 기본값 fallback 포함)
    erosion = max(0, 복종 - 60) × 0.75
    effective = max(0, raw - erosion)

    복종은 플레이어에 대한 복종만 본다 (현재 주요 관계 축).
    """
    raw = get_restraint_value(unit_id) or 0
    submission = 0
    try:
        player_id = morld.get_player_id()
        if player_id is not None:
            submission = morld.get_unit_prop(unit_id, get_submission_key(player_id)) or 0
    except Exception:
        submission = 0
    erosion = max(0, submission - RESTRAINT_EROSION_START) * RESTRAINT_EROSION_RATE
    return max(0, int(raw - erosion))


# ============================================
# 트랜스 상태 (`상태:트랜스`)
# ============================================
# 성욕 + 절정게이지 + 자제심 조합으로 산출 (prop 저장).
# 외부 요인 (`트랜스:외부`)으로 세뇌/약물/최면/알코올 가산 가능.

TRANCE_ENTRY = 60   # 흥분 트랜스 진입 임계 (페르소나 억제 풀림)
TRANCE_DEEP = 80    # 깊은 트랜스 (저항 약화, 자발성 극대)


_CLIMAX_PARTS = ("B", "M", "V", "C", "A", "P")
CLIMAX_EXPERIENCE_BONUS_CAP = 15


def _sum_climax_experience(unit_id):
    """부위별 절정 누적 경험 합산 (`경험:절정:{part}`)."""
    total = 0
    for part in _CLIMAX_PARTS:
        total += morld.get_unit_prop(unit_id, f"경험:절정:{part}") or 0
    return total


def compute_trance_level(unit_id):
    """성욕 + 절정게이지 + 절정경험 × 자제심방어 + 외부 → 트랜스 수치 (0~100).

    **비대칭 방어 전용 공식** (자제심 = 정신 공격 내성):
    - 자제심 50 이하: 방어 없음 (factor 1.0)
    - 자제심 50 초과: factor = max(0.1, 1.0 - (자제심 - 50) × 0.02)

    외부 가산(세뇌/약물 + 절정 여운)은 자제심을 직접 우회.
    누적 절정 경험은 base에 소폭 기여 (era 快楽 허들 낮추기).

    공식:
      climax_exp_bonus = min(15, sum(경험:절정:*) × 0.3)
      base = (성욕 + 게이지) / 2 + climax_exp_bonus
      base × 자제심_방어_factor
      + 트랜스:외부
      → clamp 0~100
    """
    arousal = morld.get_unit_prop(unit_id, "상태:성욕") or 0
    gauge = morld.get_unit_prop(unit_id, "상태:절정") or 0
    # 실질 자제심 (복종 침잠 반영, Phase 1.9)
    restraint = get_effective_restraint(unit_id)
    # 외부 가산 (Phase 1.9.4): 트랜스:외부(절정여운/최면/약물) + 상태:취기(알코올)
    external = morld.get_unit_prop(unit_id, "트랜스:외부") or 0
    drunk = morld.get_unit_prop(unit_id, "상태:취기") or 0
    # 누적 절정 경험 bonus (era 快楽 근사)
    climax_exp = _sum_climax_experience(unit_id)
    climax_exp_bonus = min(CLIMAX_EXPERIENCE_BONUS_CAP, int(climax_exp * 0.3))
    base = (arousal + gauge) / 2.0 + climax_exp_bonus
    # 자제심 방어 (50 초과일 때만 감쇠, 50 이하는 방어 없음)
    defense_factor = max(0.1, 1.0 - max(0, restraint - 50) * 0.02)
    base *= defense_factor
    # Phase 2 후반 §7.13 point 5 — 무관심/감정결여 억제 (trance 진입 자체 감쇠)
    from romance_core import get_disposition_value
    apathy = get_disposition_value(unit_id, "무관심")     # 0/1
    numb = get_disposition_value(unit_id, "감정결여")   # 0/1
    trance_damp = 0.5 if (apathy >= 1 or numb >= 1) else 1.0
    base *= trance_damp
    value = int(base + (external + drunk) * trance_damp)
    return max(0, min(100, value))


_LAST_TRANCE_EXITS = {}  # unit_id -> {"prev_peak": int, "shame_gain": int}


def update_trance_level(unit_id):
    """트랜스 수치 재계산 + prop 반영. 반환값은 갱신된 수치.

    Phase 1.9.2: 트랜스 이탈 감지 — 이전이 TRANCE_ENTRY 이상이고
    현재 미만이면 `on_post_trance_return` 훅 발동 + 이탈 정보 기록
    (세션 대사 삽입용 — `pop_last_trance_exit`로 소비).
    """
    prev = morld.get_unit_prop(unit_id, "상태:트랜스") or 0
    value = compute_trance_level(unit_id)
    morld.set_unit_prop(unit_id, "상태:트랜스", value)
    if prev >= TRANCE_ENTRY and value < TRANCE_ENTRY:
        shame_gain = on_post_trance_return(unit_id, prev_peak=prev)
        _LAST_TRANCE_EXITS[unit_id] = {
            "prev_peak": prev,
            "shame_gain": shame_gain if isinstance(shame_gain, int) else 15,
        }
    return value


def pop_last_trance_exit(unit_id):
    """최근 트랜스 이탈 정보 조회 + 소비 (1회성).

    세션 루프에서 update_trance_level 호출 직후 pop하여
    post_trance 대사를 last_reaction에 삽입하는 용도.
    없으면 None 반환.
    """
    return _LAST_TRANCE_EXITS.pop(unit_id, None)


def on_post_trance_return(unit_id, prev_peak):
    """트랜스 이탈 시 "방금 내가 뭘..." 수치심 발동.

    깊은 트랜스(80+)에서 이탈이면 +25, 일반 트랜스(60~79) 이탈이면 +15.
    Phase 1 수치심 시스템 (apply_shame)을 재활용.

    Returns: 적용된 수치심 gain (int).
    """
    from romance_core import apply_shame
    gain = 25 if prev_peak >= TRANCE_DEEP else 15
    apply_shame(unit_id, gain, reason="post_trance_return")
    return gain


def is_in_trance(unit_id, threshold=TRANCE_ENTRY):
    """현재 트랜스 상태 여부 (prop 기반, compute 하지 않음)."""
    return (morld.get_unit_prop(unit_id, "상태:트랜스") or 0) >= threshold


def is_in_deep_trance(unit_id):
    """깊은 트랜스 여부 (저항 약화/자발성 극대 구간)."""
    return is_in_trance(unit_id, TRANCE_DEEP)


# 트랜스 효과 배율 — apply_effects에서 모드 배율과 곱셈 합성.
# 의미: 의식 흐림 → 관계 기억(호감/반발) 약화, 몸(복종/성욕/절정/경험) 가속.
_TRANCE_MULT_ENTRY = {
    "affection": 0.6, "rebellion": 0.6, "submission": 1.2,
    "arousal": 1.1, "desire": 1.1, "climax_gauge": 1.2, "experience": 1.2,
}
_TRANCE_MULT_DEEP = {
    "affection": 0.3, "rebellion": 0.3, "submission": 1.5,
    "arousal": 1.3, "desire": 1.3, "climax_gauge": 1.5, "experience": 1.5,
}
_TRANCE_MULT_NONE = {
    "affection": 1.0, "rebellion": 1.0, "submission": 1.0,
    "arousal": 1.0, "desire": 1.0, "climax_gauge": 1.0, "experience": 1.0,
}


def compute_trance_multipliers(unit_id):
    """트랜스 수치에 따른 효과 배율 dict.

    Returns 6 key: affection / rebellion / submission / arousal / desire / experience / climax_gauge
    """
    level = morld.get_unit_prop(unit_id, "상태:트랜스") or 0
    if level >= TRANCE_DEEP:
        return dict(_TRANCE_MULT_DEEP)
    if level >= TRANCE_ENTRY:
        return dict(_TRANCE_MULT_ENTRY)
    return dict(_TRANCE_MULT_NONE)


# ============================================
# 관계 라벨 파생 (저장 X)
# ============================================

# 관계 라벨 테이블 — 순서대로 첫 매칭 반환.
# 각 row: (label, conditions dict). conditions의 모든 키가 입력 스탯 dict의
# 해당 값과 비교해 조건을 만족해야 함. "_max" suffix는 "<" 비교.
RELATIONSHIP_TIERS = [
    ("적대",        {"rebellion": 60}),
    ("배우자",      {"love": 80, "affection": 60}),
    ("연인",        {"love": 60, "affection": 60, "submission_max": 60}),
    ("헌신적 종자", {"submission": 60, "love": 40}),
    ("종복",        {"submission": 60}),
    ("친구",        {"affection": 40}),
    ("지인",        {"affection": 20}),
]


def _label_conditions_met(stats, conditions):
    for key, threshold in conditions.items():
        if key.endswith("_max"):
            base_key = key[:-4]
            if stats.get(base_key, 0) >= threshold:
                return False
        else:
            if stats.get(key, 0) < threshold:
                return False
    return True


def get_relationship_label(target_id, player_id):
    """호감/복종/애정/반발 조합 → 관계 라벨 (파생).

    `RELATIONSHIP_TIERS` 테이블 순회 — 첫 매칭이 정답. 테이블 기반이라
    조건 추가/조정이 한 곳에서 가능.
    """
    stats = {
        "affection": morld.get_unit_prop(target_id, get_affection_key(player_id)) or 0,
        "submission": morld.get_unit_prop(target_id, get_submission_key(player_id)) or 0,
        "love": get_love(target_id, player_id),
        "rebellion": morld.get_unit_prop(target_id, get_rebellion_key(player_id)) or 0,
    }
    for label, conditions in RELATIONSHIP_TIERS:
        if _label_conditions_met(stats, conditions):
            return label
    return "타인"
