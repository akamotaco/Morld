# needs.py - 욕구 시스템 (S04)
#
# S02 기반, 연애 관련 제외.
# NPC/플레이어의 기본 욕구 추적.
# 매 시간 자동 업데이트 (subscribe_time_elapsed).
#
# 욕구 목록:
#   배변 (욕구:배변) — 식사 시 증가, 화장실 사용 시 0
#   피로 (욕구:피로) — 각성 중 증가, 수면 중 감소
#   청결 (욕구:청결) — 오염 기반 증가, 목욕 시 0

import morld
from events import subscribe_time_elapsed

# === Props ===
PROP_EXCRETION = "욕구:배변"
PROP_FATIGUE = "욕구:피로"
PROP_CLEANLINESS = "욕구:청결"

# === 증가율 (시간당) ===
FATIGUE_RATE = 4              # 각성 중 +4/h (25시간에 100 도달)
FATIGUE_SLEEP_RECOVERY = 12   # 수면 중 -12/h (8시간에 ~96 감소)
CLEANLINESS_BASE_RATE = 1     # 기본 +1/h
CLEANLINESS_POLLUTION_FACTOR = 0.1  # 오염수치 x 0.1 추가

# === 임계치 (NPC 인터럽트용) ===
EXCRETION_THRESHOLD = 70
FATIGUE_THRESHOLD = 80
CLEANLINESS_THRESHOLD = 70

# 시간 상수
MILLIS_PER_HOUR = 3_600_000

# 등록된 NPC
_npc_registry = set()
_accumulated = {}  # unit_id -> 밀리초 누적
_last_year = None


# ========================================
# 등록/리셋
# ========================================

def register_character(unit_id):
    """NPC 욕구 추적 등록"""
    _npc_registry.add(unit_id)
    _accumulated[unit_id] = 0


def reset():
    """챕터 전환 시 리셋"""
    global _last_year
    _npc_registry.clear()
    _accumulated.clear()
    _last_year = None


# ========================================
# 조회 API
# ========================================

def get_excretion(unit_id):
    """배변욕 조회 (0-100)"""
    return morld.get_unit_prop(unit_id, PROP_EXCRETION) or 0


def get_fatigue(unit_id):
    """피로도 조회 (0-100)"""
    return morld.get_unit_prop(unit_id, PROP_FATIGUE) or 0


def get_cleanliness(unit_id):
    """불결도 조회 (0-100)"""
    return morld.get_unit_prop(unit_id, PROP_CLEANLINESS) or 0


# ========================================
# 수정 API
# ========================================

def add_excretion(unit_id, amount):
    """배변욕 증가 (식사 시 호출)"""
    current = get_excretion(unit_id)
    morld.set_unit_prop(unit_id, PROP_EXCRETION, min(100, current + amount))


def set_excretion(unit_id, value):
    """배변욕 설정 (화장실 사용 시 0으로)"""
    morld.set_unit_prop(unit_id, PROP_EXCRETION, max(0, min(100, value)))


def add_fatigue(unit_id, amount):
    """피로도 증가"""
    current = get_fatigue(unit_id)
    morld.set_unit_prop(unit_id, PROP_FATIGUE, min(100, current + amount))


def reduce_fatigue(unit_id, amount):
    """피로도 감소 (수면/휴식 시)"""
    current = get_fatigue(unit_id)
    morld.set_unit_prop(unit_id, PROP_FATIGUE, max(0, current - amount))


def set_cleanliness(unit_id, value):
    """불결도 설정 (목욕 시 0으로)"""
    morld.set_unit_prop(unit_id, PROP_CLEANLINESS, max(0, min(100, value)))


# ========================================
# NPC 체크 (think 인터럽트용)
# ========================================

def is_npc_need_excretion(unit_id):
    """배변 인터럽트 필요 여부"""
    return get_excretion(unit_id) >= EXCRETION_THRESHOLD


def is_npc_need_sleep(unit_id):
    """피로 인터럽트 필요 여부"""
    return get_fatigue(unit_id) >= FATIGUE_THRESHOLD


def is_npc_need_bath(unit_id):
    """목욕 인터럽트 필요 여부"""
    return get_cleanliness(unit_id) >= CLEANLINESS_THRESHOLD


# ========================================
# 파티 통합 조회 (S04 확장)
# ========================================

def get_party_fatigue_average():
    """파티 전체 평균 피로도"""
    try:
        import party
        members = party.get_members()
        if not members:
            return 0
        total = sum(get_fatigue(uid) for uid in members)
        return total / len(members)
    except ImportError:
        return 0


def get_party_needs_summary():
    """파티 전체 욕구 요약 (UI용)

    Returns: {"excretion_max", "fatigue_avg", "cleanliness_max"}
    """
    try:
        import party
        members = party.get_members()
        if not members:
            return None
        return {
            "excretion_max": max(get_excretion(uid) for uid in members),
            "fatigue_avg": sum(get_fatigue(uid) for uid in members) / len(members),
            "cleanliness_max": max(get_cleanliness(uid) for uid in members),
        }
    except ImportError:
        return None


# ========================================
# 매시간 업데이트
# ========================================

def _is_sleeping(unit_id):
    """유닛이 수면 중인지"""
    seated_on = morld.get_unit_props_by_type(unit_id, "seated_on")
    return bool(seated_on)


def _process_hourly(unit_id):
    """매시간 욕구 업데이트"""
    # 피로
    if _is_sleeping(unit_id):
        reduce_fatigue(unit_id, FATIGUE_SLEEP_RECOVERY)
    else:
        add_fatigue(unit_id, FATIGUE_RATE)

    # 청결
    pollution_val = 0
    try:
        import pollution
        loc = morld.get_unit_location(unit_id)
        if loc:
            pollution_val = pollution.get_location_pollution(loc[0], loc[1]) or 0
    except ImportError:
        pass

    cleanliness_increase = CLEANLINESS_BASE_RATE + pollution_val * CLEANLINESS_POLLUTION_FACTOR
    current_clean = get_cleanliness(unit_id)
    morld.set_unit_prop(unit_id, PROP_CLEANLINESS,
                        min(100, current_clean + cleanliness_increase))


def _on_time_elapsed(elapsed_millis):
    """시간 경과 콜백"""
    global _last_year

    # 나이 시스템: 연도 변경 감지
    time_info = morld.get_time_info()
    if time_info:
        year = time_info.get("year", 1)
        if _last_year is not None and year != _last_year:
            _age_all_characters()
        _last_year = year

    # 등록된 NPC + 플레이어 업데이트
    all_units = set(_npc_registry)
    player_id = morld.get_player_id()
    if player_id is not None:
        all_units.add(player_id)

    for unit_id in all_units:
        acc = _accumulated.get(unit_id, 0) + elapsed_millis
        if acc >= MILLIS_PER_HOUR:
            _process_hourly(unit_id)
            acc -= MILLIS_PER_HOUR
        _accumulated[unit_id] = acc


def _age_all_characters():
    """연도 전환 시 전 캐릭터 나이 +1"""
    all_units = set(_npc_registry)
    player_id = morld.get_player_id()
    if player_id is not None:
        all_units.add(player_id)

    for unit_id in all_units:
        age = morld.get_unit_prop(unit_id, "나이")
        if age is not None:
            morld.set_unit_prop(unit_id, "나이", age + 1)


# === 시간 구독 등록 ===
subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
