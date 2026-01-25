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

# ============================================
# 즉시형 행위 정의
# ============================================

INSTANT_ACTIONS = {
    "head_pat": {
        "name": "머리 쓰다듬기", "time": 3, "stamina": 1,
        "effects": {"호감": 2, "애정": 1},
        "exp_part": None, "affection_req": 40
    },
    "cheek_caress": {
        "name": "뺨 어루만지기", "time": 2, "stamina": 1,
        "effects": {"호감": 1, "애정": 1},
        "exp_part": None, "affection_req": 30
    },
    "cheek_pinch": {
        "name": "뺨 꼬집기", "time": 2, "stamina": 1,
        "effects": {"호감": 1},
        "exp_part": None, "affection_req": 35
    },
    "ear_touch": {
        "name": "귀 만지기", "time": 3, "stamina": 1,
        "effects": {"호감": 1, "애정": 1, "성욕": 1},
        "exp_part": "귀", "affection_req": 45
    },
    "whisper": {
        "name": "사랑의 속삭임", "time": 2, "stamina": 1,
        "effects": {"호감": 2, "애정": 3},
        "exp_part": None, "affection_req": 50
    },
    "french_kiss": {
        "name": "프렌치 키스", "time": 5, "stamina": 2,
        "effects": {"호감": 1, "애정": 2, "성욕": 3},
        "exp_part": "입술", "affection_req": 60
    },
    "butt_caress": {
        "name": "엉덩이 쓰다듬기", "time": 3, "stamina": 2,
        "effects": {"애정": 1, "성욕": 3},
        "exp_part": "엉덩이", "affection_req": 70
    },
}

# ============================================
# 토글형 행위 정의
# ============================================

TOGGLE_ACTIONS = {
    "hug": {
        "name": "껴안기", "time": 5, "stamina": 1,
        "effects": {"호감": 1, "애정": 2},
        "exp_part": None, "affection_req": 50
    },
    "deep_kiss": {
        "name": "딥키스", "time": 5, "stamina": 2,
        "effects": {"호감": 1, "애정": 2, "성욕": 3},
        "exp_part": "입술", "affection_req": 70
    },
    "breast_touch": {
        "name": "가슴 만지기", "time": 5, "stamina": 2,
        "effects": {"애정": 1, "성욕": 4},
        "exp_part": "가슴", "affection_req": 80
    },
}

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


