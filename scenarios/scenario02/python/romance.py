# romance.py - 연애 시스템 모듈
"""
연애 시스템 - Dialog 기반 친밀한 상호작용

핵심 기능:
- 호감도 높은 NPC와 연애 행위 (토글/즉시)
- 시간 경과 + NPC 도착 감지
- 중단/합류 이벤트 처리
- 캐릭터별 반응 시스템
"""

import morld
import stimulation
import ui

# ============================================
# 상수 정의
# ============================================

ROMANCE_ENTRY_THRESHOLD = 50   # 연애 진입 최소 호감도
ROMANCE_JOIN_THRESHOLD = 60    # 합류 가능 최소 호감도
ROMANCE_STAMINA_KEY = "연애:스태미나"
DEFAULT_STAMINA = 10
ECSTASY_THRESHOLD = 100        # 절정 발생 임계값

# 들키지 않을 확률 설정
STEALTH_BASE_CHANCE = 0.3      # 기본 은신 확률 30%
STEALTH_HIDING_BONUS = 0.4     # 은신 중일 때 추가 확률 +40%
MILLIS_PER_MINUTE = 60_000

# 탈의/노출 시스템
EXPOSURE_BONUS = 1.5           # 노출 시 효과 배율
UNDRESS_UPPER_SLOTS = ["착용:외투", "착용:상의", "착용:속옷상의"]
UNDRESS_LOWER_SLOTS = ["착용:하의", "착용:속옷하의"]

# 복종 자연 증가
SUBMISSION_ACTION_THRESHOLD = 80  # 이 이상 affection_req 행위에서 복종 증가
SUBMISSION_ACTION_GAIN = 1        # 행위당 증가량
SUBMISSION_MAX = 100              # 복종 상한

# 정액 오염 시스템
SEMEN_PARTS = ["얼굴", "가슴", "배", "음부", "엉덩이"]
SEMEN_EXTERNAL_AMOUNT = 30        # 외부 사정 시 부위별 적용량
SEMEN_INTERNAL_DRIP = 10          # 내부 사정 후 흘러나옴
PULL_OUT_STIM_THRESHOLD = 80      # 질외사정 가능 자극 임계값

# ============================================
# 감각 시스템 (부위 → M/B/A/V 매핑)
# ============================================

# 행위 부위 → 감각 카테고리 매핑
SENSATION_MAP = {
    "입술": "M",        # Mouth
    "가슴": "B",        # Breast
    "유두": "B",        # Breast (nipple)
    "엉덩이": "A",      # Anal
    "음부": "V",        # Vaginal
    "클리토리스": "C",   # Clitoral
    "음경": "P",        # Penis (male)
    "목": "F",          # Face/Neck
    "귀": "F",          # Face/Neck
    "뺨": "F",          # Face/Neck
    "머리": None,       # 비성적 부위
}

# 감각 카테고리별 prop 키
SENSATION_PROPS = {
    "F": "감각:F",     # Face/Neck sensation level
    "M": "감각:M",     # Mouth sensation level
    "B": "감각:B",     # Breast sensation level
    "A": "감각:A",     # Anal sensation level
    "V": "감각:V",     # Vaginal sensation level
    "C": "감각:C",     # Clitoral sensation level
    "P": "감각:P",     # Penis sensation level
}

# ============================================
# 관계 라벨 시스템
# ============================================

RELATIONSHIP_LABELS = {
    (False, False): "타인",   # 낮은 호감 + 낮은 욕망
    (True,  False): "친구",   # 높은 호감 + 낮은 욕망
    (False, True):  "정욕",   # 낮은 호감 + 높은 욕망
    (True,  True):  "애인",   # 높은 호감 + 높은 욕망
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
        "exp_part": "가슴", "affection_req": 75
    },
    "nipple_stimulation": {
        "name": "유두 자극", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 5, "욕망": 2},
        "exp_part": "가슴", "affection_req": 85, "requires_exposure": "upper"
    },
    "nipple_lick": {
        "name": "유두 핥기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"성욕": 5, "욕망": 2},
        "exp_part": "유두", "affection_req": 85, "requires_exposure": "upper", "uses_mouth": True
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
        "exp_part": "가슴", "affection_req": 80, "exposure_bonus": "upper"
    },
    "breast_squeeze": {
        "name": "가슴 주무르기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 4, "욕망": 2},
        "exp_part": "가슴", "affection_req": 85, "exposure_bonus": "upper"
    },
    "breast_suck": {
        "name": "가슴 빨기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 6, "욕망": 3},
        "exp_part": "가슴", "affection_req": 90, "requires_exposure": "upper", "uses_mouth": True
    },
    "nipple_suck": {
        "name": "유두 빨기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 3,
        "effects": {"성욕": 7, "욕망": 3},
        "exp_part": "유두", "affection_req": 90, "requires_exposure": "upper", "uses_mouth": True
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
}

# ============================================
# 처녀(첫경험) 시스템
# ============================================

# 행위 → 해제 부위 매핑
VIRGINITY_CLEARING_ACTIONS = {
    "vaginal_penetration": "처녀:음부",
    "receive_penetration": "처녀:음부",
    "finger_insertion": "처녀:음부",
    "anal_penetration": "처녀:항문",
    "receive_anal": "처녀:항문",
    "fellatio": "처녀:구강",
}

VIRGINITY_BONUS_AFFECTION = 5
VIRGINITY_BONUS_EXP = 3


def check_and_clear_virginity(partner_id, player_id, action_id):
    """처녀 해제 체크. 해제 시 보너스 적용 + first 반응 키 반환."""
    virginity_prop = VIRGINITY_CLEARING_ACTIONS.get(action_id)
    if not virginity_prop:
        return None
    current = morld.get_unit_prop(partner_id, virginity_prop)
    if not current:
        return None
    # 처녀 해제
    morld.set_unit_prop(partner_id, virginity_prop, 0)
    # 보너스: 호감 +5
    affection_key = get_affection_key(player_id)
    morld.modify_prop(partner_id, affection_key, VIRGINITY_BONUS_AFFECTION)
    # 보너스: 감각 경험치 +3
    exp_part = TOGGLE_ACTIONS.get(action_id, {}).get("exp_part")
    if exp_part:
        morld.modify_prop(partner_id, f"경험:{exp_part}", VIRGINITY_BONUS_EXP)
    return f"first_{action_id}"


