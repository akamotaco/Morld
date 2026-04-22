# romance_ui.py - 연애 UI 렌더링
"""
연애 세션의 UI 텍스트 생성

- render_stamina_bar(): 스태미나 바
- render_romance_ui(): 메인 연애 UI (상태 + 행위 목록)
"""

import morld
import stimulation
import position
import ui
from ui_style import c, style_muted, style_info, style_danger, style_success, style_warning, style_highlight
from romance_actions import (
    SEMEN_PARTS, INTERNAL_SEMEN_PARTS,
    LUBRICATION_THRESHOLD,
    get_relationship_label,
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    _THRUST_TOGGLE_IDS, _INSERTION_EXP_MAP,
)
from romance_actions import TOGGLE_DURING_DESCRIPTIONS
from romance_core import (
    get_character_asset as get_partner_asset,
    get_affection_key,
    get_rebellion_key, get_submission_key,
    get_sensation_level,
    is_action_available, is_anatomy_compatible, is_action_blocked_by_state,
    check_physical_req, resolve_action_mode,
    get_exposure_state,
    get_semen_total, get_internal_semen, get_internal_semen_total,
    is_pull_out_available, is_hold_back_available, is_ejaculate_available,
    get_state_description,
)


def _get_partner_archetype(partner_id):
    """파트너 아키타입 조회"""
    partner_asset = get_partner_asset(partner_id)
    if partner_asset:
        profile = getattr(partner_asset, 'REACTION_PROFILE', None)
        if profile:
            return profile.get("archetype", "stoic")
    return "stoic"


# 수간(bestiality) 세션에서 사용 불가한 액션 (대화/구강/복잡한 스킨십 제외)
_BESTIALITY_BLOCKED_ACTIONS = frozenset({
    "head_pat", "french_kiss", "lip_kiss", "hug",
    "deep_kiss", "fellatio", "cunnilingus",
    "condom_on", "condom_off",
    "ear_whisper", "neck_kiss",
})


def _get_creature_reaction(state):
    """creature 종별 물리 반응 (토글 행위 during 묘사)"""
    import creature_reactions
    return creature_reactions.get_creature_toggle_reaction(
        state["partner_id"], state.get("stim")
    )


