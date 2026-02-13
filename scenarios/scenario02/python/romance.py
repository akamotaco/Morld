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
from romance_actions import (
    MILLIS_PER_MINUTE, SEMEN_PARTS, SEMEN_EXTERNAL_AMOUNT, SEMEN_INTERNAL_DRIP,
    INTERNAL_SEMEN_PARTS,
    UNPREPARED_EFFECT_MULT, UNPREPARED_REBELLION,
    SUBMISSION_ACTION_THRESHOLD, SUBMISSION_ACTION_GAIN, SUBMISSION_MAX,
    ROMANCE_ENTRY_THRESHOLD, ROMANCE_JOIN_THRESHOLD, DEFAULT_STAMINA,
    ECSTASY_THRESHOLD, SWALLOW_M_THRESHOLD,
    SENSATION_MAP, get_relationship_label,
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    _PENETRATION_TOGGLE_IDS,
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
    _calculate_hold_back_chance, is_hold_back_available, is_pull_out_available,
    check_preparation, check_lubrication,
    calculate_stealth_chance, check_stealth_success,
    get_excitement_level, emit_romance_sound, emit_ecstasy_sound,
    get_climax_reaction_key,
    extract_preserved,
)

ROMANCE_STAMINA_KEY = "연애:스태미나"

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
# 즉시형/토글형 행위 + 공유 핵심 로직: romance_actions.py / romance_core.py에서 import
# ============================================


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
    if state["near_miss"]:
        near_miss_id = state["near_miss_id"]
        near_info = morld.get_unit_info(near_miss_id) if near_miss_id else None
        near_name = near_info.get("name", "누군가") if near_info else "누군가"
        lines.append(f"[color=orange]({near_name}(이)가 근처를 지나갔다... 들키지 않았다.)[/color]")

        # 파트너의 은신 성공 반응 (캐릭터별 특별 대사)
        stealth_reaction = state["stealth_reaction"]
        if stealth_reaction:
            lines.append(f"[color=cyan][{partner_name}] {stealth_reaction}[/color]")
            state["stealth_reaction"] = None  # 표시 후 클리어

        lines.append("")
        state["near_miss"] = False  # 표시 후 클리어
        state["near_miss_id"] = None

    # 마지막 즉시 액션 반응 (있으면 표시 후 클리어)
    last_reaction = state["last_reaction"]
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

    # 체내 정액 표시
    internal_total = get_internal_semen_total(partner_id)
    if internal_total > 0:
        internal_parts = []
        for ip in INTERNAL_SEMEN_PARTS:
            val = get_internal_semen(partner_id, ip)
            if val > 0:
                internal_parts.append(f"{ip}: {val}")
        if internal_parts:
            lines.append(f"[color=pink]체내 정액: {', '.join(internal_parts)}[/color]")

    # 윤활 상태 표시
    import gender as gender_mod
    if gender_mod.has_anatomy(partner_id, "V"):
        if state["lubricated"]:
            lines.append("[color=green]윤활: 충분[/color]")
        else:
            arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
            lines.append(f"[color=red]윤활: 건조 (성욕 {int(arousal)}/{LUBRICATION_THRESHOLD})[/color]")

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
    has_penetration = _has_active_penetration(state["active_toggles"])
    lines.append("[즉시 행위]")
    for action_id, action in INSTANT_ACTIONS.items():
        if not is_anatomy_compatible(action, partner_id, actor_id=player_id):
            continue
        # 플레이어 자신의 해부학 요구사항 (hold_back 등)
        player_self_req = action.get("requires_player_anatomy_self")
        if player_self_req:
            import gender as gender_mod
            if not gender_mod.has_anatomy(player_id, player_self_req):
                continue
        # 삽입 중 즉시형: 삽입 토글 비활성 시 숨김
        if action.get("requires_active_penetration") and not has_penetration:
            continue
        # 체내 정액 필요 행위: 해당 부위 체내 정액 없으면 숨김
        req_internal = action.get("requires_internal_semen")
        if req_internal:
            if get_internal_semen(partner_id, req_internal) <= 0:
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
    # 참기 (삽입 중 + P 자극 ≥ 80)
    if is_hold_back_available(state):
        import gender as gender_mod
        if gender_mod.has_anatomy(state["player_id"], "P"):
            chance = _calculate_hold_back_chance(state["player_id"], state["stim"])
            lines.append(f"  [url=@proc:instant:hold_back]참기 ({chance}%)[/url]")
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
        "switch_to": None,
    }

    # 전환 시 보존 상태 복원
    if preserved:
        state["stim"] = preserved["stim"]
        state["stamina"] = preserved["stamina"]
        state["elapsed_time"] = preserved["elapsed_time"]
        state["lubricated"] = preserved.get("lubricated", False)
        state["checked_npcs"] = preserved.get("checked_npcs", set())

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
            # 삽입 크기 배율 적용
            size_mod = state["size_stim_mod"]
            if size_mod != 1.0 and act_def.get("exp_part") in ("음부", "엉덩이", "음경"):
                gain = round(gain * size_mod)
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
                    r2 = stimulation.apply(stim_state, extra_cat, extra_gain)
                    if r2 and not climax_info:
                        climax_info = r2

        # 삽입 중 플레이어 P 자극 축적
        if _has_active_penetration(state.get("active_toggles", set())):
            import gender as gender_mod
            if gender_mod.has_anatomy(player_id, "P"):
                p_base = sum(
                    a["effects"].get("성욕", 0)
                    for a in all_actions
                    if a.get("exp_part") in ("음부", "엉덩이")
                ) // 2
                p_gain = max(3, p_base)
                stim_state["stim"]["P"] = min(
                    stimulation.STIM_MAX,
                    stim_state["stim"].get("P", 0) + p_gain)

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
            exp_gain = stimulation.get_climax_sensation_gain(
                rebellion, climax_info.get("chain_count", 0))
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

            # 내부 사정 → 체내 정액 저장 (사정량 동적 계산)
            if ejac_part and ejac_part in ("음부", "항문", "구강"):
                import gender as _gm
                _p_holder = player_id
                if _gm.has_anatomy(pid, "P"):
                    _p_holder = pid
                _ejac_amt = calculate_ejaculation_amount(_p_holder, state["stamina"])
                _apply_internal_semen(pid, ejac_part, _ejac_amt)

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
            # 사정량 계산
            import gender as gender_mod
            p_holder_id = state["player_id"]
            if gender_mod.has_anatomy(pid, "P"):
                p_holder_id = pid
            ejac_amount = calculate_ejaculation_amount(p_holder_id, state["stamina"])
            # 정액 적용
            _apply_semen(pid, target_part, ejac_amount)
            # 외부 사정 → 극감 수정 확률 (2%)
            if target_part == "음부":
                import pregnancy
                import random
                if random.random() < 0.02:
                    pregnancy.check_conception(state["player_id"], pid)
            # 반응 텍스트 (대량 사정 우선)
            partner_asset = get_partner_asset(pid)
            reaction = None
            if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                if ejac_amount >= 50:
                    reaction = partner_asset.get_romance_reaction(f"pull_out_{target_part}_heavy", "start")
                if not reaction:
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
                    partner_asset = get_partner_asset(state["partner_id"])
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

            # 참기 특수 처리
            if action_id == "hold_back":
                import random
                chance = _calculate_hold_back_chance(player_id, state["stim"])
                state["stamina"] -= action_def["stamina"]
                partner_asset = get_partner_asset(state["partner_id"])
                if random.randint(1, 100) <= chance:
                    # 성공: P 자극 → 60으로 감소
                    state["stim"]["stim"]["P"] = 60
                    reaction = None
                    if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                        reaction = partner_asset.get_romance_reaction("hold_back_success", "start")
                    state["last_reaction"] = reaction or "참았다."
                else:
                    # 실패: 강제 P 절정 → 현재 삽입 대상에 내부 사정
                    pen_part = _get_active_penetration_part(state["active_toggles"])
                    ejac_amount = calculate_ejaculation_amount(player_id, state["stamina"])
                    if pen_part:
                        _apply_internal_semen(state["partner_id"], pen_part, ejac_amount)
                        # 임신 판정
                        if _has_active_intercourse(state["active_toggles"], TOGGLE_ACTIONS):
                            try:
                                import pregnancy
                                pregnancy.check_conception(player_id, state["partner_id"])
                            except ImportError:
                                pass
                    else:
                        _apply_semen(state["partner_id"], "body", ejac_amount)
                    # P 자극 리셋
                    import stimulation
                    stimulation.apply_climax_reset_p(state["stim"])
                    reaction = None
                    if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                        reaction = partner_asset.get_romance_reaction("hold_back_failure", "start")
                    state["last_reaction"] = reaction or "참지 못했다...!"
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
                    if unprepared:
                        state["last_reaction"] = (state.get("last_reaction", "") +
                            " (준비 부족 — 효과 감소)")
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

            # 윤활 체크 (질 삽입 ON 시)
            if is_turning_on and action_def.get("pregnancy_check"):
                if not check_lubrication(state["partner_id"], state):
                    arousal = morld.get_unit_prop(state["partner_id"], "상태:성욕") or 0
                    state["last_reaction"] = f"아직 준비가 안 됐다. (성욕: {int(arousal)}/{LUBRICATION_THRESHOLD})"
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
                    if unprepared_toggle:
                        state["last_reaction"] = (state.get("last_reaction", "") +
                            " (준비 부족 — 효과 감소)")
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
    if state["switch_to"] == "npc":
        preserved = extract_preserved(state)
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