def _get_active_penetration_part(active_toggles):
    """활성 삽입 토글의 부위 반환 (내부 사정 판별용)"""
    for toggle_id in active_toggles:
        td = TOGGLE_ACTIONS.get(toggle_id)
        if not td:
            continue
        if td.get("pregnancy_check"):
            return "음부"
        if toggle_id in ("anal_penetration", "receive_anal"):
            return "항문"
        if toggle_id == "fellatio":
            return "구강"
    return None


# ============================================
# 정액 오염 시스템
# ============================================

def get_semen_total(unit_id):
    """전체 정액 오염 합산"""
    return sum(morld.get_unit_prop(unit_id, f"오염물:정액:{p}") or 0 for p in SEMEN_PARTS)


def _apply_semen(target_id, part, amount):
    """부위별 정액 적용"""
    prop = f"오염물:정액:{part}"
    current = morld.get_unit_prop(target_id, prop) or 0
    morld.set_unit_prop(target_id, prop, min(100, current + amount))
    # 오염도 증가
    try:
        import pollution
        current_poll = pollution.get_unit_pollution(target_id)
        pollution.set_unit_pollution(target_id, current_poll + 10)
    except Exception:
        pass


def clear_all_semen(unit_id):
    """전부위 정액 제거 (목욕 시)"""
    for p in SEMEN_PARTS:
        morld.clear_prop(unit_id, f"오염물:정액:{p}")


def is_pull_out_available(state):
    """질외사정 가능 여부: 삽입 토글 활성 + P 자극 ≥ 임계값"""
    if not _get_active_penetration_part(state.get("active_toggles", set())):
        return False
    stim = state.get("stim")
    if not stim:
        return False
    return stim.get("level", 0) >= PULL_OUT_STIM_THRESHOLD


# ============================================
# 발각 컨텍스트 (on_meet_player에 파트너 정보 전달)
# ============================================

_interrupted_context = None


def set_interrupted_context(partner_id):
    """발각 시 파트너 정보 저장 (on_meet_player에서 소비)"""
    global _interrupted_context
    _interrupted_context = {"partner_id": partner_id}


def get_interrupted_context():
    """발각 컨텍스트 반환 + 소비 (1회성)"""
    global _interrupted_context
    ctx = _interrupted_context
    _interrupted_context = None
    return ctx


# ============================================
# 유틸리티 함수
# ============================================

def get_partner_asset(partner_id):
    """파트너의 Python Asset 인스턴스 가져오기"""
    try:
        from assets.characters import get_instance
        return get_instance(partner_id)
    except:
        return None


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
    partner_asset = get_partner_asset(partner_id)
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
    partner_asset = get_partner_asset(partner_id)
    if not partner_asset:
        return
    profile = getattr(partner_asset, 'ROMANCE_SOUND_PROFILE', None)
    intensity = profile["ecstasy"] if profile else 60
    sound.emit_sound(partner_id, "moan", intensity)


def get_effective_affection_req(req, desire=0, submission=0):
    """유효 호감 요구치 (욕망/복종 할인 적용)

    각 요소: 최대 30% 할인
    합산: 최대 50% 할인
    절대 최소: 20
    """
    desire_discount = min(req * 0.3, desire * 0.3)
    submission_discount = min(req * 0.3, submission * 0.3)  # Phase C
    total = min(req * 0.5, desire_discount + submission_discount)
    return max(20, req - total)


def get_submission_key(player_id):
    """플레이어에 대한 복종 prop 키 생성"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    return f"관계:{player_name}:복종"


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
    if player_req and actor_id:
        import gender as gender_mod
        if not gender_mod.has_anatomy(actor_id, player_req):
            return False
    return True


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


def is_action_available(partner_id, player_id, action_def):
    """액션 해금 여부 (감정 + 육욕 이중 경로)"""
    affection_key = get_affection_key(player_id)
    props = morld.get_unit_props(partner_id)
    affection = props.get(affection_key, 0) if props else 0
    desire_key = get_desire_key(player_id)
    desire = props.get(desire_key, 0) if props else 0
    submission_key = get_submission_key(player_id)
    submission = props.get(submission_key, 0) if props else 0
    eff_req = get_effective_affection_req(action_def["affection_req"], desire, submission)
    return affection >= eff_req


def is_desire_unlocked(affection, action_def, desire, submission=0):
    """욕망/복종에 의한 해금인지 (정상 호감 미달이지만 욕망/복종으로 보완)"""
    return affection < action_def["affection_req"] and (desire > 0 or submission > 0)


def get_conflicting_toggles(new_action_id, active_toggles):
    """새 토글과 충돌하는 활성 토글 반환

    충돌 조건:
    1. 같은 exp_part (NPC쪽 부위 충돌)
    2. 같은 requires_player_anatomy (플레이어 신체 충돌)
    3. uses_mouth 충돌 (입/혀 행위는 동시에 하나만)
    exp_part가 None인 토글(껴안기 등)은 충돌하지 않습니다.
    """
    new_def = TOGGLE_ACTIONS.get(new_action_id)
    if not new_def:
        return set()
    new_exp_part = new_def.get("exp_part")
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
    return conflicting


def _remove_conflicting_toggles(new_action_id, active_toggles):
    """새 토글과 충돌하는 토글들을 비활성화 (in-place)"""
    conflicting = get_conflicting_toggles(new_action_id, active_toggles)
    for toggle_id in conflicting:
        active_toggles.discard(toggle_id)
    return conflicting


def get_sensation_level(unit_id, category):
    """감각 카테고리의 현재 레벨 (경험치에서 산출)

    해당 카테고리에 매핑된 부위들의 경험치 합산 → 레벨 변환.

    Args:
        unit_id: 대상 유닛 ID
        category: "M", "B", "A", "V"

    Returns:
        int: 감각 레벨 (0-10)
    """
    total_exp = 0
    for part, cat in SENSATION_MAP.items():
        if cat == category:
            total_exp += morld.get_unit_prop(unit_id, f"경험:{part}") or 0
    return min(10, total_exp // 5)


def _has_active_intercourse(active_toggles, toggle_actions):
    """활성 토글 중 pregnancy_check가 있는(삽입 행위) 것이 있는지"""
    for toggle_id in active_toggles:
        td = toggle_actions.get(toggle_id)
        if td and td.get("pregnancy_check"):
            return True
    return False


def get_climax_reaction_key(climax_info, active_toggles, toggle_actions, reactions):
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
    if _has_active_intercourse(active_toggles, toggle_actions):
        if _has_key("ecstasy_intercourse"):
            return "ecstasy_intercourse"

    is_chain = climax_info.get("is_chain")
    chain_count = climax_info.get("chain_count", 0)
    cat = climax_info.get("category")

    if is_chain:
        # 2. 3회차+ 연쇄
        if chain_count >= 2 and _has_key("ecstasy_chain_3"):
            return "ecstasy_chain_3"
        # 3. 2회차 연쇄
        if chain_count >= 1 and _has_key("ecstasy_chain_2"):
            return "ecstasy_chain_2"
        # 4. 부위별 연쇄
        if cat and _has_key(f"ecstasy_chain_{cat}"):
            return f"ecstasy_chain_{cat}"
        # 5. 범용 연쇄
        if _has_key("ecstasy_chain"):
            return "ecstasy_chain"

    # 6. 카테고리별
    if cat and _has_key(f"ecstasy_{cat}"):
        return f"ecstasy_{cat}"

    # 7. 기본
    return "ecstasy"


def get_desire_key(player_id):
    """플레이어에 대한 욕망 prop 키 생성"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    return f"관계:{player_name}:욕망"


