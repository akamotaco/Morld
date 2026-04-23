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
import position
import ui
from ui_style import style_highlight, style_danger
from romance_actions import (
    MILLIS_PER_MINUTE, SEMEN_PARTS,
    INTERNAL_SEMEN_PARTS,  # noqa: F401 — re-export (needs.py)
    UNPREPARED_EFFECT_MULT, UNPREPARED_REBELLION,
    SUBMISSION_ACTION_THRESHOLD, SUBMISSION_ACTION_GAIN, SUBMISSION_MAX,
    ROMANCE_ENTRY_THRESHOLD, ROMANCE_JOIN_THRESHOLD,
    DES_LABEL_THRESHOLD,
    LUBRICATION_THRESHOLD, SWALLOW_M_THRESHOLD,
    SENSATION_MAP,
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    _THRUST_TOGGLE_IDS, _INSERTION_INSTANT_IDS, _INSERTION_EXP_MAP,
    ACTION_DESCRIPTIONS,
)
from romance_ui import render_romance_ui, render_stamina_bar  # noqa: F401
from romance_mode import (
    MODE_CONSENSUAL, MODE_FORCED, MODE_UNCONSCIOUS, MODE_FROZEN,
    create_mode_context, get_effect_multipliers, get_reaction_prefix,
    should_advance_time, should_emit_sound, should_check_third_party,
    can_switch_initiative, check_resistance, check_wakeup,
    transition_to_forced, get_silent_narration, get_silent_climax_narration,
    apply_forced_end_penalty, apply_unconscious_end_state,
    apply_deferred_effects, defer_effect, defer_semen,
    calculate_escape_chance, get_escape_attempt_message,
)
# 공유 핵심 로직: romance_core.py에서 import (+ 외부 모듈 호환 re-export)
from romance_core import (  # noqa: F401 — re-export for external callers
    get_character_asset as get_partner_asset,
    _get_relationship_key, get_affection_key,
    get_rebellion_key, get_submission_key,
    get_effective_affection_req,
    get_sensation_level,
    is_action_available, is_lust_unlocked, is_anatomy_compatible,
    calculate_effects,
    get_exposure_state, get_next_undress_item, perform_undress,
    get_next_loot_item, perform_loot,
    get_semen_total, _apply_semen, clear_all_semen,
    get_internal_semen, get_internal_semen_total,
    _apply_internal_semen, clear_all_internal_semen,
    calculate_ejaculation_amount,
    _has_active_penetration,
    _has_active_intercourse_from_state, get_insertion_exp_part,
    get_action_exp_part, get_conflicting_toggles, _remove_conflicting_toggles,
    check_and_clear_virginity,
    record_last_experience,
    is_hold_back_available, is_ejaculate_available, is_pull_out_available,
    check_preparation, check_lubrication,
    calculate_stealth_chance, check_stealth_success,
    get_excitement_level, emit_romance_sound, emit_ecstasy_sound,
    get_climax_reaction_key,
    extract_preserved,
    calculate_npc_stamina_cost,
    calculate_climax_hp_cost,
)

from survival import EXHAUSTION_HP_THRESHOLD
ROMANCE_MIN_HEALTH = EXHAUSTION_HP_THRESHOLD  # 탈진 임계치와 통일

# NPC 선호 체위 요구 대사 훅
POSITION_REQUEST_AROUSAL = 70           # NPC 성욕 임계
POSITION_REQUEST_COOLDOWN_MS = 5 * MILLIS_PER_MINUTE  # 요구 쿨다운
POSITION_REQUEST_CHANCE = 0.3           # 매 체크마다 발동 확률

# NPC 삽입 요구 대사 훅 (삽입 없는 상태 + 트랜스)
INSERTION_REQUEST_COOLDOWN_MS = 5 * MILLIS_PER_MINUTE
INSERTION_REQUEST_CHANCE = 0.25

# 트랜스 상태 공통 fallback 대사 풀 (캐릭터 전용 trance 대사 없을 때 사용)
_GENERIC_TRANCE = [
    "...하아... 아... 응...",
    "...헉... 하아...",
    "...응아... 흐응...",
    "...아으... 하읏...",
]
_GENERIC_TRANCE_DEEP = [
    "...아우... 으아...",
    "...히잉... 아앙...",
    "...우우... 아으...",
    "...으흐... 헤에...",
    "...아... 아앙... 우...",
]

# NPC 자율 행위 루프 (Phase 1.6 — 봉사/자위 번갈아 수행)
AUTONOMY_ENTRY_AROUSAL = 80             # 진입 성욕 임계
AUTONOMY_EXIT_AROUSAL = 60              # 성욕 하락 시 종료 임계
AUTONOMY_MIN_AFFECTION = 70             # 순애 경로 진입 호감 임계
AUTONOMY_MIN_SUBMISSION = 60            # 함락 경로 진입 복종 임계
AUTONOMY_COOLDOWN_MS = 5 * MILLIS_PER_MINUTE
AUTONOMY_ENTRY_CHANCE = 0.35            # 조건 충족 시 매 턴 진입 시도 확률
AUTONOMY_MIN_DURATION = 3               # 한 행위 최소 지속 턴
AUTONOMY_MAX_DURATION = 5               # 한 행위 최대 지속 턴
AUTONOMY_MAX_TURNS = 20                 # 세션 누적 최대 턴 (무한 루프 방지)

# 자율 행위 카탈로그 (Phase 1.6 — 봉사 2 + 자위 5 + 휴식)
# kind: "service" (봉사, 파트너 대상) / "self" (자위, 자기 대상) / "rest" (휴식)
# self 행위의 part: 가중치 계산용 부위 태그 (B/M/A/V/C)
# self 행위의 access: "upper" (상체 노출) / "lower" (하체 노출)
# self 행위의 anatomy: has_anatomy 체크 카테고리
_NPC_AUTONOMY_CATALOG = {
    "fellatio": {
        "kind": "service",
        "effects": {"성욕": 8, "욕망": 4},
        "exp_part": "음경",
        "desc": "입으로 감싸고 있다.",
    },
    "penis_rub": {
        "kind": "service",
        "effects": {"성욕": 7, "욕망": 4},
        "exp_part": "음경",
        "desc": "손으로 문지르고 있다.",
    },
    "self_breast": {
        "kind": "self",
        "part": "B",
        "anatomy": "B",
        "access": "upper",
        "effects": {"성욕": 5, "욕망": 3},
        "desc": "자기 가슴을 만지고 있다.",
    },
    "self_nipple": {
        "kind": "self",
        "part": "B",
        "anatomy": "B",
        "access": "upper",
        "effects": {"성욕": 6, "욕망": 3},
        "desc": "자기 유두를 자극하고 있다.",
    },
    "self_clit": {
        "kind": "self",
        "part": "C",
        "anatomy": "C",
        "access": "lower",
        "effects": {"성욕": 7, "욕망": 4},
        "desc": "스스로 클리토리스를 자극하고 있다.",
    },
    "self_vaginal": {
        "kind": "self",
        "part": "V",
        "anatomy": "V",
        "access": "lower",
        "effects": {"성욕": 7, "욕망": 4},
        "desc": "손가락을 자기 질에 삽입하고 있다.",
    },
    "self_anal": {
        "kind": "self",
        "part": "A",
        "anatomy": "A",
        "access": "lower",
        "effects": {"성욕": 6, "욕망": 3},
        "desc": "손가락을 자기 항문에 삽입하고 있다.",
    },
    "rest": {
        "kind": "rest",
        "effects": {},
        "desc": "숨을 고르고 있다.",
    },
}


# ============================================
# 자율 루프 유틸 (모듈 수준 — closure에서 호출 + 테스트 가능)
# ============================================

def _autonomy_check_guard(state, action_id):
    """자율 행위 실행 가능 여부.

    service: 플레이어 하체 노출 + (fellatio만) 체위 facing≠back
    self:    NPC 팔 자유 + 해부학 보유 + 본인 부위 노출
    rest:    항상 가능
    """
    entry = _NPC_AUTONOMY_CATALOG.get(action_id)
    if not entry:
        return False
    kind = entry["kind"]
    if kind == "rest":
        return True
    from romance_core import get_exposure_state as _get_exp
    if kind == "service":
        player_exp = _get_exp(state["player_id"])
        if not player_exp.get("lower_exposed"):
            return False
        if action_id == "fellatio":
            pos_info = position.get_position_info(state.get("position"))
            if pos_info and pos_info.get("facing") == "back":
                return False
        return True
    if kind == "self":
        import restraint
        import gender
        pid = state["partner_id"]
        if restraint.is_upper_restrained(pid):
            return False
        anatomy = entry.get("anatomy")
        if anatomy and not gender.has_anatomy(pid, anatomy):
            return False
        access = entry.get("access")
        npc_exp = _get_exp(pid)
        if access == "upper" and not npc_exp.get("upper_exposed"):
            return False
        if access == "lower" and not npc_exp.get("lower_exposed"):
            return False
        return True
    return True


def _autonomy_compute_weight(state, action_id):
    """행위 선택 가중치.

    - rest: 성욕 반비례 (100→0.1, 80→0.4, 60→0.8)
    - service: 고정 1.0
    - self: 1.0 × (preferred_parts면 ×2) × (sensation_level≥3이면 ×1.5)
    """
    entry = _NPC_AUTONOMY_CATALOG.get(action_id, {})
    kind = entry.get("kind")
    if kind == "rest":
        arousal = morld.get_unit_prop(state["partner_id"], "상태:성욕") or 0
        return max(0.1, (100 - arousal) * 0.02)
    if kind == "service":
        return 1.0
    if kind == "self":
        base = 1.0
        part = entry.get("part")
        if part:
            pid = state["partner_id"]
            prefs = state.get("npc_prefs") or {}
            preferred = prefs.get("preferred_parts") or []
            if part in preferred:
                base *= 2.0
            try:
                from romance_core import get_sensation_level as _get_sl
                if _get_sl(pid, part) >= 3:
                    base *= 1.5
            except Exception:
                pass
        return base
    return 1.0


def _autonomy_available(state):
    """가드 통과한 행위 목록."""
    return [aid for aid in _NPC_AUTONOMY_CATALOG
            if _autonomy_check_guard(state, aid)]


def _autonomy_pick(state, pool, exclude=None):
    """가중치 기반 랜덤 선택. exclude는 직전 행위 (연속 회피)."""
    import random as _random
    candidates = [a for a in pool if a != exclude] or list(pool)
    if not candidates:
        return None
    weights = [_autonomy_compute_weight(state, a) for a in candidates]
    total = sum(weights)
    if total <= 0:
        return None
    r = _random.random() * total
    acc = 0.0
    for aid, w in zip(candidates, weights):
        acc += w
        if r <= acc:
            return aid
    return candidates[-1]


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



def can_start_romance(player_id, target_id):
    """연애 진입 가능 여부 확인"""
    # 0. 플레이어 체력 체크
    import survival
    player_stats = survival.get_survival_stats(player_id)
    if player_stats["health"] <= ROMANCE_MIN_HEALTH:
        return False, "몸에 힘이 없어 스킨십할 상태가 아니다."

    affection_key = get_affection_key(player_id)

    # 1. 대상 성욕 체크 (흥분 낮으면 애정행동 거절)
    target_props = morld.get_unit_props(target_id)
    arousal = target_props.get("상태:성욕", 0)
    if arousal < DES_LABEL_THRESHOLD:
        return False, "아직 그런 분위기가 아닙니다."

    # 2. 같은 Location 확인
    player_loc = morld.get_unit_location(player_id)
    target_loc = morld.get_unit_location(target_id)
    if player_loc != target_loc:
        return False, "같은 장소에 있어야 합니다"

    # 3. 호감도 낮은 제3자 확인
    units_at_loc = morld.get_characters_at_location(player_loc[0], player_loc[1])
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
# NPC 스태미나
# ============================================

def _deduct_npc_stamina(state, total_stamina):
    """NPC 스태미나 차감 (행동 기반) + 탈진/기절 체크

    탈진 상태(npc_exhausted=True)에서는 행동 기반 차감 스킵.
    탈진 후에는 절정 시에만 HP 감소 (_apply_climax_hp_cost에서 처리).

    Returns: None (정상), "exhausted" (최초 탈진), "fainted" (기절)
    """
    # 이미 탈진 → 행동 기반 차감 스킵 (절정에서만 감소)
    if state.get("npc_exhausted"):
        return None
    npc_id = state.get("partner_id") or state.get("npc_id")
    if npc_id is None:
        return None
    npc_cost = calculate_npc_stamina_cost(total_stamina, npc_id)
    state["npc_stamina"] -= npc_cost

    if state["npc_stamina"] <= 0:
        state["npc_stamina"] = 1  # 기절 시 HP=1 하한선
        state["npc_fainted"] = True
        return "fainted"
    elif state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD:
        state["npc_exhausted"] = True
        # 탈진 알림 (1회, render_romance_ui에서 표시)
        npc_info = morld.get_unit_info(npc_id)
        npc_name = npc_info.get("name", "상대") if npc_info else "상대"
        state["_npc_exhaustion_notice"] = style_highlight(f"({npc_name}의 몸에서 힘이 빠져간다...)")
        return "exhausted"
    return None


def _apply_climax_hp_cost(state, climax_info):
    """절정/사정 시 양방향 체력 소모

    NPC 절정(non-P parts peaked) → NPC HP 소모
    플레이어 사정(P peaked) → 플레이어 HP 소모

    Returns: True if NPC fainted from climax
    """
    non_p_parts = climax_info.get("non_p_parts", [])
    has_p = climax_info.get("has_p", False)
    npc_id = state.get("partner_id") or state.get("npc_id")
    player_id = state.get("player_id")
    npc_fainted = False

    # NPC 절정 → NPC HP 소모
    if non_p_parts and npc_id:
        npc_exhausted = state.get("npc_exhausted", False)
        cost = calculate_climax_hp_cost(npc_id, npc_exhausted)
        if cost > 0:
            state["npc_stamina"] -= cost
            if state["npc_stamina"] <= 0:
                state["npc_stamina"] = 1  # 기절 시 HP=1 하한선
                state["npc_fainted"] = True
                npc_fainted = True
            elif (state["npc_stamina"] <= EXHAUSTION_HP_THRESHOLD
                    and not state.get("npc_exhausted")):
                state["npc_exhausted"] = True
                npc_info = morld.get_unit_info(npc_id)
                npc_name = npc_info.get("name", "상대") if npc_info else "상대"
                state["_npc_exhaustion_notice"] = (
                    style_highlight(f"({npc_name}의 몸에서 힘이 빠져간다...)"))

    # 플레이어 사정 (P peaked) → 플레이어 HP 소모
    if has_p and player_id:
        player_exhausted = (state.get("exhausted", False)
                            or state.get("stamina", 100) <= EXHAUSTION_HP_THRESHOLD)
        cost = calculate_climax_hp_cost(player_id, player_exhausted)
        if cost > 0:
            state["stamina"] -= cost
            if state["stamina"] <= 0:
                state["stamina"] = 1  # HP 하한선

    return npc_fainted


# ============================================
# 시간 경과 및 NPC 감지
# ============================================

