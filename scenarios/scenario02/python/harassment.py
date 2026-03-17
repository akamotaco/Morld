# harassment.py - 성추행 시스템
#
# 옷 들추기/찢기 → 신체 노출 → 만지기 → 절정 게이지 상승.
# 관계 상태에 따라 효과 분기: welcome/unwanted/hostile.
# 전투/비전투 양방향 사용.

import random

import morld
from ui_style import style_highlight

# ========================================
# 상수
# ========================================

MILLIS_PER_MINUTE = 60_000
TEAR_DURABILITY_DAMAGE = 5

# 관계 임계치
AFFECTION_THRESHOLD_HIGH = 60   # 호감 ≥60: 환영 모드
REBELLION_THRESHOLD = 30         # 반발 ≥30: 적대 모드

# ========================================
# 액션 정의
# ========================================

HARASSMENT_ACTIONS = {
    # Phase 1: 의류 조작
    "lift_upper":    {"name": "상체 옷 들추기", "type": "lift",  "part": "upper",
                      "time": 3 * MILLIS_PER_MINUTE, "combat_time": 6_000},
    "lift_lower":    {"name": "하체 옷 들추기", "type": "lift",  "part": "lower",
                      "time": 3 * MILLIS_PER_MINUTE, "combat_time": 6_000},
    "tear_upper":    {"name": "상체 옷 찢기",   "type": "tear",  "part": "upper",
                      "time": 5 * MILLIS_PER_MINUTE, "combat_time": 8_000},
    "tear_lower":    {"name": "하체 옷 찢기",   "type": "tear",  "part": "lower",
                      "time": 5 * MILLIS_PER_MINUTE, "combat_time": 8_000},
    # Phase 2: 만지기 (노출 필요)
    "breast_grope":  {"name": "가슴 만지기",   "type": "grope", "part": "upper",
                      "requires_exposure": 2, "climax_gain": 8,  "exp_part": "가슴",
                      "time": 5 * MILLIS_PER_MINUTE, "combat_time": 10_000},
    "nipple_grope":  {"name": "유두 만지기",   "type": "grope", "part": "upper",
                      "requires_exposure": 2, "climax_gain": 10, "exp_part": "유두",
                      "time": 5 * MILLIS_PER_MINUTE, "combat_time": 10_000},
    "butt_grope":    {"name": "엉덩이 만지기", "type": "grope", "part": "lower",
                      "requires_exposure": 2, "climax_gain": 6,  "exp_part": "엉덩이",
                      "time": 5 * MILLIS_PER_MINUTE, "combat_time": 10_000},
    "genital_grope": {"name": "음부 만지기",   "type": "grope", "part": "lower",
                      "requires_exposure": 2, "climax_gain": 12, "exp_part": "음부",
                      "time": 5 * MILLIS_PER_MINUTE, "combat_time": 10_000},
}

# grope → casual_action 매핑 (welcome 모드에서 CASUAL_REACTIONS 재활용)
_GROPE_TO_CASUAL = {
    "breast_grope": "casual_breast",
    "nipple_grope": "casual_breast",
    "butt_grope": "casual_butt",
    "genital_grope": "casual_genital",
}

# ========================================
# 관계 기반 반응 모드
# ========================================

def _get_response_mode(source_id, target_id) -> str:
    """관계 상태 → 반응 모드 결정"""
    from romance_core import get_affection_key, get_rebellion_key
    props = morld.get_unit_props(target_id) or {}
    aff_key = get_affection_key(source_id)
    reb_key = get_rebellion_key(source_id)
    affection = props.get(aff_key, 0)
    rebellion = props.get(reb_key, 0)
    if rebellion >= REBELLION_THRESHOLD:
        return "hostile"
    if affection >= AFFECTION_THRESHOLD_HIGH:
        return "welcome"
    return "unwanted"


def _apply_relationship_change(source_id, target_id, action, mode):
    """관계 효과 적용 (모드별 분기)"""
    import combat
    source_name = (morld.get_unit_info(source_id) or {}).get("name", "?")
    action_type = action["type"]

    if mode == "welcome":
        # 성욕 상승 (CASUAL_ACTIONS과 유사)
        arousal_gain = action.get("climax_gain", 5)
        morld.modify_prop(target_id, "욕구:성욕", arousal_gain)
    elif mode == "hostile":
        # 적대치 대폭 증가
        hostility_map = {"lift": 15, "tear": 20, "grope": 25}
        combat.modify_hostility(target_id, source_name,
                                hostility_map.get(action_type, 15))
    else:  # unwanted
        # 호감 감소 + 반발 소폭 증가
        from romance_core import get_affection_key, get_rebellion_key
        aff_key = get_affection_key(source_id)
        reb_key = get_rebellion_key(source_id)
        aff_penalty = {"lift": -3, "tear": -5, "grope": -8}
        reb_gain = {"lift": 2, "tear": 3, "grope": 5}
        morld.modify_prop(target_id, aff_key,
                          aff_penalty.get(action_type, -5))
        morld.modify_prop(target_id, reb_key,
                          reb_gain.get(action_type, 3))


