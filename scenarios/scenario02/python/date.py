# date.py - 데이트 시스템 모듈
"""
데이트 시스템 - NPC와 함께 이동하며 애정 표현

핵심 기능:
- 호감도 조건에 따른 데이트 수락/거절
- 데이트 중 NPC가 플레이어를 따라다님 (follow 스케줄)
- 데이트 중 애정 표현 가능
- 데이트 종료 시 원래 스케줄로 복원
"""

import morld
import think
import ui

MILLIS_PER_MINUTE = 60_000
MILLIS_PER_DAY = 86_400_000

# ============================================
# 상수 정의
# ============================================

DATE_MIN_AFFECTION = 30  # 데이트 수락 최소 호감도

# 따라가기 스케줄 (24시간 follow)
FOLLOW_SCHEDULE = [
    {"name": "따라가기", "action": "follow", "start": 0, "end": MILLIS_PER_DAY, "activity": "데이트"}
]

# ============================================
# 데이트 상태 관리
# ============================================

# 현재 데이트 중인 NPC {player_id: partner_id}
_active_dates = {}


def is_on_date(player_id):
    """플레이어가 데이트 중인지 확인"""
    return player_id in _active_dates


def get_date_partner(player_id):
    """데이트 중인 파트너 ID 반환"""
    return _active_dates.get(player_id)


def _start_date(player_id, partner_id):
    """데이트 시작 (내부용)"""
    _active_dates[player_id] = partner_id

    # 플레이어의 데이트 관련 can: prop 토글
    morld.set_unit_prop(player_id, "can:date", 0)
    morld.set_unit_prop(player_id, "can:end_date", 1)
    # 애정 표현은 항상 가능 (데이트 외에서도)

    # NPC 스케줄을 follow로 push
    partner_agent = think.get_agent(partner_id)
    if partner_agent:
        partner_agent.push_schedule(FOLLOW_SCHEDULE)

    # follow job 설정 (플레이어 따라가기)
    morld.set_npc_job(partner_id, "follow", MILLIS_PER_DAY, player_id)

    print(f"[date] Started: player={player_id}, partner={partner_id}")


def _end_date(player_id):
    """데이트 종료 (내부용)"""
    if player_id not in _active_dates:
        return

    partner_id = _active_dates.pop(player_id)

    # 플레이어의 데이트 관련 can: prop 토글
    morld.set_unit_prop(player_id, "can:date", 1)
    morld.set_unit_prop(player_id, "can:end_date", 0)
    # 애정 표현은 항상 가능 (데이트 외에서도)

    # NPC 스케줄 pop (이전 스케줄로 복원)
    partner_agent = think.get_agent(partner_id)
    if partner_agent:
        partner_agent.pop_schedule()

    print(f"[date] Ended: player={player_id}, partner={partner_id}")
    return partner_id


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


def get_affection(partner_id, player_id):
    """파트너의 플레이어에 대한 호감도 조회"""
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'

    props = morld.get_unit_props(partner_id)
    if not props:
        return 0

    return props.get(f"관계:{player_name}:호감", 0)


# ============================================
# 데이트 요청 검증
# ============================================

def can_request_date(player_id, partner_id):
    """
    데이트 요청 가능 여부 확인

    Returns:
        (bool, str): (가능 여부, 불가 사유)
    """
    # 이미 데이트 중
    if is_on_date(player_id):
        return False, "이미 데이트 중이다."

    # 같은 위치 확인
    player_loc = morld.get_unit_location(player_id)
    partner_loc = morld.get_unit_location(partner_id)
    if player_loc != partner_loc:
        return False, "같은 장소에 있어야 한다."

    return True, None


def will_accept_date(partner_id, player_id):
    """
    NPC가 데이트를 수락할지 판단

    Returns:
        (bool, str): (수락 여부, 거절 사유 또는 None)
    """
    affection = get_affection(partner_id, player_id)

    if affection < DATE_MIN_AFFECTION:
        return False, "아직 그 정도로 친하지 않다."

    # 추가 조건은 캐릭터별 오버라이드 가능
    return True, None


# ============================================
# 메인 데이트 플로우
# ============================================

