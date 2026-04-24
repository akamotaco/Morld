# npc_initiative.py - NPC 주도 스킨십 모듈
"""
NPC가 주도하는 스킨십 시스템

핵심 기능:
- on_meet 이벤트에서 조건 충족 시 자동 트리거
- NPC가 주도하면서 플레이어도 행위 선택 가능
- 빠져나가기 시도 (체력/덩치 기반 확률)
- 스태미나 시스템 연동
"""

import morld
import random
import think
import ui
import stimulation
import position
from ui_style import c, style_muted, style_info, style_danger, style_success, style_warning, style_highlight
from romance_actions import (
    INSTANT_ACTIONS as PLAYER_INSTANT_ACTIONS,
    TOGGLE_ACTIONS as NPC_TOGGLE_ACTIONS,
    MILLIS_PER_MINUTE,
    SENSATION_MAP, EXPOSURE_BONUS,
    VIRGINITY_CLEARING_ACTIONS, VIRGINITY_BONUS_AFFECTION, VIRGINITY_BONUS_EXP,
    INTERNAL_SEMEN_PARTS, SWALLOW_M_THRESHOLD,
    LUBRICATION_THRESHOLD, UNPREPARED_EFFECT_MULT, UNPREPARED_REBELLION,
    SUBMISSION_ACTION_THRESHOLD, SUBMISSION_ACTION_GAIN, SUBMISSION_MAX,
    ROMANCE_ENTRY_THRESHOLD,
    _THRUST_TOGGLE_IDS, _INSERTION_EXP_MAP,
)
from romance_core import (
    get_character_asset as get_npc_asset,
    emit_romance_sound, emit_ecstasy_sound,
    is_action_available, is_anatomy_compatible,
    get_effective_affection_req, get_climax_reaction_key,
    get_sensation_level, get_rebellion_key, get_affection_key,
    get_exposure_state, get_next_undress_item, perform_undress,
    _get_relationship_key,
    get_internal_semen_total, get_internal_semen,
    _has_active_penetration,
    _has_active_intercourse_from_state, get_insertion_exp_part,
    _apply_internal_semen, _apply_semen, calculate_ejaculation_amount,
    is_hold_back_available, is_ejaculate_available,
    check_preparation, check_lubrication,
    check_and_clear_virginity,
    get_conflicting_toggles, _remove_conflicting_toggles,
    get_action_exp_part,
    calculate_stealth_chance, check_stealth_success,
    extract_preserved,
    calculate_npc_stamina_cost,
    calculate_climax_hp_cost,
)

# ============================================
# 상수 정의
# ============================================

# 빠져나가기 확률 보정
ESCAPE_BASE_CHANCE = 0.3  # 기본 30%
ESCAPE_STRENGTH_BONUS = 0.05  # 근력 1당 +5%
ESCAPE_BODY_BONUS = {
    "왜소": -0.1,
    "보통": 0.0,
    "장신": 0.05,
    "거구": 0.15,
}

INTERRUPT_JOIN_THRESHOLD = 60  # 합류 가능 최소 호감도

# 시간 상수 (밀리초) — MILLIS_PER_MINUTE은 romance_actions에서 import
MILLIS_PER_DAY = 86_400_000

# NPC 대기 스케줄 (location_id 없음 = 이동 없이 현위치 대기)
STAY_SCHEDULE = [
    {"name": "대기", "start": 0, "end": MILLIS_PER_DAY, "activity": "대기"}
]

# NPC 주도 최소 체력 (HP 가드) — 탈진 임계치와 통일
from survival import EXHAUSTION_HP_THRESHOLD
INITIATIVE_MIN_HEALTH = EXHAUSTION_HP_THRESHOLD

# NPC 만족 종료 조건
NPC_SATISFACTION_AROUSAL = 20   # 성욕 임계치
NPC_SATISFACTION_CLIMAX = 1     # 최소 절정 횟수

# 플레이어 행동 제한 (NPC 주도 모드)
NPC_INITIATIVE_CONSENT_THRESHOLD = 80   # 이 호감 이상이면 합의 (차단 없음)
NPC_BLOCK_BASE_CHANCE = 0.85            # 기본 85% 차단
NPC_BLOCK_STRENGTH_BONUS = 0.05         # 근력 1당 -5%
NPC_BLOCK_BODY_BONUS = {
    "왜소": 0.05,    # 왜소: 막기 쉬움 (+5%)
    "보통": 0.0,
    "장신": -0.05,
    "거구": -0.15,
}
NPC_BLOCK_MIN_CHANCE = 0.30     # 최소 차단 확률
NPC_BLOCK_MAX_CHANCE = 0.95     # 최대 차단 확률
NPC_BLOCK_AROUSAL_GAIN = 3      # 차단 시 NPC 성욕 기본 증가량
NPC_BLOCK_PERSONALITY_BONUS = {
    "stoic": 0.0,        # 과묵: 기본
    "gentle": -0.15,     # 온화: 차단 잘 안함
    "cheerful": -0.10,   # 활발: 차단 덜함
    "timid": -0.05,      # 소심: 약간 덜함 (겁먹어서 못 막음)
    "cold": 0.05,        # 냉담: 약간 더 차단
    "seductive": -0.10,  # 유혹: 차단 덜함 (즐기는 중)
    "fierce": 0.10,      # 격렬: 더 차단
    "proud": 0.05,       # 오만: 약간 더 차단
    "innocent": -0.05,   # 순수: 약간 덜함
    "devoted": -0.20,    # 헌신: 거의 차단 안함
}

# NPC 주도 결박 상수
NPC_RESTRAIN_COOLDOWN_MS = 86_400_000  # 24시간
NPC_RESTRAIN_MIN_AROUSAL = 60          # 최소 성욕
NPC_RESTRAIN_MIN_AFFECTION = 60        # 최소 호감
NPC_RESTRAIN_MIN_SUBMISSION = 40       # 최소 복종 (호감 미충족 시)


# ============================================
# 유틸리티 함수
# ============================================

def get_player_body_type(player_id):
    """플레이어 체형 가져오기"""
    props = morld.get_unit_props(player_id)
    if not props:
        return "보통"

    for key in props:
        if key.startswith("신체:") and props[key] > 0:
            return key.replace("신체:", "")
    return "보통"


def get_player_strength(player_id):
    """플레이어 근력 스탯 가져오기"""
    props = morld.get_unit_props(player_id)
    if not props:
        return 5
    return props.get("근력", 5)