# ========================================
# 실행 함수
# ========================================

def _find_outermost_clothing(target_id, part):
    """해당 부위의 최외곽 의류 item_id 반환 (없으면 None)"""
    import equipment as _eq
    equipped = _eq.get_equipped_items(target_id)
    # 외투 → 상의/하의 → 속옷 순 (외곽부터)
    if part == "upper":
        slot_priority = ["착용:외투", "착용:상의", "착용:속옷상의"]
    else:
        slot_priority = ["착용:외투", "착용:하의", "착용:속옷하의"]

    for slot_key in slot_priority:
        for item_id in equipped:
            info = morld.get_item_info(item_id)
            if not info:
                continue
            ep = info.get("equip_props", {})
            if ep.get(slot_key):
                return item_id
    return None


def _has_clothing_for_part(target_id, part):
    """해당 부위에 의류가 있는지 확인"""
    return _find_outermost_clothing(target_id, part) is not None


def execute_lift(source_id, target_id, action_id) -> dict:
    """옷 들추기 — 임시노출 prop 설정"""
    action = HARASSMENT_ACTIONS[action_id]
    part = action["part"]
    prop_key = "임시노출:상체" if part == "upper" else "임시노출:하체"

    current = morld.get_unit_prop(target_id, prop_key) or 0
    if current >= 2:
        return {"success": False, "message": "이미 노출되어 있다."}

    # 의류 존재 여부에 따라 노출 수준 결정
    if _has_clothing_for_part(target_id, part):
        new_level = min(2, current + 1)
    else:
        new_level = 2

    morld.set_unit_prop(target_id, prop_key, new_level)
    return {"success": True, "message": action["name"]}


def execute_tear(source_id, target_id, action_id) -> dict:
    """옷 찢기 — 최외곽 의류 내구도 감소"""
    action = HARASSMENT_ACTIONS[action_id]
    part = action["part"]

    item_id = _find_outermost_clothing(target_id, part)
    if item_id is None:
        return {"success": False, "message": "찢을 옷이 없다."}

    import combat
    combat.degrade_durability(item_id, TEAR_DURABILITY_DAMAGE, owner_id=target_id)

    item_info = morld.get_item_info(item_id)
    item_name = item_info.get("name", "옷") if item_info else "옷"
    durability = morld.get_unit_prop(item_id, "내구도")
    if durability is not None and durability <= 0:
        return {"success": True, "message": f"{item_name}이(가) 찢어져 벗겨졌다!"}
    return {"success": True, "message": f"{item_name}을(를) 찢었다."}


def execute_grope(source_id, target_id, action_id) -> dict:
    """만지기 — 절정 게이지 직접 상승 (모드 무관)"""
    action = HARASSMENT_ACTIONS[action_id]
    required = action.get("requires_exposure", 0)

    # 노출 확인
    from assets.base import Character
    exposure = Character._calculate_exposure(target_id)
    exp_key = "upper" if action["part"] == "upper" else "lower"
    if exposure[exp_key] < required:
        return {"success": False, "message": "노출이 부족하다."}

    # 절정 게이지 상승
    climax_gain = action.get("climax_gain", 5)
    morld.modify_prop(target_id, "상태:절정", climax_gain)

    return {"success": True, "message": action["name"]}


def execute_action(source_id, target_id, action_id, is_combat=False) -> dict:
    """통합 실행"""
    action = HARASSMENT_ACTIONS.get(action_id)
    if not action:
        return {"success": False, "message": "알 수 없는 행위"}

    # 타입별 실행
    handlers = {"lift": execute_lift, "tear": execute_tear, "grope": execute_grope}
    result = handlers[action["type"]](source_id, target_id, action_id)
    if not result.get("success"):
        return result

    # 관계 기반 효과
    mode = _get_response_mode(source_id, target_id)
    _apply_relationship_change(source_id, target_id, action, mode)
    result["response_mode"] = mode

    # 반응 텍스트
    reaction = _get_reaction_text(target_id, action_id, mode)
    if reaction:
        result["reaction"] = reaction

    # 시간 진행
    duration = action["combat_time"] if is_combat else action["time"]
    morld.advance_time_des(duration)

    # 적대도 임계 체크
    import combat
    source_name = (morld.get_unit_info(source_id) or {}).get("name", "?")
    result["hostility_triggered"] = (
        combat.get_hostility(target_id, source_name) >= combat.HOSTILITY_HOSTILE)

    # 절정 100 체크
    climax = morld.get_unit_prop(target_id, "상태:절정") or 0
    if climax >= 100:
        import needs
        needs._trigger_passive_climax(target_id)
        morld.set_unit_prop(target_id, "상태:절정", 0)
        result["climax_triggered"] = True

    return result


# ========================================
# 반응 텍스트
# ========================================