def advance_time_and_check(state, millis):
    """시간 경과 + NPC 도착 체크 (은신 확률 적용)"""
    cur_mode = state["mode_ctx"]["mode"]

    # 시간정지: 시간 경과 및 NPC 체크 스킵
    if not should_advance_time(cur_mode):
        return {"interrupted": False}

    # 1. 시간 진행 + NPC 이동 시뮬레이션
    morld.advance_time_des(millis)
    state["elapsed_time"] += millis

    # 무의식/강제: 제3자 감지 스킵 여부
    if not should_check_third_party(cur_mode):
        return {"interrupted": False}

    # 2. 현재 Location의 NPC 목록 확인
    player_id = morld.get_player_id()
    player_loc = morld.get_unit_location(player_id)
    units_at_loc = morld.get_characters_at_location(player_loc[0], player_loc[1])

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
        if unit_id in state["checked_npcs"]:
            continue

        # 체크 목록에 추가
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

                # Phase 1: 아슬아슬한 스릴 → 약한 수치심 상승
                from romance_core import on_stealth_near_miss
                on_stealth_near_miss(partner_id)

                continue

            # 들킴 - 중단 (수치심 상승은 세션 종료 후 on_romance_interrupted에서)
            return {"interrupted": True, "interrupter_id": unit_id}
        # TODO: 합류 로직 (Phase 6)

    return {"interrupted": False}


# ============================================
# 월경 중 삽입 거부 시스템 (모듈 레벨 — romance_ui에서 import)
# ============================================

def _get_archetype(unit_id):
    """캐릭터 아키타입 조회"""
    from assets.characters import get_instance
    char = get_instance(unit_id)
    return getattr(char, 'archetype', None) if char else None


# 아키타입별 임계치 보정
_MENSTRUATION_ARCHETYPE_MOD = {
    "seductive": -1,  # 성적으로 개방적
    "devoted": -1,    # 순종적
    "fierce": 1,      # 강한 성격
    "cold": 1,        # 거부감
}


def _get_menstruation_threshold(partner_id, mode, state):
    """월경 중 삽입 거부 임계치 (0 = 자발적 수용, 높을수록 강한 거부)"""
    if mode in ("unconscious", "frozen"):
        return 0

    base = 1 if mode == "forced" else 3

    # 아키타입 보정
    archetype = _get_archetype(partner_id)
    base += _MENSTRUATION_ARCHETYPE_MOD.get(archetype, 0)

    # 성욕 + V 자극 보정: 흥분 상태 → 거부 약화
    arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
    v_stim = state["stim"]["stim"].get("V", 0)
    if arousal >= 60:
        base -= 1
    if arousal >= 50 and v_stim >= 40:
        base -= 1

    return max(0, base)


# 월경 중 삽입 거부 대사 (아키타입별, 시도 횟수별)
_MENSTRUATION_REFUSAL = {
    "stoic": [
        "{name}(이)가 조용히 손을 밀어낸다. '...오늘은 안 돼.'",
        "{name}(이)가 단호하게 고개를 젓는다.",
        "{name}(이)가 이를 악물고 버티고 있다.",
    ],
    "gentle": [
        "'저... 오늘은 그게... 좀 곤란해...' {name}(이)가 수줍게 거절한다.",
        "'미안해... 정말 지금은...' {name}(이)가 눈을 내리깔며 말한다.",
        "'으...' {name}(이)가 더 이상 말하지 못하고 눈을 감는다.",
    ],
    "cheerful": [
        "'아, 오늘은 좀~! 다음에 하자!' {name}(이)가 밝게 거절한다.",
        "'아니 진짜로! 오늘은 진짜 안 돼!' {name}(이)가 손을 흔든다.",
        "'......' {name}(이)가 입을 다문다.",
    ],
    "timid": [
        "'아... 지, 지금은...' {name}(이)가 다리를 오므리며 떨고 있다.",
        "'안... 안 돼요, 제발...' {name}(이)가 눈물을 글썽인다.",
        "{name}(이)가 더 이상 말하지 못하고 고개를 돌린다.",
    ],
    "cold": [
        "'안 돼.' {name}(이)가 차갑게 거절한다.",
        "'들리지 않았어? 안 된다고 했어.' {name}(이)가 눈을 가늘게 뜬다.",
        "{name}(이)가 입술을 깨물며 침묵한다.",
    ],
    "seductive": [
        "'음~ 오늘은 안 되는 날이야.' {name}(이)가 손가락으로 가슴을 밀어낸다.",
        "'진짜로 안 돼. 다른 걸로 해줄까?' {name}(이)가 눈짓한다.",
        "'......하아.' {name}(이)가 체념한 듯 한숨을 내쉰다.",
    ],
    "fierce": [
        "'지금 하지 마. 조건이 안 돼.' {name}(이)가 손목을 잡아 막는다.",
        "'한 번 더 시도하면 진짜 화낸다.' {name}(이)가 이를 드러낸다.",
        "{name}(이)가 분노에 찬 눈으로 노려보지만 힘이 빠져 있다.",
        "{name}(이)가 결국 힘이 풀려 더 이상 저항하지 못한다.",
    ],
    "proud": [
        "'오늘은 좀 쉬어줄 수 없겠어?' {name}(이)가 눈을 돌린다.",
        "'...부탁이야.' {name}(이)가 처음으로 약한 모습을 보인다.",
        "{name}(이)가 굴욕감을 참으며 눈을 감는다.",
    ],
    "innocent": [
        "'에? 저... 오늘은 좀...' {name}(이)가 얼굴을 붉히며 손을 흔든다.",
        "'그, 그게... 설명하기 어려운데...' {name}(이)가 눈을 피한다.",
        "{name}(이)가 두 눈을 질끈 감는다.",
    ],
    "devoted": [
        "'주인님... 오늘은... 죄송해요.' {name}(이)가 고개를 숙인다.",
        "'제발... 오늘만은...' {name}(이)가 간청하듯 올려다본다.",
        "'......네.' {name}(이)가 결국 체념한 듯 고개를 떨군다.",
    ],
}


def _get_menstruation_refusal(partner_id, failed_count):
    """월경 중 삽입 거부 메시지 (아키타입별 + 시도 횟수별)"""
    archetype = _get_archetype(partner_id)
    pool = _MENSTRUATION_REFUSAL.get(archetype)
    if not pool:
        return "지금은 안 된다고 거절한다."
    idx = min(failed_count, len(pool) - 1)
    name_info = morld.get_unit_info(partner_id)
    name = name_info.get("name", "상대") if name_info else "상대"
    return pool[idx].format(name=name)


# 강제 삽입 성공 반응 (threshold > 0이었으나 극복)
_MENSTRUATION_FORCED_REACTION = {
    "stoic": "{name}(이)가 이를 악물고 고개를 돌린다. 눈가가 붉어져 있다.",
    "gentle": "'아...' {name}(이)가 고통스러운 듯 작은 신음을 흘린다.",
    "cheerful": "{name}의 밝은 표정이 사라지고 입술을 깨물고 있다.",
    "timid": "{name}(이)가 소리 없이 눈물을 흘린다.",
    "cold": "{name}(이)가 눈을 감고 아무 말도 하지 않는다.",
    "seductive": "'...거칠게 나오네.' {name}(이)가 작게 한숨을 내쉰다.",
    "fierce": "{name}(이)가 분노에 찬 눈으로 올려다보고 있다.",
    "proud": "{name}의 눈에 굴욕감과 분노가 서려 있다.",
    "innocent": "{name}(이)가 무슨 일이 일어나는지 이해하지 못한 채 몸을 떨고 있다.",
    "devoted": "'...알겠습니다.' {name}(이)가 고통을 참으며 순종한다.",
}


# 자발적 수용 반응 (threshold == 0, 성욕/자극이 높거나 성격상 수용)
_MENSTRUATION_WILLING_REACTION = {
    "stoic": "{name}(이)가 살짝 눈을 돌리며 '...상관없어.'라고 중얼거린다.",
    "gentle": "'그... 괜찮아, 그냥... 해도 돼...' {name}(이)가 수줍게 속삭인다.",
    "cheerful": "'에이, 어차피 이렇게 된 거~' {name}(이)가 얼굴을 붉히며 웃는다.",
    "timid": "'저... 괜찮아요... 괜찮으니까...' {name}(이)가 작은 목소리로 허락한다.",
    "cold": "'...좋을 대로 해.' {name}(이)가 시선을 피하며 힘없이 말한다.",
    "seductive": "'음... 이런 날도 나쁘진 않지.' {name}(이)가 도발하듯 미소 짓는다.",
    "fierce": "'...한 번만이야. 알겠어?' {name}(이)가 얼굴을 붉히며 으르렁거린다.",
    "proud": "'...특별히 허락하는 거야.' {name}(이)가 시선을 돌리며 말한다.",
    "innocent": "'괜... 괜찮은 거지...?' {name}(이)가 불안하면서도 거부하지 않는다.",
    "devoted": "'주인님이 원하시면... 괜찮아요.' {name}(이)가 순순히 받아들인다.",
}


def _get_menstruation_insertion_reaction(partner_id, forced, willing):
    """월경 중 삽입 성공 시 반응"""
    archetype = _get_archetype(partner_id)
    if willing:
        pool = _MENSTRUATION_WILLING_REACTION
        fallback = "상관없다는 듯 받아들인다."
    elif forced:
        pool = _MENSTRUATION_FORCED_REACTION
        fallback = "고통스러운 표정을 짓고 있다."
    else:
        return None
    template = pool.get(archetype, fallback)
    name_info = morld.get_unit_info(partner_id)
    name = name_info.get("name", "상대") if name_info else "상대"
    return template.format(name=name)


# ============================================
# 메인 연애 함수
# ============================================

