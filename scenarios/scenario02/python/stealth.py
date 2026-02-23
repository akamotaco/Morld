# stealth.py - 은신/발각 판정 시스템
#
# 발각 확률 공식 (30분 기준):
# detection_rate = 밝기 × 자세계수 × 엄폐계수 × NPC감지력
#
# 은신 상태:
# - status:stealth = 1: 은신 중
# - 0 (또는 없음): 통상 (비은신)
#
# NOTE: C# PropSet은 Dictionary<Prop, int>이므로 prop 미존재 시 GetProp이 0을 반환.

import random
import morld
import lighting


# ========================================
# 자세 계수
# ========================================

POSTURE_DETECTION = {
    "standing": 1.0,
    "crouch": 0.5,
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

def get_posture_coefficient(unit_id: int = None) -> float:
    """
    유닛 자세에 따른 발각 계수 반환

    Args:
        unit_id: 유닛 ID (None이면 플레이어)

    Returns:
        float: 0.5 (crouch) ~ 1.0 (standing)
    """
    if unit_id is None:
        unit_id = morld.get_player_id()
    if unit_id is None:
        return DEFAULT_POSTURE_DETECTION

    # 자세 확인
    if morld.get_unit_prop(unit_id, "posture:crouch") == 1:
        return POSTURE_DETECTION["crouch"]
    else:
        return POSTURE_DETECTION["standing"]


def get_cover_coefficient_for(unit_id: int) -> float:
    """
    특정 유닛 주변 엄폐물에 따른 발각 계수 반환

    현재 Location의 오브젝트와의 X 거리 중 가장 가까운 것 기준

    Args:
        unit_id: 유닛 ID

    Returns:
        float: 0.3 (근접) ~ 1.0 (없음)
    """
    loc = morld.get_unit_location(unit_id)
    if loc is None:
        return COVER_COEFFICIENT_NONE

    region_id, location_id = loc
    unit_x = morld.get_unit_x(unit_id)

    # Location 내 오브젝트 조회
    objects = morld.get_objects_at_location(region_id, location_id)
    if not objects:
        return COVER_COEFFICIENT_NONE

    # 가장 가까운 오브젝트와의 거리
    min_distance = float('inf')
    for obj_id in objects:
        obj_x = morld.get_unit_x(obj_id)
        if obj_x is not None:
            distance = abs(unit_x - obj_x)
            min_distance = min(min_distance, distance)

    # 거리에 따른 계수
    if min_distance <= COVER_DISTANCE_NEAR:
        return COVER_COEFFICIENT_NEAR
    elif min_distance <= COVER_DISTANCE_MID:
        return COVER_COEFFICIENT_MID
    else:
        return COVER_COEFFICIENT_NONE


def get_cover_coefficient() -> float:
    """플레이어 엄폐 계수 (get_cover_coefficient_for 래퍼)"""
    player_id = morld.get_player_id()
    if player_id is None:
        return COVER_COEFFICIENT_NONE
    return get_cover_coefficient_for(player_id)


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


def set_detected(npc_id: int = None) -> str:
    """
    플레이어 발각 처리: 은신 해제 + 메시지 반환

    Args:
        npc_id: 발각한 NPC ID (로그용)

    Returns:
        str: 로그 메시지
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    # 은신 해제 (통상 상태로)
    morld.clear_prop(player_id, "status:stealth")

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


# ========================================
# NPC 은신 시스템
# ========================================

def is_unit_stealthed(unit_id: int) -> bool:
    """
    유닛이 은신 중인지 확인

    Args:
        unit_id: 유닛 ID

    Returns:
        bool: status:stealth == 1
    """
    stealth = morld.get_unit_prop(unit_id, "status:stealth")
    return stealth == 1


def enter_stealth(unit_id: int) -> bool:
    """
    유닛 은신 진입 (posture:crouch + status:stealth=1)

    Args:
        unit_id: 유닛 ID

    Returns:
        bool: 은신 진입 성공 여부
    """
    # 이미 은신 중이면 스킵
    if is_unit_stealthed(unit_id):
        return True

    # posture:crouch 설정
    posture_props = morld.get_unit_props_by_type(unit_id, "posture")
    for prop_name in posture_props:
        morld.clear_prop(unit_id, f"posture:{prop_name}")
    morld.set_unit_prop(unit_id, "posture:crouch", 1)

    # 은신 상태 설정
    morld.set_unit_prop(unit_id, "status:stealth", 1)
    name = morld.get_unit_name(unit_id) or str(unit_id)
    print(f"[stealth] {name} 은신 진입")
    return True


def exit_unit_stealth(unit_id: int, stand_up: bool = True):
    """
    유닛 은신 해제

    Args:
        unit_id: 유닛 ID
        stand_up: True이면 standing 자세로 복귀
    """
    stealth = morld.get_unit_prop(unit_id, "status:stealth")
    if not stealth:  # 0 또는 None = 일반 상태
        return

    # 은신 prop 정리
    morld.clear_prop(unit_id, "status:stealth")

    # standing 자세로 복귀
    if stand_up:
        posture_props = morld.get_unit_props_by_type(unit_id, "posture")
        for prop_name in posture_props:
            morld.clear_prop(unit_id, f"posture:{prop_name}")

    name = morld.get_unit_name(unit_id) or str(unit_id)
    print(f"[stealth] {name} 은신 해제")


# ========================================
# NPC 감지 (플레이어 → 은신 NPC)
# ========================================

def get_player_perception() -> float:
    """
    플레이어 감지력 반환

    Returns:
        float: perception:base / 100 (기본 1.0)
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return 1.0
    perception = morld.get_unit_prop(player_id, "perception:base")
    if perception is None:
        perception = DEFAULT_PERCEPTION
    return perception / 100.0


def calculate_npc_detection_rate(npc_id: int) -> float:
    """
    은신 NPC 감지 확률 계산 (플레이어가 NPC를 발견할 확률)

    공식: 밝기 × NPC자세계수 × NPC엄폐계수 × 플레이어감지력

    Args:
        npc_id: 은신 NPC ID

    Returns:
        float: 0.0 ~ 1.0 (감지 확률)
    """
    # 밝기
    brightness = lighting.get_detection_brightness()

    # NPC 자세 계수
    posture = get_posture_coefficient(npc_id)

    # NPC 엄폐 계수
    cover = get_cover_coefficient_for(npc_id)

    # 플레이어 감지력
    perception = get_player_perception()

    rate = brightness * posture * cover * perception
    return max(0.0, min(1.0, rate))


def detect_stealthed_npcs(region_id: int, location_id: int) -> list:
    """
    Location 내 은신 NPC 감지 시도. 감지 성공 시 은신 해제.

    Args:
        region_id: Region ID
        location_id: Location ID

    Returns:
        list: 감지된 NPC ID 목록
    """
    # Location 내 캐릭터 조회
    player_id = morld.get_player_id()
    chars = morld.get_characters_at_location(region_id, location_id)
    if not chars:
        return []

    detected = []
    for unit_id in chars:
        if unit_id == player_id:
            continue
        if not is_unit_stealthed(unit_id):
            continue

        # 감지 판정
        rate = calculate_npc_detection_rate(unit_id)
        if random.random() < rate:
            exit_unit_stealth(unit_id)
            name = morld.get_unit_name(unit_id) or str(unit_id)
            print(f"[stealth] 플레이어가 {name}을(를) 발견! (rate={rate:.2f})")
            detected.append(unit_id)

    return detected


# ========================================
# 공개 행동 은신 자동 해제
# ========================================

def auto_exit_stealth_for_interaction():
    """
    공개 NPC 상호작용 시 플레이어 은신 → 통상 전환.
    대화, 거래 등 공개 행동에서 호출.
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return

    stealth = morld.get_unit_prop(player_id, "status:stealth")
    if not stealth:  # 0 또는 None = 일반 상태
        return

    # 은신 상태 해제
    morld.clear_prop(player_id, "status:stealth")

    # standing 자세로 복귀
    posture_props = morld.get_unit_props_by_type(player_id, "posture")
    for prop_name in posture_props:
        morld.clear_prop(player_id, f"posture:{prop_name}")

    print("[stealth] 공개 행동으로 은신 해제")


# ========================================
# 30분 주기 감지 (시간 구독)
# ========================================

_initialized = False


def _ensure_initialized():
    """lazy init — 30분 주기 구독 등록"""
    global _initialized
    if _initialized:
        return
    _initialized = True
    from events import subscribe_time_elapsed
    subscribe_time_elapsed(_on_stealth_check, min_interval=1_800_000)  # 30분
    print("[stealth] 30분 주기 감지 구독 등록")


def _on_stealth_check(millis):
    """30분마다 플레이어 위치의 은신 NPC 감지 재판정"""
    player_id = morld.get_player_id()
    if player_id is None:
        return
    loc = morld.get_unit_location(player_id)
    if loc is None:
        return
    detect_stealthed_npcs(loc[0], loc[1])


def reset():
    """챕터 전환 초기화"""
    global _initialized
    _initialized = False
    print("[stealth] reset")
