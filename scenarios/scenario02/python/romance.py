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

# ============================================
# 감각 시스템 (부위 → M/B/A/V 매핑)
# ============================================

# 행위 부위 → 감각 카테고리 매핑
SENSATION_MAP = {
    "입술": "M",        # Mouth
    "가슴": "B",        # Breast
    "엉덩이": "A",      # Anal
    "음부": "V",        # Vaginal
    "클리토리스": "C",   # Clitoral
    "음경": "P",        # Penis (male)
    "귀": None,         # 비성적 부위
    "뺨": None,
    "머리": None,
}

# 감각 카테고리별 prop 키
SENSATION_PROPS = {
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
    "french_kiss": {
        "name": "프렌치 키스", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 3, "성욕": 3},
        "exp_part": "입술", "affection_req": 60
    },
    "butt_caress": {
        "name": "엉덩이 쓰다듬기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 3, "욕망": 1},
        "exp_part": "엉덩이", "affection_req": 70
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
        "exp_part": "입술", "affection_req": 70
    },
    "breast_touch": {
        "name": "가슴 만지기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "성욕": 4, "욕망": 1},
        "exp_part": "가슴", "affection_req": 80, "exposure_bonus": "upper"
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
}

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


def is_anatomy_compatible(action_def, target_id):
    """행위가 대상의 해부학적 구조와 호환되는지"""
    exp_part = action_def.get("exp_part")
    if not exp_part:
        return True
    category = SENSATION_MAP.get(exp_part)
    if category is None:
        return True  # 비성적 부위 (귀, 뺨, 머리)
    import gender as gender_mod
    return gender_mod.has_anatomy(target_id, category)


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
        for cat in ("M", "B", "A", "V", "C", "P"):
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
    for cat in ("M", "B", "A", "V", "C", "P"):
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

    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # 토글 행위
    lines.append("[토글 행위]")
    for action_id, action in TOGGLE_ACTIONS.items():
        if not is_anatomy_compatible(action, partner_id):
            continue
        is_on = action_id in state["active_toggles"]
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
        if not is_anatomy_compatible(action, partner_id):
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

            # 절정 반응 텍스트
            partner_asset = get_partner_asset(pid)
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                reaction = partner_asset.get_romance_reaction("ecstasy", "start")
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
                state["active_toggles"].add(action_id)
            else:
                state["active_toggles"].discard(action_id)

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            ecstasy_reaction = apply_effects(action_def, active_toggle_defs)

            # 절정 반응이 있으면 우선 표시
            if ecstasy_reaction:
                state["last_reaction"] = ecstasy_reaction
                emit_ecstasy_sound(state["partner_id"])
            else:
                if is_turning_on:
                    # 토글 ON 시 반응 텍스트 (start 타이밍)
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
