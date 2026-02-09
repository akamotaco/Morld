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
from romance import check_ecstasy, emit_romance_sound, emit_ecstasy_sound

# ============================================
# 상수 정의
# ============================================

# 빠져나가기 확률 보정
ESCAPE_BASE_CHANCE = 0.3  # 기본 30%
ESCAPE_STRENGTH_BONUS = 0.05  # 힘 1당 +5%
ESCAPE_BODY_BONUS = {
    "왜소": -0.1,
    "보통": 0.0,
    "장신": 0.05,
    "거구": 0.15,
}

# 들키지 않을 확률 설정
STEALTH_BASE_CHANCE = 0.3      # 기본 은신 확률 30%
STEALTH_HIDING_BONUS = 0.4     # 은신 중일 때 추가 확률 +40%
INTERRUPT_JOIN_THRESHOLD = 60  # 합류 가능 최소 호감도

# 시간 상수 (밀리초)
MILLIS_PER_MINUTE = 60_000
MILLIS_PER_DAY = 86_400_000

# NPC 대기 스케줄 (location_id 없음 = 이동 없이 현위치 대기)
STAY_SCHEDULE = [
    {"name": "대기", "start": 0, "end": MILLIS_PER_DAY, "activity": "대기"}
]

# 스태미나 설정
ROMANCE_STAMINA_KEY = "연애:스태미나"
DEFAULT_STAMINA = 10

# 플레이어가 선택 가능한 즉시 행위 (NPC 주도 중에도 사용 가능)
# exp_part: 신체 부위 (충돌 판정용) - None이면 충돌 없음
PLAYER_INSTANT_ACTIONS = {
    "head_pat": {
        "name": "머리 쓰다듬기", "time": 3 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 2, "애정": 1},
        "exp_part": "머리", "affection_req": 40
    },
    "cheek_caress": {
        "name": "뺨 어루만지기", "time": 2 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 1, "애정": 1},
        "exp_part": "뺨", "affection_req": 30
    },
    "whisper": {
        "name": "속삭이기", "time": 2 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 2, "애정": 2},
        "exp_part": None, "affection_req": 50
    },
}

# NPC 토글 행위 정의 (romance.py와 공유)
# exp_part: 신체 부위 (충돌 판정용) - None이면 충돌 없음
NPC_TOGGLE_ACTIONS = {
    "hug": {
        "name": "껴안기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 1,
        "effects": {"호감": 1, "애정": 2},
        "exp_part": None, "affection_req": 50
    },
    "deep_kiss": {
        "name": "딥키스", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"호감": 1, "애정": 2, "성욕": 3},
        "exp_part": "입술", "affection_req": 70
    },
    "breast_touch": {
        "name": "가슴 만지기", "time": 5 * MILLIS_PER_MINUTE, "stamina": 2,
        "effects": {"애정": 1, "성욕": 4},
        "exp_part": "가슴", "affection_req": 80
    },
}


# ============================================
# 유틸리티 함수
# ============================================

def get_npc_asset(npc_id):
    """NPC의 Python Asset 인스턴스 가져오기"""
    try:
        from assets.characters import get_instance
        return get_instance(npc_id)
    except:
        return None


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
    """플레이어 힘 스탯 가져오기"""
    props = morld.get_unit_props(player_id)
    if not props:
        return 5
    return props.get("힘", 5)


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

def get_action_exp_part(action_id, action_dict=None):
    """
    액션의 신체 부위(exp_part) 반환

    Args:
        action_id: 액션 ID
        action_dict: 액션 정의 dict (없으면 자동 조회)

    Returns:
        str: 신체 부위 또는 None
    """
    if action_dict:
        return action_dict.get("exp_part")

    # 토글 액션에서 조회
    if action_id in NPC_TOGGLE_ACTIONS:
        return NPC_TOGGLE_ACTIONS[action_id].get("exp_part")

    # 즉시 액션에서 조회
    if action_id in PLAYER_INSTANT_ACTIONS:
        return PLAYER_INSTANT_ACTIONS[action_id].get("exp_part")

    return None


