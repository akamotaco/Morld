# stealth.py - 은신/발각 판정 시스템
#
# 발각 확률 공식 (30분 기준):
# detection_rate = 밝기 × 은신가시도 × 엄폐계수 × NPC감지력
#
# 은신 상태:
# - status:stealth = 1: 은신 중
# - 0 (또는 없음): 통상 (비은신)
#
# 은신은 자세(posture)/이동모드(stance)와 독립.
# 소리 기반 자동 해제: sound.emit_sound → _check_stealth_break → on_stealth_noise
#
# NOTE: C# PropSet은 Dictionary<Prop, int>이므로 prop 미존재 시 GetProp이 0을 반환.

import random
import morld
from engine import lighting
from engine.event_core import subscribe_time_elapsed

MILLIS_PER_HOUR = 3_600_000


# ========================================
# 은신 가시도
# ========================================

# 은신 ON: 기본 30% 노출 (장비/스킬로 보정 가능)
STEALTH_VISIBILITY_HIDDEN = 0.3
STEALTH_VISIBILITY_VISIBLE = 1.0


def get_stealth_visibility(unit_id: int = None) -> float:
    """은신 상태에 따른 가시도 반환

    Args:
        unit_id: 유닛 ID (None이면 플레이어)

    Returns:
        float: 0.3 (은신) ~ 1.0 (비은신)
    """
    if unit_id is None:
        unit_id = morld.get_player_id()
    if unit_id is None:
        return STEALTH_VISIBILITY_VISIBLE

    if is_unit_stealthed(unit_id):
        return STEALTH_VISIBILITY_HIDDEN
    return STEALTH_VISIBILITY_VISIBLE


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

def get_cover_coefficient_for(unit_id: int) -> float:
    """유닛 주변 엄폐물에 따른 발각 계수 반환"""
    loc = morld.get_unit_location(unit_id)
    if loc is None:
        return COVER_COEFFICIENT_NONE

    region_id, location_id = loc
    unit_info = morld.get_unit_info(unit_id)
    if not unit_info:
        return COVER_COEFFICIENT_NONE
    unit_x = unit_info.get("x")
    if unit_x is None:
        return COVER_COEFFICIENT_NONE

    objects = morld.get_objects_at_location(region_id, location_id)
    if not objects:
        return COVER_COEFFICIENT_NONE

    min_distance = float('inf')
    for obj_id in objects:
        obj_info = morld.get_unit_info(obj_id)
        obj_x = obj_info.get("x") if obj_info else None
        if obj_x is not None:
            distance = abs(unit_x - obj_x)
            min_distance = min(min_distance, distance)

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
    """NPC의 감지력 반환 (1.0 = 기본)"""
    perception = morld.get_unit_prop(npc_id, "perception:base")
    if perception is None:
        perception = DEFAULT_PERCEPTION
    return perception / 100.0


def calculate_detection_rate(npc_id: int = None) -> float:
    """발각 확률 계산 (30분 기준)

    공식: 밝기 × 은신가시도 × 엄폐 × NPC감지력
    """
    brightness = lighting.get_detection_brightness()
    visibility = get_stealth_visibility()
    cover = get_cover_coefficient()
    perception = get_npc_perception(npc_id) if npc_id is not None else 1.0

    rate = brightness * visibility * cover * perception
    return max(0.0, min(1.0, rate))


def detection_check(npc_id: int = None) -> bool:
    """발각 판정 실행 (1회). True = 발각됨"""
    rate = calculate_detection_rate(npc_id)
    return random.random() < rate


def check_detection_over_time(elapsed_minutes: int, npc_ids: list = None) -> int:
    """시간 경과에 따른 발각 판정 (30분마다). 발각한 NPC ID 반환 (없으면 None)"""
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
    """플레이어가 은신 중인지 확인"""
    player_id = morld.get_player_id()
    if player_id is None:
        return False
    return morld.get_unit_prop(player_id, "status:stealth") == 1


def is_unit_stealthed(unit_id: int) -> bool:
    """유닛이 은신 중인지 확인"""
    return morld.get_unit_prop(unit_id, "status:stealth") == 1


