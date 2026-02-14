# romance_ui.py - 연애 UI 렌더링
"""
연애 세션의 UI 텍스트 생성

- render_stamina_bar(): 스태미나 바
- render_romance_ui(): 메인 연애 UI (상태 + 행위 목록)
"""

import morld
import ui
from romance_actions import (
    SEMEN_PARTS, INTERNAL_SEMEN_PARTS, DEFAULT_STAMINA,
    LUBRICATION_THRESHOLD,
    get_relationship_label,
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    _PENETRATION_TOGGLE_IDS,
)
from romance_core import (
    get_character_asset as get_partner_asset,
    get_affection_key, get_desire_key,
    get_rebellion_key, get_submission_key,
    get_sensation_level,
    is_action_available, is_anatomy_compatible,
    get_exposure_state,
    get_semen_total, get_internal_semen, get_internal_semen_total,
    _has_active_penetration,
    is_pull_out_available, is_hold_back_available, _calculate_hold_back_chance,
)


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

    # 모드 정보
    mode_ctx = state.get("mode_ctx")
    cur_mode = mode_ctx["mode"] if mode_ctx else "consensual"

    # 헤더
    partner_name = partner_info['name']
    _MODE_LABELS = {
        "consensual": "", "forced": " [color=red][강제][/color]",
        "unconscious": " [color=gray][무의식][/color]",
        "frozen": " [color=cyan][시간정지][/color]",
    }
    mode_label = _MODE_LABELS.get(cur_mode, "")
    lines.append(f"[{partner_name}와 함께]{mode_label}                 스태미나: {render_stamina_bar(player_stamina)}")

    # 저항 게이지 (강제 모드)
    if cur_mode == "forced" and mode_ctx:
        resistance = mode_ctx.get("resistance_meter", 0)
        lines.append(f"[color=red]저항: {'█' * (resistance // 10)}{'░' * (10 - resistance // 10)} {resistance}/100[/color]")
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
    if gender_mod.has_anatomy(partner_id, "V"):
        if state["lubricated"]:
            lines.append("[color=green]윤활: 충분[/color]")
        else:
            arousal = morld.get_unit_prop(partner_id, "상태:성욕") or 0
            lines.append(f"[color=red]윤활: 건조 (성욕 {int(arousal)}/{LUBRICATION_THRESHOLD})[/color]")

    # 콘돔 상태 표시
    if state.get("condom_active"):
        if state.get("condom_punctured"):
            lines.append("[color=yellow]콘돔 착용 중 (구멍)[/color]")
        else:
            lines.append("[color=green]콘돔 착용 중[/color]")

    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # 비합의 모드: 호감도 요구 무시
    _bypass_affection = cur_mode != "consensual"

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
            if _bypass_affection or is_action_available(partner_id, player_id, action):
                lines.append(f"  [color=gray]{action['name']} (탈의 필요)[/color]")
            else:
                lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
            continue
        if _bypass_affection or is_action_available(partner_id, player_id, action):
            prefix = "■" if is_on else "▶"
            name_text = action['name']
            # 노출 보너스 힌트
            bonus_area = action.get("exposure_bonus")
            if bonus_area and exposure.get(f"{bonus_area}_exposed"):
                name_text += " [color=pink]×1.5[/color]"
            lines.append(f"  [url=@proc:toggle:{action_id}][color=pink]{prefix} {name_text}[/color][/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 즉시 행위
    has_penetration = _has_active_penetration(state["active_toggles"])
    lines.append("[즉시 행위]")

    # 콘돔 버튼 (P 해부학 보유 시)
    if gender_mod.has_anatomy(player_id, "P"):
        if state.get("condom_active"):
            lines.append(f"  [url=@proc:instant:condom_off][color=cyan]콘돔 제거[/color][/url]")
        else:
            lines.append(f"  [url=@proc:instant:condom_on][color=cyan]콘돔 착용[/color][/url]")

    for action_id, action in INSTANT_ACTIONS.items():
        if action.get("is_condom_action"):
            continue  # 콘돔 액션은 위에서 별도 렌더링
        if not is_anatomy_compatible(action, partner_id, actor_id=player_id):
            continue
        # 플레이어 자신의 해부학 요구사항 (hold_back 등)
        player_self_req = action.get("requires_player_anatomy_self")
        if player_self_req:
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
            from romance_core import get_next_undress_item
            if get_next_undress_item(partner_id, upper=is_upper) is None:
                continue
        # 노출 필요 행위: 미노출 시 잠금 표시
        req_area = action.get("requires_exposure")
        if req_area and not exposure.get(f"{req_area}_exposed"):
            if _bypass_affection or is_action_available(partner_id, player_id, action):
                lines.append(f"  [color=gray]{action['name']} (탈의 필요)[/color]")
            else:
                lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
            continue
        if _bypass_affection or is_action_available(partner_id, player_id, action):
            name_text = action['name']
            lines.append(f"  [url=@proc:instant:{action_id}][color=pink]{name_text}[/color][/url]")
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
        if gender_mod.has_anatomy(state["player_id"], "P"):
            chance = _calculate_hold_back_chance(state["player_id"], state["stim"])
            lines.append(f"  [url=@proc:instant:hold_back]참기 ({chance}%)[/url]")
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

    return "\n".join(lines)
