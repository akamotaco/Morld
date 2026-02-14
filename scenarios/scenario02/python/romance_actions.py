# romance_actions.py - 애정 행위 정의 (단일 소스)
"""
애정 행위 정의 — romance.py와 npc_initiative.py가 공유하는 행위 데이터.

모든 즉시형/토글형 행위 정의와 관련 상수를 단일 파일에서 관리.
"""

# ============================================
# 공유 상수
# ============================================

MILLIS_PER_MINUTE = 60_000

# 정액 시스템
SEMEN_PARTS = ["얼굴", "가슴", "배", "음부", "엉덩이"]
SEMEN_EXTERNAL_AMOUNT = 30
SEMEN_INTERNAL_DRIP = 10
SEMEN_AMOUNT_BASE = 30
SEMEN_AMOUNT_MIN = 10
SEMEN_AMOUNT_MAX = 100
INTERNAL_SEMEN_PARTS = ["음부", "항문", "구강"]
INTERNAL_SEMEN_MAX = 100

# 삽입/준비 관련
PULL_OUT_STIM_THRESHOLD = 80
LUBRICATION_THRESHOLD = 30
PREPARATION_THRESHOLD = 30
UNPREPARED_EFFECT_MULT = 0.5
UNPREPARED_REBELLION = 2

# 노출 시스템
EXPOSURE_BONUS = 1.5
UNDRESS_UPPER_SLOTS = ["착용:외투", "착용:상의", "착용:속옷상의"]
UNDRESS_LOWER_SLOTS = ["착용:하의", "착용:속옷하의"]

# 복종 자연 증가
SUBMISSION_ACTION_THRESHOLD = 80
SUBMISSION_ACTION_GAIN = 1
SUBMISSION_MAX = 100

# 진입/합류
ROMANCE_ENTRY_THRESHOLD = 50
ROMANCE_JOIN_THRESHOLD = 60
DEFAULT_STAMINA = 10
SWALLOW_M_THRESHOLD = 5
HOLD_BACK_P_THRESHOLD = 80

# 은신
STEALTH_BASE_CHANCE = 0.3
STEALTH_HIDING_BONUS = 0.4

# ============================================
# 감각 매핑 (부위 → 카테고리)
# ============================================

SENSATION_MAP = {
    "입술": "M",
    "가슴": "B",
    "유두": "B",
    "엉덩이": "A",
    "음부": "V",
    "클리토리스": "C",
    "음경": "P",
    "목": "F",
    "귀": "F",
    "뺨": "F",
    "머리": None,
}

# ============================================
# 관계 라벨
# ============================================

RELATIONSHIP_LABELS = {
    (False, False): "타인",
    (True,  False): "친구",
    (False, True):  "정욕",
    (True,  True):  "애인",
}
AFF_LABEL_THRESHOLD = 50
DES_LABEL_THRESHOLD = 40


def get_relationship_label(affection, desire):
    """호감+욕망 기반 관계 라벨 반환"""
    return RELATIONSHIP_LABELS[(affection >= AFF_LABEL_THRESHOLD, desire >= DES_LABEL_THRESHOLD)]


# ============================================
# 즉시형 행위 정의
# ============================================