# unwanted/hostile 기본 반응 (아키타입 미매칭 시)
_UNWANTED_REACTIONS = {
    "lift": ["...!", "뭐, 뭐 하는 거야!"],
    "tear": ["안 돼!", "그만해!"],
    "grope": ["하지 마...!", "싫어!"],
}
_HOSTILE_REACTIONS = {
    "lift": ["건드리지 마!", "죽고 싶어?!"],
    "tear": ["이 미친...!", "반드시 후회할 거야!"],
    "grope": ["꺼져!!", "죽여버리겠어!"],
}


def _get_reaction_text(target_id, action_id, mode):
    """관계 모드별 반응 텍스트"""
    action = HARASSMENT_ACTIONS.get(action_id)
    if not action:
        return None
    action_type = action["type"]

    if mode == "welcome" and action_type == "grope":
        # CASUAL_REACTIONS 재활용
        from assets.items import get_instance
        char = get_instance(target_id)
        if char:
            reactions = getattr(char, 'CASUAL_REACTIONS', {})
            casual_key = _GROPE_TO_CASUAL.get(action_id)
            if casual_key and casual_key in reactions:
                texts = reactions[casual_key].get("flirty",
                        reactions[casual_key].get("default", []))
                if texts:
                    return random.choice(texts)
        return None

    if mode == "hostile":
        pool = _HOSTILE_REACTIONS.get(action_type, [])
    elif mode == "unwanted":
        pool = _UNWANTED_REACTIONS.get(action_type, [])
    else:
        return None

    return random.choice(pool) if pool else None


# ========================================
# 가용 액션
# ========================================

def get_available_actions(source_id, target_id) -> list:
    """현재 사용 가능한 액션 ID 리스트"""
    from assets.base import Character
    exposure = Character._calculate_exposure(target_id)
    available = []
    for aid, action in HARASSMENT_ACTIONS.items():
        if action["type"] == "lift":
            prop = "임시노출:상체" if action["part"] == "upper" else "임시노출:하체"
            if (morld.get_unit_prop(target_id, prop) or 0) >= 2:
                continue
        elif action["type"] == "tear":
            if not _has_clothing_for_part(target_id, action["part"]):
                continue
        elif action["type"] == "grope":
            exp_key = "upper" if action["part"] == "upper" else "lower"
            if exposure[exp_key] < action.get("requires_exposure", 0):
                continue
        available.append(aid)
    return available


def has_temporary_exposure(unit_id) -> bool:
    """임시노출 상태 확인"""
    return bool((morld.get_unit_prop(unit_id, "임시노출:상체") or 0) +
                (morld.get_unit_prop(unit_id, "임시노출:하체") or 0))


def clear_temporary_exposure(unit_id):
    """임시노출 초기화"""
    morld.clear_prop(unit_id, "임시노출:상체")
    morld.clear_prop(unit_id, "임시노출:하체")


# ========================================
# 세션 UI (비전투)
# ========================================

def _build_session_ui(target_id, available, last_msg):
    """성추행 세션 UI 라인 생성"""
    target_info = morld.get_unit_info(target_id) or {}
    target_name = target_info.get("name", "대상")

    lines = [f"[b]{target_name}[/b]", ""]

    # 현재 노출 상태
    upper = morld.get_unit_prop(target_id, "임시노출:상체") or 0
    lower = morld.get_unit_prop(target_id, "임시노출:하체") or 0
    exp_labels = {0: "커버", 1: "속옷", 2: "노출"}
    lines.append(f"상체: {exp_labels.get(upper, '?')}  하체: {exp_labels.get(lower, '?')}")

    # 절정 게이지
    climax = morld.get_unit_prop(target_id, "상태:절정") or 0
    if climax > 0:
        lines.append(f"절정: {climax}%")

    if last_msg:
        lines.append("")
        lines.append(style_highlight(last_msg))

    lines.append("")

    # 가용 액션
    for aid in available:
        action = HARASSMENT_ACTIONS[aid]
        lines.append(f"[url=@ret:{aid}]{action['name']}[/url]")

    lines.append("")
    lines.append("[url=@ret:exit]그만두기[/url]")
    return lines


def harassment_session(source_id, target_id):
    """성추행 세션 — Generator (비전투)"""
    import ui
    last_msg = ""
    while True:
        available = get_available_actions(source_id, target_id)
        lines = _build_session_ui(target_id, available, last_msg)
        choice = yield ui.dialog("[!]" + "\n".join(lines) + "[/!]")
        if choice == "exit" or choice is None:
            break
        if choice not in HARASSMENT_ACTIONS:
            continue
        result = execute_action(source_id, target_id, choice, is_combat=False)
        action_name = HARASSMENT_ACTIONS[choice]["name"]
        last_msg = f"{action_name}: {result.get('message', '실행')}"
        if result.get("reaction"):
            last_msg += f"\n\"{result['reaction']}\""
        if result.get("hostility_triggered"):
            morld.add_action_log("상대가 적대적으로 변했다!")
            break
        if result.get("climax_triggered"):
            last_msg += "\n절정에 달했다!"