def get_conflicting_toggles(new_action_id, active_toggles, new_action_dict=None):
    """
    새 액션과 충돌하는 활성 토글 목록 반환

    같은 신체 부위(exp_part)를 사용하는 토글들을 찾습니다.
    exp_part가 None인 액션은 충돌하지 않습니다.

    Args:
        new_action_id: 새로 선택한 액션 ID
        active_toggles: 현재 활성화된 토글 set
        new_action_dict: 새 액션 정의 dict (없으면 자동 조회)

    Returns:
        set: 충돌하는 토글 ID들
    """
    new_exp_part = get_action_exp_part(new_action_id, new_action_dict)

    # exp_part가 None이면 충돌 없음
    if new_exp_part is None:
        return set()

    conflicting = set()
    for toggle_id in active_toggles:
        toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
        if toggle_def:
            toggle_exp_part = toggle_def.get("exp_part")
            if toggle_exp_part == new_exp_part:
                conflicting.add(toggle_id)

    return conflicting


def remove_conflicting_toggles(new_action_id, active_toggles, new_action_dict=None):
    """
    새 액션과 충돌하는 토글들을 비활성화

    Args:
        new_action_id: 새로 선택한 액션 ID
        active_toggles: 현재 활성화된 토글 set (in-place 수정됨)
        new_action_dict: 새 액션 정의 dict

    Returns:
        set: 제거된 토글 ID들
    """
    conflicting = get_conflicting_toggles(new_action_id, active_toggles, new_action_dict)
    for toggle_id in conflicting:
        active_toggles.discard(toggle_id)
    return conflicting


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


# ============================================
# 제3자 감지 시스템 (은신 확률)
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
    chance = calculate_stealth_chance(state)
    return random.random() < chance


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

    units_at_loc = morld.get_units_at_location(player_loc[0], player_loc[1])

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
        checked_npcs = state.get("checked_npcs", set())
        if unit_id in checked_npcs:
            continue

        # 체크 목록에 추가
        if "checked_npcs" not in state:
            state["checked_npcs"] = set()
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
        # TODO: 합류 로직 (Phase 6)

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
# NPC 액션 시스템
# ============================================

def get_available_npc_actions(npc_id, player_id):
    """
    NPC가 선택 가능한 액션 목록 반환

    NPC의 현재 성욕/호감도에 따라 가능한 액션들을 필터링합니다.

    Returns:
        list: 선택 가능한 액션 ID 리스트
    """
    affection = get_affection(npc_id, player_id)
    arousal = get_npc_arousal(npc_id)

    available = []
    for action_id, action_def in NPC_TOGGLE_ACTIONS.items():
        req_affection = action_def.get("affection_req", 0)
        if affection >= req_affection:
            available.append(action_id)

    # 성욕이 높을수록 더 적극적인 액션 선호
    # (기본적으로는 모든 가능한 액션을 반환)
    return available