def calculate_effects(action_def, partner_id):
    """경험치 보정된 효과 계산"""
    base_effects = action_def["effects"].copy()
    exp_part = action_def.get("exp_part")

    if exp_part:
        # 경험치 조회 (NPC별로 저장)
        exp_key = f"경험:{exp_part}"
        partner_props = morld.get_unit_props(partner_id)
        exp_value = partner_props.get(exp_key, 0)

        # 배율 계산: 1.0 + (경험 × 0.1)
        multiplier = 1.0 + (exp_value * 0.1)

        # 효과 적용 (반올림)
        for stat, value in base_effects.items():
            base_effects[stat] = round(value * multiplier)

        # 경험치 +1
        morld.modify_prop(partner_id, exp_key, 1)

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
    # 관계 타입: 호감, 애정 → 관계:플레이어:stat
    # 상태 타입: 성욕, 성적절정 → 상태:stat (개인 상태)
    affection_key = get_affection_key(player_id)
    love_key = affection_key.replace(":호감", ":애정")
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

    # 호감, 애정, 성욕 표시
    affection = partner_props.get(affection_key, 0)
    love = partner_props.get(love_key, 0)
    arousal = partner_props.get(arousal_key, 0)
    lines.append(f"호감: {affection}  애정: {love}  성욕: {arousal}")
    lines.append("")
    lines.append(ui.divider())
    lines.append("")

    # 토글 행위
    lines.append("[토글 행위]")
    for action_id, action in TOGGLE_ACTIONS.items():
        is_on = action_id in state["active_toggles"]
        if affection >= action["affection_req"]:
            prefix = "■" if is_on else "▶"
            lines.append(f"  [url=@proc:toggle:{action_id}]{prefix} {action['name']}[/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 즉시 행위
    lines.append("[즉시 행위]")
    for action_id, action in INSTANT_ACTIONS.items():
        if affection >= action["affection_req"]:
            lines.append(f"  [url=@proc:instant:{action_id}]{action['name']}[/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 푸터
    lines.append(ui.divider())
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


def advance_time_and_check(state, minutes):
    """시간 경과 + NPC 도착 체크 (은신 확률 적용)"""
    # 1. 시간 진행 + NPC 이동 시뮬레이션
    morld.advance_time_simulate(minutes)
    state["elapsed_time"] += minutes

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

def start_romance(player_id, partner_id):
    """연애 모드 시작 - Generator 기반"""

    # 진입 조건 체크
    can_start, reason = can_start_romance(player_id, partner_id)
    if not can_start:
        yield morld.dialog(reason)
        return

    # 파트너 NPC를 현재 위치에 고정 (스킨십 동안 이동 방지)
    # 스케줄 스택에 STAY_SCHEDULE push, 종료 시 pop으로 복원
    import think
    partner_agent = think.get_agent(partner_id)
    if partner_agent:
        partner_agent.push_schedule(think.BaseAgent.STAY_SCHEDULE)

    # 플레이어 스태미나 조회 (연애 전용)
    player_props = morld.get_unit_props(player_id)
    initial_stamina = player_props.get(ROMANCE_STAMINA_KEY, DEFAULT_STAMINA)

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
    }

    def apply_effects(action_def, active_toggle_defs):
        """
        행위 효과 적용 (즉시형 + 활성 토글들)

        Returns:
            절정 반응 텍스트 또는 None
        """
        pid = state["partner_id"]
        player_id = state["player_id"]
        affection_key = get_affection_key(player_id)

        # 즉시형/토글 행위의 효과 (경험치 보정 포함)
        effects = calculate_effects(action_def, pid)

        # 활성 토글들의 효과도 합산
        for toggle_def in active_toggle_defs:
            toggle_effects = calculate_effects(toggle_def, pid)
            for stat, value in toggle_effects.items():
                effects[stat] = effects.get(stat, 0) + value

        # 효과 적용
        # 관계 타입: 호감, 애정 → 관계:플레이어:stat
        # 상태 타입: 성욕, 성적절정 → 상태:stat (개인 상태)
        for stat, value in effects.items():
            if stat in ("성욕", "성적절정"):
                prop_key = f"상태:{stat}"
            else:
                prop_key = affection_key.replace(":호감", f":{stat}")
            morld.modify_prop(pid, prop_key, value)

        # 절정 체크 (성욕 >= 100이면 절정 발생)
        return check_ecstasy(pid)

    def proc(action):
        if action == "init":
            return render_romance_ui(state)

        # 종료
        if action == "exit":
            return True

        # 즉시형 행위
        if action.startswith("instant:"):
            action_id = action.split(":")[1]
            action_def = INSTANT_ACTIONS.get(action_id)
            if not action_def:
                return None

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
            else:
                # 캐릭터별 반응 텍스트 (start 타이밍)
                partner_asset = get_partner_asset(state["partner_id"])
                if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                    reaction = partner_asset.get_romance_reaction(action_id, "start")
                    if reaction:
                        state["last_reaction"] = reaction

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
            elif is_turning_on:
                # 토글 ON 시 반응 텍스트 (start 타이밍)
                partner_asset = get_partner_asset(state["partner_id"])
                if partner_asset and hasattr(partner_asset, 'get_romance_reaction'):
                    reaction = partner_asset.get_romance_reaction(action_id, "start")
                    if reaction:
                        state["last_reaction"] = reaction

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            return render_romance_ui(state)

        return None

    # 연애 UI 시작
    yield morld.dialog(
        render_romance_ui(state),
        autofill="off",
        proc=proc,
        result=state
    )

    # 종료 처리 - 파트너 스케줄 스택에서 pop (원래 스케줄 복원)
    partner_id = state["partner_id"]
    partner_agent = think.get_agent(partner_id)

    if state["exhausted"]:
        # 비정상 종료: 체력 소진
        if partner_agent:
            partner_agent.pop_schedule()
        yield morld.dialog("지쳤다...")
        morld.pop_to_situation()
    elif state["interrupted"]:
        # 비정상 종료: 방해 이벤트 (handle_interruption에서 flee job 설정)
        # pop은 handle_interruption 내에서 처리
        yield from handle_interruption(state)
        morld.pop_to_situation()
    else:
        # 정상 종료(exit 클릭): NPC focus로 복귀
        if partner_agent:
            partner_agent.pop_schedule()


def handle_interruption(state):
    """중단 이벤트 처리"""
    interrupter_id = state["interrupter_id"]
    partner_id = state["partner_id"]

    # 목격자 반응 다이얼로그
    interrupter_info = morld.get_unit_info(interrupter_id)
    interrupter_name = interrupter_info["name"]
    yield morld.dialog([
        f"[{interrupter_name}]",
        "어머나! 이게 무슨 꼴이람!"
    ])

    # 파트너 반응 (부끄러움 → 도망)
    partner_info = morld.get_unit_info(partner_id)
    partner_name = partner_info["name"]
    yield morld.dialog([
        f"[{partner_name}]",
        "...!"
    ])

    # 파트너 상태 변경 - 스케줄 스택 pop 후 flee job 설정
    import think
    partner_agent = think.get_agent(partner_id)
    if partner_agent:
        partner_agent.pop_schedule()

    morld.add_unit_mood(partner_id, "부끄러움")
    morld.set_npc_job(partner_id, "flee", 30, morld.get_player_id())

    # 목격자 호감도 감소 (관계:플레이어이름:호감)
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    morld.modify_prop(interrupter_id, f"관계:{player_name}:호감", -5)