INSTANT_ACTIONS = {
    "head_pat": {
        "name": "머리 쓰다듬기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 3},
        "exp_part": None, "affection_req": 40
    },
    "cheek_caress": {
        "name": "뺨 어루만지기", "time": 2 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 2},
        "exp_part": None, "affection_req": 30
    },
    "cheek_pinch": {
        "name": "뺨 꼬집기", "time": 2 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 1},
        "exp_part": None, "affection_req": 35
    },
    "ear_touch": {
        "name": "귀 만지기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 2, "성욕": 1},
        "exp_part": "귀", "affection_req": 45
    },
    "whisper": {
        "name": "사랑의 속삭임", "time": 2 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 5},
        "exp_part": None, "affection_req": 50
    },
    "lip_lick": {
        "name": "입술 핥기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 2, "성욕": 2},
        "exp_part": "입술", "affection_req": 55, "uses_mouth": True
    },
    "french_kiss": {
        "name": "프렌치 키스", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 3, "성욕": 3},
        "exp_part": "입술", "affection_req": 60, "uses_mouth": True
    },
    "neck_kiss": {
        "name": "목 키스", "time": 3 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 2, "성욕": 3},
        "exp_part": "목", "affection_req": 65, "uses_mouth": True
    },
    "butt_caress": {
        "name": "엉덩이 쓰다듬기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 3, "욕망": 1},
        "exp_part": "엉덩이", "affection_req": 70
    },
    "breast_caress": {
        "name": "가슴 쓰다듬기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 3},
        "exp_part": "가슴", "affection_req": 75, "requires_breast_size": 1
    },
    "nipple_stimulation": {
        "name": "유두 자극", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 5, "욕망": 2},
        "exp_part": "가슴", "affection_req": 85, "requires_exposure": "upper",
        "requires_breast_size": 1
    },
    "nipple_lick": {
        "name": "유두 핥기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 5, "욕망": 2},
        "exp_part": "유두", "affection_req": 85, "requires_exposure": "upper", "uses_mouth": True,
        "requires_breast_size": 1
    },
    "genital_caress": {
        "name": "음부 쓰다듬기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 4, "욕망": 2},
        "exp_part": "음부", "affection_req": 85, "requires_exposure": "lower"
    },
    "clit_stimulation": {
        "name": "클리토리스 자극", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 6, "욕망": 3},
        "exp_part": "클리토리스", "affection_req": 90, "requires_exposure": "lower"
    },
    "anal_stimulation": {
        "name": "항문 자극", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 5, "욕망": 3},
        "exp_part": "엉덩이", "affection_req": 90, "requires_exposure": "lower"
    },
    "penis_caress": {
        "name": "음경 쓰다듬기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 4, "욕망": 2},
        "exp_part": "음경", "affection_req": 85, "requires_exposure": "lower"
    },
    "penis_stimulation": {
        "name": "음경 자극", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 6, "욕망": 3},
        "exp_part": "음경", "affection_req": 90, "requires_exposure": "lower"
    },
    "undress_upper": {
        "name": "상체 옷 벗기기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 1},
        "exp_part": None, "affection_req": 70, "undress": "upper"
    },
    "undress_lower": {
        "name": "하체 옷 벗기기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 1},
        "exp_part": None, "affection_req": 80, "undress": "lower"
    },
    "swallow_semen": {
        "name": "삼키기", "time": 1 * MILLIS_PER_MINUTE, "stamina": 0,
        "effects": {"욕망": 2, "복종": 1},
        "exp_part": "입술", "affection_req": 90,
        "requires_internal_semen": "구강"
    },
    # 강도 행위
    "nipple_pinch": {
        "name": "유두 꼬집기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 7, "욕망": 3, "복종": 1},
        "exp_part": "유두", "affection_req": 90, "requires_exposure": "upper",
        "intensity": 3, "requires_breast_size": 1
    },
    "breast_grab": {
        "name": "가슴 움켜쥐기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 8, "욕망": 4, "복종": 1},
        "exp_part": "가슴", "affection_req": 90, "requires_exposure": "upper",
        "intensity": 3, "requires_breast_size": 2
    },
    "rough_finger": {
        "name": "거친 손가락 삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 9, "욕망": 5, "복종": 2},
        "exp_part": "음부", "affection_req": 98, "requires_exposure": "lower",
        "intensity": 3
    },
    # 삽입 중 즉시형 행위
    "thrust_deep": {
        "name": "깊게 밀어넣기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 8, "욕망": 4, "복종": 1},
        "exp_part": None, "affection_req": 98,
        "requires_active_penetration": True, "intensity": 3
    },
    "thrust_slow": {
        "name": "느리게 움직이기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 4, "호감": 2, "욕망": 2},
        "exp_part": None, "affection_req": 98,
        "requires_active_penetration": True, "intensity": 1
    },
    "grind": {
        "name": "밀착 흔들기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 6, "욕망": 3},
        "exp_part": "클리토리스", "affection_req": 98,
        "requires_active_penetration": True, "intensity": 2
    },
    "hold_back": {
        "name": "참기", "time": 1 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {},
        "exp_part": None, "affection_req": 0,
        "requires_player_anatomy_self": "P",
    },
    "ejaculate": {
        "name": "사정하기", "time": 1 * MILLIS_PER_MINUTE, "stamina": 0,
        "effects": {},
        "exp_part": None, "affection_req": 0,
        "requires_player_anatomy_self": "P",
    },
    "change_position": {
        "name": "체위 변경", "time": 2 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {},
        "exp_part": None, "affection_req": 0,
    },
    # 콘돔
    "condom_on": {
        "name": "콘돔 착용", "time": 1 * MILLIS_PER_MINUTE, "stamina": 0,
        "effects": {},
        "exp_part": None, "affection_req": 0,
        "requires_player_anatomy_self": "P",
        "is_condom_action": True,
    },
    "condom_off": {
        "name": "콘돔 제거", "time": 1 * MILLIS_PER_MINUTE, "stamina": 0,
        "effects": {},
        "exp_part": None, "affection_req": 0,
        "requires_player_anatomy_self": "P",
        "is_condom_action": True,
    },
}

# ============================================
# 토글형 행위 정의
# ============================================

