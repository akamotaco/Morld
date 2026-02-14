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
from romance_actions import (
    MILLIS_PER_MINUTE, SEMEN_PARTS,
    INTERNAL_SEMEN_PARTS,  # noqa: F401 — re-export (needs.py)
    UNPREPARED_EFFECT_MULT, UNPREPARED_REBELLION,
    SUBMISSION_ACTION_THRESHOLD, SUBMISSION_ACTION_GAIN, SUBMISSION_MAX,
    ROMANCE_ENTRY_THRESHOLD, ROMANCE_JOIN_THRESHOLD, DEFAULT_STAMINA,
    LUBRICATION_THRESHOLD, SWALLOW_M_THRESHOLD,
    SENSATION_MAP,
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    _PENETRATION_TOGGLE_IDS,
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
)
# 공유 핵심 로직: romance_core.py에서 import (+ 외부 모듈 호환 re-export)
from romance_core import (  # noqa: F401 — re-export for external callers
    get_character_asset as get_partner_asset,
    _get_relationship_key, get_affection_key, get_desire_key,
    get_rebellion_key, get_submission_key,
    get_effective_affection_req,
    get_sensation_level,
    is_action_available, is_desire_unlocked, is_anatomy_compatible,
    calculate_effects,
    get_exposure_state, get_next_undress_item, perform_undress,
    get_semen_total, _apply_semen, clear_all_semen,
    get_internal_semen, get_internal_semen_total,
    _apply_internal_semen, clear_all_internal_semen,
    calculate_ejaculation_amount,
    _PENETRATION_EXP_MAP,
    _get_active_penetration_part, _has_active_penetration,
    _has_active_intercourse, _get_penetration_exp_part,
    get_action_exp_part, get_conflicting_toggles, _remove_conflicting_toggles,
    check_and_clear_virginity,
    is_hold_back_available, is_ejaculate_available, is_pull_out_available,
    check_preparation, check_lubrication,
    calculate_stealth_chance, check_stealth_success,
    get_excitement_level, emit_romance_sound, emit_ecstasy_sound,
    get_climax_reaction_key,
    extract_preserved,
)

ROMANCE_STAMINA_KEY = "연애:스태미나"


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

                continue

            # 들킴 - 중단
            return {"interrupted": True, "interrupter_id": unit_id}
        # TODO: 합류 로직 (Phase 6)

    return {"interrupted": False}


# ============================================
# 메인 연애 함수
# ============================================

