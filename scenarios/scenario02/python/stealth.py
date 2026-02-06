# stealth.py - 은신/발각 판정 시스템
#
# 발각 확률 공식 (30분 기준):
# detection_rate = 밝기 × 자세계수 × 엄폐계수 × NPC감지력
#
# 은신 상태:
# - status:stealth = 1: 은신 중
# - status:stealth = 0: 발각됨
# - (없음): 일반 상태

import random
import morld
import lighting


# ========================================
# 자세 계수
# ========================================

POSTURE_DETECTION = {
    "standing": 1.0,
    "crouch": 0.5,
    "prone": 0.3,
}
DEFAULT_POSTURE_DETECTION = 1.0


# ========================================
# 엄폐 계수
# ========================================
#
# 오브젝트와의 X 거리에 따른 엄폐 효과
# - 근접 (≤5): 0.3 (숨기 좋음)
# - 중간 (≤15): 0.6
# - 멀거나 없음: 1.0 (엄폐 없음)

COVER_DISTANCE_NEAR = 5
COVER_DISTANCE_MID = 15
COVER_COEFFICIENT_NEAR = 0.3
COVER_COEFFICIENT_MID = 0.6
COVER_COEFFICIENT_NONE = 1.0


# ========================================
# NPC 감지력
# ========================================
#
# perception:base prop에서 가져옴 (없으면 100)
# 100 = 기본, 150 = 세라(경비), 10 = 잠든 NPC

DEFAULT_PERCEPTION = 100


# ========================================
# 발각 판정 함수
# ========================================

def get_posture_coefficient() -> float:
    """
    플레이어 자세에 따른 발각 계수 반환

    Returns:
        float: 0.3 (prone) ~ 1.0 (standing)
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return DEFAULT_POSTURE_DETECTION

    # 자세 확인
    if morld.get_unit_prop(player_id, "posture:prone") == 1:
        return POSTURE_DETECTION["prone"]
    elif morld.get_unit_prop(player_id, "posture:crouch") == 1:
        return POSTURE_DETECTION["crouch"]
    else:
        return POSTURE_DETECTION["standing"]


def get_cover_coefficient() -> float:
    """
    플레이어 주변 엄폐물에 따른 발각 계수 반환

    현재 Location의 오브젝트와의 X 거리 중 가장 가까운 것 기준

    Returns:
        float: 0.3 (근접) ~ 1.0 (없음)
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return COVER_COEFFICIENT_NONE

    # 플레이어 위치
    player_loc = morld.get_unit_location(player_id)
    if player_loc is None:
        return COVER_COEFFICIENT_NONE

    region_id, location_id = player_loc
    player_x = morld.get_unit_x(player_id)

    # Location 내 오브젝트 조회
    objects = morld.get_objects_at_location(region_id, location_id)
    if not objects:
        return COVER_COEFFICIENT_NONE

    # 가장 가까운 오브젝트와의 거리
    min_distance = float('inf')
    for obj_id in objects:
        obj_x = morld.get_unit_x(obj_id)
        if obj_x is not None:
            distance = abs(player_x - obj_x)
            min_distance = min(min_distance, distance)

    # 거리에 따른 계수
    if min_distance <= COVER_DISTANCE_NEAR:
        return COVER_COEFFICIENT_NEAR
    elif min_distance <= COVER_DISTANCE_MID:
        return COVER_COEFFICIENT_MID
    else:
        return COVER_COEFFICIENT_NONE


def get_npc_perception(npc_id: int) -> float:
    """
    NPC의 감지력 반환

    Args:
        npc_id: NPC 유닛 ID

    Returns:
        float: 감지력 (1.0 = 기본, 1.5 = 높음, 0.1 = 낮음)
    """
    perception = morld.get_unit_prop(npc_id, "perception:base")
    if perception is None:
        perception = DEFAULT_PERCEPTION

    return perception / 100.0


def calculate_detection_rate(npc_id: int = None) -> float:
    """
    발각 확률 계산 (30분 기준)

    Args:
        npc_id: NPC ID (None이면 NPC 감지력 1.0 사용)

    Returns:
        float: 0.0 ~ 1.0 (발각 확률)
    """
    # 밝기
    brightness = lighting.get_detection_brightness()

    # 자세 계수
    posture = get_posture_coefficient()

    # 엄폐 계수
    cover = get_cover_coefficient()

    # NPC 감지력
    if npc_id is not None:
        perception = get_npc_perception(npc_id)
    else:
        perception = 1.0

    # 발각 확률 = 밝기 × 자세 × 엄폐 × 감지력
    rate = brightness * posture * cover * perception

    # 0.0 ~ 1.0 범위로 제한
    return max(0.0, min(1.0, rate))


def detection_check(npc_id: int = None) -> bool:
    """
    발각 판정 실행 (1회)

    Args:
        npc_id: NPC ID (None이면 기본 감지력)

    Returns:
        bool: True = 발각됨, False = 은신 성공
    """
    rate = calculate_detection_rate(npc_id)
    return random.random() < rate


def check_detection_over_time(elapsed_minutes: int, npc_ids: list = None) -> int:
    """
    시간 경과에 따른 발각 판정 (30분마다)

    Args:
        elapsed_minutes: 경과 시간 (분)
        npc_ids: NPC ID 목록 (None이면 빈 목록)

    Returns:
        int: 발각한 NPC ID (없으면 None)
    """
    if npc_ids is None:
        npc_ids = []

    rounds = elapsed_minutes // 30

    for _ in range(rounds):
        for npc_id in npc_ids:
            if detection_check(npc_id):
                return npc_id

    return None


# ========================================
# 은신 상태 관리
# ========================================

def is_player_stealthed() -> bool:
    """
    플레이어가 은신 중인지 확인

    Returns:
        bool: status:stealth == 1
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return False

    stealth = morld.get_unit_prop(player_id, "status:stealth")
    return stealth == 1


def is_player_detected() -> bool:
    """
    플레이어가 발각 상태인지 확인

    Returns:
        bool: status:stealth == 0
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return False

    stealth = morld.get_unit_prop(player_id, "status:stealth")
    return stealth == 0


def set_detected(npc_id: int = None) -> str:
    """
    플레이어를 발각 상태로 설정

    Args:
        npc_id: 발각한 NPC ID (로그용)

    Returns:
        str: 로그 메시지
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    morld.set_unit_prop(player_id, "status:stealth", 0)

    if npc_id is not None:
        npc_name = morld.get_unit_name(npc_id) or "누군가"
        return f"{npc_name}에게 발각되었다!"
    else:
        return "발각되었다!"


# ========================================
# 이벤트 연동
# ========================================

def resolve_event_with_stealth(npc_id: int, is_forced: bool = False) -> tuple:
    """
    이벤트 resolve 시 은신 판정

    Args:
        npc_id: NPC ID
        is_forced: forced_event 여부

    Returns:
        tuple: (진행 여부, 로그 메시지)
            - (True, "발각!") = 이벤트 진행
            - (False, "들키지 않았다") = 이벤트 스킵
    """
    # forced_event는 은신 무시
    if is_forced:
        return (True, None)

    # 은신 상태가 아니면 바로 진행
    if not is_player_stealthed():
        return (True, None)

    # 은신 판정
    if detection_check(npc_id):
        # 발각
        msg = set_detected(npc_id)
        return (True, msg)
    else:
        # 은신 성공
        return (False, "들키지 않은 것 같다.")
