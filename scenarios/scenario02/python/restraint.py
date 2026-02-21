# restraint.py - 결박 시스템 API
#
# 결박 장비(로프, 수갑 등)에 의한 행동 제한 관리.
#
# 결박 상태 props:
#   - "결박:상체": 1  → 팔/손 결박 (장비 해제 불가, 저항 불가, 이동 가능)
#   - "결박:하체": 1  → 다리 결박 (이동 불가, 장비 해제 가능, 저항 불가)
#   - "결박:입": 1    → 말하기/구강행위/식사/소리치기 불가
#   - "결박:눈": 1    → 시각 차단 (감각 증폭 효과)
#   - "결박:강도": N  → 해제 난이도 (높을수록 자력 해제 어려움)
#
# 상체+하체 동시 결박 = 탈출 불가 (별도 prop 불필요)
#
# 결박 중 가능한 행동 (NPC think):
#   - 자력 해제 시도 (30분마다, 확률 기반)
#   - 소리치기 (입 자유 시) → sound.emit_sound("scream")
#   - 수동 대기 (절정/성욕 변화는 needs.py에서 처리)
#
# 타인에 의한 해제: 항상 성공, 2~5분 소요.
# NPC 발견: think/handlers/restraint_rescue.py에서 처리.

import random

import morld
import equipment


# ========================================
# 상태 확인 API
# ========================================

def is_upper_restrained(unit_id):
    """상체(팔/손) 결박 여부"""
    return bool(morld.get_unit_prop(unit_id, "결박:상체"))


def is_lower_restrained(unit_id):
    """하체(다리) 결박 여부"""
    return bool(morld.get_unit_prop(unit_id, "결박:하체"))


def is_restrained(unit_id):
    """어떤 형태든 결박 여부 (상체 또는 하체)"""
    return is_upper_restrained(unit_id) or is_lower_restrained(unit_id)


def is_fully_restrained(unit_id):
    """상체+하체 동시 결박 (= 탈출 불가)"""
    return is_upper_restrained(unit_id) and is_lower_restrained(unit_id)


def is_gagged(unit_id):
    """입 결박 여부"""
    return bool(morld.get_unit_prop(unit_id, "결박:입"))


def is_blindfolded(unit_id):
    """시각 차단 여부"""
    return bool(morld.get_unit_prop(unit_id, "결박:눈"))


def get_restraint_strength(unit_id):
    """결박 강도 (해제 난이도)"""
    return morld.get_unit_prop(unit_id, "결박:강도") or 0


def is_any_restrained(unit_id):
    """상체/하체/입/눈 중 하나라도 결박된 상태인지"""
    return is_restrained(unit_id) or is_gagged(unit_id) or is_blindfolded(unit_id)


def can_move(unit_id):
    """이동 가능 여부 — 하체 결박 시 불가"""
    return not is_lower_restrained(unit_id)


def can_use_hands(unit_id):
    """손 사용 가능 여부 — 상체 결박 시 불가"""
    return not is_upper_restrained(unit_id)


def can_escape_romance(unit_id):
    """로맨스 탈출 가능 여부 — 상체+하체 동시 결박 시 불가"""
    return not is_fully_restrained(unit_id)


def get_escape_multiplier(unit_id):
    """탈출 확률 배율 — 전신 0.0, 부분 0.3, 없음 1.0"""
    if is_fully_restrained(unit_id):
        return 0.0
    if is_upper_restrained(unit_id) or is_lower_restrained(unit_id):
        return 0.3
    return 1.0


# ========================================
# 결박 장착
# ========================================

def attempt_restrain(actor_id, target_id, item_id, mode=None):
    """
    결박 장비 장착 시도

    Args:
        actor_id: 장착하는 캐릭터
        target_id: 대상 캐릭터
        item_id: 결박 장비 아이템 ID
        mode: 로맨스 모드 ("consensual"/"forced"/"unconscious"/"frozen"/None)

    Returns:
        (success: bool, message: str)
    """
    # 자신에게 장착 — 항상 성공
    if actor_id == target_id:
        _apply_restraint(target_id, item_id)
        return True, "결박 장비를 장착했다."

    # 의식불명/시간정지 — 무조건 성공
    if mode in ("unconscious", "frozen"):
        _apply_restraint(target_id, item_id)
        return True, "저항 없이 결박 장비를 채웠다."

    # 합의 모드 — 호감/복종 기반 수락
    if mode == "consensual" or mode is None:
        affection = _get_relationship(target_id, actor_id, "호감")
        submission = _get_relationship(target_id, actor_id, "복종")
        if affection >= 70 or submission >= 50:
            _apply_restraint(target_id, item_id)
            return True, "상대가 순순히 결박을 받아들였다."
        return False, "상대가 결박을 거부했다."

    # 강제 모드 — 저항 체크
    if mode == "forced":
        block_chance = _calc_restrain_block_chance(actor_id, target_id)
        if random.random() >= block_chance:
            _apply_restraint(target_id, item_id)
            return True, "저항을 제압하고 결박 장비를 채웠다."
        return False, "상대가 강하게 저항하여 실패했다."

    return False, "결박할 수 없는 상태다."


def _apply_restraint(target_id, item_id):
    """결박 장비 장착 적용 — equip 시스템 사용"""
    equipment.equip_item(target_id, item_id)