def start_romance(player_id, partner_id, preserved=None, mode=MODE_CONSENSUAL):
    """연애 모드 시작 - Generator 기반

    Args:
        player_id: 플레이어 유닛 ID
        partner_id: 파트너 유닛 ID
        preserved: 공수 전환 시 보존된 상태 (None이면 신규 세션)
        mode: 동작 모드 (MODE_CONSENSUAL/MODE_FORCED/MODE_UNCONSCIOUS/MODE_FROZEN)
    """

    # 진입 조건 체크 (전환 시 스킵 — 이미 세션 중)
    if not preserved and mode == MODE_CONSENSUAL:
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

    # 모드 컨텍스트 생성
    mode_ctx = create_mode_context(mode, player_id, partner_id)

    import gender as gender_mod
    # NPC 성적 선호 조회
    partner_asset_init = get_partner_asset(partner_id)
    npc_prefs = getattr(partner_asset_init, 'SEXUAL_PREFERENCES', None)
    is_npc_init = (mode != MODE_CONSENSUAL and mode != MODE_FROZEN)
    initial_position = position.select_initial_position(
        is_npc_initiative=is_npc_init, npc_prefs=npc_prefs)

    state = {
        # 핵심 (세션 수명)
        "player_id": player_id,
        "partner_id": partner_id,
        "active_toggles": set(),
        "stamina": initial_stamina,
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
    }

    # 전환 시 보존 상태 복원
    if preserved:
        state["stim"] = preserved["stim"]
        state["stamina"] = preserved["stamina"]
        state["elapsed_time"] = preserved["elapsed_time"]
        state["lubricated"] = preserved.get("lubricated", False)
        state["checked_npcs"] = preserved.get("checked_npcs", set())
        state["condom_active"] = preserved.get("condom_active", False)
        state["condom_punctured"] = preserved.get("condom_punctured", False)
        state["condom_removed_in_trance"] = preserved.get("condom_removed_in_trance", False)
        if "position" in preserved:
            state["position"] = preserved["position"]
        if "mode_ctx" in preserved:
            state["mode_ctx"] = preserved["mode_ctx"]

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
        _STAT_MULT_MAP = {
            "호감": "affection", "욕망": "desire", "반발": "rebellion",
            "복종": "submission", "성욕": "arousal",
        }

        # 효과 적용 (호감/욕망/성욕 prop 변경) — 모드 배율 반영
        for stat, value in effects.items():
            mult_key = _STAT_MULT_MAP.get(stat)
            if mult_key:
                value = round(value * multipliers.get(mult_key, 1.0))
            if value == 0:
                continue

            if cur_mode == MODE_FROZEN:
                # 시간정지: 효과 지연
                defer_effect(state["mode_ctx"], stat, value)
                continue

            if stat in ("성욕", "성적절정"):
                prop_key = f"상태:{stat}"
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
                    r2 = stimulation.apply(stim_state, extra_cat, extra_gain)
                    if r2 and not climax_info:
                        climax_info = r2

        # 삽입 중 플레이어 P 자극 축적 (P 감각에 따른 상승 감소)
        if _has_active_penetration(state.get("active_toggles", set())):
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
        stimulation.tick_afterglow(stim_state)

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
                # 임신 판정 (pregnancy_check 토글 활성 + P 보유자 절정 시)
                if _has_active_intercourse(state["active_toggles"], TOGGLE_ACTIONS):
                    import gender as gender_mod
                    if gender_mod.has_anatomy(pid, "P"):
                        # 콘돔: 정상 콘돔이면 임신 판정 스킵
                        if not (state["condom_active"] and not state["condom_punctured"]):
                            import pregnancy
                            if cur_mode == MODE_FROZEN:
                                pregnancy.check_conception(player_id, pid, father_type="unknown")
                            else:
                                pregnancy.check_conception(player_id, pid)
                        ejac_part = "음부"
                # P 절정 + 삽입 토글 활성 → 내부 사정 부위 판별
                if not ejac_part:
                    import gender as gender_mod
                    if gender_mod.has_anatomy(pid, "P"):
                        ejac_part = _get_active_penetration_part(state["active_toggles"])

                # 내부 사정 → 체내 정액 저장 (사정량 동적 계산)
                if ejac_part and ejac_part in ("음부", "항문", "구강"):
                    import gender as _gm
                    _p_holder = player_id
                    if _gm.has_anatomy(pid, "P"):
                        _p_holder = pid
                    _ejac_amt = calculate_ejaculation_amount(_p_holder, state["stamina"])
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

            partner_asset = get_partner_asset(pid)
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                reactions = getattr(partner_asset, 'ROMANCE_REACTIONS', {})
                # 내부 사정 반응 + 절정 반응 결합
                ejac_reaction = None
                if ejac_part:
                    ejac_key = f"{reaction_prefix}ejaculation_internal_{ejac_part}"
                    ejac_reaction = partner_asset.get_romance_reaction(ejac_key, "start")
                    if not ejac_reaction and reaction_prefix:
                        ejac_reaction = partner_asset.get_romance_reaction(
                            f"ejaculation_internal_{ejac_part}", "start")
                ecstasy_key = get_climax_reaction_key(
                    climax_info, state["active_toggles"], TOGGLE_ACTIONS, reactions)
                # 강제 모드: forced_ 접두사 시도 → fallback
                reaction = None
                if reaction_prefix:
                    reaction = partner_asset.get_romance_reaction(
                        f"{reaction_prefix}{ecstasy_key}", "start")
                if not reaction:
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

        # 무의식 모드: 각성 체크
        if cur_mode == MODE_UNCONSCIOUS:
            if check_wakeup(mode_ctx, state["partner_id"], 0):
                # 각성 → FORCED 전이
                transition_to_forced(mode_ctx)
                state["wakeup_transition"] = True
                return True  # UI 전환을 위해 일단 종료

        return False

    def _get_mode_reaction(action_id, timing="start"):
        """모드별 반응 텍스트 조회"""
        mode_ctx = state["mode_ctx"]
        cur_mode = mode_ctx["mode"]
        reaction_prefix = get_reaction_prefix(cur_mode)

        if reaction_prefix is None:
            # 무반응 모드: 나레이션
            return get_silent_narration(cur_mode)

        partner_asset = get_partner_asset(state["partner_id"])
        if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
            reaction = None
            # 접두사 있으면 먼저 시도 (forced_ 등)
            if reaction_prefix:
                reaction = partner_asset.get_romance_reaction(
                    f"{reaction_prefix}{action_id}", timing)
            # fallback: 기본 반응
            if not reaction:
                reaction = partner_asset.get_romance_reaction(action_id, timing)
            return reaction
        return None

    def _check_trance_auto_insert(state):
        """트랜스 NPC 자동 삽입 판정 (apply_effects 후 호출)"""
        stim_state = state["stim"]
        if not stimulation.is_trance(stim_state):
            return None
        peaked = stimulation.get_peaked_count(stim_state)
        if peaked < 2:
            return None
        if _has_active_penetration(state.get("active_toggles", set())):
            return None
        pid = state["partner_id"]
        desire_key = get_desire_key(state["player_id"])
        desire = morld.get_unit_prop(pid, desire_key) or 0
        if desire < 50:
            return None
        # NPC 자동 삽입 (기승위)
        state["active_toggles"].add("receive_penetration")
        state["position"] = "cowgirl"
        return "receive_penetration"

    def proc(action):
        if action == "init":
            return render_romance_ui(state)

        # 체위 변경 확정
        if action.startswith("position:"):
            target_pos = action.split(":", 1)[1]
            state["pending_position_change"] = False
            state["available_positions"] = []
            current_pos = state.get("position", "missionary")
            if not position.can_transition(current_pos, target_pos):
                return render_romance_ui(state)
            state["position"] = target_pos
            pos_name = position.get_name(target_pos)
            state["last_reaction"] = f"체위를 {pos_name}(으)로 변경했다."
            # 충돌하는 토글 해제 (배면 전환 시 입 사용 행위)
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
                stimulation.force_ejaculate(stim)
            # 사정량 계산
            import gender as gender_mod
            p_holder_id = state["player_id"]
            if gender_mod.has_anatomy(pid, "P"):
                p_holder_id = pid
            ejac_amount = calculate_ejaculation_amount(p_holder_id, state["stamina"])
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

            # 삽입 중 즉시형: 유효성 + exp_part 동적 오버라이드
            if action_def.get("requires_active_penetration"):
                if not _has_active_penetration(state["active_toggles"]):
                    return render_romance_ui(state)
                # exp_part가 None이면 활성 삽입 토글의 부위 상속
                if action_def.get("exp_part") is None:
                    pen_part = _get_penetration_exp_part(state["active_toggles"])
                    if pen_part:
                        action_def = dict(action_def)
                        action_def["exp_part"] = pen_part

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
                if state["stamina"] <= total_stamina:
                    state["stamina"] = 1  # 최소 1 보존
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
                                ecstasy = apply_effects.__wrapped__(climax_info, active_toggle_defs) if hasattr(apply_effects, '__wrapped__') else None
                                # 사정 처리 (has_p인 경우)
                                if climax_info.get("has_p"):
                                    pid = state["partner_id"]
                                    pen_part = _get_active_penetration_part(state["active_toggles"])
                                    cur_mode = state["mode_ctx"]["mode"]
                                    ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"])
                                    if pen_part and pen_part in ("음부", "항문", "구강"):
                                        if cur_mode == MODE_FROZEN:
                                            defer_semen(state["mode_ctx"], pen_part, ejac_amount, internal=True)
                                        else:
                                            _apply_internal_semen(pid, pen_part, ejac_amount)
                                        if _has_active_intercourse(state["active_toggles"], TOGGLE_ACTIONS):
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
                                    elif pen_part:
                                        if cur_mode == MODE_FROZEN:
                                            defer_semen(state["mode_ctx"], pen_part, ejac_amount)
                                        else:
                                            _apply_semen(pid, pen_part, ejac_amount)

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
                stim_state = state["stim"]
                climax_info = stimulation.force_ejaculate(stim_state)
                pid = state["partner_id"]
                cur_mode = state["mode_ctx"]["mode"]

                if climax_info and climax_info.get("has_p"):
                    pen_part = _get_active_penetration_part(state["active_toggles"])
                    ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"])

                    # 내부 사정
                    if pen_part and pen_part in ("음부", "항문", "구강"):
                        if cur_mode == MODE_FROZEN:
                            defer_semen(state["mode_ctx"], pen_part, ejac_amount, internal=True)
                        else:
                            _apply_internal_semen(pid, pen_part, ejac_amount)
                        # 임신 판정
                        if _has_active_intercourse(state["active_toggles"], TOGGLE_ACTIONS):
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
                state["stamina"] = 1  # 최소 1 보존
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
            ecstasy_reaction = apply_effects(effective_action_def, active_toggle_defs)

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
                reaction = _get_mode_reaction(action_id, "start")
                if desc and reaction:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]\n[color=yellow]{reaction}[/color]"
                elif desc:
                    state["last_reaction"] = f"[color=silver]{desc}[/color]"
                elif reaction:
                    state["last_reaction"] = f"[color=yellow]{reaction}[/color]"
                if unprepared:
                    state["last_reaction"] = (state.get("last_reaction", "") +
                        "\n[color=red](준비 부족 — 효과 감소)[/color]")
                if should_emit_sound(state["mode_ctx"]["mode"]):
                    emit_romance_sound(state["partner_id"])

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            # 모드별 후처리 (저항/각성 체크)
            if _post_action_mode_check():
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
                state["stamina"] = 1  # 최소 1 보존
                state["exhausted"] = True
                return True

            # 윤활 체크 (질 삽입 ON 시)
            if is_turning_on and action_def.get("pregnancy_check"):
                if not check_lubrication(state["partner_id"], state):
                    arousal = morld.get_unit_prop(state["partner_id"], "상태:성욕") or 0
                    state["last_reaction"] = f"아직 준비가 안 됐다. (성욕: {int(arousal)}/{LUBRICATION_THRESHOLD})"
                    return render_romance_ui(state)

            # 콘돔 요구 체크 (합의 모드 + 삽입 토글 ON 시)
            if is_turning_on and action_def.get("pregnancy_check"):
                cur_mode_t = state["mode_ctx"]["mode"]
                if cur_mode_t == MODE_CONSENSUAL and not state["condom_active"]:
                    partner_asset = get_partner_asset(state["partner_id"])
                    if partner_asset and getattr(partner_asset, 'requires_condom', False):
                        # 콘돔 체념 체크 (경험:콘돔속임 ≥ 3 → 요구 해제)
                        cheat_exp = morld.get_unit_prop(state["partner_id"], "경험:콘돔속임") or 0
                        if cheat_exp < 3:
                            partner_info_c = morld.get_unit_info(state["partner_id"])
                            p_name_c = partner_info_c.get("name", "상대") if partner_info_c else "상대"
                            state["last_reaction"] = f"{p_name_c}(이)가 콘돔 없이는 안 된다고 한다."
                            return render_romance_ui(state)

            # 삽입 호환성 체크 (크기 차이)
            if is_turning_on and action_id in _PENETRATION_TOGGLE_IDS:
                import gender as gender_mod
                player_anat = action_def.get("requires_player_anatomy")
                if player_anat == "P":
                    compat = gender_mod.check_penetration_compatibility(
                        player_id, state["partner_id"])
                elif player_anat in ("V", "A"):
                    compat = gender_mod.check_penetration_compatibility(
                        state["partner_id"], player_id)
                else:
                    compat = {"needs_prep": 0, "pain": False, "stim_mod": 1.0}
                # 준비 필요 시 자극 확인
                if compat["needs_prep"] > 0:
                    stim_state = state["stim"]
                    target_cat = SENSATION_MAP.get(action_def.get("exp_part", ""), "")
                    target_stim = stim_state["stim"].get(target_cat, 0) if target_cat else 0
                    if target_stim < compat["needs_prep"]:
                        state["last_reaction"] = (
                            f"크기 차이로 더 준비가 필요하다. "
                            f"(자극: {int(target_stim)}/{compat['needs_prep']})")
                        return render_romance_ui(state)
                # 통증/배율 저장
                state["size_pain"] = compat["pain"]
                state["size_stim_mod"] = compat["stim_mod"]
                if compat["pain"]:
                    rebellion_key = get_rebellion_key(player_id)
                    morld.modify_prop(state["partner_id"], rebellion_key, 3)
                    morld.set_unit_prop(state["partner_id"], "크기통증", 1)

            # 토글 상태 변경
            if is_turning_on:
                # 같은 부위 토글 충돌 해소
                _remove_conflicting_toggles(action_id, state["active_toggles"])
                state["active_toggles"].add(action_id)
            else:
                state["active_toggles"].discard(action_id)
                # 삽입 해제 시 크기 관련 상태 정리
                if action_id in _PENETRATION_TOGGLE_IDS:
                    state.pop("size_pain", None)
                    state.pop("size_stim_mod", None)
                    morld.set_unit_prop(state["partner_id"], "크기통증", 0)

            # 처녀(첫경험) 체크 — 토글 ON 시
            first_key = None
            if is_turning_on:
                first_key = check_and_clear_virginity(
                    state["partner_id"], player_id, action_id)

            # 마일스톤: 첫 경험 (삽입 토글 ON 시)
            if is_turning_on and action_def.get("pregnancy_check"):
                if not morld.get_unit_prop(pid, "기억:첫경험"):
                    morld.set_unit_prop(pid, "기억:첫경험", 1)

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
            ecstasy_reaction = apply_effects(effective_toggle_def, active_toggle_defs)

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
                        state["last_reaction"] = f"[color=silver]{desc}[/color]\n[color=yellow]{reaction}[/color]"
                    elif desc:
                        state["last_reaction"] = f"[color=silver]{desc}[/color]"
                    elif reaction:
                        state["last_reaction"] = f"[color=yellow]{reaction}[/color]"
                    if unprepared_toggle:
                        state["last_reaction"] = (state.get("last_reaction", "") +
                            "\n[color=red](준비 부족 — 효과 감소)[/color]")
                if should_emit_sound(state["mode_ctx"]["mode"]):
                    emit_romance_sound(state["partner_id"])

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            # 모드별 후처리 (저항/각성 체크)
            if _post_action_mode_check():
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

    # 무의식→강제 전이: 새 세션 시작
    if state["wakeup_transition"]:
        preserved = extract_preserved(state)
        preserved["mode_ctx"] = state["mode_ctx"]
        yield ui.dialog("(상대가 의식을 되찾았다...!)")
        yield from start_romance(player_id, partner_id, preserved=preserved,
                                 mode=MODE_FORCED)
        return

    # 공수 전환 — NPC 주도로 전환
    if state["switch_to"] == "npc":
        preserved = extract_preserved(state)
        from npc_initiative import start_npc_initiative
        yield from start_npc_initiative(player_id, partner_id, preserved=preserved)
        return

    # 종료 처리 - 파트너 스케줄 스택에서 pop (원래 스케줄 복원)
    partner_id = state["partner_id"]
    mode_ctx = state["mode_ctx"]
    cur_mode = mode_ctx["mode"]
    partner_agent = think.get_agent(partner_id)

    # 착의 쿨다운 리셋 (탈의 후 즉시 착의 인터럽트 발동 가능하도록)
    if partner_agent:
        partner_agent._memory["clothing_last_attempt"] = None

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
            partner_agent.pop_schedule()
        yield ui.dialog("상대가 빠져나갔다...!")
        morld.pop_to_situation()
    elif state["exhausted"]:
        # 비정상 종료: 체력 소진
        if partner_agent:
            partner_agent.pop_schedule()
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