def select_random_npc_action(npc_id, player_id, active_toggles):
    """
    NPC가 랜덤으로 행위 선택

    현재 활성화된 토글을 제외하고, 조건에 맞는 액션 중 랜덤 선택합니다.
    캐릭터별 INITIATIVE_ACTION_FILTERS가 정의되어 있으면 해당 필터도 적용합니다.

    Args:
        npc_id: NPC ID
        player_id: 플레이어 ID
        active_toggles: 현재 활성화된 토글 set

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


def execute_npc_action(state, action):
    """
    NPC 액션 실행

    Args:
        state: 현재 상태 dict
        action: 실행할 액션 dict

    Returns:
        str: 반응 텍스트
    """
    npc_id = state["npc_id"]
    player_id = state["player_id"]
    action_type = action.get("action", "hug")
    duration = action.get("duration", 5 * MILLIS_PER_MINUTE)

    # 효과 적용 (romance.py의 TOGGLE_ACTIONS 참조)
    npc_asset = get_npc_asset(npc_id)
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'

    # 기본 효과 (간단화)
    effects = {
        "hug": {"호감": 1, "애정": 2},
        "deep_kiss": {"호감": 1, "애정": 2, "성욕": 3},
        "breast_touch": {"애정": 1, "성욕": 4},
    }

    action_effects = effects.get(action_type, {"호감": 1})
    for key, value in action_effects.items():
        if key in ("호감", "애정"):
            prop_key = f"관계:{player_name}:{key}"
        else:
            prop_key = f"상태:{key}"
        morld.modify_prop(npc_id, prop_key, value)

    # 시간 경과
    state["elapsed_time"] += duration

    # 반응 텍스트
    timing = f"during_{action_type}"
    if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
        reaction = npc_asset.get_initiative_reaction(timing)
        if reaction:
            return reaction

    # 기본 반응
    npc_info = morld.get_unit_info(npc_id)
    npc_name = npc_info.get('name', '그녀') if npc_info else '그녀'
    return f"{npc_name}(이)가 주도적으로 행동한다."


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

    # 목격자 정보
    interrupter_info = morld.get_unit_info(interrupter_id)
    interrupter_name = interrupter_info.get("name", "누군가") if interrupter_info else "누군가"

    # 목격자 반응 다이얼로그
    yield ui.dialog([
        f"[{interrupter_name}]",
        "어머나! 이게 무슨 꼴이람!"
    ])

    # NPC 반응 (부끄러움)
    morld.add_unit_mood(npc_id, "부끄러움")

    # NPC가 도망감
    morld.set_npc_job(npc_id, "flee", 30 * MILLIS_PER_MINUTE, player_id)

    # 목격자 호감도 감소
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    morld.modify_prop(interrupter_id, f"관계:{player_name}:호감", -5)

    # NPC 호감도 감소 (들켜서 부끄러움)
    morld.modify_prop(npc_id, f"관계:{player_name}:호감", -3)


# ============================================
# UI 렌더링
# ============================================

def render_stamina_bar(stamina, max_stamina=DEFAULT_STAMINA):
    """스태미나 바 렌더링"""
    filled = int(stamina)
    empty = max_stamina - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {stamina}"


def get_affection_key(player_id):
    """플레이어에 대한 호감도 prop 키 생성"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'
    return f"관계:{player_name}:호감"


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

    # 호감/애정/성욕 키
    affection_key = get_affection_key(player_id)
    love_key = affection_key.replace(":호감", ":애정")
    arousal_key = "상태:성욕"

    lines = []

    # 헤더 - NPC 이름 + 스태미나
    lines.append(f"[{npc_name}의 주도]                 스태미나: {render_stamina_bar(player_stamina)}")
    lines.append("")

    # 근접 경고 (누군가 지나갔지만 들키지 않음)
    if state.get("near_miss"):
        near_miss_id = state.get("near_miss_id")
        near_info = morld.get_unit_info(near_miss_id) if near_miss_id else None
        near_name = near_info.get("name", "누군가") if near_info else "누군가"
        lines.append(f"[color=orange]({near_name}(이)가 근처를 지나갔다... 들키지 않았다.)[/color]")

        # NPC의 은신 성공 반응 (캐릭터별 특별 대사)
        stealth_reaction = state.get("stealth_reaction")
        if stealth_reaction:
            lines.append(f"[color=cyan][{npc_name}] {stealth_reaction}[/color]")
            state["stealth_reaction"] = None  # 표시 후 클리어

        lines.append("")
        state["near_miss"] = False  # 표시 후 클리어
        state["near_miss_id"] = None

    # 마지막 반응 텍스트 (즉시 액션 결과 등)
    last_reaction = state.get("last_reaction")
    if last_reaction:
        lines.append(f"[color=yellow]{last_reaction}[/color]")
        lines.append("")
        state["last_reaction"] = None  # 표시 후 클리어

    # NPC의 현재 행위 표시 (활성 토글)
    npc_asset = get_npc_asset(npc_id)
    active_toggles = state.get("active_toggles", set())
    if active_toggles:
        for toggle_id in active_toggles:
            toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
            if toggle_def:
                # 캐릭터별 반응 또는 기본 반응
                if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(f"during_{toggle_id}")
                    if reaction:
                        lines.append(f"({reaction})")
                    else:
                        lines.append(f"({npc_name}(이)가 {toggle_def['name']} 중이다.)")
                else:
                    lines.append(f"({npc_name}(이)가 {toggle_def['name']} 중이다.)")
    else:
        lines.append(f"({npc_name}(이)가 당신을 붙잡고 있다.)")

    lines.append("")

    # 호감/애정/성욕 표시
    affection = npc_props.get(affection_key, 0) if npc_props else 0
    love = npc_props.get(love_key, 0) if npc_props else 0
    arousal = npc_props.get(arousal_key, 0) if npc_props else 0
    lines.append(f"호감: {affection}  애정: {love}  성욕: {arousal}")
    lines.append("")

    # 탈출 확률 표시
    escape_chance = calculate_escape_chance(player_id, npc_id)
    lines.append(f"[color=gray]탈출 확률: {int(escape_chance * 100)}%[/color]")

    # 탈출 결과 표시 (있으면)
    if state.get("escape_result"):
        lines.append(f"[color=red]{state['escape_result']}[/color]")

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

    # 플레이어 선택 가능한 즉시 행위
    lines.append("[즉시 행위] (플레이어)")
    for action_id, action in PLAYER_INSTANT_ACTIONS.items():
        if affection >= action["affection_req"]:
            if player_stamina >= action["stamina"]:
                lines.append(f"  [url=@proc:instant:{action_id}]{action['name']}[/url]")
            else:
                lines.append(f"  [color=gray]{action['name']} (스태미나 부족)[/color]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 선택지
    lines.append(ui.divider())
    lines.append("[url=@proc:escape]빠져나가기 시도[/url]")
    lines.append("[url=@proc:accept]받아들이기[/url]")
    lines.append("")
    lines.append("[url=@proc:exit][color=gray]나가기[/color][/url]")

    return "\n".join(lines)


# ============================================
# 효과 적용 함수
# ============================================

def apply_action_effects(state, action_def):
    """
    행위 효과 적용

    Args:
        state: 현재 상태
        action_def: 액션 정의 dict

    Returns:
        절정 반응 텍스트 또는 None
    """
    npc_id = state["npc_id"]
    player_id = state["player_id"]
    affection_key = get_affection_key(player_id)

    effects = action_def.get("effects", {})
    for stat, value in effects.items():
        if stat in ("성욕", "성적절정"):
            prop_key = f"상태:{stat}"
        else:
            prop_key = affection_key.replace(":호감", f":{stat}")
        morld.modify_prop(npc_id, prop_key, value)

    # 절정 체크 (성욕 >= 100이면 절정 발생, 성욕 0으로 리셋)
    return check_ecstasy(npc_id)


# ============================================
# 메인 함수
# ============================================

def start_npc_initiative(player_id, npc_id):
    """
    NPC 주도 스킨십 시작 - Generator 기반

    on_meet 이벤트에서 조건 충족 시 호출됨.
    플레이어도 즉시 행위를 선택할 수 있음.
    """
    npc_asset = get_npc_asset(npc_id)
    npc_info = morld.get_unit_info(npc_id)
    npc_name = npc_info.get('name', '그녀') if npc_info else '그녀'

    # NPC 스케줄 push (움직이지 않도록)
    npc_agent = think.get_agent(npc_id)
    if npc_agent:
        npc_agent.push_schedule(STAY_SCHEDULE)

    # 플레이어 스태미나 조회
    player_props = morld.get_unit_props(player_id)
    initial_stamina = player_props.get(ROMANCE_STAMINA_KEY, DEFAULT_STAMINA) if player_props else DEFAULT_STAMINA

    # 상태 초기화 (action_queue 제거 - 랜덤 선택 방식으로 변경)
    state = {
        "player_id": player_id,
        "npc_id": npc_id,
        "active_toggles": set(),  # NPC가 현재 하고 있는 토글 행위
        "stamina": initial_stamina,
        "elapsed_time": 0,
        "escape_attempts": 0,
        "interrupted": False,
        "interrupter_id": None,
        "npc_satisfied": False,
        "player_escaped": False,
        "exhausted": False,
        "last_reaction": None,
        "escape_result": None,
    }

    # 시작 반응
    if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
        state["last_reaction"] = npc_asset.get_initiative_reaction("start")

    # proc 콜백
    def proc(action):
        if action == "init":
            return render_npc_initiative_ui(state)

        # 빠져나가기 시도
        if action == "escape":
            state["escape_attempts"] += 1
            state["escape_result"] = None

            if attempt_escape(player_id, npc_id):
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

        # 플레이어 즉시 행위
        if action.startswith("instant:"):
            action_id = action.split(":")[1]
            action_def = PLAYER_INSTANT_ACTIONS.get(action_id)
            if not action_def:
                return None

            state["escape_result"] = None

            # 충돌 처리: 같은 신체 부위를 사용하는 토글 비활성화
            removed_toggles = remove_conflicting_toggles(action_id, state["active_toggles"], action_def)

            # 스태미나 체크 (충돌로 제거된 토글은 제외)
            required_stamina = action_def["stamina"]

            # 활성 토글들의 스태미나도 합산
            for toggle_id in state["active_toggles"]:
                toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
                if toggle_def:
                    required_stamina += toggle_def["stamina"]

            if state["stamina"] < required_stamina:
                state["exhausted"] = True
                return True  # 스태미나 부족으로 종료

            # 스태미나 소모
            state["stamina"] -= required_stamina

            # 효과 적용 (플레이어 즉시 행위)
            ecstasy_reaction = apply_action_effects(state, action_def)

            # 활성 토글들의 효과도 적용 (충돌로 제거된 토글은 제외됨)
            for toggle_id in state["active_toggles"]:
                toggle_def = NPC_TOGGLE_ACTIONS.get(toggle_id)
                if toggle_def:
                    ecstasy_result = apply_action_effects(state, toggle_def)
                    if ecstasy_result and not ecstasy_reaction:
                        ecstasy_reaction = ecstasy_result

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
                    reaction = npc_asset.get_romance_reaction(action_id, "start")
                    if reaction:
                        state["last_reaction"] = reaction

            return render_npc_initiative_ui(state)

        # 받아들이기 - NPC가 랜덤으로 행위 선택
        if action == "accept":
            state["escape_result"] = None

            # NPC가 새로운 행위를 랜덤 선택 (기존 토글 제외)
            new_action = select_random_npc_action(npc_id, player_id, state["active_toggles"])

            # 새 액션의 정의
            new_toggle_def = None
            if new_action:
                new_toggle_def = NPC_TOGGLE_ACTIONS.get(new_action)

                # 충돌 처리: 같은 신체 부위를 사용하는 토글 비활성화
                remove_conflicting_toggles(new_action, state["active_toggles"], new_toggle_def)

            # 스태미나 계산: 새 액션 + 기존 활성 토글들 (충돌로 제거된 토글 제외)
            required_stamina = 0

            # 새 액션의 스태미나
            if new_toggle_def:
                required_stamina += new_toggle_def["stamina"]

            # 기존 활성 토글들의 스태미나
            for tid in state["active_toggles"]:
                td = NPC_TOGGLE_ACTIONS.get(tid)
                if td:
                    required_stamina += td["stamina"]

            # 스태미나 체크 (최소 1 필요)
            if required_stamina == 0:
                required_stamina = 1

            if state["stamina"] <= required_stamina:
                state["exhausted"] = True
                return True  # 스태미나 부족으로 종료

            # 스태미나 소모
            state["stamina"] -= required_stamina

            # 새 액션이 있으면 토글에 추가
            if new_action and new_toggle_def:
                state["active_toggles"].add(new_action)

            # 모든 활성 토글들의 효과 적용
            ecstasy_reaction = None
            for tid in state["active_toggles"]:
                td = NPC_TOGGLE_ACTIONS.get(tid)
                if td:
                    result = apply_action_effects(state, td)
                    if result and not ecstasy_reaction:
                        ecstasy_reaction = result

            # 소음 발생
            npc_id = state["npc_id"]
            if ecstasy_reaction:
                emit_ecstasy_sound(npc_id)
            else:
                emit_romance_sound(npc_id)

            # 시간 경과 + 제3자 감지 체크 (활성 토글 중 첫 번째 기준, 기본 5분)
            time_elapsed = 5 * MILLIS_PER_MINUTE
            first_toggle = next(iter(state["active_toggles"]), None)
            if first_toggle:
                td = NPC_TOGGLE_ACTIONS.get(first_toggle)
                if td:
                    time_elapsed = td.get("time", 5 * MILLIS_PER_MINUTE)

            check_result = advance_time_and_check_npc_initiative(state, time_elapsed)

            # 제3자에게 들킴 - 중단
            if check_result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = check_result["interrupter_id"]
                return True

            # 반응 텍스트 설정
            if ecstasy_reaction:
                state["last_reaction"] = ecstasy_reaction
            elif new_action:
                # 새로 추가된 액션에 대한 반응
                timing = f"during_{new_action}"
                if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                    reaction = npc_asset.get_initiative_reaction(timing)
                    if reaction:
                        state["last_reaction"] = reaction
            elif state["active_toggles"]:
                # 기존 토글 중 하나의 반응
                for tid in state["active_toggles"]:
                    timing = f"during_{tid}"
                    if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
                        reaction = npc_asset.get_initiative_reaction(timing)
                        if reaction:
                            state["last_reaction"] = reaction
                            break

            return render_npc_initiative_ui(state)

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

    # 종료 처리
    if npc_agent:
        npc_agent.pop_schedule()

    # 종료 반응
    if state["player_escaped"]:
        yield ui.dialog(f"{npc_name}(으)로부터 벗어났다.")
    elif state.get("interrupted"):
        # 제3자에게 들킴 - 방해 이벤트
        yield from handle_npc_initiative_interruption(state, npc_name)
    elif state["exhausted"]:
        yield ui.dialog("체력이 바닥났다...")
    elif state["npc_satisfied"]:
        satisfied_text = None
        if npc_asset and hasattr(npc_asset, 'get_initiative_reaction'):
            satisfied_text = npc_asset.get_initiative_reaction("satisfied")

        if satisfied_text:
            yield ui.dialog(satisfied_text)
        else:
            yield ui.dialog(f"{npc_name}(이)가 만족한 듯 물러난다.")