def request_date(player_id, partner_id):
    """
    데이트 요청 - Generator 함수

    캐릭터의 date() 메서드에서 호출됨.
    """
    # 요청 가능 여부 확인
    can_request, reason = can_request_date(player_id, partner_id)
    if not can_request:
        yield ui.dialog(reason)
        return

    # 파트너 Asset 가져오기
    partner_asset = get_partner_asset(partner_id)
    partner_name = "그녀"
    if partner_asset:
        partner_name = getattr(partner_asset, 'name', '그녀')

    # 수락 여부 확인
    will_accept, reject_reason = will_accept_date(partner_id, player_id)

    if not will_accept:
        # 거절 반응 (캐릭터별 커스텀 가능)
        reject_text = f"[{partner_name}]\n\"{reject_reason}\""
        if partner_asset and hasattr(partner_asset, 'get_date_reject_text'):
            custom_text = partner_asset.get_date_reject_text(reject_reason)
            if custom_text:
                reject_text = custom_text
        yield ui.dialog(reject_text)
        return

    # 수락 반응
    accept_text = f"[{partner_name}]\n\"좋아.\""
    if partner_asset and hasattr(partner_asset, 'get_date_accept_text'):
        custom_text = partner_asset.get_date_accept_text()
        if custom_text:
            accept_text = custom_text
    yield ui.dialog(accept_text)

    # 데이트 시작
    _start_date(player_id, partner_id)


def end_date(player_id):
    """
    데이트 종료 - Generator 함수

    플레이어가 데이트를 종료할 때 호출.
    """
    if not is_on_date(player_id):
        yield ui.dialog("데이트 중이 아니다.")
        return

    partner_id = get_date_partner(player_id)
    partner_asset = get_partner_asset(partner_id)
    partner_name = "그녀"
    if partner_asset:
        partner_name = getattr(partner_asset, 'name', '그녀')

    # 종료 반응
    end_text = f"[{partner_name}]\n\"...그래, 또 보자.\""
    if partner_asset and hasattr(partner_asset, 'get_date_end_text'):
        custom_text = partner_asset.get_date_end_text()
        if custom_text:
            end_text = custom_text

    _end_date(player_id)
    yield ui.dialog(end_text)


# ============================================
# 애정 표현 (데이트 중 / 데이트 외)
# ============================================

# 데이트 중 애정 표현 - 낮은 조건
DATE_ACTIONS = {
    "hold_hands": {
        "name": "손 잡기",
        "effects": {"호감": 1, "애정": 1},
        "affection_req": 30
    },
    "hug": {
        "name": "안아주기",
        "effects": {"호감": 2, "애정": 2},
        "affection_req": 50
    },
    "kiss": {
        "name": "키스",
        "effects": {"호감": 2, "애정": 3},
        "affection_req": 60
    },
}

# 데이트 외 애정 표현 - 높은 조건
CASUAL_ACTIONS = {
    "hold_hands": {
        "name": "손 잡기",
        "effects": {"호감": 1, "애정": 1},
        "affection_req": 50  # 데이트 중보다 높음
    },
    "hug": {
        "name": "안아주기",
        "effects": {"호감": 2, "애정": 2},
        "affection_req": 70
    },
    "kiss": {
        "name": "키스",
        "effects": {"호감": 2, "애정": 3},
        "affection_req": 80
    },
}


def apply_date_action_effects(partner_id, player_id, action_id):
    """데이트 액션 효과 적용"""
    action = DATE_ACTIONS.get(action_id)
    if not action:
        return

    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get('name', '주인공') if player_info else '주인공'

    for key, value in action["effects"].items():
        if key in ("호감", "애정"):
            prop_key = f"관계:{player_name}:{key}"
        else:
            prop_key = key
        morld.modify_prop(partner_id, prop_key, value)


def get_available_date_actions(partner_id, player_id):
    """사용 가능한 데이트 액션 목록"""
    affection = get_affection(partner_id, player_id)
    available = []

    for action_id, action in DATE_ACTIONS.items():
        if affection >= action["affection_req"]:
            available.append((action_id, action))

    return available