def get_rebellion_key(player_id):
    """플레이어에 대한 반발 prop 키 생성"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    return f"관계:{player_name}:반발"


def calculate_effects(action_def, partner_id):
    """경험치 + 감각 보정된 효과 계산"""
    base_effects = action_def["effects"].copy()
    exp_part = action_def.get("exp_part")

    if exp_part:
        # 경험치 조회 (NPC별로 저장)
        exp_key = f"경험:{exp_part}"
        partner_props = morld.get_unit_props(partner_id)
        exp_value = partner_props.get(exp_key, 0)

        # 경험 배율: 1.0 + (경험 × 0.1)
        multiplier = 1.0 + (exp_value * 0.1)

        # 효과 적용 (반올림)
        for stat, value in base_effects.items():
            base_effects[stat] = round(value * multiplier)

        # 감각 보너스: 성적 부위의 감각 레벨에 따라 성욕 효과 증폭
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

        # 경험치 +1
        morld.modify_prop(partner_id, exp_key, 1)

    # 노출 보너스 (해당 부위 노출 시 ×1.5)
    bonus_area = action_def.get("exposure_bonus")
    if bonus_area:
        exposure = get_exposure_state(partner_id)
        if exposure.get(f"{bonus_area}_exposed"):
            for stat in base_effects:
                base_effects[stat] = round(base_effects[stat] * EXPOSURE_BONUS)

    return base_effects


def get_affection_key(player_id):
    """플레이어에 대한 호감도 prop 키 생성"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    return f"관계:{player_name}:호감"


def check_ecstasy(partner_id):
    """
    절정 체크 - 성욕 >= ECSTASY_THRESHOLD면 절정 발생

    Returns:
        절정 반응 텍스트 또는 None
    """
    partner_props = morld.get_unit_props(partner_id)
    arousal = partner_props.get("상태:성욕", 0)

    if arousal >= ECSTASY_THRESHOLD:
        # 캐릭터별 절정 반응 텍스트 (초기화 전에 조회 - 조건 체크용)
        reaction = None
        partner_asset = get_partner_asset(partner_id)
        if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
            reaction = partner_asset.get_romance_reaction("ecstasy", "start")

        # 성적절정 +1, 성욕 = 0 (반응 조회 후 초기화)
        morld.modify_prop(partner_id, "상태:성적절정", 1)
        morld.set_unit_prop(partner_id, "상태:성욕", 0)

        if reaction:
            return reaction

        # 기본 반응
        partner_info = morld.get_unit_info(partner_id)
        partner_name = partner_info.get('name', '상대') if partner_info else '상대'
        return f"{partner_name}(이)가 절정에 달했다."

    return None


def can_start_romance(player_id, target_id):
    """연애 진입 가능 여부 확인"""
    affection_key = get_affection_key(player_id)

    # 1. 대상 호감도 체크
    target_props = morld.get_unit_props(target_id)
    affection = target_props.get(affection_key, 0)
    if affection < ROMANCE_ENTRY_THRESHOLD:
        return False, f"호감도가 부족합니다 (현재: {affection}, 필요: {ROMANCE_ENTRY_THRESHOLD})"

    # 2. 같은 Location 확인
    player_loc = morld.get_unit_location(player_id)
    target_loc = morld.get_unit_location(target_id)
    if player_loc != target_loc:
        return False, "같은 장소에 있어야 합니다"

    # 3. 호감도 낮은 제3자 확인
    units_at_loc = morld.get_units_at_location(player_loc[0], player_loc[1])
    for unit_id in units_at_loc:
        if unit_id == player_id or unit_id == target_id:
            continue
        unit_props = morld.get_unit_props(unit_id)
        unit_affection = unit_props.get(affection_key, 0)
        if unit_affection < ROMANCE_ENTRY_THRESHOLD:
            unit_info = morld.get_unit_info(unit_id)
            return False, f"{unit_info['name']}(이)가 있어서 분위기가 아닙니다"

    return True, None


# ============================================
# UI 렌더링
# ============================================

def render_stamina_bar(stamina, max_stamina=DEFAULT_STAMINA):
    """체력 바 렌더링"""
    filled = int(stamina)
    empty = max_stamina - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {stamina}"