def enter_stealth(unit_id: int) -> bool:
    """은신 진입 (status:stealth=1 설정, 자세 변경 없음)"""
    if is_unit_stealthed(unit_id):
        return True

    morld.set_unit_prop(unit_id, "status:stealth", 1)
    name = morld.get_unit_name(unit_id) or str(unit_id)
    print(f"[stealth] {name} 은신 진입")
    return True


def exit_unit_stealth(unit_id: int):
    """은신 해제 (status:stealth 제거, 자세 유지)"""
    stealth = morld.get_unit_prop(unit_id, "status:stealth")
    if not stealth:
        return

    morld.clear_prop(unit_id, "status:stealth")

    player_id = morld.get_player_id()
    if unit_id == player_id:
        morld.clear_player_meetings()

    name = morld.get_unit_name(unit_id) or str(unit_id)
    print(f"[stealth] {name} 은신 해제")


def set_detected(npc_id: int = None) -> str:
    """플레이어 발각 처리: 은신 해제 + 메시지 반환"""
    player_id = morld.get_player_id()
    if player_id is None:
        return ""

    morld.clear_prop(player_id, "status:stealth")
    morld.clear_player_meetings()

    if npc_id is not None:
        npc_name = morld.get_unit_name(npc_id) or "누군가"
        return f"{npc_name}에게 발각되었다!"
    else:
        return "발각되었다!"


# ========================================
# 이벤트 연동
# ========================================

def resolve_event_with_stealth(npc_id: int, is_forced: bool = False) -> tuple:
    """이벤트 resolve 시 은신 판정"""
    if is_forced:
        return (True, None)
    if not is_player_stealthed():
        return (True, None)

    if detection_check(npc_id):
        msg = set_detected(npc_id)
        return (True, msg)
    else:
        return (False, "들키지 않은 것 같다.")


# ========================================
# NPC 감지 (플레이어 → 은신 NPC)
# ========================================

def get_player_perception() -> float:
    """플레이어 감지력 반환"""
    player_id = morld.get_player_id()
    if player_id is None:
        return 1.0
    perception = morld.get_unit_prop(player_id, "perception:base")
    if perception is None:
        perception = DEFAULT_PERCEPTION
    return perception / 100.0


def calculate_npc_detection_rate(npc_id: int) -> float:
    """은신 NPC 감지 확률 계산 (플레이어가 NPC를 발견할 확률)

    공식: 밝기 × NPC은신가시도 × NPC엄폐계수 × 플레이어감지력
    """
    brightness = lighting.get_detection_brightness()
    visibility = get_stealth_visibility(npc_id)
    cover = get_cover_coefficient_for(npc_id)
    perception = get_player_perception()

    rate = brightness * visibility * cover * perception
    return max(0.0, min(1.0, rate))


def detect_stealthed_npcs(region_id: int, location_id: int) -> list:
    """Location 내 은신 NPC 감지 시도. 감지 성공 시 은신 해제."""
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

        rate = calculate_npc_detection_rate(unit_id)
        if random.random() < rate:
            exit_unit_stealth(unit_id)
            name = morld.get_unit_name(unit_id) or str(unit_id)
            print(f"[stealth] 플레이어가 {name}을(를) 발견! (rate={rate:.2f})")
            detected.append(unit_id)

    return detected


# ========================================
# 소음 은신 해제 콜백
# ========================================

_on_noise_callback = None


def set_noise_callback(callback):
    """시나리오별 소음 은신 해제 콜백 등록

    Args:
        callback: (source_id: int, intensity: float) -> None
    """
    global _on_noise_callback
    _on_noise_callback = callback


def on_stealth_noise(source_id: int, intensity: float):
    """소리에 의한 은신 해제 (sound.py에서 호출)

    콜백 등록 시 콜백 호출, 미등록 시 개인 은신 해제.
    """
    if _on_noise_callback:
        _on_noise_callback(source_id, intensity)
    else:
        exit_unit_stealth(source_id)


# ========================================
# 30분 주기 감지 (시간 구독)
# ========================================

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
    global _on_noise_callback
    _on_noise_callback = None
    subscribe_time_elapsed(_on_stealth_check, min_interval=MILLIS_PER_HOUR // 2)
