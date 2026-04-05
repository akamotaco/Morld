# stealth.py - 은신 시스템 (S04)
#
# S02 기반 + 파티 은신 지원.
# 탐지율 = 밝기 × 자세 × 엄폐 × 적 인지력
# 파티 전체의 탐지율 = 가장 눈에 띄는 멤버 기준 (max)
# 척후 클래스 보유 시 파티 전체 탐지율 보정.

import morld
import lighting
from events import subscribe_time_elapsed

MILLIS_PER_HOUR = 3_600_000

_initialized = False

# === 자세별 탐지 계수 ===
POSTURE_COEFFICIENTS = {
    "standing": 1.0,
    "crouch": 0.5,
    "lying": 0.3,
    "sitting": 0.8,
}

# 척후 클래스 파티 보정 (파티에 척후가 있으면 전체 탐지율 x배)
SCOUT_PARTY_MODIFIER = 0.6

# 엄폐 거리 구간
COVER_NEAR = 5    # 오브젝트 5 이내 → 0.3
COVER_MID = 15    # 오브젝트 15 이내 → 0.6
COVER_FAR_COEFF = 1.0  # 그 외 → 1.0


def reset():
    """챕터 전환 시 리셋"""
    global _initialized
    _initialized = False


def _ensure_initialized():
    """lazy init"""
    global _initialized
    if _initialized:
        return
    _initialized = True


# ========================================
# 탐지율 계산
# ========================================

def get_posture_coefficient(unit_id=None):
    """자세 기반 탐지 계수"""
    if unit_id is None:
        unit_id = morld.get_player_id()
    if unit_id is None:
        return 1.0
    posture_props = morld.get_unit_props_by_type(unit_id, "posture")
    if posture_props:
        posture = list(posture_props.keys())[0]
        return POSTURE_COEFFICIENTS.get(posture, 1.0)
    return 1.0


def get_cover_coefficient(unit_id=None):
    """엄폐 계수 (가장 가까운 오브젝트와의 거리 기반)"""
    if unit_id is None:
        unit_id = morld.get_player_id()
    if unit_id is None:
        return COVER_FAR_COEFF

    loc = morld.get_unit_location(unit_id)
    if not loc:
        return COVER_FAR_COEFF

    info = morld.get_unit_info(unit_id)
    if not info:
        return COVER_FAR_COEFF
    unit_x = info.get("x", 0)

    objects = morld.get_objects_at_location(loc[0], loc[1])
    if not objects:
        return COVER_FAR_COEFF

    min_dist = 9999
    for obj_id in objects:
        obj_info = morld.get_unit_info(obj_id)
        if obj_info:
            obj_x = obj_info.get("x", 0)
            dist = abs(unit_x - obj_x)
            if dist < min_dist:
                min_dist = dist

    if min_dist <= COVER_NEAR:
        return 0.3
    if min_dist <= COVER_MID:
        return 0.6
    return COVER_FAR_COEFF


def get_npc_perception(npc_id):
    """NPC 인지력 (perception:base prop, 기본 100 → 1.0)"""
    val = morld.get_unit_prop(npc_id, "perception:base")
    if val is None:
        return 1.0
    return max(0.1, val / 100)


def get_player_perception():
    """플레이어 인지력"""
    player_id = morld.get_player_id()
    if player_id is None:
        return 1.0
    val = morld.get_unit_prop(player_id, "perception:base")
    if val is None:
        return 1.0
    return max(0.1, val / 100)


def calculate_detection_rate(unit_id=None, npc_id=None):
    """단일 유닛의 탐지율 계산 (0.0 ~ 1.0)

    탐지율 = 밝기 × 자세 × 엄폐 × 적 인지력
    """
    if unit_id is None:
        unit_id = morld.get_player_id()
    if unit_id is None:
        return 1.0

    brightness = lighting.get_detection_brightness()
    posture = get_posture_coefficient(unit_id)
    cover = get_cover_coefficient(unit_id)
    perception = get_npc_perception(npc_id) if npc_id else 1.0

    rate = brightness * posture * cover * perception
    return max(0.0, min(1.0, rate))


# ========================================
# 파티 은신 (S04 확장)
# ========================================

def calculate_party_detection_rate(npc_id=None):
    """파티 전체 탐지율 = 가장 눈에 띄는 멤버 기준 (max)

    척후 클래스가 파티에 있으면 전체 탐지율 × SCOUT_PARTY_MODIFIER.

    Returns: float 0.0 ~ 1.0
    """
    try:
        import party
        members = party.get_members()
    except ImportError:
        members = None

    if not members:
        return calculate_detection_rate(npc_id=npc_id)

    # 각 멤버의 개별 탐지율
    max_rate = 0.0
    has_scout = False
    for uid in members:
        rate = calculate_detection_rate(unit_id=uid, npc_id=npc_id)
        if rate > max_rate:
            max_rate = rate
        # 척후 클래스 체크
        char_class = morld.get_unit_prop(uid, "character_class")
        if char_class == "척후":
            has_scout = True

    # 척후 보정
    if has_scout:
        max_rate *= SCOUT_PARTY_MODIFIER

    return max(0.0, min(1.0, max_rate))