def render_romance_ui(state):
    """연애 UI 텍스트 생성"""
    player_id = state["player_id"]
    partner_id = state["partner_id"]
    partner_info = morld.get_unit_info(partner_id)
    partner_props = morld.get_unit_props(partner_id)
    player_stamina = state["stamina"]

    # 플레이어에 대한 prop 키
    affection_key = get_affection_key(player_id)
    arousal_key = "상태:성욕"

    lines = []

    # 헤더
    partner_name = partner_info['name']
    lines.append(f"[{partner_name}와 함께]                 스태미나: {render_stamina_bar(player_stamina)}")
    lines.append("")

    # 근접 경고 (누군가 지나갔지만 들키지 않음)
    if state.get("near_miss"):
        near_miss_id = state.get("near_miss_id")
        near_info = morld.get_unit_info(near_miss_id) if near_miss_id else None
        near_name = near_info.get("name", "누군가") if near_info else "누군가"
        lines.append(f"[color=orange]({near_name}(이)가 근처를 지나갔다... 들키지 않았다.)[/color]")

        # 파트너의 은신 성공 반응 (캐릭터별 특별 대사)
        stealth_reaction = state.get("stealth_reaction")
        if stealth_reaction:
            lines.append(f"[color=cyan][{partner_name}] {stealth_reaction}[/color]")
            state["stealth_reaction"] = None  # 표시 후 클리어

        lines.append("")
        state["near_miss"] = False  # 표시 후 클리어
        state["near_miss_id"] = None

    # 마지막 즉시 액션 반응 (있으면 표시 후 클리어)
    last_reaction = state.get("last_reaction")
    if last_reaction:
        lines.append(f"[color=yellow]{last_reaction}[/color]")
        lines.append("")
        state["last_reaction"] = None  # 표시 후 클리어

    # 파트너 반응 텍스트 (활성 토글 기반)
    partner_asset = get_partner_asset(partner_id)
    reaction_lines = []
    for toggle_id in state["active_toggles"]:
        if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
            reaction = partner_asset.get_romance_reaction(toggle_id, "during")
        else:
            # 기본 반응
            toggle_def = TOGGLE_ACTIONS.get(toggle_id)
            reaction = f"{partner_name}(이)가 당신과 {toggle_def['name']} 중이다." if toggle_def else None

        if reaction:
            reaction_lines.append(f"({reaction})")

    if reaction_lines:
        for line in reaction_lines:
            lines.append(line)
    else:
        lines.append(f"({partner_name}(이)가 당신을 바라보고 있다.)")

    lines.append("")

    # 임신 상태 표시
    import pregnancy as _pregnancy_mod
    preg_text = _pregnancy_mod.get_pregnancy_status_text(partner_id)
    if preg_text:
        lines.append(preg_text)
        lines.append("")

    # 호감, 욕망, 복종, 반발, 성욕 표시
    affection = partner_props.get(affection_key, 0)
    desire_key = get_desire_key(player_id)
    desire = partner_props.get(desire_key, 0)
    submission_key = get_submission_key(player_id)
    submission = partner_props.get(submission_key, 0)
    rebellion_key = get_rebellion_key(player_id)
    rebellion = partner_props.get(rebellion_key, 0)
    arousal = partner_props.get(arousal_key, 0)

    # 관계 라벨
    rel_label = get_relationship_label(affection, desire)
    stat_line = f"[{rel_label}] 호감: {affection}  욕망: {desire}  성욕: {arousal}"
    if submission > 0:
        stat_line += f"  복종: {submission}"
    if rebellion > 0:
        stat_line += f"  반발: {rebellion}"
    lines.append(stat_line)

    # 자극 표시 (세션 스코프, 대상 성별 기반)
    import gender as gender_mod
    partner_anatomy = gender_mod.get_anatomy(partner_id)
    stim_state = state.get("stim")
    if stim_state:
        stim_parts = []
        for cat in ("F", "M", "B", "A", "V", "C", "P"):
            if cat not in partner_anatomy:
                continue
            val = stim_state["stim"].get(cat, 0)
            stim_parts.append(f"{cat}:{val}")
        stim_line = f"자극: {' '.join(stim_parts)}"
        if stim_state.get("refractory", 0) > 0:
            stim_line += f"  [color=red][불응기][/color]"
        elif stim_state["afterglow"] > 0:
            chain = stim_state["chain_count"]
            if chain > 0:
                stim_line += f"  [color=pink][여운 ×{chain + 1}][/color]"
            else:
                stim_line += f"  [color=pink][여운][/color]"
        if stim_state["climax_total"] > 0:
            stim_line += f"  절정: {stim_state['climax_total']}"
        lines.append(stim_line)

    # 감각 레벨 표시 (1 이상인 것만, 대상 성별 기반)
    sensation_parts = []
    for cat in ("F", "M", "B", "A", "V", "C", "P"):
        if cat not in partner_anatomy:
            continue
        level = get_sensation_level(partner_id, cat)
        if level > 0:
            sensation_parts.append(f"{cat}:{level}")
    if sensation_parts:
        lines.append(f"감각: {' '.join(sensation_parts)}")

    # 노출 상태 표시
    exposure = get_exposure_state(partner_id)
    exposure_parts = []
    if exposure["upper_exposed"]:
        exposure_parts.append("[color=pink]상체 노출[/color]")
    if exposure["lower_exposed"]:
        exposure_parts.append("[color=pink]하체 노출[/color]")
    if exposure_parts:
        lines.append(f"복장: {' '.join(exposure_parts)}")

    # 정액 오염 표시
    semen_total = get_semen_total(partner_id)
    if semen_total > 0:
        if semen_total >= 60:
            lines.append("[color=pink]정액이 온몸에 흥건하다[/color]")
        elif semen_total >= 30:
            lines.append("[color=pink]정액이 묻어 있다[/color]")
        else:
            semen_detail = []
            for sp in SEMEN_PARTS:
                if (morld.get_unit_prop(partner_id, f"오염물:정액:{sp}") or 0) > 0:
                    semen_detail.append(sp)
            if semen_detail:
                lines.append(f"[color=pink]정액: {', '.join(semen_detail)}[/color]")

    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # 토글 행위
    _intercourse_blocked = _pregnancy_mod.is_intercourse_blocked(partner_id)
    lines.append("[토글 행위]")
    for action_id, action in TOGGLE_ACTIONS.items():
        if not is_anatomy_compatible(action, partner_id, actor_id=player_id):
            continue
        # 임신 후기: 삽입 행위 비활성화
        if _intercourse_blocked and action.get("pregnancy_check"):
            lines.append(f"  [color=gray]{action['name']} (임신 후기)[/color]")
            continue
        is_on = action_id in state["active_toggles"]
        # 노출 필요 행위: 미노출 시 잠금 표시
        req_area = action.get("requires_exposure")
        if req_area and not exposure.get(f"{req_area}_exposed") and not is_on:
            if is_action_available(partner_id, player_id, action):
                lines.append(f"  [color=gray]{action['name']} (탈의 필요)[/color]")
            else:
                lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
            continue
        if is_action_available(partner_id, player_id, action):
            prefix = "■" if is_on else "▶"
            name_text = action['name']
            # 노출 보너스 힌트
            bonus_area = action.get("exposure_bonus")
            if bonus_area and exposure.get(f"{bonus_area}_exposed"):
                name_text += " [color=pink]×1.5[/color]"
            if is_desire_unlocked(affection, action, desire, submission):
                lines.append(f"  [url=@proc:toggle:{action_id}][color=pink]{prefix} {name_text}[/color][/url]")
            else:
                lines.append(f"  [url=@proc:toggle:{action_id}]{prefix} {name_text}[/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 즉시 행위
    lines.append("[즉시 행위]")
    for action_id, action in INSTANT_ACTIONS.items():
        if not is_anatomy_compatible(action, partner_id, actor_id=player_id):
            continue
        # 탈의 행위: 벗을 것 없으면 숨김
        if action.get("undress"):
            is_upper = action["undress"] == "upper"
            if get_next_undress_item(partner_id, upper=is_upper) is None:
                continue
        # 노출 필요 행위: 미노출 시 잠금 표시
        req_area = action.get("requires_exposure")
        if req_area and not exposure.get(f"{req_area}_exposed"):
            if is_action_available(partner_id, player_id, action):
                lines.append(f"  [color=gray]{action['name']} (탈의 필요)[/color]")
            else:
                lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
            continue
        if is_action_available(partner_id, player_id, action):
            name_text = action['name']
            if is_desire_unlocked(affection, action, desire, submission):
                lines.append(f"  [url=@proc:instant:{action_id}][color=pink]{name_text}[/color][/url]")
            else:
                lines.append(f"  [url=@proc:instant:{action_id}]{name_text}[/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    # 질외사정 (삽입 중 + P 자극 ≥ 임계값)
    if is_pull_out_available(state):
        lines.append("")
        lines.append("[질외사정]")
        for target in SEMEN_PARTS:
            lines.append(f"  [url=@proc:pull_out_target:{target}]{target}[/url]")
    lines.append("")

    # 푸터
    lines.append(ui.divider())

    # 공수 전환 버튼 (NPC가 주도 가능할 때만)
    partner_asset = get_partner_asset(partner_id)
    if partner_asset and getattr(partner_asset, 'INITIATIVE_CONFIG', None):
        init_aff_threshold = partner_asset.INITIATIVE_CONFIG.get("affection_threshold", 60)
        if affection >= init_aff_threshold:
            lines.append("[url=@proc:switch]주도권 넘기기[/url]")

    lines.append("[url=@proc:exit]그만두기[/url]")

    return "\n".join(lines)


# ============================================
# 시간 경과 및 NPC 감지
# ============================================

def calculate_stealth_chance(state):
    """
    들키지 않을 확률 계산

    조건에 따라 은신 확률이 달라집니다:
    - 기본 확률: 30%
    - 은신 중(hiding=True): +40%
    - 추후 확장: 장소 특성, 시간대 등

    Returns:
        float: 은신 성공 확률 (0.0 ~ 1.0)
    """
    chance = STEALTH_BASE_CHANCE

    # 은신 상태 체크 (state에서 플래그 확인)
    if state.get("hiding"):
        chance += STEALTH_HIDING_BONUS

    # 최대 90%로 제한 (항상 들킬 가능성 존재)
    return min(chance, 0.9)


def check_stealth_success(state):
    """
    은신 성공 여부 판정

    Returns:
        bool: True면 들키지 않음, False면 들킴
    """
    import random
    chance = calculate_stealth_chance(state)
    return random.random() < chance


def advance_time_and_check(state, millis):
    """시간 경과 + NPC 도착 체크 (은신 확률 적용)"""
    # 1. 시간 진행 + NPC 이동 시뮬레이션
    morld.advance_time_des(millis)
    state["elapsed_time"] += millis

    # 2. 현재 Location의 NPC 목록 확인
    player_id = morld.get_player_id()
    player_loc = morld.get_unit_location(player_id)
    units_at_loc = morld.get_units_at_location(player_loc[0], player_loc[1])

    # 3. 새로 도착한 NPC 중 호감도 체크
    for unit_id in units_at_loc:
        if unit_id == state["partner_id"]:
            continue
        if unit_id == player_id:
            continue

        # 이미 체크한 NPC는 스킵 (같은 NPC에게 여러번 들키지 않음)
        # [Future Enhancement] 시간 기반 재판정 구현 시:
        #   checked_npcs를 dict로 변경하여 마지막 판정 시간 저장
        #   checked_npcs = {unit_id: last_check_time, ...}
        #   일정 시간(예: 30분) 경과 시 재판정 가능하도록 변경:
        #   last_check = checked_npcs.get(unit_id)
        #   if last_check is not None:
        #       if state["elapsed_time"] - last_check < 30:
        #           continue  # 아직 재판정 시간 안 됨
        #   checked_npcs[unit_id] = state["elapsed_time"]
        checked_npcs = state.get("checked_npcs", set())
        if unit_id in checked_npcs:
            continue

        # 체크 목록에 추가
        if "checked_npcs" not in state:
            state["checked_npcs"] = set()
        state["checked_npcs"].add(unit_id)

        # 호감도 체크
        props = morld.get_unit_props(unit_id)
        affection = props.get("호감", 0)

        if affection < ROMANCE_JOIN_THRESHOLD:
            # 은신 성공 여부 판정
            if check_stealth_success(state):
                # 은신 성공 - 들키지 않음 (근처 접근 표시만)
                state["near_miss"] = True
                state["near_miss_id"] = unit_id

                # 파트너 캐릭터의 은신 성공 반응 처리
                partner_id = state["partner_id"]
                partner_asset = get_partner_asset(partner_id)
                if partner_asset:
                    # 효과 적용 (예: 스릴에 더 흥분)
                    if hasattr(partner_asset, 'apply_stealth_success_effects'):
                        partner_asset.apply_stealth_success_effects(player_id)

                    # 반응 텍스트 (near_miss 메시지에 추가)
                    if hasattr(partner_asset, 'get_stealth_success_reaction'):
                        reaction = partner_asset.get_stealth_success_reaction(player_id)
                        if reaction:
                            state["stealth_reaction"] = reaction

                continue

            # 들킴 - 중단
            return {"interrupted": True, "interrupter_id": unit_id}
        # TODO: 합류 로직 (Phase 6)

    return {"interrupted": False}


# ============================================
# 메인 연애 함수
# ============================================

def _extract_preserved(state):
    """공수 전환 시 보존할 상태 추출"""
    return {
        "stim": state["stim"],
        "stamina": state["stamina"],
        "elapsed_time": state["elapsed_time"],
        "checked_npcs": state.get("checked_npcs", set()),
        "schedule_pushed": True,
    }


def start_romance(player_id, partner_id, preserved=None):
    """연애 모드 시작 - Generator 기반

    Args:
        player_id: 플레이어 유닛 ID
        partner_id: 파트너 유닛 ID
        preserved: 공수 전환 시 보존된 상태 (None이면 신규 세션)
    """

    # 진입 조건 체크 (전환 시 스킵 — 이미 세션 중)
    if not preserved:
        can_start, reason = can_start_romance(player_id, partner_id)
        if not can_start:
            yield ui.dialog(reason)
            return

    # 파트너 NPC를 현재 위치에 고정 (스킨십 동안 이동 방지)
    # 스케줄 스택에 STAY_SCHEDULE push, 종료 시 pop으로 복원
    import think
    partner_agent = think.get_agent(partner_id)
    schedule_pushed = preserved.get("schedule_pushed", False) if preserved else False
    if not schedule_pushed:
        if partner_agent:
            partner_agent.push_schedule(think.BaseAgent.STAY_SCHEDULE)

    # 플레이어 스태미나 조회 (연애 전용)
    player_props = morld.get_unit_props(player_id)
    initial_stamina = player_props.get(ROMANCE_STAMINA_KEY, DEFAULT_STAMINA)

    import gender as gender_mod
    state = {
        "player_id": player_id,
        "partner_id": partner_id,
        "active_toggles": set(),  # 현재 ON인 토글들 (복수 가능)
        "stamina": initial_stamina,  # 남은 스태미나
        "elapsed_time": 0,
        "interrupted": False,
        "interrupter_id": None,
        "exhausted": False,  # 체력 소진 종료
        "last_reaction": None,  # 마지막 즉시 액션 반응 텍스트
        "stim": stimulation.create_state(
            male_mode=(gender_mod.get_gender(partner_id) == "male")
        ),  # 부위별 자극 상태 (세션 스코프)
    }

    # 전환 시 보존 상태 복원
    if preserved:
        state["stim"] = preserved["stim"]
        state["stamina"] = preserved["stamina"]
        state["elapsed_time"] = preserved["elapsed_time"]
        if preserved.get("checked_npcs"):
            state["checked_npcs"] = preserved["checked_npcs"]

    def apply_effects(action_def, active_toggle_defs):
        """
        행위 효과 적용 (즉시형 + 활성 토글들) + 자극 계산

        Returns:
            절정 반응 텍스트 또는 None
        """
        pid = state["partner_id"]
        player_id = state["player_id"]
        affection_key = get_affection_key(player_id)
        stim_state = state["stim"]

        # 즉시형/토글 행위의 효과 (경험치 보정 포함)
        effects = calculate_effects(action_def, pid)

        # 활성 토글들의 효과도 합산
        for toggle_def in active_toggle_defs:
            toggle_effects = calculate_effects(toggle_def, pid)
            for stat, value in toggle_effects.items():
                effects[stat] = effects.get(stat, 0) + value

        # 효과 적용 (호감/욕망/성욕 prop 변경)
        for stat, value in effects.items():
            if stat in ("성욕", "성적절정"):
                prop_key = f"상태:{stat}"
            else:
                prop_key = affection_key.replace(":호감", f":{stat}")
            morld.modify_prop(pid, prop_key, value)

        # 자극 계산 — 각 행위의 exp_part 기반
        rebellion_key = get_rebellion_key(player_id)
        partner_props = morld.get_unit_props(pid)
        rebellion = partner_props.get(rebellion_key, 0) if partner_props else 0

        # 복종 자연 증가: 고요구 행위 수행 시 (반발 50 미만)
        req = action_def.get("affection_req", 0)
        if req >= SUBMISSION_ACTION_THRESHOLD:
            submission_key = affection_key.replace(":호감", ":복종")
            current_sub = (partner_props or {}).get(submission_key, 0)
            if current_sub < SUBMISSION_MAX and rebellion < 50:
                morld.modify_prop(pid, submission_key, SUBMISSION_ACTION_GAIN)

        all_actions = [action_def] + list(active_toggle_defs)
        climax_info = None

        for act_def in all_actions:
            exp_part = act_def.get("exp_part")
            if not exp_part:
                continue
            category = SENSATION_MAP.get(exp_part)
            if not category:
                continue
            base = act_def["effects"].get("성욕", 0)
            if base <= 0:
                continue
            sensation = get_sensation_level(pid, category)
            gain = stimulation.calc_gain(base, sensation, rebellion, stim_state["afterglow"], stim_state.get("refractory", 0))
            result = stimulation.apply(stim_state, category, gain)
            if result and not climax_info:
                climax_info = result

        # 여운 감소 (턴당 1회)
        stimulation.tick_afterglow(stim_state)

        # 절정 처리
        if climax_info:
            # 성욕 일부 감소 (전액 초기화 대신)
            current_arousal = partner_props.get("상태:성욕", 0) if partner_props else 0
            new_arousal = max(0, current_arousal - stimulation.CLIMAX_AROUSAL_REDUCTION)
            morld.set_unit_prop(pid, "상태:성욕", new_arousal)
            # 성적절정 +1
            morld.modify_prop(pid, "상태:성적절정", 1)
            # 절정 부위 감각 경험치 보너스
            exp_gain = stimulation.get_climax_sensation_gain(rebellion)
            if exp_gain > 0:
                cat = climax_info["category"]
                for part, c in SENSATION_MAP.items():
                    if c == cat:
                        morld.modify_prop(pid, f"경험:{part}", exp_gain)
                        break

            # 절정 시 복종 증가 (반발에 의해 억제)
            climax_sub_gain = max(0, 2 - rebellion // 25)
            if climax_sub_gain > 0:
                submission_key = affection_key.replace(":호감", ":복종")
                current_sub = (partner_props or {}).get(submission_key, 0)
                if current_sub < SUBMISSION_MAX:
                    morld.modify_prop(pid, submission_key, climax_sub_gain)

            # 임신 판정 (pregnancy_check 토글 활성 + P 보유자 절정 시)
            ejac_part = None
            if _has_active_intercourse(state["active_toggles"], TOGGLE_ACTIONS):
                import gender as gender_mod
                if gender_mod.has_anatomy(pid, "P"):
                    import pregnancy
                    pregnancy.check_conception(player_id, pid)
                    ejac_part = "음부"
            # P 절정 + 삽입 토글 활성 → 내부 사정 부위 판별
            if not ejac_part:
                import gender as gender_mod
                if gender_mod.has_anatomy(pid, "P"):
                    ejac_part = _get_active_penetration_part(state["active_toggles"])

            # 내부 사정 → 정액 흘러나옴
            if ejac_part and ejac_part in ("음부", "항문"):
                _apply_semen(pid, ejac_part, SEMEN_INTERNAL_DRIP)

            # 절정 반응 텍스트 (우선순위: intercourse > chain > category > default)
            partner_asset = get_partner_asset(pid)
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                reactions = getattr(partner_asset, 'ROMANCE_REACTIONS', {})
                # 내부 사정 반응 + 절정 반응 결합
                ejac_reaction = None
                if ejac_part:
                    ejac_key = f"ejaculation_internal_{ejac_part}"
                    ejac_reaction = partner_asset.get_romance_reaction(ejac_key, "start")
                ecstasy_key = get_climax_reaction_key(
                    climax_info, state["active_toggles"], TOGGLE_ACTIONS, reactions)
                reaction = partner_asset.get_romance_reaction(ecstasy_key, "start")
                if ejac_reaction and reaction:
                    return f"{ejac_reaction}\n{reaction}"
                if ejac_reaction:
                    return ejac_reaction
                if reaction:
                    return reaction
            partner_info = morld.get_unit_info(pid)
            partner_name = partner_info.get('name', '상대') if partner_info else '상대'
            return f"{partner_name}(이)가 절정에 달했다."

        return None

    def proc(action):
        if action == "init":
            return render_romance_ui(state)

        # 종료
        if action == "exit":
            return True

        # 공수 전환 (플레이어 → NPC 주도)
        if action == "switch":
            state["switch_to"] = "npc"
            return True

        # 질외사정
        if action.startswith("pull_out_target:"):
            target_part = action.split(":", 1)[1]
            if target_part not in SEMEN_PARTS:
                return render_romance_ui(state)
            if not is_pull_out_available(state):
                return render_romance_ui(state)
            pid = state["partner_id"]
            # 삽입 토글 해제
            penetration_toggles = set()
            for tid in state["active_toggles"]:
                td = TOGGLE_ACTIONS.get(tid)
                if td and (td.get("pregnancy_check") or tid in ("anal_penetration", "receive_anal", "fellatio")):
                    penetration_toggles.add(tid)
            for tid in penetration_toggles:
                state["active_toggles"].discard(tid)
            # P 절정 강제 발동
            stim = state.get("stim")
            if stim:
                stimulation.force_climax(stim, "P")
            # 정액 적용
            _apply_semen(pid, target_part, SEMEN_EXTERNAL_AMOUNT)
            # 외부 사정 → 극감 수정 확률 (2%)
            if target_part == "음부":
                import pregnancy
                import random
                if random.random() < 0.02:
                    pregnancy.check_conception(state["player_id"], pid)
            # 반응 텍스트
            partner_asset = get_partner_asset(pid)
            reaction = None
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                reaction = partner_asset.get_romance_reaction(f"pull_out_{target_part}", "start")
            if reaction:
                state["last_reaction"] = reaction
            else:
                partner_info = morld.get_unit_info(pid)
                pname = partner_info.get('name', '상대') if partner_info else '상대'
                state["last_reaction"] = f"{pname}의 {target_part}에 사정했다."
            emit_ecstasy_sound(pid)
            # 시간 경과
            result = advance_time_and_check(state, 3 * MILLIS_PER_MINUTE)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True
            return render_romance_ui(state)

        # 즉시형 행위
        if action.startswith("instant:"):
            action_id = action.split(":")[1]
            action_def = INSTANT_ACTIONS.get(action_id)
            if not action_def:
                return None

            # 탈의 전용 처리
            if action_def.get("undress"):
                is_upper = action_def["undress"] == "upper"
                item_id = get_next_undress_item(state["partner_id"], upper=is_upper)
                if item_id is None:
                    return render_romance_ui(state)  # 벗을 것 없음
                # 스태미나 + 시간 처리
                total_stamina = action_def["stamina"]
                for toggle_id in state["active_toggles"]:
                    total_stamina += TOGGLE_ACTIONS[toggle_id]["stamina"]
                if state["stamina"] <= total_stamina:
                    state["exhausted"] = True
                    return True
                state["stamina"] -= total_stamina
                perform_undress(state["partner_id"], item_id)
                item_info = morld.get_item_info(item_id)
                item_name = item_info.get("name", "옷") if item_info else "옷"
                partner_info = morld.get_unit_info(state["partner_id"])
                p_name = partner_info.get("name", "상대") if partner_info else "상대"
                state["last_reaction"] = f"{p_name}의 {item_name}을(를) 벗겼다."
                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                return render_romance_ui(state)

            # 체력 계산: 즉시형 + 활성 토글들
            total_stamina = action_def["stamina"]
            total_time = action_def["time"]

            active_toggle_defs = []
            for toggle_id in state["active_toggles"]:
                toggle_def = TOGGLE_ACTIONS[toggle_id]
                total_stamina += toggle_def["stamina"]
                active_toggle_defs.append(toggle_def)

            # 체력 부족 체크 (스태미나 소진 시 props 변화 없이 종료)
            if state["stamina"] <= total_stamina:
                state["exhausted"] = True
                return True  # 체력 부족 종료

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            ecstasy_reaction = apply_effects(action_def, active_toggle_defs)

            # 절정 반응이 있으면 우선 표시
            if ecstasy_reaction:
                state["last_reaction"] = ecstasy_reaction
                emit_ecstasy_sound(state["partner_id"])
            else:
                # 캐릭터별 반응 텍스트 (start 타이밍)
                partner_asset = get_partner_asset(state["partner_id"])
                if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                    reaction = partner_asset.get_romance_reaction(action_id, "start")
                    if reaction:
                        state["last_reaction"] = reaction
                emit_romance_sound(state["partner_id"])

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            return render_romance_ui(state)

        # 토글형 행위
        if action.startswith("toggle:"):
            action_id = action.split(":")[1]
            action_def = TOGGLE_ACTIONS.get(action_id)
            if not action_def:
                return None

            # 토글 전환
            is_turning_on = action_id not in state["active_toggles"]

            # 체력 계산 (토글 ON/OFF 모두 시간 흐름)
            total_stamina = action_def["stamina"]
            total_time = action_def["time"]

            # 다른 활성 토글들도 체력 소모
            active_toggle_defs = []
            for toggle_id in state["active_toggles"]:
                if toggle_id != action_id:
                    toggle_def = TOGGLE_ACTIONS[toggle_id]
                    total_stamina += toggle_def["stamina"]
                    active_toggle_defs.append(toggle_def)

            # 체력 부족 체크 (스태미나 소진 시 props 변화 없이 종료)
            if state["stamina"] <= total_stamina:
                state["exhausted"] = True
                return True

            # 토글 상태 변경
            if is_turning_on:
                # 같은 부위 토글 충돌 해소
                _remove_conflicting_toggles(action_id, state["active_toggles"])
                state["active_toggles"].add(action_id)
            else:
                state["active_toggles"].discard(action_id)

            # 처녀(첫경험) 체크 — 토글 ON 시
            first_key = None
            if is_turning_on:
                first_key = check_and_clear_virginity(
                    state["partner_id"], player_id, action_id)

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            ecstasy_reaction = apply_effects(action_def, active_toggle_defs)

            # 절정 반응이 있으면 우선 표시
            if ecstasy_reaction:
                state["last_reaction"] = ecstasy_reaction
                emit_ecstasy_sound(state["partner_id"])
            else:
                if is_turning_on:
                    # 첫경험 반응 우선, 없으면 일반 start 반응
                    partner_asset = get_partner_asset(state["partner_id"])
                    if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                        reaction = None
                        if first_key:
                            reaction = partner_asset.get_romance_reaction(first_key, "start")
                        if not reaction:
                            reaction = partner_asset.get_romance_reaction(action_id, "start")
                        if reaction:
                            state["last_reaction"] = reaction
                emit_romance_sound(state["partner_id"])

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            return render_romance_ui(state)

        return None

    # 연애 UI 시작
    yield ui.dialog(
        render_romance_ui(state),
        autofill="off",
        proc=proc,
        result=state
    )

    # 공수 전환 — NPC 주도로 전환
    if state.get("switch_to") == "npc":
        preserved = _extract_preserved(state)
        from npc_initiative import start_npc_initiative
        yield from start_npc_initiative(player_id, partner_id, preserved=preserved)
        return

    # 종료 처리 - 파트너 스케줄 스택에서 pop (원래 스케줄 복원)
    partner_id = state["partner_id"]
    partner_agent = think.get_agent(partner_id)

    # 착의 쿨다운 리셋 (탈의 후 즉시 착의 인터럽트 발동 가능하도록)
    if partner_agent:
        partner_agent._memory["clothing_last_attempt"] = None

    if state["exhausted"]:
        # 비정상 종료: 체력 소진
        if partner_agent:
            partner_agent.pop_schedule()
        yield ui.dialog("지쳤다...")
        morld.pop_to_situation()
    elif state["interrupted"]:
        # 비정상 종료: 제3자 도착으로 중단
        player_id = state["player_id"]
        interrupter_id = state["interrupter_id"]
        # 1. 발각 컨텍스트 저장 (on_meet_player에서 파트너 정보 사용)
        set_interrupted_context(state["partner_id"])
        # 2. 파트너 스케줄 복원
        handle_interruption(state)
        # 3. 중단 로그 표시
        interrupter_info = morld.get_unit_info(interrupter_id)
        interrupter_name = interrupter_info.get("name", "누군가") if interrupter_info else "누군가"
        morld.add_action_log(f"{interrupter_name}의 방해로 중단되었다.")
        # 4. 상황 복원 (로맨스 UI 종료)
        morld.pop_to_situation()
        # 5. 도착 NPC의 on_meet 이벤트를 C# 핸들러 큐에 추가
        #    → 다음 FlushEvents/ProcessPendingEvents에서 자동 처리
        #    → on_meet_player() 자연 실행 (privacy 체크, first-meet 등)
        morld.queue_event("meet", player_id, [player_id, interrupter_id])
    else:
        # 정상 종료(exit 클릭): NPC focus로 복귀
        if partner_agent:
            partner_agent.pop_schedule()


def handle_interruption(state):
    """중단 이벤트 처리 — 로맨스 세션 정리

    로맨스 중 제3자가 도착하면 세션을 조용히 종료한다.
    도착 NPC의 후속 반응은 이벤트 큐를 통해 on_meet_player()에서 자연 처리.
    (privacy 체크, first-meet 등 모든 on_meet 핸들러가 정상 실행됨)

    TODO: 캐릭터별 목격/중단 반응 분기
    현재는 세션만 조용히 종료되지만, 향후 캐릭터 성격에 따라 달라야 자연스럽다.
    예시:
      - 리나가 밀라&플레이어 목격 → 리나 놀라서 도주, 밀라는 당당
      - 밀라가 리나&플레이어 목격 → 리나 놀라서 도주, 밀라가 플레이어 추방
      - 세라가 밀라&플레이어 목격 → 세라 덤덤하게 무시, 애정행위 계속
    구현 시 목격자(interrupter) × 파트너(partner) × 장소 조합별 분기 필요.
    욕실/침실 등 장소에 따라서도 반응이 달라질 수 있음.
    """
    partner_id = state["partner_id"]

    # 파트너 스케줄 복원 (원래 행동으로 복귀)
    import think
    partner_agent = think.get_agent(partner_id)
    if partner_agent:
        partner_agent.pop_schedule()