def do_date_action(player_id, partner_id, action_id):
    """
    데이트 중 애정 표현 실행 - Generator 함수
    """
    if not is_on_date(player_id):
        yield ui.dialog("데이트 중이 아니다.")
        return

    action = DATE_ACTIONS.get(action_id)
    if not action:
        yield ui.dialog("알 수 없는 행동이다.")
        return

    partner_asset = get_partner_asset(partner_id)
    partner_name = "그녀"
    if partner_asset:
        partner_name = getattr(partner_asset, 'name', '그녀')

    affection = get_affection(partner_id, player_id)
    if affection < action["affection_req"]:
        # 거부 반응
        reject_text = f"{partner_name}(이)가 거부했다."
        if partner_asset and hasattr(partner_asset, 'get_date_action_reject'):
            custom_text = partner_asset.get_date_action_reject(action_id)
            if custom_text:
                reject_text = custom_text

        yield ui.dialog(reject_text)
        return

    # 효과 적용
    apply_date_action_effects(partner_id, player_id, action_id)

    # 성공 반응 텍스트 (데이트 중)
    reaction_text = f"{partner_name}(이)가 미소를 짓는다."
    if partner_asset and hasattr(partner_asset, 'get_date_action_reaction'):
        custom_text = partner_asset.get_date_action_reaction(action_id)
        if custom_text:
            reaction_text = custom_text

    yield ui.dialog(reaction_text)


def do_casual_action(player_id, partner_id, action_id):
    """
    데이트 외 애정 표현 실행 - Generator 함수

    데이트 중이 아닐 때 높은 호감도 조건으로 애정 표현 가능.
    """
    # 같은 위치 확인
    player_loc = morld.get_unit_location(player_id)
    partner_loc = morld.get_unit_location(partner_id)
    if player_loc != partner_loc:
        yield ui.dialog("같은 장소에 있어야 한다.")
        return

    action = CASUAL_ACTIONS.get(action_id)
    if not action:
        yield ui.dialog("알 수 없는 행동이다.")
        return

    partner_asset = get_partner_asset(partner_id)
    partner_name = "그녀"
    if partner_asset:
        partner_name = getattr(partner_asset, 'name', '그녀')

    affection = get_affection(partner_id, player_id)
    if affection < action["affection_req"]:
        # 거부 반응 (데이트 외)
        reject_text = f"{partner_name}(이)가 거부했다."
        if partner_asset and hasattr(partner_asset, 'get_casual_action_reject'):
            custom_text = partner_asset.get_casual_action_reject(action_id)
            if custom_text:
                reject_text = custom_text

        yield ui.dialog(reject_text)
        return

    # 효과 적용
    apply_date_action_effects(partner_id, player_id, action_id)

    # 성공 반응 텍스트 (데이트 외 - 다른 반응)
    reaction_text = f"{partner_name}(이)가 살짝 미소를 짓는다."
    if partner_asset and hasattr(partner_asset, 'get_casual_action_reaction'):
        custom_text = partner_asset.get_casual_action_reaction(action_id)
        if custom_text:
            reaction_text = custom_text

    yield ui.dialog(reaction_text)


# ============================================
# 애정 표현 액션 표시 조건 관리
# ============================================

def update_affection_action_visibility(player_id, partner_id):
    """
    애정 표현 액션 표시 여부 업데이트

    데이트 중: 항상 표시 (거부 가능)
    일상: 호감도 조건 충족 시만 표시 (거부 없음)

    NPC focus 시점에서 호출됨.
    """
    if is_on_date(player_id):
        # 데이트 중: 항상 표시
        morld.set_unit_prop(player_id, "can:hold_hands", 1)
        morld.set_unit_prop(player_id, "can:date_hug", 1)
        morld.set_unit_prop(player_id, "can:date_kiss", 1)
    else:
        # 일상: 호감도 조건 체크
        affection = get_affection(partner_id, player_id)

        # hold_hands (손잡기) - CASUAL_ACTIONS 기준 호감도 50
        hold_hands_req = CASUAL_ACTIONS.get("hold_hands", {}).get("affection_req", 50)
        morld.set_unit_prop(player_id, "can:hold_hands", 1 if affection >= hold_hands_req else 0)

        # hug (안아주기) - CASUAL_ACTIONS 기준 호감도 70
        hug_req = CASUAL_ACTIONS.get("hug", {}).get("affection_req", 70)
        morld.set_unit_prop(player_id, "can:date_hug", 1 if affection >= hug_req else 0)

        # kiss (키스) - CASUAL_ACTIONS 기준 호감도 80
        kiss_req = CASUAL_ACTIONS.get("kiss", {}).get("affection_req", 80)
        morld.set_unit_prop(player_id, "can:date_kiss", 1 if affection >= kiss_req else 0)