def render_stamina_bar(stamina, max_stamina=100):
    """체력 바 렌더링 (10칸 정규화)"""
    BAR_WIDTH = 10
    ratio = stamina / max(1, max_stamina)
    filled = max(0, min(BAR_WIDTH, round(ratio * BAR_WIDTH)))
    empty = BAR_WIDTH - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {int(stamina)}/{int(max_stamina)}"


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

    # 모드 정보
    mode_ctx = state.get("mode_ctx")
    cur_mode = mode_ctx["mode"] if mode_ctx else "consensual"

    # 헤더
    partner_name = partner_info['name']
    _MODE_LABELS = {
        "consensual": "", "forced": f" {style_danger('[강제]')}",
        "unconscious": f" {style_muted('[무의식]')}",
        "frozen": f" {style_info('[시간정지]')}",
    }
    mode_label = _MODE_LABELS.get(cur_mode, "")
    cur_pos = state.get("position", "missionary")
    pos_name_hdr = position.get_name(cur_pos)
    pos_facing_hdr = "대면" if position.get_facing(cur_pos) == "front" else "배면"
    max_stamina = state.get("max_stamina", 100)
    npc_stamina = state.get("npc_stamina", 100)
    npc_max = state.get("npc_max_stamina", 100)
    lines.append(f"[{partner_name}와 함께]{mode_label}  체위: {pos_name_hdr}({pos_facing_hdr})")
    lines.append(f"  체력: {render_stamina_bar(player_stamina, max_stamina)}  {partner_name}: {render_stamina_bar(npc_stamina, npc_max)}")

    # 저항 게이지 + 탈출 확률 (강제 모드)
    if cur_mode == "forced" and mode_ctx:
        resistance = mode_ctx.get("resistance_meter", 0)
        bar = "█" * (resistance // 10) + "░" * (10 - resistance // 10)
        escape_chance = mode_ctx.get("last_escape_chance", 0.0)
        escape_text = style_muted("불가능") if escape_chance <= 0 else f"{int(escape_chance * 100)}%"
        lines.append(style_danger(f"저항: {bar} {resistance}/100  탈출: {escape_text}"))

        # 신체 반응 묘사
        from romance_body_reaction import get_body_reaction
        archetype = _get_partner_archetype(partner_id)
        arousal = partner_props.get("상태:성욕", 0)
        stim_state_br = state.get("stim")
        gauge_br = stim_state_br.get("climax_gauge", 0) if stim_state_br else 0
        climax_br = stim_state_br.get("climax_total", 0) if stim_state_br else 0
        body_text = get_body_reaction(archetype, partner_name, arousal, gauge_br, climax_br)
        if body_text:
            lines.append(f"[color=magenta]({body_text})[/color]")
    lines.append("")

    # 근접 경고 (누군가 지나갔지만 들키지 않음)
    if state["near_miss"]:
        near_miss_id = state["near_miss_id"]
        near_info = morld.get_unit_info(near_miss_id) if near_miss_id else None
        near_name = near_info.get("name", "누군가") if near_info else "누군가"
        lines.append(style_warning(f"({near_name}(이)가 근처를 지나갔다... 들키지 않았다.)"))

        # 파트너의 은신 성공 반응 (캐릭터별 특별 대사)
        stealth_reaction = state["stealth_reaction"]
        if stealth_reaction:
            lines.append(style_info(f"[{partner_name}] {stealth_reaction}"))
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

    # 마지막 즉시 액션 반응 (있으면 표시 후 클리어)
    last_reaction = state["last_reaction"]
    if last_reaction:
        lines.append(last_reaction)  # 이미 color 태그 포함
        lines.append("")
        state["last_reaction"] = None  # 표시 후 클리어

    # 파트너 반응 텍스트 (활성 토글 기반 — 묘사 + NPC 대사)
    partner_asset = get_partner_asset(partner_id)
    has_toggle_lines = False
    for toggle_id in state["active_toggles"]:
        # 1. 행위 묘사 (항상)
        desc = TOGGLE_DURING_DESCRIPTIONS.get(toggle_id)
        if desc:
            lines.append(f"[color=silver]({desc})[/color]")
            has_toggle_lines = True

        # 2. NPC 대사/반응 (있으면)
        if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
            reaction = partner_asset.get_romance_reaction(toggle_id, "during", stim_state=state.get("stim"))
            if reaction:
                lines.append(f"  [color=yellow]{reaction}[/color]")
                has_toggle_lines = True
        elif state.get("is_bestiality"):
            # creature 기본 물리 반응 (대사 없음)
            creature_reaction = _get_creature_reaction(state)
            if creature_reaction:
                lines.append(f"  [color=yellow]{creature_reaction}[/color]")
                has_toggle_lines = True

    if not has_toggle_lines:
        if state.get("is_bestiality"):
            lines.append(f"({partner_name}(이)가 꿈틀거리고 있다.)")
        else:
            lines.append(f"({partner_name}(이)가 당신을 바라보고 있다.)")

    # 상태 묘사 (자극 수준 기반)
    stim_state = state.get("stim")
    if stim_state:
        import gender as gender_mod_desc
        partner_anatomy = gender_mod_desc.get_anatomy(partner_id)
        state_descs = get_state_description(stim_state, partner_anatomy)
        for sd in state_descs:
            lines.append(style_muted(sd))

    lines.append("")

    # 임신 상태 표시
    import pregnancy as _pregnancy_mod
    preg_text = _pregnancy_mod.get_pregnancy_status_text(partner_id)
    if preg_text:
        lines.append(preg_text)
        lines.append("")
    elif _pregnancy_mod.is_menstruating(partner_id):
        lines.append(style_warning("월경 중"))
        lines.append("")

    # 호감, 복종, 반발, 성욕 표시
    affection = partner_props.get(affection_key, 0)
    submission_key = get_submission_key(player_id)
    submission = partner_props.get(submission_key, 0)
    rebellion_key = get_rebellion_key(player_id)
    rebellion = partner_props.get(rebellion_key, 0)
    arousal = partner_props.get(arousal_key, 0)

    # 관계 라벨 (호감 + 성욕 기반)
    rel_label = get_relationship_label(affection, arousal)
    stat_line = f"[{rel_label}] 호감: {affection}  성욕: {arousal}"
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
        exposure_parts.append(c("pink", "상체 노출"))
    if exposure["lower_exposed"]:
        exposure_parts.append(c("pink", "하체 노출"))
    if exposure_parts:
        lines.append(f"복장: {' '.join(exposure_parts)}")

    # 정액 오염 표시
    semen_total = get_semen_total(partner_id)
    if semen_total > 0:
        if semen_total >= 60:
            lines.append(c("pink", "정액이 온몸에 흥건하다"))
        elif semen_total >= 30:
            lines.append(c("pink", "정액이 묻어 있다"))
        else:
            semen_detail = []
            for sp in SEMEN_PARTS:
                if (morld.get_unit_prop(partner_id, f"오염물:정액:{sp}") or 0) > 0:
                    semen_detail.append(sp)
            if semen_detail:
                lines.append(c("pink", f"정액: {', '.join(semen_detail)}"))

    # 체내 정액 표시
    internal_total = get_internal_semen_total(partner_id)
    if internal_total > 0:
        internal_parts = []
        for ip in INTERNAL_SEMEN_PARTS:
            val = get_internal_semen(partner_id, ip)
            if val > 0:
                internal_parts.append(f"{ip}: {val}")
        if internal_parts:
            lines.append(c("pink", f"체내 정액: {', '.join(internal_parts)}"))

    # 윤활 상태 표시
    if gender_mod.has_anatomy(partner_id, "V"):
        if state["lubricated"]:
            lines.append(style_success("윤활: 충분"))
        else:
            arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
            lines.append(style_danger(f"윤활: 건조 (성욕 {int(arousal)}/{LUBRICATION_THRESHOLD})"))

    # 콘돔 상태 표시
    if state.get("condom_active"):
        if state.get("condom_punctured"):
            lines.append(style_warning("콘돔 착용 중 (구멍)"))
        else:
            lines.append(style_success("콘돔 착용 중"))

    # 삽입 상태 표시
    insertion = state.get("insertion", {})
    is_inserted = insertion.get("active", False)
    if is_inserted:
        orifice_name = {"vaginal": "질", "anal": "항문"}.get(insertion.get("orifice"), "?")
        who_name = "플레이어" if insertion.get("who") == "player" else partner_name
        lines.append(style_danger(f"삽입 중 ({orifice_name}) — {who_name}"))
        # 현재 허리흔들기 강도
        active_thrust = None
        for tid in state["active_toggles"]:
            if tid in _THRUST_TOGGLE_IDS:
                active_thrust = TOGGLE_ACTIONS[tid]["name"]
                break
        if active_thrust:
            lines.append(f"  └ {active_thrust}")
        else:
            lines.append(f"  └ {style_muted('정지 (허리흔들기 선택 필요)')}")

    # NPC 애원 표시 (미삽입 + 높은 절정게이지/성욕/욕망)
    if not is_inserted:
        stim_beg = state.get("stim")
        if stim_beg and stim_beg.get("climax_gauge", 0) >= 70:
            from romance_actions import DES_LABEL_THRESHOLD
            beg_arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
            if beg_arousal >= max(50, DES_LABEL_THRESHOLD):
                lines.append(c("magenta", f"{partner_name}(이)가 삽입을 애원하고 있다..."))

    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # 비합의 모드: 호감도 요구 무시
    _bypass_affection = cur_mode != "consensual"

    # 토글 행위
    _intercourse_blocked = _pregnancy_mod.is_intercourse_blocked(partner_id)
    _is_bestiality = state.get("is_bestiality", False)
    lines.append("[토글 행위]")
    for action_id, action in TOGGLE_ACTIONS.items():
        if _is_bestiality and action_id in _BESTIALITY_BLOCKED_ACTIONS:
            continue
        if not is_anatomy_compatible(action, partner_id, actor_id=player_id):
            continue
        # physical_req (근력 등) — 물리 전제는 모드 무관 hard gate
        _ok_phys, _phys_reason = check_physical_req(action, partner_id, player_id)
        if not _ok_phys:
            lines.append(f"  {style_muted(action['name'] + ' (' + _phys_reason + ')')}")
            continue
        # 임신 후기: 삽입 행위 비활성화
        if _intercourse_blocked and action.get("pregnancy_check"):
            _aname = action['name']
            lines.append(f"  {style_muted(_aname + ' (임신 후기)')}")
            continue
        is_on = action_id in state["active_toggles"]
        # 허리흔들기 토글: 삽입 상태가 아니면 숨김 (이미 ON이면 해제 가능)
        if action.get("requires_active_insertion") and not is_on:
            if not is_inserted:
                continue
        # sync_thrust: NPC thrust trance 중에만 표시
        if action.get("requires_npc_thrust_trance") and not is_on:
            if not state.get("npc_thrust_trance"):
                continue
        # 결박/기생체/삽입물에 의한 차단 (이미 ON이면 해제 가능)
        blocked_reason = is_action_blocked_by_state(action, partner_id)
        if blocked_reason and not is_on:
            _aname = action['name']
            lines.append(f"  {style_muted(_aname + ' (' + blocked_reason + ')')}")
            continue
        # 배면 체위: 입 사용 행위 비활성화 (이미 ON이면 해제 가능)
        if action.get("uses_mouth") and not is_on:
            if position.get_facing(state.get("position", "missionary")) == "back":
                _aname = action['name']
                lines.append(f"  {style_muted(_aname + ' (배면 체위)')}")
                continue
        # 노출 필요 행위: 미노출 시 잠금 표시 (물리 전제 — 모드 무관)
        req_area = action.get("requires_exposure")
        if req_area and not exposure.get(f"{req_area}_exposed") and not is_on:
            lines.append(f"  {style_muted(action['name'] + ' (탈의 필요)')}")
            continue
        # 3상태 렌더링: consensual / forced / (unavailable은 위 physical_req에서 이미 처리)
        prefix = "■" if is_on else "▶"
        name_text = action['name']
        bonus_area = action.get("exposure_bonus")
        if bonus_area and exposure.get(f"{bonus_area}_exposed"):
            name_text += " " + c('pink', '×1.5')
        if _bypass_affection:
            # 세션 이미 비합의 (forced/unconscious/frozen) — 모든 액션 normal 렌더링
            lines.append(f"  [url=@proc:toggle:{action_id}]{c('pink', prefix + ' ' + name_text)}[/url]")
        else:
            mode = resolve_action_mode(partner_id, player_id, action)
            if mode == "consensual":
                lines.append(f"  [url=@proc:toggle:{action_id}]{c('pink', prefix + ' ' + name_text)}[/url]")
            else:  # forced — 호감 미달, 강제 옵션으로 노출
                lines.append(f"  [url=@proc:force_toggle:{action_id}]{style_danger(prefix + ' 강제 ' + name_text)}[/url]")
    lines.append("")

    # 즉시 행위
    lines.append("[즉시 행위]")

    # 콘돔 버튼 (P 해부학 보유 시, 수간 시 숨김)
    if not _is_bestiality and gender_mod.has_anatomy(player_id, "P"):
        if state.get("condom_active"):
            lines.append(f"  [url=@proc:instant:condom_off]{style_info('콘돔 제거')}[/url]")
        else:
            lines.append(f"  [url=@proc:instant:condom_on]{style_info('콘돔 착용')}[/url]")

    for action_id, action in INSTANT_ACTIONS.items():
        if _is_bestiality and action_id in _BESTIALITY_BLOCKED_ACTIONS:
            continue
        if action.get("is_condom_action"):
            continue  # 콘돔 액션은 위에서 별도 렌더링
        if action_id in ("hold_back", "ejaculate"):
            continue  # 특수 표시 영역에서 처리
        if action.get("npc_initiative_only"):
            continue  # NPC 주도 전용 행위는 일반 모드에서 숨김
        if not is_anatomy_compatible(action, partner_id, actor_id=player_id):
            continue
        # physical_req (근력 등) — 물리 전제는 모드 무관 hard gate
        _ok_phys, _phys_reason = check_physical_req(action, partner_id, player_id)
        if not _ok_phys:
            lines.append(f"  {style_muted(action['name'] + ' (' + _phys_reason + ')')}")
            continue
        # 삽입 시도: 이미 삽입 중이면 숨김
        if action.get("is_insertion_attempt") and is_inserted:
            continue
        # 삽입 상태 필요 즉시형: 삽입 중이 아니면 숨김
        if action.get("requires_active_insertion") and not is_inserted:
            continue
        # thrust_stop: 삽입 중 + thrust 활성일 때만 표시
        if action_id == "thrust_stop":
            if not any(t in _THRUST_TOGGLE_IDS for t in state.get("active_toggles", set())):
                continue
        # 활성 토글 필요 즉시형 (tongue_play → deep_kiss 필요)
        req_toggle = action.get("requires_active_toggle")
        if req_toggle and req_toggle not in state.get("active_toggles", set()):
            continue
        # 월경 중 질삽입: 클릭 가능하되 경고 표시
        if action_id == "vaginal_insert" and not is_inserted:
            if _pregnancy_mod.is_menstruating(partner_id):
                from romance import _get_menstruation_threshold
                threshold = _get_menstruation_threshold(
                    partner_id, cur_mode, state)
                failed = state["insertion"].get("failed_count", 0)
                if threshold > 0 and failed < threshold:
                    remaining = threshold - failed
                    hint = f" ({remaining})" if remaining > 1 else ""
                    _aname = action['name']
                    lines.append(
                        f"  [url=@proc:instant:vaginal_insert]"
                        f"{style_warning(_aname + ' (월경 중' + hint + ')')}"
                        f"[/url]")
                    continue
                # threshold==0 (자발적 수용) 또는 도달: 정상 렌더링
        # 결박/기생체/삽입물에 의한 차단
        blocked_reason = is_action_blocked_by_state(action, partner_id)
        if blocked_reason:
            _aname = action['name']
            lines.append(f"  {style_muted(_aname + ' (' + blocked_reason + ')')}")
            continue
        # 배면 체위: 입 사용 행위 비활성화
        if action.get("uses_mouth"):
            if position.get_facing(state.get("position", "missionary")) == "back":
                _aname = action['name']
                lines.append(f"  {style_muted(_aname + ' (배면 체위)')}")
                continue
        # 플레이어 자신의 해부학 요구사항 (hold_back 등)
        player_self_req = action.get("requires_player_anatomy_self")
        if player_self_req:
            if not gender_mod.has_anatomy(player_id, player_self_req):
                continue
        # 체내 정액 필요 행위: 해당 부위 체내 정액 없으면 숨김
        req_internal = action.get("requires_internal_semen")
        if req_internal:
            if get_internal_semen(partner_id, req_internal) <= 0:
                continue
        # 인벤토리 카테고리 필요 (결박 장비 등): 없으면 숨김
        req_inv_cat = action.get("requires_inventory_category")
        if req_inv_cat:
            from assets.items import get_instance as get_item_instance
            inv = morld.get_unit_inventory(player_id)
            found = False
            if inv:
                for iid in inv:
                    inst = get_item_instance(int(iid))
                    if inst and getattr(inst, 'category', '') == req_inv_cat:
                        found = True
                        break
            if not found:
                continue
        # 결박 해제: 결박 상태일 때만 표시
        if action_id == "unrestrain_partner":
            import restraint
            if not restraint.is_any_restrained(partner_id):
                continue
        # 기생체 제거: 기생체 부착 상태일 때만 표시
        if action_id == "remove_parasite_partner":
            import parasite as _parasite_mod
            if not _parasite_mod.has_any_parasite(partner_id):
                continue
        # 탈의 행위: 벗을 것 없으면 숨김
        if action.get("undress"):
            is_upper = action["undress"] == "upper"
            from romance_core import get_next_undress_item
            if get_next_undress_item(partner_id, upper=is_upper) is None:
                continue
        # 강탈 행위: 해당 부위에 강탈 가능한 의류 없으면 숨김
        if action.get("loot"):
            is_upper = action["loot"] == "upper"
            from romance_core import get_next_loot_item
            item_id, _ = get_next_loot_item(partner_id, upper=is_upper)
            if item_id is None:
                continue
        # 노출 필요 행위: 미노출 시 잠금 표시 (물리 전제 — 모드 무관)
        req_area = action.get("requires_exposure")
        if req_area and not exposure.get(f"{req_area}_exposed"):
            lines.append(f"  {style_muted(action['name'] + ' (탈의 필요)')}")
            continue
        # 3상태 렌더링: consensual / forced / (unavailable은 위 physical_req에서 이미 처리)
        name_text = action['name']
        if _bypass_affection:
            lines.append(f"  [url=@proc:instant:{action_id}]{c('pink', name_text)}[/url]")
        else:
            mode = resolve_action_mode(partner_id, player_id, action)
            if mode == "consensual":
                lines.append(f"  [url=@proc:instant:{action_id}]{c('pink', name_text)}[/url]")
            else:  # forced — 호감 미달, 강제 옵션으로 노출
                lines.append(f"  [url=@proc:force_instant:{action_id}]{style_danger('강제 ' + name_text)}[/url]")
    # 질외사정 (삽입 중 + P 자극 ≥ 임계값)
    if is_pull_out_available(state):
        lines.append("")
        lines.append("[질외사정]")
        for target in SEMEN_PARTS:
            lines.append(f"  [url=@proc:pull_out_target:{target}]{target}[/url]")
    # 참기 (peaked 부위 존재 + 게이지 > 0)
    if is_hold_back_available(state):
        hb_count = stim_state.get("hold_back_count", 0) if stim_state else 0
        chance = max(stimulation.HOLD_BACK_MIN_CHANCE,
                     stimulation.HOLD_BACK_BASE_CHANCE - hb_count * stimulation.HOLD_BACK_CHANCE_DECAY)
        reduction = max(stimulation.HOLD_BACK_REDUCTION_MIN,
                        stimulation.HOLD_BACK_REDUCTION - hb_count * stimulation.HOLD_BACK_REDUCTION_DECAY)
        lines.append(f"  [url=@proc:instant:hold_back]참기 (성공률 {chance}%, 성공 시 -{reduction})[/url]")
    # 사정하기 (P stim >= threshold)
    if is_ejaculate_available(state, state["player_id"]):
        p_stim = stim_state["stim"].get("P", 0) if stim_state else 0
        p_sensation = get_sensation_level(state["player_id"], "P")
        threshold = stimulation.get_ejaculate_threshold(p_sensation)
        lines.append(f"  [url=@proc:instant:ejaculate]사정하기 (P: {p_stim}/{threshold})[/url]")
    lines.append("")

    # 체위 변경 메뉴
    if state.get("pending_position_change"):
        lines.append("[체위 변경]")
        for pos in state.get("available_positions", []):
            pn = position.get_name(pos)
            pf = "대면" if position.get_facing(pos) == "front" else "배면"
            lines.append(f"  [url=@proc:position:{pos}]{pn} ({pf})[/url]")
        lines.append("")

    # 푸터
    lines.append(ui.divider())

    # 공수 전환 버튼 (합의 모드 + NPC 주도 가능 시만)
    if cur_mode == "consensual":
        partner_asset = get_partner_asset(partner_id)
        if partner_asset and getattr(partner_asset, 'INITIATIVE_CONFIG', None):
            init_aff_threshold = partner_asset.INITIATIVE_CONFIG.get("affection_threshold", 60)
            if affection >= init_aff_threshold:
                lines.append("[url=@proc:switch]주도권 넘기기[/url]")

    lines.append("[url=@proc:exit]그만두기[/url]")

    return "[!]" + "\n".join(lines) + "[/!]"