def detection_check(npc_id=None, use_party=True):
    """탐지 판정 (True = 발각)"""
    import random
    if use_party:
        rate = calculate_party_detection_rate(npc_id)
    else:
        rate = calculate_detection_rate(npc_id=npc_id)
    return random.random() < rate


# ========================================
# 은신 상태 관리
# ========================================

def is_player_stealthed():
    """플레이어 은신 상태 여부"""
    player_id = morld.get_player_id()
    if player_id is None:
        return False
    return morld.get_unit_prop(player_id, "status:stealth") == 1


def is_unit_stealthed(unit_id):
    """유닛 은신 상태 여부"""
    return morld.get_unit_prop(unit_id, "status:stealth") == 1


def enter_stealth(unit_id):
    """은신 진입 (자세 변경 없음)"""
    if is_unit_stealthed(unit_id):
        return True
    morld.set_unit_prop(unit_id, "status:stealth", 1)
    name = morld.get_unit_name(unit_id) or str(unit_id)
    print(f"[stealth] {name} 은신 진입")
    return True


def exit_unit_stealth(unit_id):
    """은신 해제 (자세 유지)"""
    if not morld.get_unit_prop(unit_id, "status:stealth"):
        return
    morld.clear_prop(unit_id, "status:stealth")
    player_id = morld.get_player_id()
    if unit_id == player_id:
        morld.clear_player_meetings()
    name = morld.get_unit_name(unit_id) or str(unit_id)
    print(f"[stealth] {name} 은신 해제")


def enter_party_stealth():
    """파티 전체 은신 진입"""
    try:
        import party
        members = party.get_members()
        if members:
            for uid in members:
                enter_stealth(uid)
            return True
    except ImportError:
        pass
    # 파티 없으면 플레이어만
    player_id = morld.get_player_id()
    if player_id:
        return enter_stealth(player_id)
    return False


def exit_party_stealth():
    """파티 전체 은신 해제"""
    try:
        import party
        members = party.get_members()
        if members:
            for uid in members:
                exit_unit_stealth(uid)
            return
    except ImportError:
        pass
    player_id = morld.get_player_id()
    if player_id:
        exit_unit_stealth(player_id)


def is_party_stealthed():
    """파티 전체가 은신 중인지 (전원 은신이어야 True)"""
    try:
        import party
        members = party.get_members()
        if members:
            return all(is_unit_stealthed(uid) for uid in members)
    except ImportError:
        pass
    return is_player_stealthed()


def set_detected(npc_id=None):
    """발각 처리 — 파티 전체 은신 해제"""
    exit_party_stealth()
    try:
        morld.clear_player_meetings()
    except Exception:
        pass
    npc_name = ""
    if npc_id:
        info = morld.get_unit_info(npc_id)
        npc_name = info.get("name", "") if info else ""
    if npc_name:
        return f"{npc_name}에게 발각되었다!"
    return "발각되었다!"


# ========================================
# 이벤트 연동
# ========================================

def resolve_event_with_stealth(npc_id, is_forced=False):
    """on_meet 이벤트에서 은신 판정

    Returns: (proceed: bool, message: str|None)
    """
    if is_forced:
        return True, None

    if not is_party_stealthed():
        return True, None

    if detection_check(npc_id, use_party=True):
        msg = set_detected(npc_id)
        return True, msg
    else:
        return False, None


def detect_stealthed_npcs(region_id, location_id):
    """Location 내 은신 NPC 탐지 (플레이어 시점)

    Returns: list of detected NPC unit_ids
    """
    import random
    detected = []
    units = morld.get_characters_at_location(region_id, location_id)
    if not units:
        return detected

    player_id = morld.get_player_id()
    player_perception = get_player_perception()

    for uid in units:
        if uid == player_id:
            continue
        if not is_unit_stealthed(uid):
            continue

        brightness = lighting.get_detection_brightness()
        npc_posture = get_posture_coefficient(uid)
        npc_cover = get_cover_coefficient(uid)
        rate = brightness * npc_posture * npc_cover * player_perception

        if random.random() < rate:
            exit_unit_stealth(uid)
            detected.append(uid)

    return detected


# === 30분 주기 탐지 체크 ===

def _on_stealth_check(millis):
    """주기적 은신 NPC 탐지"""
    _ensure_initialized()
    player_id = morld.get_player_id()
    if player_id is None:
        return
    loc = morld.get_unit_location(player_id)
    if loc:
        detect_stealthed_npcs(loc[0], loc[1])


subscribe_time_elapsed(_on_stealth_check, min_interval=MILLIS_PER_HOUR // 2)