def _calc_restrain_block_chance(actor_id, target_id):
    """강제 결박 시 차단 확률 계산"""
    # 대상의 저항력
    target_strength = morld.get_unit_prop(target_id, "근력") or 5
    rebellion = _get_relationship(target_id, actor_id, "반발")

    # 액터의 제압력
    actor_strength = morld.get_unit_prop(actor_id, "근력") or 5

    # 기본 차단 확률 70% (일반 차단보다 낮음)
    block_chance = 0.70

    # 힘 차이
    strength_diff = target_strength - actor_strength
    block_chance += strength_diff * 0.03

    # 반발이 높으면 저항이 강함
    block_chance += rebellion * 0.002

    # 대상 성욕/절정이 높으면 저항이 약함
    arousal = morld.get_unit_prop(target_id, "상태:성욕") or 0
    climax = morld.get_unit_prop(target_id, "상태:절정") or 0
    block_chance -= arousal * 0.002
    block_chance -= climax * 0.003

    return max(0.15, min(0.90, block_chance))


# ========================================
# 결박 해제
# ========================================

def attempt_self_escape(unit_id):
    """
    자력 해제 시도

    확률 = power / (difficulty + power)
    - power = 근력×2 + 체격×3 + HP비율×50
    - difficulty = 결박강도 + 절정×0.3

    Returns:
        bool: 해제 성공 여부
    """
    import survival

    strength = morld.get_unit_prop(unit_id, "근력") or 5
    body_type = morld.get_unit_prop(unit_id, "체격") or 2

    max_hp = survival.get_max_health(unit_id)
    current_hp = survival.get_health(unit_id)
    hp_ratio = current_hp / max_hp if max_hp > 0 else 0.5

    climax = morld.get_unit_prop(unit_id, "상태:절정") or 0
    restraint_str = get_restraint_strength(unit_id)

    power = strength * 2 + body_type * 3 + hp_ratio * 50
    difficulty = restraint_str + climax * 0.3

    chance = min(0.70, max(0.05, power / (difficulty + power)))
    return random.random() < chance


def release_unit(unit_id):
    """
    타인에 의한 결박 해제 — 항상 성공

    결박 관련 equip 아이템을 모두 해제.
    """
    equipped_items = equipment.get_equipped_items(unit_id)
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:상체") or ep.get("결박:하체") or ep.get("결박:입") or ep.get("결박:눈"):
            equipment.unequip_item(unit_id, item_id)


def release_self(unit_id):
    """
    자력 결박 해제 — 하나의 결박 아이템만 해제 (하체 전용 → 상체 전용 → 전신 순)

    입/눈 결박은 사지가 자유로워야 해제 가능 (별도 호출).
    """
    equipped_items = equipment.get_equipped_items(unit_id)
    # 하체 전용 아이템 먼저 해제 시도
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:하체") and not ep.get("결박:상체"):
            equipment.unequip_item(unit_id, item_id)
            return True
    # 상체 전용 아이템
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:상체") and not ep.get("결박:하체"):
            equipment.unequip_item(unit_id, item_id)
            return True
    # 전신 아이템 (상체+하체 동시)
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:상체") and ep.get("결박:하체"):
            equipment.unequip_item(unit_id, item_id)
            return True
    return False


def release_mouth(unit_id):
    """입 결박 해제 (상체 자유 상태에서만 호출)"""
    equipped_items = equipment.get_equipped_items(unit_id)
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:입"):
            equipment.unequip_item(unit_id, item_id)
            break


def release_eyes(unit_id):
    """눈 결박 해제 (상체 자유 상태에서만 호출)"""
    equipped_items = equipment.get_equipped_items(unit_id)
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:눈"):
            equipment.unequip_item(unit_id, item_id)
            break


def release_unit_and_collect(unit_id):
    """결박 해제 + 해제된 아이템 ID 반환 (회수용)

    Returns:
        list[int]: 해제된 결박 아이템 ID 리스트
    """
    equipped_items = equipment.get_equipped_items(unit_id)
    released = []
    for item_id in list(equipped_items):
        ep = _get_equip_props(item_id)
        if ep.get("결박:상체") or ep.get("결박:하체") or ep.get("결박:입") or ep.get("결박:눈"):
            equipment.unequip_item(unit_id, item_id)
            released.append(item_id)
    return released


# ========================================
# 유틸리티
# ========================================

def _get_equip_props(item_id):
    """아이템 equip_props 조회 헬퍼"""
    item_info = morld.get_item_info(item_id)
    if not item_info:
        return {}
    return item_info.get("equip_props", {})


def _get_relationship(unit_id, target_id, key):
    """관계 prop 조회 헬퍼"""
    target_info = morld.get_unit_info(target_id)
    if not target_info:
        return 0
    target_name = target_info.get("name", "")
    return morld.get_unit_prop(unit_id, f"관계:{target_name}:{key}") or 0


def get_restrained_units_at(location_id):
    """
    특정 location에 있는 결박된 유닛 목록

    Returns:
        list[int]: 결박된 유닛 ID 리스트
    """
    units = morld.get_units_at_location(location_id)
    if not units:
        return []
    return [uid for uid in units if is_restrained(uid)]