def start_romance(player_id, partner_id, preserved=None, mode=MODE_CONSENSUAL,
                   is_bestiality=False):
    """연애 모드 시작 - Generator 기반

    Args:
        player_id: 플레이어 유닛 ID
        partner_id: 파트너 유닛 ID
        preserved: 공수 전환 시 보존된 상태 (None이면 신규 세션)
        mode: 동작 모드 (MODE_CONSENSUAL/MODE_FORCED/MODE_UNCONSCIOUS/MODE_FROZEN)
        is_bestiality: True면 생물체(creature) 대상 수간 세션
    """

    # 진입 조건 체크 (전환 시 스킵 — 이미 세션 중)
    if not preserved and mode == MODE_CONSENSUAL:
        can_start, reason = can_start_romance(player_id, partner_id)
        if not can_start:
            yield ui.dialog(reason)
            return

    # 파트너 NPC를 현재 위치에 고정 (스킨십 동안 이동 방지)
    # 스케줄 스택에 STAY_SCHEDULE push, 종료 시 pop으로 복원
    # think() 생존 인터럽트 차단 (상태:로맨스중 prop)
    import think
    partner_agent = think.get_agent(partner_id)
    schedule_pushed = preserved.get("schedule_pushed", False) if preserved else False
    if not schedule_pushed:
        # HoldState: FSM + 스케줄 + 이동중 플래그 일괄 동결
        if partner_agent:
            partner_agent.begin_hold()
        # 기타 시스템 하위 호환용 prop (think() 체크/스탯 표시 등)
        morld.set_unit_prop(partner_id, "상태:로맨스중", 1)

    # 플레이어 체력 조회 (생존:체력 기반)
    import survival
    player_stats = survival.get_survival_stats(player_id)
    initial_stamina = player_stats["health"]
    max_stamina = player_stats["max_health"]

    # NPC 체력 조회
    npc_stats = survival.get_survival_stats(partner_id)
    npc_initial_stamina = npc_stats["health"]
    npc_max_stamina = npc_stats["max_health"]

    # 모드 컨텍스트 생성
    mode_ctx = create_mode_context(mode, player_id, partner_id)

    import gender as gender_mod
    # NPC 성적 선호 조회
    partner_asset_init = get_partner_asset(partner_id)
    npc_prefs = getattr(partner_asset_init, 'SEXUAL_PREFERENCES', None)
    # NPC 주도만 NPC 풀, 강제/시간정지/합의는 플레이어 풀, 의식불명은 전용 풀
    is_npc_init = (mode not in {MODE_CONSENSUAL, MODE_FORCED, MODE_FROZEN, MODE_UNCONSCIOUS})
    initial_position = position.select_initial_position(
        is_npc_initiative=is_npc_init, npc_prefs=npc_prefs, mode=mode)

    state = {
        # 핵심 (세션 수명)
        "player_id": player_id,
        "partner_id": partner_id,
        "active_toggles": set(),
        "stamina": initial_stamina,
        "initial_stamina": initial_stamina,
        "max_stamina": max_stamina,
        "npc_stamina": npc_initial_stamina,
        "npc_initial_stamina": npc_initial_stamina,
        "npc_max_stamina": npc_max_stamina,
        "npc_exhausted": False,
        "npc_fainted": False,
        "npc_faint_transition": False,
        "elapsed_time": 0,
        "lubricated": False,
        "stim": stimulation.create_state(
            male_mode=(gender_mod.get_gender(partner_id) == "male")
        ),
        # 체위
        "position": initial_position,
        # 동작 모드
        "mode_ctx": mode_ctx,
        # 삽입 호환 (삽입 토글 ON 시 설정)
        "size_pain": False,
        "size_stim_mod": 1.0,
        # 제3자 추적
        "checked_npcs": set(),
        # UI 일시적 (렌더링 후 소비)
        "last_reaction": None,
        "near_miss": False,
        "near_miss_id": None,
        "stealth_reaction": None,
        # 종료 조건
        "interrupted": False,
        "interrupter_id": None,
        "exhausted": False,
        "escaped": False,         # NPC 저항 탈출 (forced 모드)
        "wakeup_transition": False,  # 무의식→강제 전이
        "switch_to": None,
        # 콘돔
        "condom_active": False,
        "condom_punctured": False,
        "condom_removed_in_trance": False,
        # NPC 선호
        "npc_prefs": npc_prefs,
        # 삽입 상태
        "insertion": {
            "active": False,
            "orifice": None,      # "vaginal" or "anal"
            "who": None,           # "player" or "npc"
            "failed_count": 0,
        },
        # NPC 자율 허리흔들기 트랜스
        "npc_thrust_trance": False,
        # NPC 선호 체위 요구 쿨다운 (세션 elapsed_time 기준)
        "last_position_request_elapsed": None,
        # NPC 삽입 요구 쿨다운
        "last_insertion_request_elapsed": None,
        # NPC 자율 행위 루프 (Phase 1.6)
        "npc_autonomy": {
            "active": False,
            "current_action": None,
            "duration_remaining": 0,
            "total_turns": 0,
            "last_exit_elapsed": None,
        },
        # 수간(bestiality) 세션 여부
        "is_bestiality": is_bestiality,
    }

    # 수간 세션: creature 기본 props 초기화
    if is_bestiality and not preserved:
        for prop in ("상태:성욕", "상태:절정"):
            if morld.get_unit_prop(partner_id, prop) is None:
                morld.set_unit_prop(partner_id, prop, 0)
        # 관계 props (없으면 0 기본)
        player_name = morld.get_unit_info(player_id).get("name", "?")
        for suffix in ("호감", "욕망", "반발", "복종"):
            key = f"관계:{player_name}:{suffix}"
            if morld.get_unit_prop(partner_id, key) is None:
                morld.set_unit_prop(partner_id, key, 0)

    # 신규 세션: 상시 절정 prop → 세션 게이지 동기화
    if not preserved:
        climax_prop = morld.get_unit_prop(partner_id, "상태:절정") or 0
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
        state["condom_active"] = preserved.get("condom_active", False)
        state["condom_punctured"] = preserved.get("condom_punctured", False)
        state["condom_removed_in_trance"] = preserved.get("condom_removed_in_trance", False)
        if preserved.get("npc_stamina") is not None:
            state["npc_stamina"] = preserved["npc_stamina"]
            state["npc_initial_stamina"] = preserved.get("npc_initial_stamina", state["npc_stamina"])
            state["npc_max_stamina"] = preserved.get("npc_max_stamina", npc_max_stamina)
        if "insertion" in preserved:
            state["insertion"] = preserved["insertion"]
        if "position" in preserved:
            state["position"] = preserved["position"]
        if "mode_ctx" in preserved:
            state["mode_ctx"] = preserved["mode_ctx"]
        state["npc_thrust_trance"] = preserved.get("npc_thrust_trance", False)

    # ── NPC Thrust Trance 시스템 ──────────────────────────────

    _DEFAULT_THRUST_CONFIG = {
        "entry_arousal": 50,
        "entry_gauge": 30,
        "gentle_arousal": 50,
        "normal_arousal": 70,
        "rough_arousal": 90,
        "escalation_chance": 0.2,
    }

    def _get_npc_thrust_config(partner_id):
        asset = get_partner_asset(partner_id)
        if asset and hasattr(asset, 'NPC_THRUST_CONFIG') and asset.NPC_THRUST_CONFIG:
            # 기본값과 병합 (캐릭터가 일부만 오버라이드해도 동작)
            merged = dict(_DEFAULT_THRUST_CONFIG)
            merged.update(asset.NPC_THRUST_CONFIG)
            return merged
        return _DEFAULT_THRUST_CONFIG

    def _select_thrust_intensity(arousal, config):
        """성욕 기반 thrust 강도 선택."""
        if arousal >= config["rough_arousal"]:
            return "thrust_rough"
        elif arousal >= config["normal_arousal"]:
            return "thrust_normal"
        return "thrust_gentle"

    def _get_partner_name(state):
        partner_info = morld.get_unit_info(state["partner_id"])
        return partner_info.get("name", "상대") if partner_info else "상대"

    def _check_npc_thrust_trance(state):
        """NPC thrust trance 진입 판정.
        삽입 중 + thrust 비활성 + NPC 조건 충족 시 트랜스 진입.
        Returns: {"thrust_id": str, "reaction": str} 또는 None
        """
        if not state["insertion"]["active"]:
            return None
        if state.get("npc_thrust_trance"):
            return None
        if any(t in _THRUST_TOGGLE_IDS for t in state["active_toggles"]):
            return None

        pid = state["partner_id"]
        config = _get_npc_thrust_config(pid)

        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        gauge = state["stim"]["climax_gauge"]

        # 트랜스 상태면 임계 -20 (자제심 낮거나 외부 자극으로 흥분 고조 시)
        from romance_dynamics import update_trance_level, is_in_trance
        # 절정게이지 동기화 후 재계산 (매번 최신값 반영)
        morld.set_unit_prop(pid, "상태:절정", gauge)
        update_trance_level(pid)
        entry_arousal = config["entry_arousal"]
        entry_gauge = config["entry_gauge"]
        if is_in_trance(pid):
            entry_arousal = max(20, entry_arousal - 20)
            entry_gauge = max(10, entry_gauge - 10)

        if arousal < entry_arousal or gauge < entry_gauge:
            return None

        thrust_id = _select_thrust_intensity(arousal, config)

        state["npc_thrust_trance"] = True
        state["active_toggles"].add(thrust_id)

        reaction = _get_mode_reaction("npc_thrust_trance", "start")
        if not reaction:
            pname = _get_partner_name(state)
            reaction = f"{pname}(이)가 스스로 허리를 흔들기 시작했다..."
        return {"thrust_id": thrust_id, "reaction": reaction}

    def _tick_npc_thrust_trance(state):
        """트랜스 중 강도 재평가. 매 턴 호출."""
        if not state.get("npc_thrust_trance"):
            return

        pid = state["partner_id"]
        config = _get_npc_thrust_config(pid)

        if random.random() >= config["escalation_chance"]:
            return

        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        new_thrust = _select_thrust_intensity(arousal, config)

        current = next((t for t in state["active_toggles"]
                        if t in _THRUST_TOGGLE_IDS), None)
        if current and current != new_thrust:
            state["active_toggles"].discard(current)
            state["active_toggles"].add(new_thrust)

    def _end_npc_thrust_trance(state):
        """트랜스 종료 — thrust + sync_thrust 토글 해제."""
        state["npc_thrust_trance"] = False
        for tid in list(state["active_toggles"]):
            if tid in _THRUST_TOGGLE_IDS or tid == "sync_thrust":
                state["active_toggles"].discard(tid)

    def _check_npc_beg_reaction(state):
        """삽입+정지 + 트랜스 미진입 시 애원 반응 (대사 전용).
        Returns: str 또는 None
        """
        pid = state["partner_id"]
        config = _get_npc_thrust_config(pid)
        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        beg_threshold = config["entry_arousal"] - 15
        if arousal >= beg_threshold:
            return _get_mode_reaction("npc_beg_thrust", "start")
        return None

    def _check_npc_position_request(state):
        """선호 체위 요구 대사 (대사 전용, 실제 체위 전환은 플레이어 선택).

        조건:
          - 삽입 중
          - 현재 체위가 NPC 선호 체위 리스트에 없음
          - NPC 성욕 ≥ POSITION_REQUEST_AROUSAL
          - 쿨다운 경과 (POSITION_REQUEST_COOLDOWN_MS)
          - 확률 게이트 (POSITION_REQUEST_CHANCE)

        Returns: 대사 텍스트 or None.
        """
        if not state["insertion"]["active"]:
            return None
        prefs = state.get("npc_prefs") or {}
        preferred = prefs.get("preferred_positions") or []
        if not preferred:
            return None
        current_pos = state.get("position")
        if current_pos in preferred:
            return None

        pid = state["partner_id"]
        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        if arousal < POSITION_REQUEST_AROUSAL:
            return None

        last = state.get("last_position_request_elapsed")
        if last is not None and state["elapsed_time"] - last < POSITION_REQUEST_COOLDOWN_MS:
            return None

        import random as _random
        if _random.random() >= POSITION_REQUEST_CHANCE:
            return None

        target_pos = _random.choice(preferred)
        state["last_position_request_elapsed"] = state["elapsed_time"]

        # 캐릭터 반응 풀: "npc_position_request:{pos_id}" 우선, fallback "npc_position_request:start"
        reaction = _get_mode_reaction("npc_position_request", target_pos)
        if not reaction:
            reaction = _get_mode_reaction("npc_position_request", "start")
        if not reaction:
            pos_name = position.get_name(target_pos)
            pname = _get_partner_name(state)
            reaction = f"{pname}(이)가 {pos_name}를 원하는 듯한 몸짓을 보였다..."
        return reaction

    def _try_npc_thrust_after_action(state, action_id):
        """행위 후 NPC 자율 thrust / 체위 요구 체크 (삽입+정지 상태에서).
        thrust_stop/withdraw 직후에는 호출하지 않음.
        반환된 반응 텍스트가 있으면 last_reaction에 추가.
        """
        if action_id in ("thrust_stop", "withdraw"):
            return
        if not state["insertion"]["active"]:
            return
        if any(t in _THRUST_TOGGLE_IDS for t in state["active_toggles"]):
            return
        npc_action = _check_npc_thrust_trance(state)
        if npc_action:
            prev = state.get("last_reaction") or ""
            state["last_reaction"] = (prev + f"\n{npc_action['reaction']}").strip()
            return  # 트랜스 진입 시 체위 요구 대사는 생략
        pos_request = _check_npc_position_request(state)
        if pos_request:
            prev = state.get("last_reaction") or ""
            state["last_reaction"] = (prev + f"\n{pos_request}").strip()

    # ── NPC 자율 행위 루프 (삽입 없음 상태) ────────────────────────

    # closure alias — 모듈 수준 함수를 state 바인딩 없이 위임
    _autonomy_guard = _autonomy_check_guard
    _autonomy_available_actions = _autonomy_available
    _autonomy_weight = _autonomy_compute_weight
    _autonomy_pick_action = _autonomy_pick

    def _can_enter_autonomy(state):
        """자율 루프 진입 조건 — 트랜스 기반 (복종/호감 게이트 제거).

        페르소나 관점: 성욕+흥분이 충분하고 자제심이 낮으면
        (= 트랜스 상태) 자연스럽게 자발 행동에 나선다. 함락(복종) 여부는
        트랜스 수치에 직접 영향을 주지 않지만 추후 세뇌/약물로 가산 가능.
        """
        auto = state["npc_autonomy"]
        if auto["active"]:
            return False
        if state["insertion"]["active"]:
            return False
        pid = state["partner_id"]
        # 트랜스 재계산 후 게이트
        from romance_dynamics import update_trance_level, is_in_trance
        update_trance_level(pid)
        if not is_in_trance(pid):
            return False
        last_exit = auto.get("last_exit_elapsed")
        if last_exit is not None and state["elapsed_time"] - last_exit < AUTONOMY_COOLDOWN_MS:
            return False
        return True

    def _should_exit_autonomy(state):
        """종료 사유 반환 (없으면 None)."""
        auto = state["npc_autonomy"]
        if not auto["active"]:
            return None
        if state["insertion"]["active"]:
            return "insertion_started"
        pid = state["partner_id"]
        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        if arousal < AUTONOMY_EXIT_AROUSAL:
            return "arousal_low"
        if auto["total_turns"] >= AUTONOMY_MAX_TURNS:
            return "max_turns"
        return None

    def _exit_autonomy(state, reason):
        """자율 루프 종료."""
        auto = state["npc_autonomy"]
        auto["active"] = False
        auto["current_action"] = None
        auto["duration_remaining"] = 0
        auto["total_turns"] = 0
        auto["last_exit_elapsed"] = state["elapsed_time"]

    def _apply_autonomy_effects(state, action_id):
        """자율 행위 효과 적용 (매 턴 지속 효과)."""
        entry = _NPC_AUTONOMY_CATALOG.get(action_id)
        if not entry or not entry.get("effects"):
            return
        pid = state["partner_id"]
        player_id = state["player_id"]
        affection_key = get_affection_key(player_id)
        for stat, value in entry["effects"].items():
            if value == 0:
                continue
            if stat in ("성욕", "성적절정"):
                morld.modify_prop(pid, f"상태:{stat}", value)
            elif stat == "욕망":
                morld.modify_prop(pid, "상태:성욕", value)
            else:
                morld.modify_prop(pid, affection_key.replace(":호감", f":{stat}"), value)

    def _get_autonomy_reaction(state, action_id, timing):
        """자율 행위 대사 조회. 우선순위: 행위별 → 공통 start."""
        reaction = _get_mode_reaction(f"npc_autonomy_{action_id}", timing)
        if not reaction:
            reaction = _get_mode_reaction("npc_autonomy", timing)
        return reaction

    def _try_enter_autonomy(state):
        """진입 시도 — 성공 시 첫 행위 선택 + 대사 반환."""
        import random as _random
        if not _can_enter_autonomy(state):
            return None
        if _random.random() >= AUTONOMY_ENTRY_CHANCE:
            return None
        available = _autonomy_available_actions(state)
        # rest만 가능하면 진입 안 함 (성욕 있는데 아무것도 못 하면 패스)
        non_rest = [a for a in available
                    if _NPC_AUTONOMY_CATALOG[a]["kind"] != "rest"]
        if not non_rest:
            return None
        choice = _autonomy_pick_action(state, non_rest)
        if not choice:
            return None
        auto = state["npc_autonomy"]
        auto["active"] = True
        auto["current_action"] = choice
        auto["duration_remaining"] = _random.randint(
            AUTONOMY_MIN_DURATION, AUTONOMY_MAX_DURATION)
        auto["total_turns"] = 0
        _apply_autonomy_effects(state, choice)
        reaction = _get_autonomy_reaction(state, choice, "start")
        if not reaction:
            entry = _NPC_AUTONOMY_CATALOG[choice]
            pname = _get_partner_name(state)
            reaction = f"{pname}(이)가 스스로 {entry.get('desc', '무언가')}"
        return reaction

    def _tick_autonomy(state):
        """진행 중 자율 루프 tick. 전환 시 대사 반환."""
        import random as _random
        auto = state["npc_autonomy"]
        if not auto["active"]:
            return None
        reason = _should_exit_autonomy(state)
        if reason:
            _exit_autonomy(state, reason)
            return None
        # 지속 효과
        _apply_autonomy_effects(state, auto["current_action"])
        auto["total_turns"] += 1
        auto["duration_remaining"] -= 1
        if auto["duration_remaining"] > 0:
            return None  # 지속 중, 대사 없음
        # 전환
        available = _autonomy_available_actions(state)
        next_action = _autonomy_pick_action(
            state, available, exclude=auto["current_action"])
        if not next_action:
            _exit_autonomy(state, "no_actions")
            return None
        auto["current_action"] = next_action
        auto["duration_remaining"] = _random.randint(
            AUTONOMY_MIN_DURATION, AUTONOMY_MAX_DURATION)
        return _get_autonomy_reaction(state, next_action, "switch") \
            or _get_autonomy_reaction(state, next_action, "start")

    def _check_npc_insertion_request(state):
        """삽입 없는 상태에서 NPC가 삽입을 요구하는 대사 (대사만).

        조건:
        - 삽입 없음
        - NPC 트랜스 ≥ 60
        - NPC 해부학 V 또는 A 보유 + 플레이어 P 보유
        - 플레이어 하체 노출
        - 쿨다운 5분, 확률 25%
        """
        if state["insertion"]["active"]:
            return None
        pid = state["partner_id"]
        player_id = state["player_id"]
        from romance_dynamics import update_trance_level, is_in_trance
        update_trance_level(pid)
        if not is_in_trance(pid):
            return None
        import gender
        if not gender.has_anatomy(player_id, "P"):
            return None
        from romance_core import get_exposure_state as _get_exp
        if not _get_exp(player_id).get("lower_exposed"):
            return None
        available = []
        if gender.has_anatomy(pid, "V"):
            available.append(("vaginal", "V"))
        if gender.has_anatomy(pid, "A"):
            available.append(("anal", "A"))
        if not available:
            return None
        last = state.get("last_insertion_request_elapsed")
        if last is not None and \
                state["elapsed_time"] - last < INSERTION_REQUEST_COOLDOWN_MS:
            return None
        import random as _random
        if _random.random() >= INSERTION_REQUEST_CHANCE:
            return None

        # 선호 부위 가중치 선택
        prefs = state.get("npc_prefs") or {}
        preferred = prefs.get("preferred_parts") or []
        weights = [2.0 if part in preferred else 1.0 for _, part in available]
        total = sum(weights)
        r = _random.random() * total
        acc = 0.0
        target_orifice = available[-1][0]
        for (orifice, _), w in zip(available, weights):
            acc += w
            if r <= acc:
                target_orifice = orifice
                break
        state["last_insertion_request_elapsed"] = state["elapsed_time"]

        reaction = _get_mode_reaction("npc_insertion_request", target_orifice)
        if not reaction:
            reaction = _get_mode_reaction("npc_insertion_request", "start")
        if not reaction:
            pname = _get_partner_name(state)
            label = "질" if target_orifice == "vaginal" else "항문"
            reaction = f"{pname}(이)가 {label}에 삽입해주기를 원하는 듯한 몸짓을 보였다..."
        return reaction

    def _try_npc_autonomy_after_action(state, action_id):
        """행위 후 NPC 자율 행위 루프 + 삽입 요구 체크 (삽입 없음 상태).

        삽입 중이면 thrust_trance로 이관되므로 여기서는 삽입 여부 선체크.
        반환된 대사는 last_reaction에 추가.
        """
        if action_id in ("exit", "thrust_stop", "withdraw"):
            return
        if state["insertion"]["active"]:
            # 삽입이 시작되었으면 autonomy 종료
            if state["npc_autonomy"]["active"]:
                _exit_autonomy(state, "insertion_started")
            return
        # 플레이어가 수동으로 fellatio/penis_rub을 토글 중이면 NPC가 그 위에 자율 진입하지 않음
        conflicting = {"fellatio", "penis_rub"}
        if conflicting & set(state["active_toggles"]):
            if state["npc_autonomy"]["active"]:
                _exit_autonomy(state, "player_took_over")
            return

        auto = state["npc_autonomy"]
        if auto["active"]:
            reaction = _tick_autonomy(state)
        else:
            reaction = _try_enter_autonomy(state)
        if reaction:
            prev = state.get("last_reaction") or ""
            state["last_reaction"] = (prev + f"\n{reaction}").strip()

        # 삽입 요구는 autonomy inactive일 때만 (자발 행동 중엔 생략)
        if not auto["active"]:
            insertion_req = _check_npc_insertion_request(state)
            if insertion_req:
                prev = state.get("last_reaction") or ""
                state["last_reaction"] = (prev + f"\n{insertion_req}").strip()

    # ── NPC Thrust Trance 끝 ──────────────────────────────────

    def _get_afterglow_reaction():
        """여운 중 행위 시 추가 반응 (감도 증가 표현)."""
        afterglow = state["stim"].get("afterglow", 0)
        if afterglow <= 0:
            return None
        partner_asset = get_partner_asset(state["partner_id"])
        if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
            if afterglow >= 40:
                key = "afterglow_sensitive"
            elif afterglow >= 20:
                key = "afterglow_trembling"
            else:
                key = "afterglow_fading"
            return partner_asset.get_romance_reaction(
                key, "start", stim_state=state["stim"])
        return None

    def _append_afterglow_reaction(ecstasy_reaction, afterglow_result):
        """여운 반응/종료 반응을 last_reaction에 추가."""
        if ecstasy_reaction:
            return  # 절정 반응이 우선
        parts = []
        ag_reaction = _get_afterglow_reaction()
        if ag_reaction:
            parts.append(ag_reaction)
        if afterglow_result == "ended":
            partner_asset = get_partner_asset(state["partner_id"])
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                end_text = partner_asset.get_romance_reaction(
                    "afterglow_end", "start", stim_state=state["stim"])
                if end_text:
                    parts.append(end_text)
        if parts:
            existing = state.get("last_reaction") or ""
            combined = "\n".join(p for p in parts if p)
            state["last_reaction"] = (existing + "\n" + combined).strip() if existing else combined

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
        effects = calculate_effects(action_def, pid, player_id)

        # 활성 토글들의 효과도 합산
        for toggle_def in active_toggle_defs:
            toggle_effects = calculate_effects(toggle_def, pid, player_id)
            for stat, value in toggle_effects.items():
                effects[stat] = effects.get(stat, 0) + value

        # 모드별 효과 배율 적용
        cur_mode = state["mode_ctx"]["mode"]
        multipliers = get_effect_multipliers(cur_mode)
        # 트랜스 배율 (모드 배율과 곱셈 합성) — 의식 흐림 시 관계 약화, 몸 가속
        from romance_dynamics import compute_trance_multipliers
        trance_mult = compute_trance_multipliers(pid)
        _STAT_MULT_MAP = {
            "호감": "affection", "욕망": "desire", "반발": "rebellion",
            "복종": "submission", "성욕": "arousal",
        }

        # 효과 적용 (호감/욕망/성욕 prop 변경) — 모드 배율 × 트랜스 배율 반영
        for stat, value in effects.items():
            mult_key = _STAT_MULT_MAP.get(stat)
            if mult_key:
                mode_m = multipliers.get(mult_key, 1.0)
                trance_m = trance_mult.get(mult_key, 1.0)
                value = round(value * mode_m * trance_m)
            if value == 0:
                continue

            if cur_mode == MODE_FROZEN:
                # 시간정지: 효과 지연
                defer_effect(state["mode_ctx"], stat, value)
                continue

            if stat in ("성욕", "성적절정"):
                prop_key = f"상태:{stat}"
            elif stat == "욕망":
                # 욕망 deprecated → 상태:성욕으로 통합 (Phase 0)
                prop_key = "상태:성욕"
            else:
                prop_key = affection_key.replace(":호감", f":{stat}")
            morld.modify_prop(pid, prop_key, value)

        # 강제 모드: 매 행위마다 반발 +1
        if cur_mode == MODE_FORCED:
            rebellion_key = get_rebellion_key(player_id)
            morld.modify_prop(pid, rebellion_key, 1)

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
            # 삽입 크기 배율 적용
            size_mod = state["size_stim_mod"]
            if size_mod != 1.0 and act_def.get("exp_part") in ("음부", "엉덩이", "음경"):
                gain = round(gain * size_mod)
            # NPC 선호 보너스 (체위/부위)
            pref_mult = position.get_preference_mult(state["position"], category, state.get("npc_prefs"))
            if pref_mult != 1.0:
                gain = round(gain * pref_mult)
            # 트랜스 가속 (절정 게이지 × 1.2 / 1.5)
            gauge_mult = trance_mult.get("climax_gauge", 1.0)
            if gauge_mult != 1.0:
                gain = max(1, round(gain * gauge_mult))
            result = stimulation.apply(stim_state, category, gain)
            if result and not climax_info:
                climax_info = result
            # 추가 자극 (tribadism: V+C 동시)
            extra = act_def.get("extra_exp_part")
            if extra:
                extra_cat = SENSATION_MAP.get(extra)
                if extra_cat:
                    extra_sens = get_sensation_level(pid, extra_cat)
                    extra_gain = stimulation.calc_gain(base, extra_sens, rebellion, stim_state["afterglow"], stim_state.get("refractory", 0))
                    extra_pref = position.get_preference_mult(state["position"], extra_cat, state.get("npc_prefs"))
                    if extra_pref != 1.0:
                        extra_gain = round(extra_gain * extra_pref)
                    if gauge_mult != 1.0:
                        extra_gain = max(1, round(extra_gain * gauge_mult))
                    r2 = stimulation.apply(stim_state, extra_cat, extra_gain)
                    if r2 and not climax_info:
                        climax_info = r2

        # 삽입 중 플레이어 P 자극 축적 (P 감각에 따른 상승 감소)
        if state["insertion"]["active"] and any(t in _THRUST_TOGGLE_IDS for t in state["active_toggles"]):
            import gender as gender_mod
            if gender_mod.has_anatomy(player_id, "P"):
                p_base = sum(
                    a["effects"].get("성욕", 0)
                    for a in all_actions
                    if a.get("exp_part") in ("음부", "엉덩이")
                ) // 2
                p_gain = max(3, p_base)
                # P 감각 스케일링 (경험 ↑ → 지속력 ↑)
                p_sensation = get_sensation_level(player_id, "P")
                p_gain = max(1, round(p_gain * stimulation.get_p_gain_multiplier(p_sensation)))
                r_p = stimulation.apply(stim_state, "P", p_gain)
                if r_p and not climax_info:
                    climax_info = r_p

        # 여운 감소 (턴당 1회)
        afterglow_result = stimulation.tick_afterglow(stim_state)
        state["_afterglow_result"] = afterglow_result

        # 절정 처리 (다중 부위 동시 절정)
        if climax_info:
            exp_mult = multipliers.get("sensation_exp", 1.0)
            sim_mult = climax_info.get("simultaneous_mult", 1.0)
            peaked_parts = climax_info.get("peaked_parts", [climax_info["category"]])
            non_p_parts = climax_info.get("non_p_parts", peaked_parts)
            has_p = climax_info.get("has_p", False)

            if cur_mode == MODE_FROZEN:
                # 시간정지: 절정 횟수만 축적, 실제 효과 지연
                state["mode_ctx"]["deferred_climax_count"] += 1
            else:
                # 성욕 일부 감소 (동시 절정 배율 적용)
                arousal_reduction = round(stimulation.CLIMAX_AROUSAL_REDUCTION * sim_mult)
                current_arousal = partner_props.get("상태:성욕", 0) if partner_props else 0
                new_arousal = max(0, current_arousal - arousal_reduction)
                morld.set_unit_prop(pid, "상태:성욕", new_arousal)
                # 성적절정 +1
                morld.modify_prop(pid, "상태:성적절정", 1)

            # 절정 부위 감각 경험치 보너스 (모드 배율 적용, 부위별)
            exp_gain = stimulation.get_climax_sensation_gain(
                rebellion, climax_info.get("chain_count", 0))
            exp_gain = round(exp_gain * exp_mult * sim_mult)
            for cat in non_p_parts:
                if exp_gain > 0:
                    for part, c in SENSATION_MAP.items():
                        if c == cat:
                            morld.modify_prop(pid, f"경험:{part}", exp_gain)
                            break

                # 절정 횟수 카운트 (부위별)
                climax_count_key = f"경험:절정:{cat}"
                morld.set_unit_prop(pid, climax_count_key,
                                    (morld.get_unit_prop(pid, climax_count_key) or 0) + 1)

            # 절정 시 일시 자제심 상실 → 트랜스:외부 +20 (Phase 1.9.1)
            # 여운 중 의식 흐림 표현. 1h tick으로 자연 회복.
            morld.modify_prop(pid, "트랜스:외부", 20)

            # 마일스톤: 첫 절정
            if not morld.get_unit_prop(pid, "기억:첫절정"):
                morld.set_unit_prop(pid, "기억:첫절정", 1)

            # 절정 시 복종 증가 (반발에 의해 억제) — frozen은 지연
            if cur_mode != MODE_FROZEN:
                climax_sub_gain = max(0, 2 - rebellion // 25)
                if cur_mode == MODE_FORCED:
                    climax_sub_gain = round(climax_sub_gain * multipliers.get("submission", 1.0))
                if climax_sub_gain > 0:
                    submission_key = affection_key.replace(":호감", ":복종")
                    current_sub = (partner_props or {}).get(submission_key, 0)
                    if current_sub < SUBMISSION_MAX:
                        morld.modify_prop(pid, submission_key, climax_sub_gain)

            # P 절정 (사정) 처리
            ejac_part = None
            if has_p:
                insertion = state["insertion"]
                if insertion["active"]:
                    orifice = insertion["orifice"]
                    if orifice == "vaginal":
                        # 임신 판정 (질 삽입 + P 보유자 절정)
                        import gender as gender_mod
                        if gender_mod.has_anatomy(pid, "P"):
                            if not (state["condom_active"] and not state["condom_punctured"]):
                                import pregnancy
                                if cur_mode == MODE_FROZEN:
                                    pregnancy.check_conception(player_id, pid, father_type="unknown")
                                else:
                                    pregnancy.check_conception(player_id, pid)
                        ejac_part = "음부"
                    elif orifice == "anal":
                        ejac_part = "항문"
                # 삽입 미활성 + 펠라치오 활성 → 구강 사정
                if not ejac_part and "fellatio" in state["active_toggles"]:
                    import gender as gender_mod
                    if gender_mod.has_anatomy(pid, "P"):
                        ejac_part = "구강"

                # 내부 사정 → 체내 정액 저장 (사정량 동적 계산)
                if ejac_part and ejac_part in ("음부", "항문", "구강"):
                    import gender as _gm
                    _p_holder = player_id
                    if _gm.has_anatomy(pid, "P"):
                        _p_holder = pid
                    _ejac_amt = calculate_ejaculation_amount(_p_holder, state["stamina"], state["max_stamina"])
                    if cur_mode == MODE_FROZEN:
                        defer_semen(state["mode_ctx"], ejac_part, _ejac_amt, internal=True)
                    else:
                        _apply_internal_semen(pid, ejac_part, _ejac_amt)
                    # 경험 축적: 사정 횟수
                    morld.set_unit_prop(pid, "경험:사정횟수",
                                        (morld.get_unit_prop(pid, "경험:사정횟수") or 0) + 1)
                    # 플레이어 통계: 총 사정량
                    morld.set_unit_prop(player_id, "통계:총사정량",
                                        (morld.get_unit_prop(player_id, "통계:총사정량") or 0) + _ejac_amt)

                # 트랜스 중 콘돔 제거 → 사정 후 발각
                if state.get("condom_removed_in_trance") and ejac_part:
                    rebellion_key = get_rebellion_key(player_id)
                    morld.modify_prop(pid, rebellion_key, 5)
                    state["condom_removed_in_trance"] = False
                    state["last_reaction"] = "...콘돔이...빠져 있었...어...?"

                # 구멍 뚫린 콘돔 발각 (사정 시 70% 확률)
                if state["condom_active"] and state["condom_punctured"] and ejac_part:
                    import random
                    if random.random() < 0.7 and cur_mode not in (MODE_UNCONSCIOUS, MODE_FROZEN):
                        rebellion_key = get_rebellion_key(player_id)
                        morld.modify_prop(pid, rebellion_key, 10)
                        # 경험 축적
                        cheat_count = (morld.get_unit_prop(pid, "경험:콘돔속임") or 0) + 1
                        morld.set_unit_prop(pid, "경험:콘돔속임", cheat_count)
                        state["last_reaction"] = "...콘돔에 구멍이 뚫려 있다는 걸 알아챘다!"

            # 절정 시 허리흔들기 토글 해제 (삽입 상태는 유지)
            for tid in list(state["active_toggles"]):
                if tid in _THRUST_TOGGLE_IDS:
                    state["active_toggles"].discard(tid)

            # NPC 절정 시 thrust trance 종료
            if state.get("npc_thrust_trance"):
                _end_npc_thrust_trance(state)

            # ── 절정/사정 시 체력 소모 ──
            _apply_climax_hp_cost(state, climax_info)

            # 트랜스 자동 삽입 체크 (절정 후 NPC 비-P 부위 아직 peaked)
            auto_insert = _check_trance_auto_insert(state)
            if auto_insert:
                trance_reaction = _get_mode_reaction("trance_insert", "start")
                if trance_reaction:
                    state["last_reaction"] = trance_reaction

            # 절정 반응 텍스트 — 모드별 분기
            reaction_prefix = get_reaction_prefix(cur_mode)
            if reaction_prefix is None:
                # 무반응 모드 (무의식/시간정지): 나레이션
                return get_silent_climax_narration(cur_mode)

            # creature (bestiality): 종별 절정 반응
            if state.get("is_bestiality"):
                import creature_reactions
                cr = creature_reactions.get_creature_climax_reaction(pid)
                if cr:
                    return cr

            partner_asset = get_partner_asset(pid)
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                reactions = getattr(partner_asset, 'ROMANCE_REACTIONS', {})
                # 내부 사정 반응 + 절정 반응 결합
                ejac_reaction = None
                if ejac_part:
                    ejac_key = f"{reaction_prefix}ejaculation_internal_{ejac_part}"
                    ejac_reaction = partner_asset.get_romance_reaction(ejac_key, "start", stim_state=state["stim"])
                    if not ejac_reaction and reaction_prefix:
                        ejac_reaction = partner_asset.get_romance_reaction(
                            f"ejaculation_internal_{ejac_part}", "start", stim_state=state["stim"])
                ecstasy_key = get_climax_reaction_key(
                    climax_info, state["active_toggles"], TOGGLE_ACTIONS, reactions, state=state)
                # 강제 모드: forced_ 접두사 시도 → fallback
                reaction = None
                if reaction_prefix:
                    reaction = partner_asset.get_romance_reaction(
                        f"{reaction_prefix}{ecstasy_key}", "start", stim_state=state["stim"])
                if not reaction:
                    reaction = partner_asset.get_romance_reaction(ecstasy_key, "start", stim_state=state["stim"])
                if ejac_reaction and reaction:
                    return f"{ejac_reaction}\n{reaction}"
                if ejac_reaction:
                    return ejac_reaction
                if reaction:
                    return reaction
            partner_info = morld.get_unit_info(pid)
            partner_name = partner_info.get('name', '상대') if partner_info else '상대'
            return f"{partner_name}(이)가 절정에 달했다."

        # 절정 미발생 시에도 트랜스 체크
        auto_insert = _check_trance_auto_insert(state)
        if auto_insert:
            trance_reaction = _get_mode_reaction("trance_insert", "start")
            if trance_reaction:
                return trance_reaction

        return None

    def _post_action_mode_check():
        """행위 후 모드별 체크 (저항/각성). True면 세션 종료 필요."""
        mode_ctx = state["mode_ctx"]
        cur_mode = mode_ctx["mode"]
        mode_ctx["action_count"] = mode_ctx.get("action_count", 0) + 1

        # 강제 모드: NPC 저항 체크
        if cur_mode == MODE_FORCED:
            result = check_resistance(mode_ctx, state["partner_id"])
            if result["escaped"]:
                state["escaped"] = True
                return True
            # 탈출 시도 메시지 (실패)
            if result.get("attempted"):
                msg = get_escape_attempt_message(
                    state["partner_id"], result.get("escape_chance"))
                if msg:
                    existing = state.get("last_reaction") or ""
                    if existing:
                        state["last_reaction"] = existing + "\n" + msg
                    else:
                        state["last_reaction"] = msg

        # 무의식 모드: 각성 체크
        if cur_mode == MODE_UNCONSCIOUS:
            if check_wakeup(mode_ctx, state["partner_id"], 0):
                # 각성 → FORCED 전이
                transition_to_forced(mode_ctx)
                state["wakeup_transition"] = True
                return True  # UI 전환을 위해 일단 종료

        return False

    def _get_mode_reaction(action_id, timing="start"):
        """모드별 반응 텍스트 조회.

        우선순위:
        1. 트랜스 접두어 (`trance_deep:` > `trance:`) — 깊은 트랜스일수록 인간어 상실
        2. 모드 접두어 (forced_ 등)
        3. 기본 반응
        4. 공통 트랜스 fallback 풀 (의성어)
        """
        mode_ctx = state["mode_ctx"]
        cur_mode = mode_ctx["mode"]
        reaction_prefix = get_reaction_prefix(cur_mode)

        if reaction_prefix is None:
            # 무반응 모드: 나레이션
            return get_silent_narration(cur_mode)

        # 트랜스 상태 확인
        pid = state["partner_id"]
        trance_level = morld.get_unit_prop(pid, "상태:트랜스") or 0
        trance_keys = []
        if trance_level >= 80:  # TRANCE_DEEP
            trance_keys.append(f"trance_deep:{action_id}")
            trance_keys.append(f"trance:{action_id}")
        elif trance_level >= 60:  # TRANCE_ENTRY
            trance_keys.append(f"trance:{action_id}")

        partner_asset = get_partner_asset(state["partner_id"])
        if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
            reaction = None
            # 1. 트랜스 접두어 우선
            for tk in trance_keys:
                reaction = partner_asset.get_romance_reaction(
                    tk, timing, stim_state=state["stim"])
                if reaction:
                    return reaction
            # 2. 모드 접두사 (forced_ 등)
            if reaction_prefix:
                reaction = partner_asset.get_romance_reaction(
                    f"{reaction_prefix}{action_id}", timing, stim_state=state["stim"])
            # 3. 기본 반응
            if not reaction:
                reaction = partner_asset.get_romance_reaction(action_id, timing, stim_state=state["stim"])
            # 4. 공통 트랜스 fallback (캐릭터 전용 없는 경우)
            if not reaction and trance_keys:
                import random as _random
                pool = _GENERIC_TRANCE_DEEP if trance_level >= 80 else _GENERIC_TRANCE
                reaction = _random.choice(pool)
            return reaction

        # creature (bestiality): 종별 즉시 반응
        if state.get("is_bestiality") and timing == "start":
            import creature_reactions
            return creature_reactions.get_creature_instant_reaction(
                state["partner_id"], action_id)

        return None

    def _check_trance_auto_insert(state):
        """트랜스 NPC 자동 삽입 판정 (apply_effects 후 호출)"""
        stim_state = state["stim"]
        if not stimulation.is_trance(stim_state):
            return None
        peaked = stimulation.get_peaked_count(stim_state)
        if peaked < 2:
            return None
        if state["insertion"]["active"]:
            return None
        pid = state["partner_id"]
        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        if arousal < 50:
            return None
        # NPC 자동 삽입 (기승위) — 삽입 상태 활성화 + 허리흔들기
        state["insertion"]["active"] = True
        state["insertion"]["orifice"] = "vaginal"
        state["insertion"]["who"] = "npc"
        state["active_toggles"].add("thrust_normal")
        state["position"] = "cowgirl"
        return "npc_auto_insert"

    def _check_insertion_hard_fail(state, action_def, partner_id):
        """삽입 확정 실패 조건 체크. 실패 메시지 반환 또는 None."""
        # 0. 기생체 부착 시 삽입 불가
        orifice = action_def.get("insertion_orifice")
        if orifice:
            from romance_core import _ORIFICE_TO_PARASITE_SLOT
            parasite_slot = _ORIFICE_TO_PARASITE_SLOT.get(orifice)
            if parasite_slot and morld.get_unit_prop(partner_id, parasite_slot):
                part = parasite_slot.split(":")[1]
                return f"기생체가 {part}에 부착되어 삽입할 수 없다."

        # 1. 월경 중 삽입 거부 (soft block — 동적 임계치)
        if action_def.get("insertion_orifice") == "vaginal":
            import pregnancy as _pregnancy_mod
            if _pregnancy_mod.is_menstruating(partner_id):
                threshold = _get_menstruation_threshold(
                    partner_id, state["mode_ctx"]["mode"], state)
                if threshold > 0:
                    failed = state["insertion"]["failed_count"]
                    if failed < threshold:
                        return _get_menstruation_refusal(partner_id, failed)
                # threshold 도달 or threshold==0 → 삽입 허용
                state["menstruation_forced"] = (threshold > 0)
                state["menstruation_willing"] = (threshold == 0)

        # 2. 윤활 조건 미충족 (질삽입 시) → 항상 실패
        if action_def.get("insertion_orifice") == "vaginal":
            if not check_lubrication(partner_id, state):
                arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
                return f"아직 준비가 안 됐다. (성욕: {int(arousal)}/{LUBRICATION_THRESHOLD})"

        # 2. 크기 차이 + 자극 부족 → 항상 실패
        import gender as gender_mod
        compat = gender_mod.check_penetration_compatibility(
            state["player_id"], partner_id)
        if compat["needs_prep"] > 0:
            orifice = action_def.get("insertion_orifice", "vaginal")
            exp_part = _INSERTION_EXP_MAP.get(orifice, "음부")
            cat = SENSATION_MAP.get(exp_part, "V")
            target_stim = state["stim"]["stim"].get(cat, 0)
            if target_stim < compat["needs_prep"]:
                return (f"크기 차이로 더 준비가 필요하다. "
                        f"(자극: {int(target_stim)}/{compat['needs_prep']})")

        return None

    def _check_npc_autonomous_action(state):
        """NPC 자율 행동 판정 (가만히 있기 시 호출)

        Returns:
            dict {"type": str, "reaction": str} 또는 None
        """
        pid = state["partner_id"]
        stim = state["stim"]

        # 조건: 절정게이지 ≥ 80 AND 성욕 ≥ 60
        if stim["climax_gauge"] < 80:
            return None
        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        if arousal < 60:
            return None

        # 이미 삽입 중이면 스킵
        if state["insertion"]["active"]:
            return None

        # 월경 중 NPC 자율 삽입 차단
        import pregnancy as _pregnancy_auto
        if _pregnancy_auto.is_menstruating(pid):
            return None

        # 하체 노출 필요
        exposure = get_exposure_state(pid)
        if not exposure.get("lower_exposed"):
            return None

        # NPC에 P 해부학 필요 (삽입 주체)
        import gender as gender_mod
        if not gender_mod.has_anatomy(pid, "P"):
            return None

        # 플레이어 V 해부학 필요 (피삽입 대상)
        player_id = state["player_id"]
        if not gender_mod.has_anatomy(player_id, "V"):
            return None

        # 윤활 체크
        if not check_lubrication(pid, state):
            return None

        # NPC 자율 삽입 실행
        state["insertion"]["active"] = True
        state["insertion"]["orifice"] = "vaginal"
        state["insertion"]["who"] = "npc"

        # 체위 변경 (기승위)
        state["position"] = "cowgirl"

        # 자율 허리흔들기 시작
        state["active_toggles"].add("thrust_normal")

        # 크기 호환성 체크
        compat = gender_mod.check_penetration_compatibility(pid, player_id)
        state["size_pain"] = compat["pain"]
        state["size_stim_mod"] = compat["stim_mod"]

        # 처녀 체크
        check_and_clear_virginity(player_id, pid, "vaginal_insert")

        # 반응 텍스트
        reaction = _get_mode_reaction("npc_self_insert", "start")
        if not reaction:
            partner_info = morld.get_unit_info(pid)
            pname = partner_info.get("name", "상대") if partner_info else "상대"
            reaction = f"{pname}(이)가 스스로 올라탔다..."

        return {"type": "self_insert", "reaction": reaction}

    def _check_npc_beg_state(state):
        """NPC 애원 조건 확인 (삽입 시도 자동 성공 판정용)"""
        if state["insertion"]["active"]:
            return False
        stim = state["stim"]
        if stim["climax_gauge"] < 70:
            return False
        pid = state["partner_id"]
        arousal = morld.get_unit_prop(pid, "상태:성욕") or 0
        return arousal >= DES_LABEL_THRESHOLD

    def _do_parasite_removal(state, chosen_slot):
        """기생체 제거 실행 (선택 후 공통 경로)"""
        import parasite as parasite_mod
        pid = state["partner_id"]
        action_def = INSTANT_ACTIONS["remove_parasite_partner"]
        parasite_mod.remove_with_item(pid, chosen_slot)
        reaction = _get_mode_reaction("remove_parasite_partner", "start")
        state["last_reaction"] = reaction or "기생체를 제거했다."
        result = advance_time_and_check(state, action_def["time"])
        if result["interrupted"]:
            state["interrupted"] = True
            state["interrupter_id"] = result["interrupter_id"]
            return True
        if _post_action_mode_check():
            return True
        return render_romance_ui(state)

    def proc(action):
        # 일회성 강제 override — consensual 세션에서 "강제 {name}" 클릭 시
        # 해당 액션만 forced 효과 배율 + NPC 저항 체크. 완료 후 원래 모드 복원.
        # Why: 세션 전체 모드 전환 없이 액션 단위로 합의/강제 혼합 허용.
        _forced_override = False
        if action.startswith("force_instant:"):
            action = "instant:" + action[len("force_instant:"):]
            _forced_override = True
        elif action.startswith("force_toggle:"):
            action = "toggle:" + action[len("force_toggle:"):]
            _forced_override = True
        if _forced_override:
            _mode_ctx = state["mode_ctx"]
            state["_saved_mode"] = _mode_ctx["mode"]
            _mode_ctx["mode"] = MODE_FORCED
            _mode_ctx.setdefault("resistance_meter", 0)
            _mode_ctx.setdefault("break_free_attempts", 0)
            _mode_ctx.setdefault("last_escape_chance", 0.0)
        try:
            return _proc_dispatch(action)
        finally:
            if _forced_override:
                state["mode_ctx"]["mode"] = state.pop("_saved_mode", MODE_CONSENSUAL)

    def _proc_dispatch(action):
        if action == "init":
            return render_romance_ui(state)

        # 기생체 제거 선택 (proc 재진입)
        if action == "parasite_cancel":
            return render_romance_ui(state)
        if action.startswith("parasite_select:"):
            chosen_slot = action.split(":", 1)[1]
            return _do_parasite_removal(state, chosen_slot)

        # 체위 변경 확정
        if action.startswith("position:"):
            target_pos = action.split(":", 1)[1]
            state["pending_position_change"] = False
            state["available_positions"] = []
            current_pos = state.get("position", "missionary")
            if not position.can_transition(current_pos, target_pos):
                return render_romance_ui(state)

            # 의식불명 모드: 수동 체위만 허용
            mode_ctx = state["mode_ctx"]
            if mode_ctx["mode"] == MODE_UNCONSCIOUS and target_pos not in position.UNCONSCIOUS_INIT_POOL:
                state["last_reaction"] = "의식이 없는 상대방은 그 체위를 취할 수 없다."
                return render_romance_ui(state)

            # 강제 모드: 체위 변경 실패 가능성
            if mode_ctx["mode"] == MODE_FORCED:
                import random
                pid = state["partner_id"]
                escape_info = calculate_escape_chance(pid, state["player_id"])
                resist_chance = escape_info["chance"]
                mode_ctx["last_escape_chance"] = resist_chance
                if random.random() < resist_chance:
                    delta = escape_info["meter_delta"]
                    mode_ctx["resistance_meter"] += delta
                    if mode_ctx["resistance_meter"] >= 100:
                        state["escaped"] = True
                        return True
                    esc_msg = get_escape_attempt_message(pid, resist_chance)
                    state["last_reaction"] = f"체위를 변경하려 했으나 저항에 막혔다.\n{esc_msg}"
                    result = advance_time_and_check(state, 2 * MILLIS_PER_MINUTE)
                    if result["interrupted"]:
                        state["interrupted"] = True
                        state["interrupter_id"] = result["interrupter_id"]
                        return True
                    if _post_action_mode_check():
                        return True
                    return render_romance_ui(state)
                else:
                    # 성공: 저항 게이지 초기화
                    mode_ctx["resistance_meter"] = 0

            state["position"] = target_pos
            pos_name = position.get_name(target_pos)
            state["last_reaction"] = f"체위를 {pos_name}(으)로 변경했다."
            # 체위 변경 시 토글 해제:
            # 1. 삽입 토글 (thrust) — 물리적 재배치이므로 항상 해제
            for tid in list(state["active_toggles"]):
                if tid in _THRUST_TOGGLE_IDS:
                    state["active_toggles"].discard(tid)
            # 2. 배면 전환 시 입 사용 행위 추가 해제
            if position.get_facing(target_pos) == "back":
                mouth_toggles = {t for t in state["active_toggles"]
                                 if TOGGLE_ACTIONS.get(t, {}).get("uses_mouth")}
                for mt in mouth_toggles:
                    state["active_toggles"].discard(mt)
            # 시간 경과
            result = advance_time_and_check(state, 2 * MILLIS_PER_MINUTE)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True
            if _post_action_mode_check():
                return True
            return render_romance_ui(state)

        # 종료
        if action == "exit":
            return True

        # 공수 전환 (플레이어 → NPC 주도) — 합의 모드에서만
        if action == "switch":
            if not can_switch_initiative(state["mode_ctx"]["mode"]):
                return render_romance_ui(state)
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
            cur_mode = state["mode_ctx"]["mode"]
            # NPC thrust trance 종료 + 허리흔들기 토글 해제 + 삽입 상태 해제
            _end_npc_thrust_trance(state)
            for tid in list(state["active_toggles"]):
                if tid in _THRUST_TOGGLE_IDS:
                    state["active_toggles"].discard(tid)
            # 펠라치오 해제 (구강 사정의 경우)
            if "fellatio" in state["active_toggles"]:
                state["active_toggles"].discard("fellatio")
            # 삽입 상태 해제
            state["insertion"]["active"] = False
            state["insertion"]["orifice"] = None
            state["insertion"]["who"] = None
            state.pop("size_pain", None)
            state.pop("size_stim_mod", None)
            morld.set_unit_prop(pid, "크기통증", 0)
            # P 절정 강제 발동
            stim = state.get("stim")
            if stim:
                stimulation.force_ejaculate(stim)
            # 사정량 계산
            import gender as gender_mod
            p_holder_id = state["player_id"]
            if gender_mod.has_anatomy(pid, "P"):
                p_holder_id = pid
            ejac_amount = calculate_ejaculation_amount(p_holder_id, state["stamina"], state["max_stamina"])
            # 정액 적용 (시간정지: 지연)
            if cur_mode == MODE_FROZEN:
                defer_semen(state["mode_ctx"], target_part, ejac_amount)
            else:
                _apply_semen(pid, target_part, ejac_amount)
            # 경험 축적: 사정 횟수
            morld.set_unit_prop(pid, "경험:사정횟수",
                                (morld.get_unit_prop(pid, "경험:사정횟수") or 0) + 1)
            # 플레이어 통계: 총 사정량
            morld.set_unit_prop(player_id, "통계:총사정량",
                                (morld.get_unit_prop(player_id, "통계:총사정량") or 0) + ejac_amount)
            # 외부 사정 → 극감 수정 확률 (2%) — 콘돔 착용 시 스킵
            if target_part == "음부":
                if not (state["condom_active"] and not state["condom_punctured"]):
                    import pregnancy
                    import random
                    if random.random() < 0.02:
                        if cur_mode == MODE_FROZEN:
                            pregnancy.check_conception(state["player_id"], pid,
                                                       father_type="unknown")
                        else:
                            pregnancy.check_conception(state["player_id"], pid)
            # 반응 텍스트 (모드별 분기)
            reaction = None
            if ejac_amount >= 50:
                reaction = _get_mode_reaction(f"pull_out_{target_part}_heavy", "start")
            if not reaction:
                reaction = _get_mode_reaction(f"pull_out_{target_part}", "start")
            if reaction:
                state["last_reaction"] = reaction
            else:
                partner_info = morld.get_unit_info(pid)
                pname = partner_info.get('name', '상대') if partner_info else '상대'
                state["last_reaction"] = f"{pname}의 {target_part}에 사정했다."
            if should_emit_sound(state["mode_ctx"]["mode"]):
                emit_ecstasy_sound(pid)
            # 시간 경과
            result = advance_time_and_check(state, 3 * MILLIS_PER_MINUTE)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True
            if _post_action_mode_check():
                return True
            return render_romance_ui(state)

        # 즉시형 행위
        if action.startswith("instant:"):
            action_id = action.split(":")[1]
            action_def = INSTANT_ACTIONS.get(action_id)
            if not action_def:
                return None

            # 강제 행위 액션 (구 harassment.py에서 이관) — 비표준 side-effect로 분기
            # 임시노출/내구도/상태:절정 변동은 harassment.execute_* 헬퍼가 담당.
            # 일반 효과 파이프라인(호감/반발/복종 etc.)은 건너뜀.
            if action_def.get("harassment_exec"):
                import harassment as _harassment
                _handlers = {
                    "lift": _harassment.execute_lift,
                    "tear": _harassment.execute_tear,
                    "grope": _harassment.execute_grope,
                }
                _result = _handlers[action_def["harassment_exec"]](
                    state["player_id"], state["partner_id"], action_def)
                # 실패 시 UI 복귀
                if not _result.get("success"):
                    state["last_reaction"] = _result.get("message", "")
                    return render_romance_ui(state)
                # 관계 변동 + 반응 적용 (harassment.execute_action의 후처리 단축 버전)
                _mode_label = _harassment._get_response_mode(
                    state["player_id"], state["partner_id"])
                _harassment._apply_relationship_change(
                    state["player_id"], state["partner_id"], action_def, _mode_label)
                _reaction = _harassment._get_reaction_text(
                    state["partner_id"], action_id, _mode_label)
                _msg = _result.get("message", action_def["name"])
                state["last_reaction"] = _msg + (f"\n\"{_reaction}\"" if _reaction else "")
                # 절정 100 체크
                _climax = morld.get_unit_prop(state["partner_id"], "상태:절정") or 0
                if _climax >= 100:
                    import needs as _needs
                    _needs._trigger_passive_climax(state["partner_id"])
                    morld.set_unit_prop(state["partner_id"], "상태:절정", 0)
                    state["last_reaction"] += "\n절정에 달했다!"
                # 시간 경과 + 저항 체크
                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 활성 토글 필요 체크 (예: tongue_play → deep_kiss 활성 필요)
            req_toggle = action_def.get("requires_active_toggle")
            if req_toggle and req_toggle not in state["active_toggles"]:
                return render_romance_ui(state)

            # 삽입 중 즉시형: 유효성 + exp_part 동적 오버라이드
            if action_def.get("requires_active_insertion"):
                if not state["insertion"]["active"]:
                    return render_romance_ui(state)
                # exp_part가 None이면 삽입 부위에서 동적 결정
                if action_def.get("exp_part") is None:
                    orifice = state["insertion"]["orifice"]
                    pen_part = _INSERTION_EXP_MAP.get(orifice)
                    if pen_part:
                        action_def = dict(action_def)
                        action_def["exp_part"] = pen_part
                        # 질삽입이면 pregnancy_check 동적 설정
                        if orifice == "vaginal":
                            action_def["pregnancy_check"] = True

            # 삽입 시도 (성공/실패 판정)
            if action_def.get("is_insertion_attempt"):
                orifice = action_def["insertion_orifice"]
                pid = state["partner_id"]

                # 이미 삽입 중이면 무시
                if state["insertion"]["active"]:
                    state["last_reaction"] = "이미 삽입 중이다."
                    return render_romance_ui(state)

                # 정액 체크 (삽입자 발기 불가)
                try:
                    import semen as semen_mod
                    inserter_id = state["player_id"]
                    if not semen_mod.can_erect(inserter_id):
                        state["last_reaction"] = "발기를 유지할 수 없다."
                        return render_romance_ui(state)
                except ImportError:
                    pass

                # 확정 실패 조건 체크
                fail_result = _check_insertion_hard_fail(state, action_def, pid)
                if fail_result:
                    state["last_reaction"] = fail_result
                    state["insertion"]["failed_count"] += 1
                    result = advance_time_and_check(state, action_def["time"])
                    if result["interrupted"]:
                        state["interrupted"] = True
                        state["interrupter_id"] = result["interrupter_id"]
                        return True
                    if _post_action_mode_check():
                        return True
                    return render_romance_ui(state)

                # 확률 기반 저항 (강제 모드에서만)
                mode_ctx = state["mode_ctx"]
                if mode_ctx["mode"] == MODE_FORCED:
                    # NPC 애원 중이면 저항 스킵 (자동 성공)
                    if not _check_npc_beg_state(state):
                        import random
                        escape_info = calculate_escape_chance(pid, state["player_id"])
                        resist_chance = escape_info["chance"]
                        if random.random() < resist_chance:
                            state["insertion"]["failed_count"] += 1
                            msg = get_escape_attempt_message(pid, resist_chance)
                            state["last_reaction"] = "삽입하려 했지만 저항에 막혔다."
                            if msg:
                                state["last_reaction"] += f"\n{msg}"
                            mode_ctx["resistance_meter"] += escape_info["meter_delta"]
                            if mode_ctx["resistance_meter"] >= 100:
                                state["escaped"] = True
                                return True
                            result = advance_time_and_check(state, action_def["time"])
                            if result["interrupted"]:
                                state["interrupted"] = True
                                state["interrupter_id"] = result["interrupter_id"]
                                return True
                            return render_romance_ui(state)

                # 삽입 성공
                state["insertion"]["active"] = True
                state["insertion"]["orifice"] = orifice
                state["insertion"]["who"] = "player"
                state["insertion"]["failed_count"] = 0

                # 성공 시 반발 감소
                rebellion_key = get_rebellion_key(player_id)
                morld.modify_prop(pid, rebellion_key, -3)

                # 삽입 호환성 체크 (크기)
                import gender as gender_mod
                compat = gender_mod.check_penetration_compatibility(
                    player_id, state["partner_id"])
                state["size_pain"] = compat["pain"]
                state["size_stim_mod"] = compat["stim_mod"]
                if compat["pain"]:
                    rebellion_key_pain = get_rebellion_key(player_id)
                    morld.modify_prop(pid, rebellion_key_pain, 3)
                    morld.set_unit_prop(pid, "크기통증", 1)

                # 처녀 체크 + 부위별 첫경험 기록
                _virginity_exp_type = "bestiality" if state.get("is_bestiality") else state.get("mode", "consensual")
                first_key = check_and_clear_virginity(pid, player_id, action_id, exp_type=_virginity_exp_type)

                # 이하 일반 즉시형 처리로 fall-through (stamina/effects/time)

            # 멈추기 특수 처리 (허리흔들기 중단, 삽입 유지)
            if action_id == "thrust_stop":
                if not state["insertion"]["active"]:
                    return render_romance_ui(state)
                # NPC thrust trance 종료 + 허리흔들기 토글 전부 해제
                _end_npc_thrust_trance(state)
                for tid in list(state["active_toggles"]):
                    if tid in _THRUST_TOGGLE_IDS:
                        state["active_toggles"].discard(tid)
                state["last_reaction"] = "움직임을 멈췄다."
                reaction = _get_mode_reaction("thrust_stop", "start")
                if reaction:
                    state["last_reaction"] += "\n" + style_highlight(reaction)
                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 빼기 특수 처리
            if action_id == "withdraw":
                if not state["insertion"]["active"]:
                    return render_romance_ui(state)
                pid = state["partner_id"]
                orifice = state["insertion"]["orifice"]

                # NPC thrust trance 종료
                _end_npc_thrust_trance(state)

                # 활성 허리흔들기 토글 해제
                for tid in list(state["active_toggles"]):
                    if tid in _THRUST_TOGGLE_IDS:
                        state["active_toggles"].discard(tid)

                # 삽입 상태 해제
                state["insertion"]["active"] = False
                state["insertion"]["orifice"] = None
                state["insertion"]["who"] = None

                # 크기 관련 상태 정리
                state.pop("size_pain", None)
                state.pop("size_stim_mod", None)
                morld.set_unit_prop(pid, "크기통증", 0)

                # 체내 정액 있으면 흘러나옴 묘사
                internal_part = "음부" if orifice == "vaginal" else "항문"
                internal_amount = get_internal_semen(pid, internal_part)
                if internal_amount > 0:
                    drip = min(internal_amount, 20)
                    exp_part = _INSERTION_EXP_MAP.get(orifice, "음부")
                    _apply_semen(pid, exp_part, drip)
                    state["last_reaction"] = "빼냈다. 정액이 흘러나오고 있다..."
                else:
                    state["last_reaction"] = "빼냈다."

                reaction = _get_mode_reaction("withdraw", "start")
                if reaction:
                    state["last_reaction"] += "\n" + style_highlight(reaction)

                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 가만히 있기 특수 처리
            if action_id == "stay_still":
                pid = state["partner_id"]

                # 활성 토글 효과만 적용 (즉시형 효과 없음)
                active_toggle_defs = [TOGGLE_ACTIONS[t] for t in state["active_toggles"]]
                ecstasy = None
                if active_toggle_defs:
                    ecstasy = apply_effects(
                        {"effects": {}, "exp_part": None, "affection_req": 0,
                         "time": 0, "stamina": 0},
                        active_toggle_defs)
                    if ecstasy:
                        state["last_reaction"] = ecstasy
                        if should_emit_sound(state["mode_ctx"]["mode"]):
                            emit_ecstasy_sound(pid)
                    else:
                        state["last_reaction"] = "가만히 있는다..."
                else:
                    state["last_reaction"] = "가만히 있는다..."

                # 여운 반응 추가 (절정 미발생 시)
                _append_afterglow_reaction(ecstasy, state.get("_afterglow_result"))

                # NPC 자율 행동 판정
                npc_action = _check_npc_autonomous_action(state)
                if npc_action:
                    state["last_reaction"] = npc_action["reaction"]

                # NPC thrust trance 진입 판정 (삽입+정지 상태)
                if not npc_action:
                    trance_result = _check_npc_thrust_trance(state)
                    if trance_result:
                        state["last_reaction"] = trance_result["reaction"]
                    elif (state["insertion"]["active"]
                            and not any(t in _THRUST_TOGGLE_IDS
                                        for t in state["active_toggles"])):
                        # 트랜스 미진입 — 애원 반응 (대사 전용)
                        beg = _check_npc_beg_reaction(state)
                        if beg:
                            state["last_reaction"] = beg

                # 트랜스 강도 재평가
                _tick_npc_thrust_trance(state)

                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 체내 정액 필요 행위 유효성 검증
            req_internal = action_def.get("requires_internal_semen")
            if req_internal:
                if get_internal_semen(state["partner_id"], req_internal) <= 0:
                    return render_romance_ui(state)
                # 삼키기: M 감각 레벨에 따라 분기
                if action_id == "swallow_semen":
                    m_level = get_sensation_level(state["partner_id"], "M")
                    semen_amount = get_internal_semen(state["partner_id"], req_internal)
                    if m_level >= SWALLOW_M_THRESHOLD:
                        # 정상 삼키기
                        morld.clear_prop(state["partner_id"], f"체내:정액:{req_internal}")
                    elif m_level >= 3:
                        # 뱉기 — 구강 제거, 가슴에 일부 적용
                        morld.clear_prop(state["partner_id"], f"체내:정액:{req_internal}")
                        spit_amount = semen_amount // 2
                        if spit_amount > 0:
                            ext = morld.get_unit_prop(state["partner_id"], "오염물:정액:가슴") or 0
                            morld.set_unit_prop(state["partner_id"], "오염물:정액:가슴",
                                                min(100, ext + spit_amount))
                        action_id = "swallow_semen_spit"
                    elif m_level >= 1:
                        # 흘림 — 절반 제거, 나머지 외부
                        half = semen_amount // 2
                        morld.set_unit_prop(state["partner_id"], f"체내:정액:{req_internal}",
                                            max(0, semen_amount - half))
                        ext = morld.get_unit_prop(state["partner_id"], "오염물:정액:가슴") or 0
                        morld.set_unit_prop(state["partner_id"], "오염물:정액:가슴",
                                            min(100, ext + half))
                        action_id = "swallow_semen_drip"
                    else:
                        # 구역질 — 구강 유지, 반발 +2
                        rebellion_key = get_rebellion_key(player_id)
                        morld.modify_prop(state["partner_id"], rebellion_key, 2)
                        action_id = "swallow_semen_vomit"

            # 콘돔 전용 처리
            if action_def.get("is_condom_action"):
                if action_id == "condom_on":
                    if state["condom_active"]:
                        state["last_reaction"] = "이미 콘돔을 착용 중이다."
                        return render_romance_ui(state)
                    # 인벤토리에서 콘돔 찾기
                    inventory = morld.get_unit_inventory(player_id)
                    condom_item_id = None
                    condom_is_punctured = False
                    if inventory:
                        from assets.items import get_instance as get_item_instance
                        # 구멍 뚫린 콘돔 우선 사용
                        for iid in inventory:
                            inst = get_item_instance(int(iid))
                            if inst and getattr(inst, 'unique_id', '') == "condom":
                                if morld.get_unit_prop(int(iid), "상태:구멍") == 1:
                                    condom_item_id = int(iid)
                                    condom_is_punctured = True
                                    break
                        if not condom_item_id:
                            for iid in inventory:
                                inst = get_item_instance(int(iid))
                                if inst and getattr(inst, 'unique_id', '') == "condom":
                                    condom_item_id = int(iid)
                                    break
                    if not condom_item_id:
                        state["last_reaction"] = "콘돔이 없다."
                        return render_romance_ui(state)
                    morld.lost_item(player_id, condom_item_id)
                    state["condom_active"] = True
                    state["condom_punctured"] = condom_is_punctured
                    state["last_reaction"] = "콘돔을 착용했다."
                    return render_romance_ui(state)
                elif action_id == "condom_off":
                    if not state["condom_active"]:
                        return render_romance_ui(state)
                    state["condom_active"] = False
                    state["condom_punctured"] = False
                    # 트랜스 중: NPC가 인지 못함
                    if stimulation.is_trance(state["stim"]):
                        state["condom_removed_in_trance"] = True
                        state["last_reaction"] = "(...눈치채지 못한 것 같다.)"
                    else:
                        state["last_reaction"] = "콘돔을 제거했다."
                    return render_romance_ui(state)

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
                if state["stamina"] - total_stamina <= EXHAUSTION_HP_THRESHOLD:
                    state["exhausted"] = True
                    return True
                state["stamina"] -= total_stamina
                npc_result = _deduct_npc_stamina(state, total_stamina)
                if npc_result == "fainted" and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                    state["npc_faint_transition"] = True
                    return True
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

            # 옷 강탈 처리 (부위별: 장착 해제 + 이동)
            if action_def.get("loot"):
                is_upper = action_def["loot"] == "upper"
                item_id, is_equipped = get_next_loot_item(
                    state["partner_id"], upper=is_upper)
                if item_id is None:
                    return render_romance_ui(state)
                # 스태미나 처리
                total_stamina = action_def["stamina"]
                for toggle_id in state["active_toggles"]:
                    total_stamina += TOGGLE_ACTIONS[toggle_id]["stamina"]
                if state["stamina"] - total_stamina <= EXHAUSTION_HP_THRESHOLD:
                    state["exhausted"] = True
                    return True
                state["stamina"] -= total_stamina
                npc_result = _deduct_npc_stamina(state, total_stamina)
                if npc_result == "fainted" and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                    state["npc_faint_transition"] = True
                    return True
                # 아이템 이동: 장착해제(필요시) + NPC → 플레이어
                perform_loot(state["partner_id"], item_id, player_id,
                             is_equipped)
                item_info = morld.get_item_info(item_id)
                item_name = item_info.get("name", "옷") if item_info else "옷"
                partner_info = morld.get_unit_info(state["partner_id"])
                p_name = partner_info.get("name", "상대") if partner_info else "상대"
                state["last_reaction"] = f"{p_name}의 {item_name}을(를) 빼앗았다."
                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                return render_romance_ui(state)

            # 참기 특수 처리 (확률 기반 + 감쇠형)
            if action_id == "hold_back":
                stim_state = state["stim"]
                hb_result = stimulation.hold_back(stim_state)
                state["stamina"] = max(0, state["stamina"] - action_def["stamina"])

                if hb_result["success"]:
                    reaction = _get_mode_reaction("hold_back_success", "start")
                    state["last_reaction"] = reaction or f"(이를 악물고 참았다... -{hb_result['reduction']})"
                else:
                    # 실패: 게이지 오히려 증가
                    reaction = _get_mode_reaction("hold_back_failure", "start")
                    state["last_reaction"] = reaction or "(참으려 했지만 실패했다...!)"
                    # 실패 + 게이지 만충 + peaked 존재 → 즉시 절정
                    if hb_result["gauge"] >= stimulation.CLIMAX_GAUGE_MAX:
                        if stimulation.get_peaked_count(stim_state) > 0:
                            climax_info = stimulation.force_climax(stim_state)
                            if climax_info:
                                active_toggle_defs = [TOGGLE_ACTIONS[t] for t in state["active_toggles"]]
                                ecstasy = apply_effects(climax_info, active_toggle_defs)
                                # 사정 처리 (has_p인 경우)
                                if climax_info.get("has_p"):
                                    pid = state["partner_id"]
                                    cur_mode = state["mode_ctx"]["mode"]
                                    ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"], state["max_stamina"])
                                    # 정액 소모
                                    try:
                                        import semen as semen_mod
                                        semen_mod.consume_semen(player_id, semen_mod.EJACULATION_COST)
                                    except ImportError:
                                        pass
                                    insertion = state["insertion"]
                                    if insertion["active"]:
                                        orifice = insertion["orifice"]
                                        pen_part = _INSERTION_EXP_MAP.get(orifice)
                                        if pen_part and pen_part in ("음부", "항문"):
                                            if cur_mode == MODE_FROZEN:
                                                defer_semen(state["mode_ctx"], pen_part, ejac_amount, internal=True)
                                            else:
                                                _apply_internal_semen(pid, pen_part, ejac_amount)
                                            if orifice == "vaginal":
                                                if not (state["condom_active"] and not state["condom_punctured"]):
                                                    try:
                                                        import pregnancy
                                                        if cur_mode == MODE_FROZEN:
                                                            pregnancy.check_conception(player_id, pid,
                                                                                       father_type="unknown")
                                                        else:
                                                            pregnancy.check_conception(player_id, pid)
                                                    except ImportError:
                                                        pass
                                # 참기 실패 절정 → 체력 소모
                                _apply_climax_hp_cost(state, climax_info)
                                if state.get("npc_fainted") and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                                    state["npc_faint_transition"] = True
                                    return True

                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 사정하기 특수 처리
            if action_id == "ejaculate":
                # 정액 체크
                try:
                    import semen as semen_mod
                    if not semen_mod.can_ejaculate(player_id):
                        state["last_reaction"] = "사정할 수 없다."
                        return render_romance_ui(state)
                except ImportError:
                    pass

                stim_state = state["stim"]
                climax_info = stimulation.force_ejaculate(stim_state)
                pid = state["partner_id"]
                cur_mode = state["mode_ctx"]["mode"]

                # NPC thrust trance 종료 + 허리흔들기 토글 해제 (삽입 상태는 유지)
                _end_npc_thrust_trance(state)
                for tid in list(state["active_toggles"]):
                    if tid in _THRUST_TOGGLE_IDS:
                        state["active_toggles"].discard(tid)

                if climax_info and climax_info.get("has_p"):
                    insertion = state["insertion"]
                    ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"], state["max_stamina"])
                    # 정액 소모
                    try:
                        import semen as semen_mod
                        semen_mod.consume_semen(player_id, semen_mod.EJACULATION_COST)
                    except ImportError:
                        pass

                    # 삽입 중이면 내부 사정
                    pen_part = None
                    if insertion["active"]:
                        orifice = insertion["orifice"]
                        pen_part = _INSERTION_EXP_MAP.get(orifice)
                    elif "fellatio" in state["active_toggles"]:
                        pen_part = "구강"

                    if pen_part and pen_part in ("음부", "항문", "구강"):
                        if cur_mode == MODE_FROZEN:
                            defer_semen(state["mode_ctx"], pen_part, ejac_amount, internal=True)
                        else:
                            _apply_internal_semen(pid, pen_part, ejac_amount)
                        # 임신 판정 (질삽입)
                        if insertion["active"] and insertion["orifice"] == "vaginal":
                            if not (state["condom_active"] and not state["condom_punctured"]):
                                try:
                                    import pregnancy
                                    if cur_mode == MODE_FROZEN:
                                        pregnancy.check_conception(player_id, pid,
                                                                   father_type="unknown")
                                    else:
                                        pregnancy.check_conception(player_id, pid)
                                except ImportError:
                                    pass
                        # 경험/통계
                        morld.set_unit_prop(pid, "경험:사정횟수",
                                            (morld.get_unit_prop(pid, "경험:사정횟수") or 0) + 1)
                        morld.set_unit_prop(player_id, "통계:총사정량",
                                            (morld.get_unit_prop(player_id, "통계:총사정량") or 0) + ejac_amount)
                    elif pen_part:
                        if cur_mode == MODE_FROZEN:
                            defer_semen(state["mode_ctx"], pen_part, ejac_amount)
                        else:
                            _apply_semen(pid, pen_part, ejac_amount)

                    # 트랜스 중 콘돔 제거 발각
                    if state.get("condom_removed_in_trance"):
                        rebellion_key = get_rebellion_key(player_id)
                        morld.modify_prop(pid, rebellion_key, 5)
                        state["condom_removed_in_trance"] = False
                        state["last_reaction"] = "...콘돔이...빠져 있었...어...?"
                    else:
                        reaction = _get_mode_reaction("ejaculate", "start")
                        state["last_reaction"] = reaction or "사정했다."

                    if should_emit_sound(state["mode_ctx"]["mode"]):
                        emit_ecstasy_sound(pid)

                # 사정/절정 → 체력 소모
                if climax_info:
                    _apply_climax_hp_cost(state, climax_info)
                    if state.get("npc_fainted") and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                        state["npc_faint_transition"] = True
                        return True

                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 체위 변경 특수 처리
            if action_id == "change_position":
                current_pos = state.get("position", "missionary")
                transitions = position.get_available_transitions(current_pos)
                if not transitions:
                    state["last_reaction"] = "변경 가능한 체위가 없다."
                    return render_romance_ui(state)
                # 선택지 리턴 (UI에서 처리)
                state["pending_position_change"] = True
                state["available_positions"] = transitions
                return render_romance_ui(state)

            # 결박 장착 특수 처리
            if action_id == "restrain_partner":
                import restraint
                pid = state["partner_id"]
                # 플레이어 인벤에서 restraint 카테고리 아이템 탐색
                from assets.items import get_instance as get_item_instance
                inventory = morld.get_unit_inventory(player_id)
                restraint_item_id = None
                if inventory:
                    for iid in inventory:
                        inst = get_item_instance(int(iid))
                        if inst and getattr(inst, 'category', '') == "restraint":
                            restraint_item_id = int(iid)
                            break
                if restraint_item_id is None:
                    state["last_reaction"] = "결박 장비가 없다."
                    return render_romance_ui(state)
                # 스태미나 체크
                total_stamina = action_def["stamina"]
                for tid in state["active_toggles"]:
                    total_stamina += TOGGLE_ACTIONS[tid]["stamina"]
                if state["stamina"] - total_stamina <= EXHAUSTION_HP_THRESHOLD:
                    state["exhausted"] = True
                    return True
                state["stamina"] -= total_stamina
                npc_result = _deduct_npc_stamina(state, total_stamina)
                if npc_result == "fainted" and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                    state["npc_faint_transition"] = True
                    return True
                # 아이템 이동: 플레이어→NPC
                morld.remove_item(player_id, restraint_item_id, 1)
                morld.give_item(pid, restraint_item_id, 1)
                # 결박 시도
                cur_mode = state["mode_ctx"]["mode"]
                success, message = restraint.attempt_restrain(
                    player_id, pid, restraint_item_id, mode=cur_mode)
                if not success:
                    # 실패: 아이템 되돌리기
                    morld.remove_item(pid, restraint_item_id, 1)
                    morld.give_item(player_id, restraint_item_id, 1)
                    state["last_reaction"] = message
                else:
                    # 성공: 효과 적용
                    reb_key = get_rebellion_key(player_id)
                    morld.modify_prop(pid, reb_key, action_def["effects"].get("반발", 0))
                    sub_key = get_submission_key(player_id)
                    morld.modify_prop(pid, sub_key, action_def["effects"].get("복종", 0))
                    item_info = morld.get_item_info(restraint_item_id)
                    item_name = item_info.get("name", "결박 장비") if item_info else "결박 장비"
                    reaction = _get_mode_reaction("restrain_partner", "start")
                    state["last_reaction"] = reaction or f"{item_name}을(를) 채웠다."
                # 시간 진행
                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 결박 해제 특수 처리
            if action_id == "unrestrain_partner":
                import restraint
                import inventory as inv_mod
                pid = state["partner_id"]
                if not restraint.is_any_restrained(pid):
                    state["last_reaction"] = "결박 상태가 아니다."
                    return render_romance_ui(state)
                # 해제 + 아이템 회수
                released = restraint.release_unit_and_collect(pid)
                for item_id in released:
                    morld.remove_item(pid, item_id, 1)
                    inv_mod.safe_give_item(player_id, item_id, 1)
                reaction = _get_mode_reaction("unrestrain_partner", "start")
                state["last_reaction"] = reaction or "결박을 해제했다."
                result = advance_time_and_check(state, action_def["time"])
                if result["interrupted"]:
                    state["interrupted"] = True
                    state["interrupter_id"] = result["interrupter_id"]
                    return True
                if _post_action_mode_check():
                    return True
                return render_romance_ui(state)

            # 기생체 제거 특수 처리
            if action_id == "remove_parasite_partner":
                import parasite as parasite_mod
                pid = state["partner_id"]
                attached = parasite_mod.get_attached_parasites(pid)
                if not attached:
                    state["last_reaction"] = "부착된 기생체가 없다."
                    return render_romance_ui(state)

                # 선택 UI (1개면 자동 선택, 다수면 proc 재진입으로 선택 받기)
                if len(attached) == 1:
                    return _do_parasite_removal(state, attached[0][0])

                sel_lines = ["제거할 기생체 선택\n"]
                for slot, item_id, pname in attached:
                    part = slot.split(":")[1]
                    sel_lines.append(
                        f"[url=@proc:parasite_select:{slot}]{pname} ({part})[/url]")
                sel_lines.append("\n[url=@proc:parasite_cancel]취소[/url]")
                return "\n".join(sel_lines)

            # 체력 계산: 즉시형 + 활성 토글들
            total_stamina = action_def["stamina"]
            total_time = action_def["time"]

            active_toggle_defs = []
            for toggle_id in state["active_toggles"]:
                toggle_def = TOGGLE_ACTIONS[toggle_id]
                total_stamina += toggle_def["stamina"]
                active_toggle_defs.append(toggle_def)

            # 체력 부족 체크 (탈진 임계치 이하로 떨어지면 종료)
            if state["stamina"] - total_stamina <= EXHAUSTION_HP_THRESHOLD:
                state["exhausted"] = True
                return True  # 체력 부족 종료

            # 준비 부족 체크 (강도 행위)
            unprepared = not check_preparation(state["stim"], action_def)
            effective_action_def = action_def
            if unprepared:
                effective_action_def = dict(action_def)
                effective_action_def["effects"] = {
                    k: round(v * UNPREPARED_EFFECT_MULT)
                    for k, v in action_def["effects"].items()
                }
                effective_action_def["exp_part"] = None  # 경험치 미부여
                rebellion_key = get_rebellion_key(player_id)
                morld.modify_prop(state["partner_id"], rebellion_key, UNPREPARED_REBELLION)

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            npc_result = _deduct_npc_stamina(state, total_stamina)
            if npc_result == "fainted" and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                state["npc_faint_transition"] = True
                return True
            ecstasy_reaction = apply_effects(effective_action_def, active_toggle_defs)

            # 절정 후 NPC 기절 → MODE_UNCONSCIOUS 전이
            if state.get("npc_fainted") and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                state["npc_faint_transition"] = True
                return True

            # 마일스톤 기록 (첫 키스)
            if "kiss" in action_id and not morld.get_unit_prop(pid, "기억:첫키스"):
                morld.set_unit_prop(pid, "기억:첫키스", 1)

            # 행위 묘사 + 반응 결합
            desc = ACTION_DESCRIPTIONS.get(action_id, "")
            if ecstasy_reaction:
                if desc:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]\n{ecstasy_reaction}"
                else:
                    state["last_reaction"] = ecstasy_reaction
                if should_emit_sound(state["mode_ctx"]["mode"]):
                    emit_ecstasy_sound(state["partner_id"])
            else:
                # 월경 중 삽입 성공 반응 (강제/자발적)
                _m_forced = state.pop("menstruation_forced", False)
                _m_willing = state.pop("menstruation_willing", False)
                if _m_forced or _m_willing:
                    reaction = _get_menstruation_insertion_reaction(
                        pid, _m_forced, _m_willing)
                    # 강제 삽입 시 반발 증가
                    if _m_forced and state["mode_ctx"]["mode"] == "consensual":
                        rebellion_key = get_rebellion_key(player_id)
                        morld.modify_prop(pid, rebellion_key, 5)
                else:
                    reaction = _get_mode_reaction(action_id, "start")
                if desc and reaction:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]\n" + style_highlight(reaction)
                elif desc:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]"
                elif reaction:
                    state["last_reaction"] = style_highlight(reaction)
                if unprepared:
                    state["last_reaction"] = (state.get("last_reaction", "") +
                        "\n" + style_danger("(준비 부족 — 효과 감소)"))
                if should_emit_sound(state["mode_ctx"]["mode"]):
                    emit_romance_sound(state["partner_id"])

            # 여운 반응 추가 (절정 미발생 시)
            _append_afterglow_reaction(ecstasy_reaction, state.get("_afterglow_result"))

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            # 모드별 후처리 (저항/각성 체크)
            if _post_action_mode_check():
                return True

            # NPC 자율 thrust 체크 (삽입+정지 시 트랜스 진입) + 강도 재평가
            _try_npc_thrust_after_action(state, action_id)
            _tick_npc_thrust_trance(state)
            # NPC 자율 행위 루프 (삽입 없음 상태 — 봉사/자위/휴식 번갈아)
            _try_npc_autonomy_after_action(state, action_id)

            return render_romance_ui(state)

        # 토글형 행위
        if action.startswith("toggle:"):
            action_id = action.split(":")[1]
            action_def = TOGGLE_ACTIONS.get(action_id)
            if not action_def:
                return None

            # 토글 전환
            is_turning_on = action_id not in state["active_toggles"]
            # thrust 토글 재선택 시: OFF하지 않고 계속 유지 (효과 재적용)
            if not is_turning_on and action_id in _THRUST_TOGGLE_IDS:
                is_turning_on = True

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
            if state["stamina"] - total_stamina <= EXHAUSTION_HP_THRESHOLD:
                state["exhausted"] = True
                return True

            # 허리흔들기 ON 시: 삽입 상태 필요 + exp_part 동적 결정
            if is_turning_on and action_def.get("requires_active_insertion"):
                if not state["insertion"]["active"]:
                    state["last_reaction"] = "삽입 상태가 아니다."
                    return render_romance_ui(state)
                # exp_part 동적 결정
                if action_def.get("exp_part") is None:
                    orifice = state["insertion"]["orifice"]
                    action_def = dict(action_def)
                    action_def["exp_part"] = _INSERTION_EXP_MAP.get(orifice, "음부")
                    if orifice == "vaginal":
                        action_def["pregnancy_check"] = True

            # 토글 상태 변경
            if is_turning_on:
                # 같은 부위 토글 충돌 해소
                _remove_conflicting_toggles(action_id, state["active_toggles"])
                # 허리흔들기 토글끼리 충돌 (하나만 활성)
                # 플레이어가 직접 thrust 선택 → NPC trance 해제 (플레이어가 제어권 획득)
                if action_id in _THRUST_TOGGLE_IDS:
                    if state.get("npc_thrust_trance"):
                        state["npc_thrust_trance"] = False
                        state["active_toggles"].discard("sync_thrust")
                    for tid in list(state["active_toggles"]):
                        if tid in _THRUST_TOGGLE_IDS:
                            state["active_toggles"].discard(tid)
                state["active_toggles"].add(action_id)
            else:
                state["active_toggles"].discard(action_id)

            # 처녀(첫경험) 체크 — 토글 ON 시 (fellatio 등)
            first_key = None
            if is_turning_on:
                first_key = check_and_clear_virginity(
                    state["partner_id"], player_id, action_id)

            # 준비 부족 체크 (강도 행위 — 토글 ON 시)
            unprepared_toggle = is_turning_on and not check_preparation(state["stim"], action_def)
            effective_toggle_def = action_def
            if unprepared_toggle:
                effective_toggle_def = dict(action_def)
                effective_toggle_def["effects"] = {
                    k: round(v * UNPREPARED_EFFECT_MULT)
                    for k, v in action_def["effects"].items()
                }
                effective_toggle_def["exp_part"] = None
                rebellion_key = get_rebellion_key(player_id)
                morld.modify_prop(state["partner_id"], rebellion_key, UNPREPARED_REBELLION)

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            npc_result = _deduct_npc_stamina(state, total_stamina)
            if npc_result == "fainted" and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                state["npc_faint_transition"] = True
                return True
            ecstasy_reaction = apply_effects(effective_toggle_def, active_toggle_defs)

            # 절정 후 NPC 기절 → MODE_UNCONSCIOUS 전이
            if state.get("npc_fainted") and state["mode_ctx"]["mode"] != MODE_UNCONSCIOUS:
                state["npc_faint_transition"] = True
                return True

            # 행위 묘사 + 반응 결합
            desc = ACTION_DESCRIPTIONS.get(action_id, "") if is_turning_on else ""
            if ecstasy_reaction:
                if desc:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]\n{ecstasy_reaction}"
                else:
                    state["last_reaction"] = ecstasy_reaction
                if should_emit_sound(state["mode_ctx"]["mode"]):
                    emit_ecstasy_sound(state["partner_id"])
            else:
                if is_turning_on:
                    reaction = None
                    if first_key:
                        reaction = _get_mode_reaction(first_key, "start")
                    if not reaction:
                        reaction = _get_mode_reaction(action_id, "start")
                    if desc and reaction:
                        state["last_reaction"] = f"[color=silver]{desc}[/color]\n" + style_highlight(reaction)
                    elif desc:
                        state["last_reaction"] = f"[color=silver]{desc}[/color]"
                    elif reaction:
                        state["last_reaction"] = style_highlight(reaction)
                    if unprepared_toggle:
                        state["last_reaction"] = (state.get("last_reaction", "") +
                            "\n" + style_danger("(준비 부족 — 효과 감소)"))
                if should_emit_sound(state["mode_ctx"]["mode"]):
                    emit_romance_sound(state["partner_id"])

            # 여운 반응 추가 (절정 미발생 시)
            _append_afterglow_reaction(ecstasy_reaction, state.get("_afterglow_result"))

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            # 모드별 후처리 (저항/각성 체크)
            if _post_action_mode_check():
                return True

            # NPC 자율 thrust 체크 (삽입+정지 시 트랜스 진입) + 강도 재평가
            _try_npc_thrust_after_action(state, action_id)
            _tick_npc_thrust_trance(state)
            # NPC 자율 행위 루프 (삽입 없음 상태 — 봉사/자위/휴식 번갈아)
            _try_npc_autonomy_after_action(state, action_id)

            return render_romance_ui(state)

        return None

    # 연애 UI 시작
    yield ui.dialog(
        render_romance_ui(state),
        autofill="off",
        proc=proc,
        result=state
    )

    # 무의식→강제 전이: 새 세션 시작
    if state["wakeup_transition"]:
        preserved = extract_preserved(state)
        preserved["mode_ctx"] = state["mode_ctx"]
        yield ui.dialog("(상대가 의식을 되찾았다...!)")
        yield from start_romance(player_id, partner_id, preserved=preserved,
                                 mode=MODE_FORCED)
        return

    # NPC 기절 → MODE_UNCONSCIOUS 전이
    if state.get("npc_faint_transition"):
        survival.set_health(player_id, max(1, state["stamina"]))
        survival.set_health(partner_id, 1)  # 기절 시 HP=1 하한선
        survival._enter_faint(partner_id)
        partner_info = morld.get_unit_info(partner_id)
        partner_name = partner_info.get("name", "상대") if partner_info else "상대"
        preserved = extract_preserved(state)
        preserved["mode_ctx"] = create_mode_context(MODE_UNCONSCIOUS, player_id, partner_id)
        yield ui.dialog(f"({partner_name}(이)가 힘이 빠져 의식을 잃었다...)")
        yield from start_romance(player_id, partner_id, preserved=preserved,
                                 mode=MODE_UNCONSCIOUS)
        return

    # 공수 전환 — NPC 주도로 전환
    if state["switch_to"] == "npc":
        preserved = extract_preserved(state)
        from npc_initiative import start_npc_initiative
        yield from start_npc_initiative(player_id, partner_id, preserved=preserved)
        return

    # 로맨스 세션 종료 — think() 가드 해제
    morld.clear_prop(partner_id, "상태:로맨스중")

    # 종료 처리 - 양쪽 체력 기록 (HP 연동, 최소 1 보장)
    survival.set_health(player_id, max(1, state["stamina"]))
    survival.set_health(partner_id, max(1, state["npc_stamina"]))

    # 종료 처리 - 절정 게이지 → 상시 prop 동기화
    partner_id = state["partner_id"]
    final_climax = state["stim"].get("climax_gauge", 0)
    morld.set_unit_prop(partner_id, "상태:절정", max(0, min(100, final_climax)))

    # 파트너 스케줄 스택에서 pop (원래 스케줄 복원)
    mode_ctx = state["mode_ctx"]
    cur_mode = mode_ctx["mode"]
    partner_agent = think.get_agent(partner_id)

    # 착의 쿨다운 리셋 (탈의 후 즉시 착의 인터럽트 발동 가능하도록)
    if partner_agent:
        partner_agent._memory["clothing_last_attempt"] = None
        # 애정 행위 기억 저장
        loc = morld.get_unit_location(partner_id)
        partner_agent._memory["romance_last"] = {
            "partner_id": player_id,
            "region_id": loc[0] if loc else None,
            "location_id": loc[1] if loc else None,
            "timestamp": morld.get_game_time(),
            "mode": cur_mode,
        }

    # 경험 축적: 총 만남 횟수
    total_count = (morld.get_unit_prop(partner_id, "경험:총만남횟수") or 0) + 1
    morld.set_unit_prop(partner_id, "경험:총만남횟수", total_count)

    # 경험 축적: 모드별 횟수
    MODE_EXP_KEYS = {
        MODE_CONSENSUAL: "경험:합의횟수",
        MODE_FORCED: "경험:강제횟수",
        MODE_UNCONSCIOUS: "경험:무의식횟수",
        MODE_FROZEN: "경험:시간정지횟수",
    }
    mode_key = MODE_EXP_KEYS.get(cur_mode)
    if mode_key:
        mode_count = (morld.get_unit_prop(partner_id, mode_key) or 0) + 1
        morld.set_unit_prop(partner_id, mode_key, mode_count)

    # 마지막 경험 기록
    _last_exp_type = "bestiality" if state.get("is_bestiality") else cur_mode
    record_last_experience(partner_id, player_id, _last_exp_type)

    # 플레이어 통계: 총 만남/강제 횟수
    morld.set_unit_prop(player_id, "통계:총만남횟수",
                        (morld.get_unit_prop(player_id, "통계:총만남횟수") or 0) + 1)
    if cur_mode == MODE_FORCED:
        morld.set_unit_prop(player_id, "통계:강제횟수",
                            (morld.get_unit_prop(player_id, "통계:강제횟수") or 0) + 1)

    # 경험 축적: 질내 사정 (내부 정액 잔존)
    internal_vaginal = get_internal_semen(partner_id, "음부")
    if internal_vaginal > 0:
        vaginal_count = (morld.get_unit_prop(partner_id, "경험:질내사정") or 0) + 1
        morld.set_unit_prop(partner_id, "경험:질내사정", vaginal_count)

    # 모드별 종료 패널티 적용
    if cur_mode == MODE_FORCED:
        apply_forced_end_penalty(partner_id, mode_ctx, player_id)
    elif cur_mode == MODE_UNCONSCIOUS:
        apply_unconscious_end_state(partner_id, mode_ctx)
    elif cur_mode == MODE_FROZEN:
        # 시간정지: 축적된 지연 효과 일괄 적용 (30% 감쇠)
        apply_deferred_effects(partner_id, mode_ctx, player_id)

    if state["escaped"]:
        # NPC 저항 탈출 (강제 모드)
        if partner_agent:
            partner_agent.end_hold()
        # 마지막 행위 로그 포함 (탈출 직전 진행된 내용 표시)
        escape_lines = []
        last_reaction = state.get("last_reaction")
        if last_reaction:
            escape_lines.append(last_reaction)
        escape_lines.append("\n" + style_danger("상대가 빠져나갔다...!"))
        yield ui.dialog("\n".join(escape_lines))
        morld.pop_to_situation()
    elif state["exhausted"]:
        # 비정상 종료: 체력 소진
        if partner_agent:
            partner_agent.end_hold()
        yield ui.dialog("몸에 힘이 빠져 더 이상 움직일 수 없다...")
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
            partner_agent.end_hold()


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
        partner_agent.end_hold()