def get_affection(npc_id, player_id):
    """NPC의 플레이어에 대한 호감도 조회"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'

    props = morld.get_unit_props(npc_id)
    if not props:
        return 0

    return props.get(f"관계:{player_name}:호감", 0)


def get_npc_arousal(npc_id):
    """NPC의 성욕 조회"""
    props = morld.get_unit_props(npc_id)
    if not props:
        return 0
    return props.get("상태:성욕", 0)


# ============================================
# 행위 충돌 시스템 (신체 부위 기반)
# ============================================

# ============================================
# 빠져나가기 시스템
# ============================================

def calculate_escape_chance(player_id, npc_id):
    """
    빠져나가기 성공 확률 계산

    Returns:
        float: 0.0 ~ 1.0 범위의 확률
    """
    chance = ESCAPE_BASE_CHANCE

    # 힘 보정
    strength = get_player_strength(player_id)
    chance += (strength - 5) * ESCAPE_STRENGTH_BONUS

    # 체형 보정
    body_type = get_player_body_type(player_id)
    chance += ESCAPE_BODY_BONUS.get(body_type, 0.0)

    # 범위 제한
    return max(0.05, min(0.95, chance))


def attempt_escape(player_id, npc_id):
    """
    빠져나가기 시도

    Returns:
        bool: True면 성공, False면 실패
    """
    chance = calculate_escape_chance(player_id, npc_id)
    return random.random() < chance


# 저항 모드 상수
RESISTANCE_BASE_GAIN = 15    # 기본 저항 축적량
RESISTANCE_MAX = 100         # 저항 임계치 (도달 시 탈출)


def calculate_resistance_gain(player_id, npc_id):
    """저항 모드: 매 턴 저항 축적량 계산

    Returns:
        int: 저항 축적량 (RESISTANCE_MAX 도달 시 탈출)
    """
    # 성욕이 높으면 저항 불가 (정욕 quadrant)
    from romance_actions import DES_LABEL_THRESHOLD
    npc_props = morld.get_unit_props(npc_id)
    arousal = npc_props.get("상태:성욕", 0) if npc_props else 0
    if arousal >= DES_LABEL_THRESHOLD:
        return 0

    from romance_mode import get_strength
    diff = get_strength(player_id) - get_strength(npc_id)
    gain = RESISTANCE_BASE_GAIN + int(diff * 2)
    return max(5, min(40, gain))


# ============================================
# 플레이어 행동 차단 시스템 (NPC 주도 모드)
# ============================================

def _check_npc_block(player_id, npc_id, action_def, state):
    """NPC 주도 모드에서 플레이어 능동 행위 차단 판정.

    차단 확률 = base - 근력 - 체형 + 성격 - 호감(점진) - 성욕
    차단 성공 시 NPC 성욕 증가 (반복 시도 → 점진적 무력화)

    Returns:
        (blocked: bool, reaction: str | None)
    """
    # 수동 행위는 항상 허용
    if action_def.get("passive_in_npc_initiative"):
        return False, None

    # 호감 임계치 이상이면 합의 → 차단 안 함
    affection = get_affection(npc_id, player_id)
    if affection >= NPC_INITIATIVE_CONSENT_THRESHOLD:
        return False, None

    # --- 차단 확률 계산 ---
    strength = get_player_strength(player_id)
    body_type = get_player_body_type(player_id)

    block_chance = NPC_BLOCK_BASE_CHANCE

    # 1) 근력 보정 (기존)
    block_chance -= (strength - 5) * NPC_BLOCK_STRENGTH_BONUS

    # 2) 체형 보정 (기존)
    block_chance += NPC_BLOCK_BODY_BONUS.get(body_type, 0.0)

    # 3) 성격 보정 (아키타입 기반)
    npc_asset = get_npc_asset(npc_id)
    archetype = "stoic"
    if npc_asset:
        profile = getattr(npc_asset, 'REACTION_PROFILE', {})
        archetype = profile.get('archetype', 'stoic')
    block_chance += NPC_BLOCK_PERSONALITY_BONUS.get(archetype, 0.0)

    # 4) 호감도 점진적 감소: 50~80 구간에서 최대 -30%
    if affection >= 50:
        affection_reduction = (affection - 50) / 30.0 * 0.30
        block_chance -= affection_reduction

    # 5) 성욕 보정: 50~100 구간에서 최대 -20%
    npc_props = morld.get_unit_props(npc_id)
    arousal = npc_props.get("상태:성욕", 0) if npc_props else 0
    if arousal >= 50:
        arousal_reduction = (arousal - 50) / 50.0 * 0.20
        block_chance -= arousal_reduction

    block_chance = max(NPC_BLOCK_MIN_CHANCE, min(NPC_BLOCK_MAX_CHANCE, block_chance))

    if random.random() < block_chance:
        # 차단 성공 — NPC 성욕 증가 (플레이어의 시도가 자극)
        arousal_gain = NPC_BLOCK_AROUSAL_GAIN
        if affection >= 50:
            arousal_gain += 2  # 호감 높으면 더 자극
        morld.modify_prop(npc_id, "상태:성욕", arousal_gain)

        # 차단 반응 생성
        reaction = None
        if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
            reaction = npc_asset.get_romance_reaction(
                "npc_block_player", "start", stim_state=state.get("stim"))
        if not reaction:
            npc_info = morld.get_unit_info(npc_id)
            npc_name = npc_info.get("name", "상대") if npc_info else "상대"
            reaction = f"{npc_name}(이)가 당신의 손을 뿌리쳤다."
        return True, reaction

    return False, None


# ============================================
# 제3자 감지 시스템 (은신 — romance_core에서 import)
# ============================================

def check_third_party_arrival(state):
    """
    제3자 도착 체크 (은신 확률 적용)

    시간 경과 후 호출하여 새로 도착한 NPC가 있는지 확인합니다.

    Args:
        state: 현재 상태 dict

    Returns:
        dict: {"interrupted": bool, "interrupter_id": int or None}
    """
    player_id = state["player_id"]
    npc_id = state["npc_id"]

    # 현재 Location의 캐릭터 목록 확인
    player_loc = morld.get_unit_location(player_id)
    if not player_loc:
        return {"interrupted": False}

    units_at_loc = morld.get_characters_at_location(player_loc[0], player_loc[1])

    # 새로 도착한 NPC 중 호감도 체크
    for unit_id in units_at_loc:
        if unit_id == npc_id:
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
        if unit_id in state["checked_npcs"]:
            continue

        # 체크 목록에 추가
        state["checked_npcs"].add(unit_id)

        # 호감도 체크
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        props = morld.get_unit_props(unit_id)
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0

        if affection < INTERRUPT_JOIN_THRESHOLD:
            # 은신 성공 여부 판정
            if check_stealth_success(state):
                # 은신 성공 - 들키지 않음 (근처 접근 표시만)
                state["near_miss"] = True
                state["near_miss_id"] = unit_id

                # NPC 캐릭터의 은신 성공 반응 처리
                npc_id = state["npc_id"]
                npc_asset = get_npc_asset(npc_id)
                if npc_asset:
                    # 효과 적용 (예: 스릴에 더 흥분)
                    if hasattr(npc_asset, 'apply_stealth_success_effects'):
                        npc_asset.apply_stealth_success_effects(player_id)

                    # 반응 텍스트 (near_miss 메시지에 추가)
                    if hasattr(npc_asset, 'get_stealth_success_reaction'):
                        reaction = npc_asset.get_stealth_success_reaction(player_id)
                        if reaction:
                            state["stealth_reaction"] = reaction

                continue

            # 들킴 - 중단
            return {"interrupted": True, "interrupter_id": unit_id}
        # 합류/난교 로직은 TBA (세부 다인 시나리오는 현 범위 밖)

    return {"interrupted": False}


def advance_time_and_check_npc_initiative(state, millis):
    """
    시간 경과 + NPC 도착 체크 (NPC 주도용)

    Args:
        state: 현재 상태 dict
        millis: 경과 시간 (밀리초)

    Returns:
        dict: {"interrupted": bool, "interrupter_id": int or None}
    """
    # 시간 진행 + NPC 자율 행동 시뮬레이션 (DES)
    morld.advance_time_des(millis)

    # 제3자 도착 체크
    return check_third_party_arrival(state)


# ============================================
# NPC 주도 결박 트리거
# ============================================

def _find_restraint_in_npc_inventory(npc_id):
    """NPC 인벤토리에서 결박 아이템 탐색"""
    import equipment as eq
    inventory = morld.get_unit_inventory(npc_id)
    if not inventory:
        return None
    equipped = set(eq.get_equipped_items(npc_id)) if hasattr(eq, 'get_equipped_items') else set()
    for item_id, count in inventory.items():
        item_id_int = int(item_id)
        if item_id_int in equipped:
            continue
        info = morld.get_item_info(item_id_int)
        if not info:
            continue
        ep = info.get("equip_props", {})
        if ep.get("결박:상체") or ep.get("결박:하체"):
            return item_id_int
    return None


def check_npc_restrain_trigger(state):
    """NPC 주도 결박 판정

    조건:
      1. NPC dominance ≥ 0.3, restraint_preference ≥ 0.2
      2. NPC 인벤토리에 결박 아이템 보유
      3. NPC 성욕 ≥ 60
      4. 플레이어 호감 ≥ 60 OR 복종 ≥ 40
      5. 쿨다운 24시간
      6. 확률 = dominance × restraint_pref × (arousal / 100)

    Returns:
        (should_try, item_id, message)
    """
    npc_id = state["npc_id"]
    player_id = state["player_id"]

    # 이미 결박 중이면 스킵
    import restraint
    if restraint.is_any_restrained(player_id):
        return False, None, ""

    # 1. 성향 체크
    npc_asset = get_npc_asset(npc_id)
    prefs = getattr(npc_asset, 'SEXUAL_PREFERENCES', {}) or {}
    dom = prefs.get("dominance", 0)
    res_pref = prefs.get("restraint_preference", 0)
    if dom < 0.3 or res_pref < 0.2:
        return False, None, ""

    # 2. 인벤토리에 결박 아이템 확인
    restraint_item = _find_restraint_in_npc_inventory(npc_id)
    if restraint_item is None:
        return False, None, ""

    # 3. 성욕 체크
    arousal = morld.get_unit_prop(npc_id, "상태:성욕") or 0
    if arousal < NPC_RESTRAIN_MIN_AROUSAL:
        return False, None, ""

    # 4. 관계 체크 (호감 60+ OR 복종 40+)
    player_info = morld.get_unit_info(player_id)
    p_name = player_info.get("name", "주인공") if player_info else "주인공"
    aff = morld.get_unit_prop(npc_id, f"관계:{p_name}:호감") or 0
    sub = morld.get_unit_prop(npc_id, f"관계:{p_name}:복종") or 0
    if aff < NPC_RESTRAIN_MIN_AFFECTION and sub < NPC_RESTRAIN_MIN_SUBMISSION:
        return False, None, ""

    # 5. 쿨다운 (24h)
    last = morld.get_unit_prop(npc_id, "NPC주도:결박쿨다운") or 0
    if morld.get_game_time() - last < NPC_RESTRAIN_COOLDOWN_MS:
        return False, None, ""

    # 6. 확률 판정
    chance = dom * res_pref * (arousal / 100)
    if random.random() > chance:
        return False, None, ""

    # 반응 메시지 (캐릭터 반응 시스템)
    msg = ""
    if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
        msg = npc_asset.get_romance_reaction(
            "npc_restrain_attempt", "start",
            stim_state=state.get("stim")) or ""
    if not msg:
        msg = "(결박 장비를 꺼내며 다가온다...)"

    return True, restraint_item, msg


# ============================================
# NPC 액션 시스템
# ============================================

def get_available_npc_actions(npc_id, player_id):
    """
    NPC가 선택 가능한 액션 목록 반환

    NPC의 현재 성욕/호감도에 따라 가능한 액션들을 필터링합니다.

    Returns:
        list: 선택 가능한 액션 ID 리스트
    """
    arousal = get_npc_arousal(npc_id)

    available = []
    for action_id, action_def in NPC_TOGGLE_ACTIONS.items():
        if not is_anatomy_compatible(action_def, player_id, actor_id=npc_id):
            continue
        if is_action_available(npc_id, player_id, action_def):
            available.append(action_id)

    # 성욕이 높을수록 더 적극적인 액션 선호
    # (기본적으로는 모든 가능한 액션을 반환)
    return available


def select_random_npc_action(npc_id, player_id, active_toggles, lubricated=True,
                             cur_position="missionary", is_inserted=False):
    """
    NPC가 랜덤으로 행위 선택

    현재 활성화된 토글을 제외하고, 조건에 맞는 액션 중 랜덤 선택합니다.
    캐릭터별 INITIATIVE_ACTION_FILTERS가 정의되어 있으면 해당 필터도 적용합니다.

    Args:
        npc_id: NPC ID
        player_id: 플레이어 ID
        active_toggles: 현재 활성화된 토글 set
        lubricated: 윤활 상태 (False면 pregnancy_check 행위 제외)
        cur_position: 현재 체위 (배면 체위 시 uses_mouth 행위 제외)
        is_inserted: 삽입 상태 (False면 requires_active_insertion 행위 제외)

    Returns:
        str: 선택된 액션 ID 또는 None (더 이상 선택할 액션 없음)
    """
    available = get_available_npc_actions(npc_id, player_id)

    # 캐릭터별 필터링 적용 (INITIATIVE_ACTION_FILTERS)
    npc_asset = get_npc_asset(npc_id)
    if npc_asset and hasattr(npc_asset, 'get_allowed_initiative_actions'):
        allowed = npc_asset.get_allowed_initiative_actions(player_id)
        if allowed is not None:
            # 허용된 액션만 남김
            available = [a for a in available if a in allowed]

    # 윤활 미충족 시 질 삽입 행위 제외
    if not lubricated:
        available = [a for a in available
                     if not NPC_TOGGLE_ACTIONS.get(a, {}).get("pregnancy_check")]

    # 배면 체위: 입 사용 행위 제외
    if position.get_facing(cur_position) == "back":
        available = [a for a in available
                     if not NPC_TOGGLE_ACTIONS.get(a, {}).get("uses_mouth")]

    # 삽입 상태 필요 토글: 미삽입 시 제외
    if not is_inserted:
        available = [a for a in available
                     if not NPC_TOGGLE_ACTIONS.get(a, {}).get("requires_active_insertion")]

    # 이미 활성화된 토글 제외
    candidates = [a for a in available if a not in active_toggles]

    if not candidates:
        return None  # 더 이상 추가할 액션 없음

    # 성욕 기반 가중치 (높을수록 더 적극적인 액션 선호)
    arousal = get_npc_arousal(npc_id)

    # 간단한 가중치: 성욕 높으면 적극적인 액션 선호
    weights = []
    for action_id in candidates:
        action_def = NPC_TOGGLE_ACTIONS[action_id]
        req = action_def.get("affection_req", 0)

        # 성욕이 높을수록 높은 req 액션에 가중치
        if arousal >= 80:
            weight = req  # 높은 req에 높은 가중치
        elif arousal >= 50:
            weight = 50   # 균등
        else:
            weight = 100 - req  # 낮은 req에 높은 가중치

        weights.append(max(weight, 10))  # 최소 가중치 10

    # 가중치 기반 랜덤 선택
    return random.choices(candidates, weights=weights, k=1)[0]


# ============================================
# 제3자 방해 이벤트 처리
# ============================================

def handle_npc_initiative_interruption(state, npc_name):
    """
    NPC 주도 중 제3자에게 들켰을 때 처리

    Args:
        state: 현재 상태 dict
        npc_name: NPC 이름

    Yields:
        다이얼로그 요청들
    """
    interrupter_id = state.get("interrupter_id")
    npc_id = state["npc_id"]
    player_id = state["player_id"]

    # 캐릭터별 발각 반응 시도
    from assets.characters import get_instance
    interrupter = get_instance(interrupter_id)
    if interrupter and hasattr(interrupter, 'on_romance_discovered'):
        result = interrupter.on_romance_discovered(player_id, npc_id)
        if result is not None:
            yield from result
        else:
            # fallback: 기본 대사
            interrupter_info = morld.get_unit_info(interrupter_id)
            interrupter_name = interrupter_info.get("name", "누군가") if interrupter_info else "누군가"
            yield ui.dialog([f"[{interrupter_name}]", "...!"])
    else:
        # 캐릭터 인스턴스 없음: 기본 대사
        interrupter_info = morld.get_unit_info(interrupter_id)
        interrupter_name = interrupter_info.get("name", "누군가") if interrupter_info else "누군가"
        yield ui.dialog([f"[{interrupter_name}]", "...!"])

    # NPC 반응 (부끄러움)
    morld.add_unit_mood(npc_id, "부끄러움")

    # NPC가 도망감
    morld.set_npc_job(npc_id, "flee", 30 * MILLIS_PER_MINUTE, player_id)

    # NPC 호감도 감소 + 반발 (들켜서 부끄러움)
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    morld.modify_prop(npc_id, f"관계:{player_name}:호감", -3)
    morld.modify_prop(npc_id, f"관계:{player_name}:반발", 3)

    # 나체 발각 추가 페널티
    exposure = get_exposure_state(npc_id)
    if exposure.get("upper_exposed") or exposure.get("lower_exposed"):
        morld.modify_prop(npc_id, f"관계:{player_name}:호감", -2)
        morld.modify_prop(npc_id, f"관계:{player_name}:반발", 5)

    # Phase 1: 수치심 상태 상승 (나체 시 추가) — 이후 게이트 평가에 영향
    from romance_core import on_romance_discovered as _on_romance_discovered
    _on_romance_discovered(npc_id)


# ============================================
# UI 렌더링
# ============================================

def render_stamina_bar(stamina, max_stamina=100):
    """체력 바 렌더링 (10칸 정규화)"""
    BAR_WIDTH = 10
    ratio = stamina / max(1, max_stamina)
    filled = max(0, min(BAR_WIDTH, round(ratio * BAR_WIDTH)))
    empty = BAR_WIDTH - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {int(stamina)}/{int(max_stamina)}"


def get_affection_key(player_id):
    """플레이어에 대한 호감도 prop 키 생성"""

    return _get_relationship_key(player_id, "호감")


def render_npc_initiative_ui(state):
    """
    NPC 주도 스킨십 UI 렌더링 (romance.py 스타일)

    Returns:
        str: BBCode 형식의 UI 텍스트
    """
    npc_id = state["npc_id"]
    player_id = state["player_id"]
    player_stamina = state["stamina"]

    npc_info = morld.get_unit_info(npc_id)
    npc_name = npc_info.get('name', '그녀') if npc_info else '그녀'
    npc_props = morld.get_unit_props(npc_id)

    # 호감/성욕 키
    affection_key = get_affection_key(player_id)
    arousal_key = "상태:성욕"

    lines = []

    # 헤더 - NPC 이름 + 스태미나
    resistance_mode = state.get("resistance_mode", False)
    mode_label = (" " + style_danger("[저항 중]")) if resistance_mode else ""
    cur_pos = state.get("position", "missionary")
    pos_name_hdr = position.get_name(cur_pos)
    pos_facing_hdr = "대면" if position.get_facing(cur_pos) == "front" else "배면"
    max_stamina = state.get("max_stamina", 100)
    npc_stamina = state.get("npc_stamina", 100)
    npc_max = state.get("npc_max_stamina", 100)
    lines.append(f"[{npc_name}의 주도]{mode_label}  체위: {pos_name_hdr}({pos_facing_hdr})")
    lines.append(f"  체력: {render_stamina_bar(player_stamina, max_stamina)}  {npc_name}: {render_stamina_bar(npc_stamina, npc_max)}")

    # 저항 게이지 (저항 모드)
    if resistance_mode:
        meter = state.get("resistance_meter", 0)
        lines.append(style_danger(f"저항: {'█' * (meter // 10)}{'░' * (10 - meter // 10)} {meter}/{RESISTANCE_MAX}"))
    lines.append("")

    # 근접 경고 (누군가 지나갔지만 들키지 않음)
    if state["near_miss"]:
        near_miss_id = state["near_miss_id"]
        near_info = morld.get_unit_info(near_miss_id) if near_miss_id else None
        near_name = near_info.get("name", "누군가") if near_info else "누군가"
        lines.append(style_warning(f"({near_name}(이)가 근처를 지나갔다... 들키지 않았다.)"))

        # NPC의 은신 성공 반응 (캐릭터별 특별 대사)
        stealth_reaction = state["stealth_reaction"]
        if stealth_reaction:
            lines.append(style_info(f"[{npc_name}] {stealth_reaction}"))
            state["stealth_reaction"] = None  # 표시 후 클리어

        lines.append("")
        state["near_miss"] = False  # 표시 후 클리어
        state["near_miss_id"] = None

    # NPC 탈진 알림 (1회, 표시 후 클리어)
    npc_exhaustion_notice = state.get("_npc_exhaustion_notice")
    if npc_exhaustion_notice:
        lines.append(npc_exhaustion_notice)
        lines.append("")
        state["_npc_exhaustion_notice"] = None

    # 마지막 반응 텍스트 (즉시 액션 결과 등)
    last_reaction = state["last_reaction"]
    if last_reaction:
        lines.append(last_reaction)  # 이미 color 태그 포함
        lines.append("")
        state["last_reaction"] = None  # 표시 후 클리어

    # NPC의 현재 행위 표시 (활성 토글 — 묘사 + NPC 대사)
    from romance_actions import TOGGLE_DURING_DESCRIPTIONS
    npc_asset = get_npc_asset(npc_id)
    active_toggles = state.get("active_toggles", set())
    has_toggle_lines = False
    if active_toggles:
        for toggle_id in active_toggles:
            toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
            if toggle_def:
                # 1. 행위 묘사
                desc = TOGGLE_DURING_DESCRIPTIONS.get(toggle_id)
                if desc:
                    lines.append(f"[color=silver]({desc})[/color]")
                    has_toggle_lines = True
                # 2. NPC 반응
                reaction = None
                if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(f"during_{toggle_id}")
                if reaction:
                    lines.append(f"  [color=yellow]{reaction}[/color]")
                    has_toggle_lines = True
                elif not desc:
                    lines.append(f"({npc_name}(이)가 {toggle_def['name']} 중이다.)")
                    has_toggle_lines = True
    if not has_toggle_lines:
        lines.append(f"({npc_name}(이)가 당신을 붙잡고 있다.)")

    # 상태 묘사 (자극 수준 기반)
    stim_state_desc = state.get("stim")
    if stim_state_desc:
        import gender as gender_mod_desc
        npc_anatomy_desc = gender_mod_desc.get_anatomy(npc_id)
        from romance_core import get_state_description
        state_descs = get_state_description(stim_state_desc, npc_anatomy_desc)
        for sd in state_descs:
            lines.append(style_muted(sd))

    lines.append("")

    # 호감/성욕 표시
    affection = npc_props.get(affection_key, 0) if npc_props else 0
    arousal = npc_props.get(arousal_key, 0) if npc_props else 0
    from romance_actions import get_relationship_label
    rel_label = get_relationship_label(affection, arousal)
    lines.append(f"[{rel_label}] 호감: {affection}  성욕: {arousal}")

    # 자극 표시 (세션 스코프, 대상 성별 기반)
    stim_state = state.get("stim")
    if stim_state:
        import gender as gender_mod
        npc_anatomy = gender_mod.get_anatomy(npc_id)
        stim_parts = []
        for cat in ("F", "M", "B", "A", "V", "C", "P"):
            if cat not in npc_anatomy:
                continue
            val = stim_state["stim"].get(cat, 0)
            if val >= stimulation.STIM_MAX:
                stim_parts.append(style_highlight(f"{cat}:{val}★"))
            else:
                stim_parts.append(f"{cat}:{val}")
        stim_line = f"자극: {' '.join(stim_parts)}"
        if stim_state.get("refractory", 0) > 0:
            stim_line += f"  {style_danger('[불응기]')}"
        elif stim_state["afterglow"] > 0:
            chain = stim_state["chain_count"]
            if chain > 0:
                stim_line += f"  {c('pink', f'[여운 ×{chain + 1}]')}"
            else:
                stim_line += f"  {c('pink', '[여운]')}"
        if stim_state["climax_total"] > 0:
            stim_line += f"  절정: {stim_state['climax_total']}"
        lines.append(stim_line)
        # 절정 게이지
        gauge = stim_state.get("climax_gauge", 0)
        gauge_filled = int(gauge / 10)
        gauge_empty = 10 - gauge_filled
        gauge_line = f"절정: {'█' * gauge_filled}{'░' * gauge_empty} {int(gauge)}/{stimulation.CLIMAX_GAUGE_MAX}"
        if stimulation.is_trance(stim_state):
            gauge_line += f"  {c('magenta', '[트랜스]')}"
        if stimulation.is_p_peaked(stim_state):
            gauge_line += f"  {style_danger('[사정감]')}"
        lines.append(gauge_line)
    # 노출 상태 표시
    exposure = get_exposure_state(npc_id)
    exposure_parts = []
    if exposure["upper_exposed"]:
        exposure_parts.append(c("pink", "상체 노출"))
    if exposure["lower_exposed"]:
        exposure_parts.append(c("pink", "하체 노출"))
    if exposure_parts:
        lines.append(f"복장: {' '.join(exposure_parts)}")

    # 체내 정액 표시

    internal_total = get_internal_semen_total(npc_id)
    if internal_total > 0:
        internal_parts = []
        for ip in INTERNAL_SEMEN_PARTS:
            val = get_internal_semen(npc_id, ip)
            if val > 0:
                internal_parts.append(f"{ip}: {val}")
        if internal_parts:
            lines.append(c("pink", f"체내 정액: {', '.join(internal_parts)}"))

    # 윤활 상태 표시
    import gender as gender_mod

    if gender_mod.has_anatomy(npc_id, "V"):
        if state["lubricated"]:
            lines.append(style_success("윤활: 충분"))
        else:
            arousal = morld.get_unit_prop(npc_id, "상태:성욕") or 0
            lines.append(style_danger(f"윤활: 건조 (성욕 {int(arousal)}/{LUBRICATION_THRESHOLD})"))

    lines.append("")

    # 결박 상태 표시
    if state.get("player_restrained"):
        import restraint
        parts_restrained = []
        if restraint.is_upper_restrained(player_id):
            parts_restrained.append("상체")
        if restraint.is_lower_restrained(player_id):
            parts_restrained.append("하체")
        if parts_restrained:
            lines.append(style_danger(f"결박: {'+'.join(parts_restrained)}"))

    # 탈출 확률 표시
    escape_chance = calculate_escape_chance(player_id, npc_id)
    import restraint as restraint_mod
    escape_mult = restraint_mod.get_escape_multiplier(player_id)
    effective_escape = escape_chance * escape_mult
    lines.append(style_muted(f"탈출 확률: {int(effective_escape * 100)}%"))

    # 탈출 결과 표시 (있으면)
    if state["escape_result"]:
        lines.append(style_danger(state['escape_result']))

    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # NPC 현재 행위 (토글 - NPC가 주도)
    lines.append("[NPC 행위]")
    for toggle_id in active_toggles:
        toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
        if toggle_def:
            lines.append(f"  ■ {toggle_def['name']} (진행 중)")
    if not active_toggles:
        lines.append("  (없음)")
    lines.append("")

    # 플레이어 선택 가능한 즉시 행위 (저항 모드에서는 숨김)
    insertion = state.get("insertion", {})
    is_inserted = insertion.get("active", False)
    if not resistance_mode:
        lines.append("[즉시 행위] (플레이어)")
        for action_id, action in PLAYER_INSTANT_ACTIONS.items():
            if not is_anatomy_compatible(action, npc_id, actor_id=player_id):
                continue
            # 플레이어 자신의 해부학 요구사항 (hold_back 등)
            player_self_req = action.get("requires_player_anatomy_self")
            if player_self_req:
                import gender as gender_mod
                if not gender_mod.has_anatomy(player_id, player_self_req):
                    continue
            # hold_back/ejaculate: 특수 표시 영역에서 처리
            if action_id in ("hold_back", "ejaculate"):
                continue
            # 삽입 시도: 이미 삽입 중이면 숨김
            if action.get("is_insertion_attempt") and is_inserted:
                continue
            # 삽입 상태 필요 즉시형: 삽입 중이 아니면 숨김
            if action.get("requires_active_insertion") and not is_inserted:
                continue
            # 활성 토글 필요 즉시형 (tongue_play → deep_kiss 필요)
            req_toggle = action.get("requires_active_toggle")
            if req_toggle and req_toggle not in active_toggles:
                continue
            # 배면 체위: 입 사용 행위 비활성화
            if action.get("uses_mouth"):
                if position.get_facing(state.get("position", "missionary")) == "back":
                    _aname = action['name']
                    lines.append(f"  {style_muted(_aname + ' (배면 체위)')}")
                    continue
            # 체내 정액 필요 행위: 해당 부위 체내 정액 없으면 숨김
            req_internal = action.get("requires_internal_semen")
            if req_internal:
                if get_internal_semen(npc_id, req_internal) <= 0:
                    continue
            # 탈의 행위: 벗을 것 없으면 숨김
            if action.get("undress"):
                is_upper = action["undress"] == "upper"
                if get_next_undress_item(npc_id, upper=is_upper) is None:
                    continue
            # 노출 필요 행위: 미노출 시 잠금
            req_area = action.get("requires_exposure")
            if req_area and not exposure.get(f"{req_area}_exposed"):
                _aname = action['name']
                if is_action_available(npc_id, player_id, action):
                    lines.append(f"  {style_muted(_aname + ' (탈의 필요)')}")
                else:
                    submission_key = affection_key.replace(":호감", ":복종")
                    eff_req = get_effective_affection_req(action["affection_req"],
                        npc_props.get("상태:성욕", 0) if npc_props else 0,
                        npc_props.get(submission_key, 0) if npc_props else 0)
                    lines.append(f"  {style_muted(_aname + ' (호감 ' + str(eff_req) + ' 필요)')}")
                continue
            if is_action_available(npc_id, player_id, action):
                if player_stamina >= action["stamina"]:
                    # 능동 행위 + 호감 부족 → 제지 가능 표시
                    is_passive = action.get("passive_in_npc_initiative", False)
                    if not is_passive and affection < NPC_INITIATIVE_CONSENT_THRESHOLD:
                        _aname = action['name']
                        lines.append(
                            f"  [url=@proc:instant:{action_id}]"
                            f"{style_highlight(_aname)}"
                            f" {style_muted('(제지 가능)')}[/url]")
                    else:
                        lines.append(f"  [url=@proc:instant:{action_id}]{action['name']}[/url]")
                else:
                    _aname = action['name']
                    lines.append(f"  {style_muted(_aname + ' (스태미나 부족)')}")
            else:
                _aname = action['name']
                submission_key = affection_key.replace(":호감", ":복종")
                eff_req = get_effective_affection_req(action["affection_req"],
                    npc_props.get("상태:성욕", 0) if npc_props else 0,
                    npc_props.get(submission_key, 0) if npc_props else 0)
                lines.append(f"  {style_muted(_aname + ' (호감 ' + str(eff_req) + ' 필요)')}")
        # 참기 (peaked 부위 존재 + 게이지 > 0)
        if is_hold_back_available(state):
            import gender as gender_mod
            if gender_mod.has_anatomy(player_id, "P"):
                hb_count = stim_state.get("hold_back_count", 0) if stim_state else 0
                chance = max(stimulation.HOLD_BACK_MIN_CHANCE,
                             stimulation.HOLD_BACK_BASE_CHANCE - hb_count * stimulation.HOLD_BACK_CHANCE_DECAY)
                reduction = max(stimulation.HOLD_BACK_REDUCTION_MIN,
                                stimulation.HOLD_BACK_REDUCTION - hb_count * stimulation.HOLD_BACK_REDUCTION_DECAY)
                lines.append(f"  [url=@proc:instant:hold_back]참기 (성공률 {chance}%, 성공 시 -{reduction})[/url]")
        # 사정하기 (P stim >= threshold)
        if is_ejaculate_available(state, player_id):
            p_stim = stim_state["stim"].get("P", 0) if stim_state else 0
            p_sensation = get_sensation_level(player_id, "P")
            threshold = stimulation.get_ejaculate_threshold(p_sensation)
            lines.append(f"  [url=@proc:instant:ejaculate]사정하기 (P: {p_stim}/{threshold})[/url]")
        lines.append("")

    # 선택지
    lines.append(ui.divider())
    # Slice P4: 합의 제안 — 관계 기반 평화 전환 (저항/수용 양쪽에서 노출)
    from romance_core import (
        calculate_consent_success_chance,
        calculate_switch_takeover_chance,
    )
    consent_chance = calculate_consent_success_chance(npc_id, player_id)

    if resistance_mode:
        # 저항 모드: 저항/포기 + 합의 제안
        gain = calculate_resistance_gain(player_id, npc_id)
        lines.append(f"[url=@proc:resist]{style_danger('저항하기 (+' + str(gain) + ')')}[/url]")
        lines.append("[url=@proc:surrender]포기하기[/url]")
        if consent_chance > 0:
            lines.append(
                f"[url=@proc:suggest_consent]합의 제안 ({int(consent_chance * 100)}%)[/url]"
            )
    else:
        lines.append("[url=@proc:escape]빠져나가기 시도[/url]")
        lines.append(f"[url=@proc:resist_start]{style_danger('저항하기')}[/url]")
        lines.append("[url=@proc:accept]받아들이기[/url]")
        if consent_chance > 0:
            lines.append(
                f"[url=@proc:suggest_consent]합의 제안 ({int(consent_chance * 100)}%)[/url]"
            )

        # 결박 해제 시도 (결박 상태일 때)
        if state.get("player_restrained"):
            lines.append(f"[url=@proc:escape_restraint]{style_warning('결박 해제 시도')}[/url]")

        # 공수 전환 버튼 — Slice P3: 지배 기반 조건
        if affection >= ROMANCE_ENTRY_THRESHOLD:
            switch_chance = calculate_switch_takeover_chance(npc_id, player_id)
            if switch_chance > 0:
                label = "주도권 빼앗기"
                if switch_chance < 1.0:
                    label += f" ({int(switch_chance * 100)}%)"
                lines.append(f"[url=@proc:switch]{label}[/url]")

    lines.append("")
    lines.append(f"[url=@proc:exit]{style_muted('나가기')}[/url]")

    return "\n".join(lines)


# ============================================
# 절정 시 체력 소모 헬퍼
# ============================================

def _apply_climax_hp_cost_npc(state, climax_info):
    """절정/사정 시 양방향 체력 소모 (NPC 주도용)

    NPC 절정(non-P parts peaked) → NPC HP 소모
    플레이어 사정(P peaked) → 플레이어 HP 소모
    """
    non_p_parts = climax_info.get("non_p_parts", [])
    has_p = climax_info.get("has_p", False)
    npc_id = state.get("npc_id")
    player_id = state.get("player_id")

    # NPC 절정 → NPC HP 소모
    if non_p_parts and npc_id:
        npc_exhausted = state.get("npc_exhausted", False)
        cost = calculate_climax_hp_cost(npc_id, npc_exhausted)
        if cost > 0:
            state["npc_stamina"] -= cost
            if state["npc_stamina"] <= 0:
                state["npc_stamina"] = 1  # 기절 시 HP=1 하한선
                state["npc_exhausted"] = True
            elif (state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD
                    and not state.get("npc_exhausted")):
                state["npc_exhausted"] = True

    # 플레이어 사정 (P peaked) → 플레이어 HP 소모
    if has_p and player_id:
        player_exhausted = (state.get("exhausted", False)
                            or state.get("stamina", 100) <= EXHAUSTION_HP_THRESHOLD)
        cost = calculate_climax_hp_cost(player_id, player_exhausted)
        if cost > 0:
            state["stamina"] -= cost
            if state["stamina"] <= 0:
                state["stamina"] = 1  # HP 하한선


# ============================================
# 효과 적용 함수
# ============================================

def apply_action_effects(state, action_def):
    """
    행위 효과 적용 + 자극 계산

    Args:
        state: 현재 상태
        action_def: 액션 정의 dict

    Returns:
        절정 반응 텍스트 또는 None

    Note:
        tick_afterglow()는 호출자가 턴당 1회 호출해야 함.
    """
    npc_id = state["npc_id"]
    player_id = state["player_id"]
    affection_key = get_affection_key(player_id)

    effects = dict(action_def.get("effects", {}))
    # 노출 보너스 적용 (해당 부위 노출 시 ×1.5)
    bonus_area = action_def.get("exposure_bonus")
    if bonus_area:
        exposure = get_exposure_state(npc_id)
        if exposure.get(f"{bonus_area}_exposed"):
            effects = {k: round(v * EXPOSURE_BONUS) for k, v in effects.items()}
    # 수유 보너스: B 카테고리 + 수유 중 → ×1.3
    exp_part_check = action_def.get("exp_part")
    if exp_part_check and SENSATION_MAP.get(exp_part_check) == "B":
        import pregnancy
        if pregnancy.is_lactating(npc_id):
            effects = {k: round(v * 1.3) for k, v in effects.items()}
    for stat, value in effects.items():
        if stat in ("성욕", "성적절정"):
            prop_key = f"상태:{stat}"
        else:
            prop_key = affection_key.replace(":호감", f":{stat}")
        morld.modify_prop(npc_id, prop_key, value)

    # 반발 조회 (자극 계산 + 복종 증가에 사용)
    rebellion_key = get_rebellion_key(player_id)
    npc_props = morld.get_unit_props(npc_id)
    rebellion = npc_props.get(rebellion_key, 0) if npc_props else 0

    # 복종 자연 증가: 고요구 행위 수행 시 (반발 50 미만)

    req = action_def.get("affection_req", 0)
    if req >= SUBMISSION_ACTION_THRESHOLD:
        submission_key = affection_key.replace(":호감", ":복종")
        current_sub = (npc_props or {}).get(submission_key, 0)
        if current_sub < SUBMISSION_MAX and rebellion < 50:
            morld.modify_prop(npc_id, submission_key, SUBMISSION_ACTION_GAIN)

    # 자극 계산
    stim_state = state.get("stim")
    if not stim_state:
        return None

    exp_part = action_def.get("exp_part")
    if not exp_part:
        return None
    category = SENSATION_MAP.get(exp_part)
    if not category:
        return None

    base = effects.get("성욕", 0)
    if base <= 0:
        return None
    sensation = get_sensation_level(npc_id, category)
    gain = stimulation.calc_gain(base, sensation, rebellion, stim_state["afterglow"], stim_state.get("refractory", 0))
    # 삽입 크기 배율 적용
    size_mod = state["size_stim_mod"]
    if size_mod != 1.0 and exp_part in ("음부", "엉덩이", "음경"):
        gain = round(gain * size_mod)
    # NPC 선호 보너스 (체위/부위)
    pref_mult = position.get_preference_mult(state["position"], category, state.get("npc_prefs"))
    if pref_mult != 1.0:
        gain = round(gain * pref_mult)
    climax_info = stimulation.apply(stim_state, category, gain)
    # 추가 자극 (tribadism: V+C 동시)
    extra = action_def.get("extra_exp_part")
    if extra:
        extra_cat = SENSATION_MAP.get(extra)
        if extra_cat:
            extra_sens = get_sensation_level(npc_id, extra_cat)
            extra_gain = stimulation.calc_gain(base, extra_sens, rebellion, stim_state["afterglow"], stim_state.get("refractory", 0))
            extra_pref = position.get_preference_mult(state["position"], extra_cat, state.get("npc_prefs"))
            if extra_pref != 1.0:
                extra_gain = round(extra_gain * extra_pref)
            r2 = stimulation.apply(stim_state, extra_cat, extra_gain)
            if r2 and not climax_info:
                climax_info = r2

    # 삽입 중 플레이어 P 자극 축적 (P 감각 스케일링)
    if (exp_part in ("음부", "엉덩이")
            and state.get("insertion", {}).get("active")
            and any(t in _THRUST_TOGGLE_IDS for t in state.get("active_toggles", set()))):
        import gender as gender_mod
        if gender_mod.has_anatomy(player_id, "P"):
            p_gain = max(3, base // 2)
            p_sensation = get_sensation_level(player_id, "P")
            p_gain = max(1, round(p_gain * stimulation.get_p_gain_multiplier(p_sensation)))
            r_p = stimulation.apply(stim_state, "P", p_gain)
            if r_p and not climax_info:
                climax_info = r_p

    if climax_info:
        sim_mult = climax_info.get("simultaneous_mult", 1.0)
        peaked_parts = climax_info.get("peaked_parts", [climax_info["category"]])
        non_p_parts = climax_info.get("non_p_parts", peaked_parts)
        has_p = climax_info.get("has_p", False)

        # 성욕 일부 감소 (동시 절정 배율 적용)
        npc_props = morld.get_unit_props(npc_id)
        arousal_reduction = round(stimulation.CLIMAX_AROUSAL_REDUCTION * sim_mult)
        current_arousal = npc_props.get("상태:성욕", 0) if npc_props else 0
        new_arousal = max(0, current_arousal - arousal_reduction)
        morld.set_unit_prop(npc_id, "상태:성욕", new_arousal)
        # 성적절정 +1
        morld.modify_prop(npc_id, "상태:성적절정", 1)

        # 절정 부위 감각 경험치 보너스 (부위별)
        exp_gain = stimulation.get_climax_sensation_gain(
            rebellion, climax_info.get("chain_count", 0))
        exp_gain = round(exp_gain * sim_mult)
        for cat in non_p_parts:
            if exp_gain > 0:
                for part, c in SENSATION_MAP.items():
                    if c == cat:
                        morld.modify_prop(npc_id, f"경험:{part}", exp_gain)
                        break
            # 절정 횟수 카운트 (부위별)
            climax_count_key = f"경험:절정:{cat}"
            morld.set_unit_prop(npc_id, climax_count_key,
                                (morld.get_unit_prop(npc_id, climax_count_key) or 0) + 1)

        # 절정 시 일시 자제심 상실 → 트랜스:외부 +20 (Phase 1.9.1)
        # 여운 중 의식 흐림. 1h tick으로 자연 회복.
        morld.modify_prop(npc_id, "트랜스:외부", 20)

        # 절정 시 복종 증가 (반발에 의해 억제)
        climax_sub_gain = max(0, 2 - rebellion // 25)
        if climax_sub_gain > 0:
            submission_key = affection_key.replace(":호감", ":복종")
            current_sub = (npc_props or {}).get(submission_key, 0)
            if current_sub < SUBMISSION_MAX:
                morld.modify_prop(npc_id, submission_key, climax_sub_gain)

        # P 절정 (사정) 처리
        ejac_part = None
        if has_p:
            insertion = state.get("insertion", {})
            if insertion.get("active"):
                orifice = insertion.get("orifice")
                if orifice == "vaginal":
                    import gender as gender_mod
                    if gender_mod.has_anatomy(npc_id, "P"):
                        import pregnancy
                        pregnancy.check_conception(player_id, npc_id)
                        ejac_part = "음부"
                elif orifice == "anal":
                    ejac_part = "항문"
            if not ejac_part and "fellatio" in state.get("active_toggles", set()):
                ejac_part = "구강"

            # 내부 사정 → 체내 정액 저장 (사정량 동적 계산)
            if ejac_part and ejac_part in ("음부", "항문", "구강"):
                import gender as _gm
                _p_holder = npc_id if _gm.has_anatomy(npc_id, "P") else state["player_id"]
                _ejac_amt = calculate_ejaculation_amount(_p_holder, state["stamina"], state["max_stamina"])
                _apply_internal_semen(npc_id, ejac_part, _ejac_amt)
                # 정액 소모
                try:
                    import semen as semen_mod
                    semen_mod.consume_semen(_p_holder, semen_mod.EJACULATION_COST)
                except ImportError:
                    pass

        # ── 절정/사정 시 양방향 체력 소모 ──
        non_p_parts = climax_info.get("non_p_parts", [])
        has_p = climax_info.get("has_p", False)
        # NPC 절정 → NPC HP 소모
        if non_p_parts:
            npc_exhausted = state.get("npc_exhausted", False)
            cost = calculate_climax_hp_cost(npc_id, npc_exhausted)
            if cost > 0:
                state["npc_stamina"] -= cost
                if state["npc_stamina"] <= 0:
                    state["npc_stamina"] = 1  # 기절 시 HP=1 하한선
                    state["npc_exhausted"] = True
                elif (state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD
                        and not state.get("npc_exhausted")):
                    state["npc_exhausted"] = True
        # 플레이어 사정 (P peaked) → 플레이어 HP 소모
        if has_p:
            player_exhausted = (state.get("exhausted", False)
                                or state.get("stamina", 100) <= EXHAUSTION_HP_THRESHOLD)
            cost = calculate_climax_hp_cost(state["player_id"], player_exhausted)
            if cost > 0:
                state["stamina"] -= cost
                if state["stamina"] <= 0:
                    state["stamina"] = 1  # HP 하한선

        # 절정 반응 텍스트
        npc_asset = get_npc_asset(npc_id)
        if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
            reactions = getattr(npc_asset, 'ROMANCE_REACTIONS', {})
            ejac_reaction = None
            if ejac_part:
                ejac_key = f"ejaculation_internal_{ejac_part}"
                ejac_reaction = npc_asset.get_romance_reaction(ejac_key, "start", stim_state=state.get("stim"))
            ecstasy_key = get_climax_reaction_key(
                climax_info, state["active_toggles"], NPC_TOGGLE_ACTIONS, reactions, state=state)
            reaction = npc_asset.get_romance_reaction(ecstasy_key, "start", stim_state=state.get("stim"))
            if ejac_reaction and reaction:
                return f"{ejac_reaction}\n{reaction}"
            if ejac_reaction:
                return ejac_reaction
            if reaction:
                return reaction
        npc_info = morld.get_unit_info(npc_id)
        npc_name = npc_info.get('name', '상대') if npc_info else '상대'
        return f"{npc_name}(이)가 절정에 달했다."

    return None


# ============================================
# 메인 함수
# ============================================

def start_npc_initiative(player_id, npc_id, preserved=None):
    """
    NPC 주도 스킨십 시작 - Generator 기반

    on_meet 이벤트에서 조건 충족 시 호출됨.
    플레이어도 즉시 행위를 선택할 수 있음.

    Args:
        player_id: 플레이어 유닛 ID
        npc_id: NPC 유닛 ID
        preserved: 공수 전환 시 보존된 상태 (None이면 신규 세션)
    """
    npc_asset = get_npc_asset(npc_id)
    npc_info = morld.get_unit_info(npc_id)
    npc_name = npc_info.get('name', '그녀') if npc_info else '그녀'

    # NPC 동결 (HoldState: FSM + 스케줄 + 이동중 일괄 차단)
    npc_agent = think.get_agent(npc_id)
    schedule_pushed = preserved.get("schedule_pushed", False) if preserved else False
    if not schedule_pushed:
        if npc_agent:
            npc_agent.begin_hold()
        morld.set_unit_prop(npc_id, "상태:로맨스중", 1)

    # 플레이어 체력 조회 (생존:체력 기반)
    import survival
    player_stats = survival.get_survival_stats(player_id)
    initial_stamina = player_stats["health"]
    max_stamina = player_stats["max_health"]

    # NPC 체력 조회
    npc_stats = survival.get_survival_stats(npc_id)
    npc_initial_stamina = npc_stats["health"]
    npc_max_stamina = npc_stats["max_health"]

    # 상태 초기화
    import gender as gender_mod
    npc_prefs = getattr(npc_asset, 'SEXUAL_PREFERENCES', None) if npc_asset else None
    initial_position = position.select_initial_position(
        is_npc_initiative=True, npc_prefs=npc_prefs)
    state = {
        # 핵심 (세션 수명)
        "player_id": player_id,
        "npc_id": npc_id,
        "active_toggles": set(),
        "stamina": initial_stamina,
        "initial_stamina": initial_stamina,
        "max_stamina": max_stamina,
        "npc_stamina": npc_initial_stamina,
        "npc_initial_stamina": npc_initial_stamina,
        "npc_max_stamina": npc_max_stamina,
        "npc_exhausted": False,
        "elapsed_time": 0,
        "lubricated": False,
        "stim": stimulation.create_state(
            male_mode=(gender_mod.get_gender(npc_id) == "male")
        ),
        # 체위
        "position": initial_position,
        # 삽입 상태
        "insertion": {
            "active": False,
            "orifice": None,
            "who": None,
            "failed_count": 0,
        },
        # 삽입 호환 (삽입 시 설정)
        "size_pain": False,
        "size_stim_mod": 1.0,
        # 제3자 추적
        "checked_npcs": set(),
        # NPC 선호
        "npc_prefs": npc_prefs,
        # NPC 주도 전용
        "escape_attempts": 0,
        "escape_result": None,
        "resistance_mode": False,    # 저항 모드 (NPC 강제, 플레이어 저항)
        "resistance_meter": 0,       # 저항 축적 (100 도달 시 탈출)
        # UI 일시적 (렌더링 후 소비)
        "last_reaction": None,
        "near_miss": False,
        "near_miss_id": None,
        "stealth_reaction": None,
        # 종료 조건
        "interrupted": False,
        "interrupter_id": None,
        "npc_satisfied": False,
        "player_escaped": False,
        "exhausted": False,
        "switch_to": None,
    }

    # 신규 세션: 상시 절정 prop → 세션 게이지 동기화
    if not preserved:
        climax_prop = morld.get_unit_prop(npc_id, "상태:절정") or 0
        state["stim"]["climax_gauge"] = climax_prop

    # 전환 시 보존 상태 복원
    if preserved:
        state["stim"] = preserved["stim"]
        state["stamina"] = preserved["stamina"]
        state["initial_stamina"] = preserved.get("initial_stamina", state["stamina"])
        state["max_stamina"] = preserved.get("max_stamina", max_stamina)
        state["elapsed_time"] = preserved["elapsed_time"]
        state["lubricated"] = preserved.get("lubricated", False)
        state["checked_npcs"] = preserved.get("checked_npcs", set())
        if preserved.get("npc_stamina") is not None:
            state["npc_stamina"] = preserved["npc_stamina"]
            state["npc_initial_stamina"] = preserved.get("npc_initial_stamina", state["npc_stamina"])
            state["npc_max_stamina"] = preserved.get("npc_max_stamina", npc_max_stamina)
        if "position" in preserved:
            state["position"] = preserved["position"]
        if "insertion" in preserved:
            state["insertion"] = preserved["insertion"]

    # 시작 반응 (전환 시 생략 — 이미 진행 중)
    if not preserved:
        if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
            state["last_reaction"] = npc_asset.get_initiative_reaction("start")

    # ── 여운 반응 헬퍼 ──────────────────────────────────
    def _get_afterglow_reaction_text():
        """여운 중 행위 시 추가 반응."""
        afterglow = state["stim"].get("afterglow", 0)
        if afterglow <= 0:
            return None
        if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
            if afterglow >= 40:
                key = "afterglow_sensitive"
            elif afterglow >= 20:
                key = "afterglow_trembling"
            else:
                key = "afterglow_fading"
            return npc_asset.get_romance_reaction(
                key, "start", stim_state=state["stim"])
        return None

    def _append_afterglow_text(ecstasy_reaction, afterglow_result):
        """여운 반응/종료 반응을 last_reaction에 추가."""
        if ecstasy_reaction:
            return  # 절정 반응이 우선
        parts = []
        ag_text = _get_afterglow_reaction_text()
        if ag_text:
            parts.append(ag_text)
        if afterglow_result == "ended":
            if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
                end_text = npc_asset.get_romance_reaction(
                    "afterglow_end", "start", stim_state=state["stim"])
                if end_text:
                    parts.append(end_text)
        if parts:
            existing = state.get("last_reaction") or ""
            combined = "\n".join(p for p in parts if p)
            state["last_reaction"] = (
                (existing + "\n" + combined).strip() if existing else combined)

    # NPC 행위 자동 진행 (accept / resist에서 공유)
    def _npc_auto_advance(state, npc_id, player_id, npc_asset, forced_reaction=False):
        """NPC가 랜덤으로 행위를 선택하고 효과 적용

        forced_reaction: True면 forced_ 접두사 반응 사용 (저항 모드)
        state["exhausted"], state["interrupted"] 가 True로 설정될 수 있음.
        """
        # 윤활 상태 업데이트
        check_lubrication(npc_id, state)

        # NPC 결박 시도 (여운 아닐 때, 미결박 상태)
        afterglow = state["stim"].get("afterglow", 0)
        if afterglow <= 0 and not state.get("player_restrained"):
            should_try, r_item, r_msg = check_npc_restrain_trigger(state)
            if should_try:
                import restraint
                success, _ = restraint.attempt_restrain(
                    npc_id, player_id, r_item, mode="forced")
                if success:
                    state["player_restrained"] = True
                    morld.set_unit_prop(npc_id, "NPC주도:결박쿨다운",
                                        morld.get_game_time())
                    state["last_reaction"] = r_msg
                    return
                # 실패 시 쿨다운만 설정 (같은 세션 내 재시도 방지)
                morld.set_unit_prop(npc_id, "NPC주도:결박쿨다운",
                                    morld.get_game_time())

        # 여운 중: NPC는 새 행위를 선택하지 않음 (기존 토글만 유지)
        if afterglow > 0:
            new_action = None
            new_toggle_def = None
        else:
            # NPC 랜덤 행위 선택
            new_action = select_random_npc_action(
                npc_id, player_id, state["active_toggles"],
                lubricated=state["lubricated"],
                cur_position=state.get("position", "missionary"),
                is_inserted=state["insertion"]["active"])

        new_toggle_def = None if afterglow > 0 else (
            NPC_TOGGLE_ACTIONS.get(new_action) if new_action else None)
        if new_action and new_toggle_def:
            _remove_conflicting_toggles(new_action, state["active_toggles"], new_toggle_def)

        # 스태미나 계산
        required_stamina = 0
        if new_toggle_def:
            required_stamina += new_toggle_def["stamina"]
        for tid in state["active_toggles"]:
            td = NPC_TOGGLE_ACTIONS.get(tid)
            if td:
                required_stamina += td["stamina"]
        if required_stamina == 0:
            required_stamina = 1

        # 플레이어 HP 차감 (탈진 상태면 행동 기반 차감 스킵 — 절정에서만 감소)
        if not state.get("exhausted"):
            if state["stamina"] - required_stamina <= EXHAUSTION_HP_THRESHOLD:
                state["exhausted"] = True
            else:
                state["stamina"] -= required_stamina

        # NPC 스태미나 차감 (NPC 주도 → NPC 탈진 시 세션 종료)
        npc_cost = calculate_npc_stamina_cost(required_stamina, npc_id)
        state["npc_stamina"] -= npc_cost
        if state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD:
            state["npc_stamina"] = max(1, state["npc_stamina"])  # HP=1 하한선
            state["npc_exhausted"] = True
            return

        # NPC 자동 삽입 시도 (미삽입 + 성욕 ≥ 70 + 윤활 충족 + 여운 아님)
        if not state["insertion"]["active"] and afterglow <= 0:
            npc_arousal = morld.get_unit_prop(npc_id, "상태:성욕") or 0
            if npc_arousal >= 70 and state["lubricated"]:
                import gender as gender_mod
                # NPC가 P 보유 → 질/항문 삽입 시도
                if gender_mod.has_anatomy(npc_id, "P"):
                    orifice = "vaginal"
                    if gender_mod.has_anatomy(player_id, "V"):
                        orifice = "vaginal"
                    elif gender_mod.has_anatomy(player_id, "A"):
                        orifice = "anal"
                    else:
                        orifice = None
                    # 월경 중 질삽입 차단
                    if orifice == "vaginal":
                        import pregnancy as _preg_npc
                        if _preg_npc.is_menstruating(player_id):
                            orifice = None
                    if orifice:
                        state["insertion"]["active"] = True
                        state["insertion"]["orifice"] = orifice
                        state["insertion"]["who"] = "npc"
                        # 크기 호환성 체크
                        compat = gender_mod.check_penetration_compatibility(npc_id, player_id)
                        state["size_pain"] = compat["pain"]
                        state["size_stim_mod"] = compat["stim_mod"]
                        if compat["pain"]:
                            rebellion_key = get_rebellion_key(player_id)
                            morld.modify_prop(npc_id, rebellion_key, 3)
                            morld.set_unit_prop(npc_id, "크기통증", 1)
                        # 자동으로 thrust_normal 시작
                        if new_action not in _THRUST_TOGGLE_IDS:
                            state["active_toggles"].add("thrust_normal")
                        # 처녀 체크
                        insert_action = "vaginal_insert" if orifice == "vaginal" else "anal_insert"
                        check_and_clear_virginity(npc_id, player_id, insert_action)

        # 새 액션 처리
        first_key = None
        if new_action and new_toggle_def:
            state["active_toggles"].add(new_action)
            first_key = check_and_clear_virginity(npc_id, player_id, new_action)

        # 효과 적용
        ecstasy_reaction = None
        for tid in state["active_toggles"]:
            td = NPC_TOGGLE_ACTIONS.get(tid)
            if td:
                result = apply_action_effects(state, td)
                if result and not ecstasy_reaction:
                    ecstasy_reaction = result

        # NPC 주도 개편 Slice P2: 행위 턴마다 지배 상승
        # 저항 모드 (NPC 강제) = +2 (강제로 당함), 수용 모드 = +1
        if state["active_toggles"]:
            from romance_core import modify_dominance as _modify_dom
            _dom_gain = 2 if state.get("resistance_mode") else 1
            _modify_dom(npc_id, player_id, _dom_gain)

        afterglow_result = stimulation.tick_afterglow(state["stim"])

        # NPC 만족 체크 (절정 후 성욕 감소 → 임계치 미만)
        stim_state = state["stim"]
        npc_arousal = morld.get_unit_prop(npc_id, "상태:성욕") or 0
        if (stim_state["climax_total"] >= NPC_SATISFACTION_CLIMAX
                and npc_arousal < NPC_SATISFACTION_AROUSAL):
            state["npc_satisfied"] = True
            return

        # 소음 (저항 모드에서도 소음 방출)
        if ecstasy_reaction:
            emit_ecstasy_sound(npc_id)
        else:
            emit_romance_sound(npc_id)

        # 시간 경과 + 제3자 감지
        time_elapsed = 5 * MILLIS_PER_MINUTE
        first_toggle = next(iter(state["active_toggles"]), None)
        if first_toggle:
            td = NPC_TOGGLE_ACTIONS.get(first_toggle)
            if td:
                time_elapsed = td.get("time", 5 * MILLIS_PER_MINUTE)

        check_result = advance_time_and_check_npc_initiative(state, time_elapsed)
        if check_result["interrupted"]:
            state["interrupted"] = True
            state["interrupter_id"] = check_result["interrupter_id"]
            return

        # 반응 텍스트 (묘사 + 대사 결합)
        from romance_actions import ACTION_DESCRIPTIONS
        if ecstasy_reaction:
            if new_action:
                desc = ACTION_DESCRIPTIONS.get(new_action, "")
                if desc:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]\n{ecstasy_reaction}"
                else:
                    state["last_reaction"] = ecstasy_reaction
            else:
                state["last_reaction"] = ecstasy_reaction
        elif new_action:
            desc = ACTION_DESCRIPTIONS.get(new_action, "")
            reaction = None
            if first_key and npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
                reaction = npc_asset.get_romance_reaction(first_key, "start", stim_state=state.get("stim"))
            if not reaction:
                timing = f"during_{new_action}"
                if forced_reaction and npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(f"forced_{timing}")
                if not reaction and npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(timing)
            if desc and reaction:
                state["last_reaction"] = f"[color=silver]{desc}[/color]\n[color=yellow]{reaction}[/color]"
            elif desc:
                state["last_reaction"] = f"[color=silver]{desc}[/color]"
            elif reaction:
                state["last_reaction"] = f"[color=yellow]{reaction}[/color]"
        elif state["active_toggles"]:
            for tid in state["active_toggles"]:
                timing = f"during_{tid}"
                reaction = None
                if forced_reaction and npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(f"forced_{timing}")
                if not reaction and npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(timing)
                if reaction:
                    state["last_reaction"] = f"[color=yellow]{reaction}[/color]"
                    break

        # 여운 반응 추가 (절정 미발생 시)
        _append_afterglow_text(ecstasy_reaction, afterglow_result)

    # proc 콜백
    def proc(action):
        if action == "init":
            return render_npc_initiative_ui(state)

        # 빠져나가기 시도
        if action == "escape":
            state["escape_attempts"] += 1
            state["escape_result"] = None

            if attempt_escape(player_id, npc_id):
                # 지배 -5 (주도권 역전 소폭)
                from romance_core import modify_dominance as _modify_dom
                _modify_dom(npc_id, player_id, -5)
                state["player_escaped"] = True
                return True  # 다이얼로그 종료

            # 실패 반응
            if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                fail_text = npc_asset.get_initiative_reaction("escape_fail")
                if fail_text:
                    state["escape_result"] = fail_text
                else:
                    state["escape_result"] = "빠져나가지 못했다."
            else:
                state["escape_result"] = "빠져나가지 못했다."

            return render_npc_initiative_ui(state)

        # 결박 해제 시도
        if action == "escape_restraint":
            state["escape_result"] = None
            import restraint
            success = restraint.attempt_self_escape(player_id)
            if success:
                # 아직 결박 남아있는지 확인
                if not restraint.is_any_restrained(player_id):
                    state["player_restrained"] = False
                    state["last_reaction"] = "(결박에서 빠져나왔다!)"
                else:
                    state["last_reaction"] = "(결박 일부를 풀었다.)"
            else:
                state["last_reaction"] = "(결박을 풀지 못했다...)"
            # NPC는 계속 행위 (시간 경과)
            _npc_auto_advance(state, npc_id, player_id, npc_asset)
            if state["exhausted"] or state["interrupted"] or state["npc_satisfied"]:
                return True
            return render_npc_initiative_ui(state)

        # 저항 모드 진입
        if action == "resist_start":
            state["resistance_mode"] = True
            state["resistance_meter"] = 0
            state["escape_result"] = None
            state["last_reaction"] = "(저항하기 시작했다.)"
            return render_npc_initiative_ui(state)

        # 저항 (저항 모드 중)
        if action == "resist":
            state["escape_result"] = None

            # 저항 축적
            gain = calculate_resistance_gain(player_id, npc_id)
            state["resistance_meter"] += gain

            if state["resistance_meter"] >= RESISTANCE_MAX:
                # 탈출 성공 — 지배 -10 (주도권 큰 반전)
                from romance_core import modify_dominance as _modify_dom
                _modify_dom(npc_id, player_id, -10)
                state["player_escaped"] = True
                return True

            # NPC는 계속 행위 (accept와 동일한 NPC 행위 흐름)
            _npc_auto_advance(state, npc_id, player_id, npc_asset, forced_reaction=True)
            if state["exhausted"] or state["interrupted"] or state["npc_satisfied"]:
                return True

            state["last_reaction"] = f"(필사적으로 저항하고 있다... [{state['resistance_meter']}/{RESISTANCE_MAX}])"
            return render_npc_initiative_ui(state)

        # 포기 (저항 모드 → 합의로 전환)
        if action == "surrender":
            state["resistance_mode"] = False
            state["resistance_meter"] = 0
            # 지배 +3 (체념·받아들임, 주도권 NPC 쪽으로 확정)
            from romance_core import modify_dominance as _modify_dom
            _modify_dom(npc_id, player_id, 3)
            state["last_reaction"] = "(저항을 포기했다...)"
            return render_npc_initiative_ui(state)

        # Slice P4: 합의 제안 — 관계 기반 평화 전환
        if action == "suggest_consent":
            from romance_core import (
                calculate_consent_success_chance,
                modify_dominance as _modify_dom,
                modify_submission_mutex as _modify_sub,
            )
            chance = calculate_consent_success_chance(npc_id, player_id)
            if chance <= 0.0:
                # 차단 (지배가 너무 높음) — 시도 자체가 부작용
                _modify_dom(npc_id, player_id, 2)
                state["last_reaction"] = (
                    "(합의를 제안해봤지만, NPC는 당신의 말을 듣지 않는다...)"
                )
                return render_npc_initiative_ui(state)
            if random.random() < chance:
                # 성공 — 합의 분위기 전환
                state["resistance_mode"] = False
                state["resistance_meter"] = 0
                _modify_dom(npc_id, player_id, -10)  # 역전 경로
                _modify_sub(npc_id, player_id, 5)    # NPC 자발 협력
                state["last_reaction"] = (
                    f"(호흡을 맞추기 시작했다. 분위기가 부드러워진다.)"
                )
            else:
                # 실패 — 지배 + 3 페널티
                _modify_dom(npc_id, player_id, 3)
                state["last_reaction"] = (
                    "(제안이 거부됐다. NPC는 아랑곳하지 않는다.)"
                )
            return render_npc_initiative_ui(state)

        # 플레이어 즉시 행위
        if action.startswith("instant:"):
            action_id = action.split(":")[1]
            action_def = PLAYER_INSTANT_ACTIONS.get(action_id)
            if not action_def:
                return None

            state["escape_result"] = None

            # NPC 주도 전용 행위 필터 (beg: NPC 주도에서만)
            if action_def.get("npc_initiative_only"):
                pass  # NPC 주도 모드이므로 허용

            # NPC 차단 판정 (능동 행위)
            blocked, block_reaction = _check_npc_block(
                player_id, npc_id, action_def, state)
            if blocked:
                state["last_reaction"] = block_reaction
                state["stamina"] = max(0, state["stamina"] - 1)
                check_result = advance_time_and_check_npc_initiative(
                    state, 2 * MILLIS_PER_MINUTE)
                if check_result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = check_result["interrupter_id"]
                    return True
                return render_npc_initiative_ui(state)

            # beg 전용 처리
            if action_id == "beg":
                morld.modify_prop(npc_id, "상태:성욕", 5)
                state["beg_boost"] = state.get("beg_boost", 0) + 1
                reaction = None
                if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
                    reaction = npc_asset.get_romance_reaction(
                        "beg", "start", stim_state=state.get("stim"))
                if not reaction:
                    reaction = "(애원했다...)"
                state["last_reaction"] = reaction
                check_result = advance_time_and_check_npc_initiative(
                    state, action_def["time"])
                if check_result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = check_result["interrupter_id"]
                    return True
                return render_npc_initiative_ui(state)

            # 삽입 상태 필요 즉시형: 유효성 + exp_part 동적 오버라이드
            if action_def.get("requires_active_insertion"):
                if not state["insertion"]["active"]:
                    return render_npc_initiative_ui(state)
                if action_def.get("exp_part") is None:
                    orifice = state["insertion"]["orifice"]
                    exp_part = _INSERTION_EXP_MAP.get(orifice)
                    if exp_part:
                        action_def = dict(action_def)
                        action_def["exp_part"] = exp_part
                        if orifice == "vaginal":
                            action_def["pregnancy_check"] = True

            # 체내 정액 필요 행위 유효성 검증
            req_internal = action_def.get("requires_internal_semen")
            if req_internal:
                if get_internal_semen(npc_id, req_internal) <= 0:
                    return render_npc_initiative_ui(state)
                # 삼키기: M 감각 레벨에 따라 분기
                if action_id == "swallow_semen":
                    m_level = get_sensation_level(npc_id, "M")
                    semen_amount = get_internal_semen(npc_id, req_internal)
                    if m_level >= SWALLOW_M_THRESHOLD:
                        morld.clear_prop(npc_id, f"체내:정액:{req_internal}")
                    elif m_level >= 3:
                        morld.clear_prop(npc_id, f"체내:정액:{req_internal}")
                        spit_amount = semen_amount // 2
                        if spit_amount > 0:
                            ext = morld.get_unit_prop(npc_id, "오염물:정액:가슴") or 0
                            morld.set_unit_prop(npc_id, "오염물:정액:가슴",
                                                min(100, ext + spit_amount))
                        action_id = "swallow_semen_spit"
                    elif m_level >= 1:
                        half = semen_amount // 2
                        morld.set_unit_prop(npc_id, f"체내:정액:{req_internal}",
                                            max(0, semen_amount - half))
                        ext = morld.get_unit_prop(npc_id, "오염물:정액:가슴") or 0
                        morld.set_unit_prop(npc_id, "오염물:정액:가슴",
                                            min(100, ext + half))
                        action_id = "swallow_semen_drip"
                    else:
                        rebellion_key = get_rebellion_key(player_id)
                        morld.modify_prop(npc_id, rebellion_key, 2)
                        action_id = "swallow_semen_vomit"

            # 탈의 전용 처리
            if action_def.get("undress"):
                npc_id = state["npc_id"]
                is_upper = action_def["undress"] == "upper"
                item_id = get_next_undress_item(npc_id, upper=is_upper)
                if item_id is None:
                    return render_npc_initiative_ui(state)
                required_stamina = action_def["stamina"]
                for tid in state["active_toggles"]:
                    td = NPC_TOGGLE_ACTIONS.get(tid)
                    if td:
                        required_stamina += td["stamina"]
                # 플레이어 HP 차감 (탈진이면 스킵)
                if not state.get("exhausted"):
                    if state["stamina"] - required_stamina <= EXHAUSTION_HP_THRESHOLD:
                        state["exhausted"] = True
                        return True
                    state["stamina"] -= required_stamina
                npc_cost = calculate_npc_stamina_cost(required_stamina, state["npc_id"])
                state["npc_stamina"] -= npc_cost
                if state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD:
                    state["npc_stamina"] = max(1, state["npc_stamina"])
                    state["npc_exhausted"] = True
                    return True
                perform_undress(npc_id, item_id)
                item_info = morld.get_item_info(item_id)
                item_name = item_info.get("name", "옷") if item_info else "옷"
                npc_info = morld.get_unit_info(npc_id)
                n_name = npc_info.get("name", "상대") if npc_info else "상대"
                state["last_reaction"] = f"{n_name}의 {item_name}을(를) 벗겼다."
                # NPC 턴 처리 (활성 토글 효과)
                for tid in state["active_toggles"]:
                    td = NPC_TOGGLE_ACTIONS.get(tid)
                    if td:
                        apply_action_effects(state, td)
                stimulation.tick_afterglow(state["stim"])
                # 시간 경과 + 제3자 감지
                check_result = advance_time_and_check_npc_initiative(state, action_def["time"])
                if check_result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = check_result["interrupter_id"]
                    return True
                return render_npc_initiative_ui(state)

            # 참기 특수 처리 (확률 기반 + 감쇠형)
            if action_id == "hold_back":
                stim_state = state["stim"]
                hb_result = stimulation.hold_back(stim_state)
                state["stamina"] = max(0, state["stamina"] - action_def["stamina"])
                npc_asset = get_npc_asset(npc_id)
                if hb_result["success"]:
                    reaction = None
                    if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
                        reaction = npc_asset.get_romance_reaction("hold_back_success", "start", stim_state=state.get("stim"))
                    state["last_reaction"] = reaction or f"(이를 악물고 참았다... -{hb_result['reduction']})"
                else:
                    reaction = None
                    if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
                        reaction = npc_asset.get_romance_reaction("hold_back_failure", "start", stim_state=state.get("stim"))
                    state["last_reaction"] = reaction or "(참으려 했지만 실패했다...!)"
                    # 실패 + 게이지 만충 + peaked 존재 → 즉시 절정
                    if hb_result["gauge"] >= stimulation.CLIMAX_GAUGE_MAX:
                        if stimulation.get_peaked_count(stim_state) > 0:
                            climax_info = stimulation.force_climax(stim_state)
                            if climax_info and climax_info.get("has_p"):
                                ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"], state["max_stamina"])
                                insertion = state["insertion"]
                                ejac_part = None
                                if insertion.get("active"):
                                    orifice = insertion.get("orifice")
                                    ejac_part = _INSERTION_EXP_MAP.get(orifice)
                                if not ejac_part and "fellatio" in state["active_toggles"]:
                                    ejac_part = "구강"
                                if ejac_part and ejac_part in ("음부", "항문", "구강"):
                                    _apply_internal_semen(npc_id, ejac_part, ejac_amount)
                                    if insertion.get("active") and insertion.get("orifice") == "vaginal":
                                        try:
                                            import pregnancy
                                            pregnancy.check_conception(player_id, npc_id)
                                        except ImportError:
                                            pass
                                elif ejac_part:
                                    _apply_semen(npc_id, ejac_part, ejac_amount)
                            # 참기 실패 절정 → 체력 소모
                            if climax_info:
                                _apply_climax_hp_cost_npc(state, climax_info)
                check_result = advance_time_and_check_npc_initiative(state, action_def["time"])
                if check_result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = check_result["interrupter_id"]
                    return True
                return render_npc_initiative_ui(state)

            # 사정하기 특수 처리
            if action_id == "ejaculate":
                stim_state = state["stim"]
                climax_info = stimulation.force_ejaculate(stim_state)
                if climax_info and climax_info.get("has_p"):
                    # 정액 소모
                    try:
                        import semen as semen_mod
                        semen_mod.consume_semen(player_id, semen_mod.EJACULATION_COST)
                    except ImportError:
                        pass
                    ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"], state["max_stamina"])
                    insertion = state["insertion"]
                    ejac_part = None
                    if insertion.get("active"):
                        orifice = insertion.get("orifice")
                        ejac_part = _INSERTION_EXP_MAP.get(orifice)
                    if not ejac_part and "fellatio" in state["active_toggles"]:
                        ejac_part = "구강"
                    # 허리흔들기 토글 해제 (삽입 상태 유지)
                    for tid in list(state["active_toggles"]):
                        if tid in _THRUST_TOGGLE_IDS:
                            state["active_toggles"].discard(tid)
                    if ejac_part and ejac_part in ("음부", "항문", "구강"):
                        _apply_internal_semen(npc_id, ejac_part, ejac_amount)
                        if insertion.get("active") and insertion.get("orifice") == "vaginal":
                            try:
                                import pregnancy
                                pregnancy.check_conception(player_id, npc_id)
                            except ImportError:
                                pass
                        morld.set_unit_prop(npc_id, "경험:사정횟수",
                                            (morld.get_unit_prop(npc_id, "경험:사정횟수") or 0) + 1)
                        morld.set_unit_prop(player_id, "통계:총사정량",
                                            (morld.get_unit_prop(player_id, "통계:총사정량") or 0) + ejac_amount)
                    elif ejac_part:
                        _apply_semen(npc_id, ejac_part, ejac_amount)
                    state["last_reaction"] = "사정했다."
                    emit_ecstasy_sound(npc_id)
                # 사정/절정 → 체력 소모
                if climax_info:
                    _apply_climax_hp_cost_npc(state, climax_info)
                check_result = advance_time_and_check_npc_initiative(state, action_def["time"])
                if check_result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = check_result["interrupter_id"]
                    return True
                return render_npc_initiative_ui(state)

            # 충돌 처리: 같은 신체 부위를 사용하는 토글 비활성화
            removed_toggles = _remove_conflicting_toggles(action_id, state["active_toggles"], action_def)

            # 스태미나 체크 (충돌로 제거된 토글은 제외)
            required_stamina = action_def["stamina"]

            # 활성 토글들의 스태미나도 합산
            for toggle_id in state["active_toggles"]:
                toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
                if toggle_def:
                    required_stamina += toggle_def["stamina"]

            # 플레이어 HP 차감 (탈진이면 스킵)
            if not state.get("exhausted"):
                if state["stamina"] - required_stamina <= EXHAUSTION_HP_THRESHOLD:
                    state["exhausted"] = True
                    return True  # 스태미나 부족으로 종료
                state["stamina"] -= required_stamina

            # NPC 스태미나 소모
            npc_cost = calculate_npc_stamina_cost(required_stamina, state["npc_id"])
            state["npc_stamina"] -= npc_cost
            if state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD:
                state["npc_stamina"] = max(1, state["npc_stamina"])
                state["npc_exhausted"] = True
                return True

            # 준비 부족 체크 (강도 행위)
            effective_def = action_def
            if not check_preparation(state["stim"], action_def):
                effective_def = dict(action_def)
                effective_def["effects"] = {
                    k: round(v * UNPREPARED_EFFECT_MULT)
                    for k, v in action_def["effects"].items()
                }
                effective_def["exp_part"] = None
                rebellion_key = get_rebellion_key(player_id)
                morld.modify_prop(state["npc_id"], rebellion_key, UNPREPARED_REBELLION)

            # 효과 적용 (플레이어 즉시 행위)
            ecstasy_reaction = apply_action_effects(state, effective_def)

            # 활성 토글들의 효과도 적용 (충돌로 제거된 토글은 제외됨)
            for toggle_id in state["active_toggles"]:
                toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
                if toggle_def:
                    ecstasy_result = apply_action_effects(state, toggle_def)
                    if ecstasy_result and not ecstasy_reaction:
                        ecstasy_reaction = ecstasy_result

            # 여운 감소 (턴당 1회)
            afterglow_result = stimulation.tick_afterglow(state["stim"])

            # 소음 발생
            npc_id = state["npc_id"]
            if ecstasy_reaction:
                emit_ecstasy_sound(npc_id)
            else:
                emit_romance_sound(npc_id)

            # 시간 경과 + 제3자 감지 체크
            total_time = action_def["time"]
            check_result = advance_time_and_check_npc_initiative(state, total_time)

            # 제3자에게 들킴 - 중단
            if check_result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = check_result["interrupter_id"]
                return True

            # 절정 발생 시 반응 표시 (종료하지 않음 - 플레이어 체력 소진 또는 탈출 성공까지 계속)
            if ecstasy_reaction:
                state["last_reaction"] = ecstasy_reaction
            else:
                # 반응 텍스트
                if npc_asset and hasattr(npc_asset, 'get_romance_reaction'):
                    reaction = npc_asset.get_romance_reaction(action_id, "start", stim_state=state.get("stim"))
                    if reaction:
                        state["last_reaction"] = reaction

            # 여운 반응 추가 (절정 미발생 시)
            _append_afterglow_text(ecstasy_reaction, afterglow_result)

            return render_npc_initiative_ui(state)

        # 받아들이기 - NPC가 랜덤으로 행위 선택
        if action == "accept":
            state["escape_result"] = None
            _npc_auto_advance(state, npc_id, player_id, npc_asset)
            if state["exhausted"] or state["interrupted"] or state["npc_satisfied"]:
                return True
            return render_npc_initiative_ui(state)

        # 공수 전환 (NPC → 플레이어 주도) — Slice P3: 지배 기반 조건화
        if action == "switch":
            from romance_core import (
                calculate_switch_takeover_chance,
                modify_dominance as _modify_dom,
            )
            chance = calculate_switch_takeover_chance(npc_id, player_id)
            if chance <= 0.0:
                # 완전 차단 — NPC가 주도권을 놓지 않음
                state["last_reaction"] = (
                    "(주도권을 되찾으려 했지만, 당신은 이미 너무 깊이 끌려들어와 있다...)"
                )
                # 시도 자체가 지배를 더 강화
                _modify_dom(npc_id, player_id, 3)
                return render_npc_initiative_ui(state)
            if random.random() >= chance:
                # 확률 실패 — 저항 실패 페널티
                state["last_reaction"] = (
                    f"(전환을 시도했지만 NPC가 놓아주지 않는다...)"
                )
                _modify_dom(npc_id, player_id, 2)
                return render_npc_initiative_ui(state)
            # 성공 — 플레이어 주도로 전환
            state["switch_to"] = "player"
            return True

        # 강제 종료 (디버그용)
        if action == "exit":
            state["player_escaped"] = True
            return True

        return None

    # 다이얼로그 시작
    yield ui.dialog(
        render_npc_initiative_ui(state),
        autofill="off",
        proc=proc,
        result=state
    )

    # 공수 전환 — 플레이어 주도로 전환
    if state["switch_to"] == "player":
        preserved = extract_preserved(state)
        from romance import start_romance
        yield from start_romance(player_id, npc_id, preserved=preserved)
        return

    # 로맨스 세션 종료 — think() 가드 해제
    morld.clear_prop(npc_id, "상태:로맨스중")

    # 결박 해제 (NPC 성욕 < 30 → 자동 해제)
    if state.get("player_restrained"):
        npc_arousal_final = morld.get_unit_prop(npc_id, "상태:성욕") or 0
        if npc_arousal_final < 30:
            import restraint
            restraint.release_unit(player_id)
            state["player_restrained"] = False

    # 종료 처리 — 양쪽 체력 기록 (HP 연동, 최소 1 보장)
    survival.set_health(player_id, max(1, state["stamina"]))
    survival.set_health(npc_id, max(1, state["npc_stamina"]))

    # 종료 처리 — 절정 게이지 → 상시 prop 동기화
    final_climax = state["stim"].get("climax_gauge", 0)
    morld.set_unit_prop(npc_id, "상태:절정", max(0, min(100, final_climax)))

    # 조건부 쿨다운: 체력 변동이 있었으면(행위 발생) 쿨다운 적용
    if state["stamina"] < state["initial_stamina"]:
        if npc_asset:
            npc_asset.mark_initiative_cooldown()

    # 착의 쿨다운 리셋 (탈의 후 즉시 착의 인터럽트 발동)
    if npc_agent:
        npc_agent._memory["clothing_last_attempt"] = None
        # 애정 행위 기억 저장
        loc = morld.get_unit_location(npc_id)
        npc_agent._memory["romance_last"] = {
            "partner_id": player_id,
            "region_id": loc[0] if loc else None,
            "location_id": loc[1] if loc else None,
            "timestamp": morld.get_game_time(),
            "mode": "consensual",
        }
        # 마지막 경험 기록
        from romance_core import record_last_experience
        record_last_experience(npc_id, player_id, "consensual")
        npc_agent.end_hold()

    # 종료 반응
    if state["player_escaped"]:
        yield ui.dialog(f"{npc_name}(으)로부터 벗어났다.")
    elif state.get("interrupted"):
        # 제3자에게 들킴 - 방해 이벤트
        yield from handle_npc_initiative_interruption(state, npc_name)
    elif state.get("npc_exhausted"):
        yield ui.dialog(f"({npc_name}(이)가 탈진하여 쓰러졌다...)")
    elif state["exhausted"]:
        yield ui.dialog("몸에 힘이 빠져 더 이상 움직일 수 없다...")
    elif state["npc_satisfied"]:
        satisfied_text = None
        if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
            satisfied_text = npc_asset.get_initiative_reaction("satisfied")

        if satisfied_text:
            yield ui.dialog(satisfied_text)
        else:
            yield ui.dialog(f"{npc_name}(이)가 만족한 듯 물러난다.")