TOGGLE_ACTIONS = {
    "hug": {
        "name": "껴안기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 3},
        "exp_part": None, "affection_req": 50
    },
    "deep_kiss": {
        "name": "딥키스", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 3, "성욕": 3},
        "exp_part": "입술", "affection_req": 70, "uses_mouth": True
    },
    "tongue_play": {
        "name": "혀 섞기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 2, "성욕": 4},
        "exp_part": "입술", "affection_req": 75, "uses_mouth": True
    },
    "butt_squeeze": {
        "name": "엉덩이 주무르기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 3, "욕망": 1},
        "exp_part": "엉덩이", "affection_req": 75
    },
    "breast_touch": {
        "name": "가슴 만지기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 4, "욕망": 1},
        "exp_part": "가슴", "affection_req": 80, "exposure_bonus": "upper",
        "requires_breast_size": 1
    },
    "breast_squeeze": {
        "name": "가슴 주무르기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 4, "욕망": 2},
        "exp_part": "가슴", "affection_req": 85, "exposure_bonus": "upper",
        "requires_breast_size": 2
    },
    "breast_suck": {
        "name": "가슴 빨기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 6, "욕망": 3},
        "exp_part": "가슴", "affection_req": 90, "requires_exposure": "upper", "uses_mouth": True,
        "requires_breast_size": 2
    },
    "nipple_suck": {
        "name": "유두 빨기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 7, "욕망": 3},
        "exp_part": "유두", "affection_req": 90, "requires_exposure": "upper", "uses_mouth": True,
        "requires_breast_size": 1
    },
    "paizuri": {
        "name": "파이즈리", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 8, "욕망": 4},
        "exp_part": "가슴", "affection_req": 95, "requires_exposure": "upper",
        "requires_breast_size": 2, "requires_player_anatomy": "P"
    },
    "genital_touch": {
        "name": "음부 만지기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"호감": 1, "성욕": 5, "욕망": 3},
        "exp_part": "음부", "affection_req": 90, "exposure_bonus": "lower"
    },
    "clit_rub": {
        "name": "클리토리스 문지르기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 7, "욕망": 4},
        "exp_part": "클리토리스", "affection_req": 95, "exposure_bonus": "lower"
    },
    "clit_lick": {
        "name": "클리토리스 핥기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 8, "욕망": 4},
        "exp_part": "클리토리스", "affection_req": 95, "requires_exposure": "lower", "uses_mouth": True
    },
    "cunnilingus": {
        "name": "커닐링구스", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 8, "욕망": 4},
        "exp_part": "음부", "affection_req": 95, "requires_exposure": "lower", "uses_mouth": True
    },
    "finger_insertion": {
        "name": "손가락 삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 7, "욕망": 4, "복종": 1},
        "exp_part": "음부", "affection_req": 95, "requires_exposure": "lower"
    },
    "penis_touch": {
        "name": "음경 만지기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"호감": 1, "성욕": 5, "욕망": 3},
        "exp_part": "음경", "affection_req": 90, "exposure_bonus": "lower"
    },
    "penis_rub": {
        "name": "음경 문지르기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 7, "욕망": 4},
        "exp_part": "음경", "affection_req": 95, "exposure_bonus": "lower"
    },
    "fellatio": {
        "name": "펠라치오", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 8, "욕망": 4},
        "exp_part": "음경", "affection_req": 95, "requires_exposure": "lower", "uses_mouth": True
    },
    # 삽입 행위
    "vaginal_penetration": {
        "name": "삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
        "effects": {"성욕": 8, "욕망": 5, "복종": 1},
        "exp_part": "음부", "affection_req": 98,
        "requires_player_anatomy": "P",
        "requires_exposure": "lower",
        "pregnancy_check": True,
    },
    "receive_penetration": {
        "name": "피삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
        "effects": {"성욕": 8, "욕망": 5},
        "exp_part": "음경", "affection_req": 98,
        "requires_player_anatomy": "V",
        "requires_exposure": "lower",
        "pregnancy_check": True,
    },
    "anal_penetration": {
        "name": "항문 삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
        "effects": {"성욕": 8, "욕망": 5, "복종": 2},
        "exp_part": "엉덩이", "affection_req": 98,
        "requires_player_anatomy": "P",
        "requires_exposure": "lower",
    },
    "receive_anal": {
        "name": "피항문삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
        "effects": {"성욕": 8, "욕망": 5},
        "exp_part": "음경", "affection_req": 98,
        "requires_player_anatomy": "A",
        "requires_exposure": "lower",
    },
    # 강도 행위
    "rough_thrust": {
        "name": "거칠게 삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 5,
        "effects": {"성욕": 11, "욕망": 7, "복종": 2},
        "exp_part": "음부", "affection_req": 100,
        "requires_player_anatomy": "P",
        "requires_exposure": "lower",
        "pregnancy_check": True, "intensity": 3
    },
    "hard_anal": {
        "name": "거친 항문 삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 5,
        "effects": {"성욕": 11, "욕망": 7, "복종": 3},
        "exp_part": "엉덩이", "affection_req": 100,
        "requires_player_anatomy": "P",
        "requires_exposure": "lower",
        "intensity": 3
    },
    # 상호 행위
    "tribadism": {
        "name": "트리바디즘", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
        "effects": {"성욕": 8, "욕망": 5},
        "exp_part": "음부", "extra_exp_part": "클리토리스",
        "affection_req": 98,
        "requires_both_anatomy": "V",
        "requires_exposure": "lower",
    },
}

