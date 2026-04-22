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

def calculate_availability_score(partner_id, player_id, action_def):
    """액션 가용성 점수 — 베이스라인 + 모디파이어 합산

    Returns 0 이상 → 합의 가능, 미만 → 강제 필요 (또는 거부).

    현재 모디파이어:
    - 호감 (베이스라인)
    - 성욕 할인 (get_effective_affection_req 경유)
    - 복종 할인 (get_effective_affection_req 경유)

    Why: era TW GET_SUCCESS_RATE 패턴 — 모든 가감 요소를 점수로 통합.
         이후 성격/각인/자제심 모디파이어가 더해질 여지를 열어둠.
    """
    props = morld.get_unit_props(partner_id) or {}
    affection = props.get(get_affection_key(player_id), 0)
    arousal = props.get("상태:성욕", 0)
    submission = props.get(get_submission_key(player_id), 0)
    eff_req = get_effective_affection_req(
        action_def.get("affection_req", 0), arousal, submission)
    return affection - eff_req


def resolve_action_mode(partner_id, player_id, action_def):
    """액션 모드 해석 — 'consensual' / 'forced' / 'unavailable'

    - physical_req 불충족 → 'unavailable' (TODO: 다음 슬라이스에서 근력 조건 추가)
    - 점수 >= 0 → 'consensual' (합의)
    - 점수 < 0 → 'forced' (호감 미달, 강제 필요)
    """
    # TODO: physical_req 체크 (근력 비교, 노출, 삽입 등 hard gate)
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

        # 경험치 +1
        morld.modify_prop(partner_id, exp_key, 1)

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


def _apply_internal_semen(target_id, part, amount):
    """체내 정액 적용"""
    prop = f"체내:정액:{part}"
    current = morld.get_unit_prop(target_id, prop) or 0
    morld.set_unit_prop(target_id, prop, min(INTERNAL_SEMEN_MAX, current + amount))


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
    }
    if "mode_ctx" in state:
        preserved["mode_ctx"] = state["mode_ctx"]
    if "insertion" in state:
        preserved["insertion"] = state["insertion"].copy()
    return preserved