# ============================================
# 처녀(첫경험) 시스템
# ============================================

VIRGINITY_CLEARING_ACTIONS = {
    "vaginal_penetration": "처녀:음부",
    "receive_penetration": "처녀:음부",
    "finger_insertion": "처녀:음부",
    "rough_finger": "처녀:음부",
    "rough_thrust": "처녀:음부",
    "anal_penetration": "처녀:항문",
    "receive_anal": "처녀:항문",
    "hard_anal": "처녀:항문",
    "fellatio": "처녀:구강",
}

VIRGINITY_BONUS_AFFECTION = 5
VIRGINITY_BONUS_EXP = 3

# ============================================
# 삽입 토글 ID
# ============================================

_PENETRATION_TOGGLE_IDS = frozenset({
    "vaginal_penetration", "receive_penetration",
    "anal_penetration", "receive_anal",
    "rough_thrust", "hard_anal",
})


# ============================================
# 행위 묘사 (3인칭 나레이션)
# ============================================

# 즉시형 행위 묘사
ACTION_DESCRIPTIONS = {
    "head_pat": "머리를 부드럽게 쓰다듬는다.",
    "cheek_caress": "뺨을 어루만진다.",
    "cheek_pinch": "뺨을 가볍게 꼬집는다.",
    "ear_touch": "귀를 손가락으로 만진다.",
    "whisper": "귓가에 속삭인다.",
    "lip_lick": "입술을 천천히 핥는다.",
    "french_kiss": "깊은 키스를 한다.",
    "neck_kiss": "목에 입술을 가져간다.",
    "butt_caress": "엉덩이를 부드럽게 쓰다듬는다.",
    "breast_caress": "가슴을 부드럽게 어루만진다.",
    "nipple_stimulation": "유두를 손가락으로 자극한다.",
    "nipple_lick": "유두를 혀로 핥는다.",
    "genital_caress": "은밀한 곳을 부드럽게 쓰다듬는다.",
    "clit_stimulation": "클리토리스를 자극한다.",
    "anal_stimulation": "항문을 자극한다.",
    "penis_caress": "음경을 부드럽게 어루만진다.",
    "penis_stimulation": "음경을 자극한다.",
    "nipple_pinch": "유두를 세게 꼬집는다.",
    "breast_grab": "가슴을 세게 움켜쥔다.",
    "rough_finger": "거칠게 손가락을 삽입한다.",
    "thrust_deep": "깊숙이 밀어넣는다.",
    "thrust_slow": "천천히 움직인다.",
    "grind": "밀착하여 허리를 흔든다.",
}

# 토글형 행위 묘사 (진행 중 상태)
TOGGLE_DURING_DESCRIPTIONS = {
    "hug": "서로를 껴안고 있다.",
    "deep_kiss": "깊은 키스가 이어지고 있다.",
    "tongue_play": "혀를 섞고 있다.",
    "butt_squeeze": "엉덩이를 주무르고 있다.",
    "breast_touch": "가슴을 만지고 있다.",
    "breast_squeeze": "가슴을 주무르고 있다.",
    "breast_suck": "가슴을 빨고 있다.",
    "nipple_suck": "유두를 빨고 있다.",
    "paizuri": "가슴 사이에 끼운 채 움직이고 있다.",
    "genital_touch": "은밀한 곳을 만지고 있다.",
    "clit_rub": "클리토리스를 문지르고 있다.",
    "clit_lick": "클리토리스를 핥고 있다.",
    "cunnilingus": "구강으로 자극하고 있다.",
    "finger_insertion": "손가락이 안에서 움직이고 있다.",
    "penis_touch": "음경을 만지고 있다.",
    "penis_rub": "음경을 문지르고 있다.",
    "fellatio": "입으로 감싸고 있다.",
    "vaginal_penetration": "삽입이 이어지고 있다.",
    "receive_penetration": "삽입이 이어지고 있다.",
    "anal_penetration": "항문 삽입이 이어지고 있다.",
    "receive_anal": "항문 삽입이 이어지고 있다.",
    "rough_thrust": "거친 삽입이 이어지고 있다.",
    "hard_anal": "거친 항문 삽입이 이어지고 있다.",
    "tribadism": "서로의 은밀한 곳을 맞대고 있다.",
}
