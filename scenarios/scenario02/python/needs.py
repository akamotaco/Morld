# needs.py - 욕구 시스템
#
# NPC/플레이어의 5대 욕구를 수치로 추적.
# 매 시간 자동 업데이트 (subscribe_time_elapsed).
#
# 욕구 목록:
#   배변 (욕구:배변) — 식사 시 증가, 화장실 사용 시 0
#   피로 (욕구:피로) — 각성 중 증가, 수면 중 감소
#   청결 (욕구:청결) — 오염/젖음 기반 증가, 목욕 시 0
#   사회 (욕구:사회) — 고립 시 증가, 대화/교류 시 감소
#   성욕 (상태:성욕) — 자연 증가 (50 상한), romance.py 소유
#
# DES 호환: subscribe_time_elapsed(min_interval=1h)

import morld
from events import subscribe_time_elapsed

# === Props ===
PROP_EXCRETION = "욕구:배변"
PROP_FATIGUE = "욕구:피로"
PROP_CLEANLINESS = "욕구:청결"
PROP_SOCIAL = "욕구:사회"
PROP_AROUSAL = "상태:성욕"  # romance.py 소유, 읽기+자연증가만

# === 증가율 (시간당) ===
FATIGUE_RATE = 4              # 각성 중 +4/h (25시간에 100 도달)
FATIGUE_SLEEP_RECOVERY = 12   # 수면 중 -12/h (8시간에 ~96 감소)
CLEANLINESS_BASE_RATE = 1     # 기본 +1/h
CLEANLINESS_POLLUTION_FACTOR = 0.1  # 오염수치 x 0.1 추가
CLEANLINESS_WETNESS_FACTOR = 0.05   # 젖음 x 0.05 추가
SOCIAL_RATE = 1               # 고립 시 +1/h
AROUSAL_NATURAL_RATE = 0.5    # 자연 성욕 증가 +0.5/h
AROUSAL_NATURAL_CAP = 50      # 자연 증가 상한
SUBMISSION_DECAY_INTERVAL = 2 # 복종 자연 감소 간격 (시간) — 미사용 (항상성으로 대체)

# === 관계 항상성 (basin 수렴) ===
HOMEOSTASIS_RATE = 0.5  # 시간당 수렴 속도

# basins: (upper_bound, attractor) — current ≤ upper_bound → attractor로 수렴
AFFECTION_BASINS = [(35, 0), (75, 50), (100, 100)]
REBELLION_BASINS = [(25, 0), (50, 35), (100, 75)]
SUBMISSION_BASINS = [(20, 0), (60, 40), (100, 80)]

# === 임계치 (NPC 인터럽트, Phase B에서 사용) ===
EXCRETION_THRESHOLD = 70
FATIGUE_THRESHOLD = 80
CLEANLINESS_THRESHOLD = 70

# 시간 상수
MILLIS_PER_HOUR = 3_600_000

# 등록된 NPC
_npc_registry = set()
_accumulated = {}  # unit_id -> 밀리초 누적
_last_year = None  # 나이 시스템: 연도 변경 감지용


# ========================================
# 등록/리셋
# ========================================

def register_character(unit_id):
    """NPC 욕구 추적 등록 (Agent.__init__에서 호출)"""
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


def get_social(unit_id):
    """사회 욕구 조회 (0-100)"""
    return morld.get_unit_prop(unit_id, PROP_SOCIAL) or 0


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
    """피로도 감소 (수면 중)"""
    current = get_fatigue(unit_id)
    morld.set_unit_prop(unit_id, PROP_FATIGUE, max(0, current - amount))


def set_cleanliness(unit_id, value):
    """불결도 설정 (목욕 시 0으로)"""
    morld.set_unit_prop(unit_id, PROP_CLEANLINESS, max(0, min(100, value)))


def reduce_social(unit_id, amount):
    """사회 욕구 감소 (대화/교류 시)"""
    current = get_social(unit_id)
    morld.set_unit_prop(unit_id, PROP_SOCIAL, max(0, current - amount))


# ========================================
# NPC 체크 (Phase B — think 인터럽트용)
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
# 매시간 업데이트 (내부)
# ========================================

def _get_max_desire(unit_id):
    """유닛의 모든 관계에서 최고 욕망 값 반환"""
    props = morld.get_unit_props(unit_id)
    if not props:
        return 0
    max_val = 0
    for key, val in props.items():
        if key.startswith("관계:") and key.endswith(":욕망"):
            if isinstance(val, (int, float)) and val > max_val:
                max_val = val
    return max_val


def _get_arousal_cap(unit_id):
    """욕망 기반 성욕 자연 상한 계산

    욕망 0 → cap 50, 욕망 50 → cap 75, 욕망 100 → cap 100
    """
    max_desire = _get_max_desire(unit_id)
    return min(100, AROUSAL_NATURAL_CAP + max_desire * 0.5)


def _is_sleeping(unit_id):
    """유닛이 수면 중인지 (seated_on prop = 침대에 누움)"""
    seated_on = morld.get_unit_props_by_type(unit_id, "seated_on")
    return bool(seated_on)


def _is_alone(unit_id):
    """같은 location에 다른 캐릭터가 없으면 True"""
    loc = morld.get_unit_location(unit_id)
    if not loc:
        return True
    units = morld.get_units_at_location(loc[0], loc[1])
    if not units:
        return True
    return len([u for u in units if u != unit_id]) == 0


def _apply_homeostasis(unit_id, prop_key, basins):
    """관계 수치를 attractor basin으로 수렴

    basins: [(upper_bound, attractor), ...] — 오름차순
    current ≤ upper_bound인 첫 번째 basin의 attractor로 수렴.
    """
    current = morld.get_unit_prop(unit_id, prop_key) or 0
    # 해당 basin 찾기
    attractor = basins[-1][1]  # fallback: 마지막 basin
    for upper, attr in basins:
        if current <= upper:
            attractor = attr
            break
    if current == attractor:
        return
    # attractor 방향으로 수렴
    if attractor > current:
        delta = min(attractor - current, HOMEOSTASIS_RATE)
    else:
        delta = -min(current - attractor, HOMEOSTASIS_RATE)
    new_val = max(0, min(100, current + delta))
    morld.set_unit_prop(unit_id, prop_key, new_val)


def _process_hourly(unit_id):
    """캐릭터 1시간 욕구 업데이트"""
    # 피로: 수면 중이면 감소, 아니면 증가
    if _is_sleeping(unit_id):
        reduce_fatigue(unit_id, FATIGUE_SLEEP_RECOVERY)
    else:
        add_fatigue(unit_id, FATIGUE_RATE)
        # 임신 3분기 피로 보너스
        try:
            import pregnancy
            trimester = pregnancy.get_trimester(unit_id)
            if trimester == "trimester_3":
                fatigue_bonus = pregnancy.PREGNANCY_EFFECTS["trimester_3"]["fatigue_bonus"]
                if fatigue_bonus > 0:
                    add_fatigue(unit_id, fatigue_bonus)
        except ImportError:
            pass

    # 청결: 오염 + 젖음 기반 증가
    pollution_val = 0
    wetness_val = 0
    try:
        import pollution
        pollution_val = pollution.get_unit_pollution(unit_id) or 0
    except ImportError:
        pass
    try:
        import humidity
        wetness_val = humidity.get_unit_wetness(unit_id) or 0
    except ImportError:
        pass

    # 정액 오염: 불결도 기여 + 자연 감소
    semen_total = 0
    _SEMEN_PARTS = ["얼굴", "가슴", "배", "음부", "엉덩이"]
    for sp in _SEMEN_PARTS:
        val = morld.get_unit_prop(unit_id, f"오염물:정액:{sp}") or 0
        semen_total += val
        if val > 0:
            morld.set_unit_prop(unit_id, f"오염물:정액:{sp}", max(0, val - 5))

    cleanliness_increase = (CLEANLINESS_BASE_RATE
                            + pollution_val * CLEANLINESS_POLLUTION_FACTOR
                            + wetness_val * CLEANLINESS_WETNESS_FACTOR
                            + semen_total * 0.2)
    current = get_cleanliness(unit_id)
    morld.set_unit_prop(unit_id, PROP_CLEANLINESS,
                        min(100, current + cleanliness_increase))

    # 체내 정액: 매시간 -10 감소, 음부/항문은 외부로 흘러나옴
    try:
        from romance import INTERNAL_SEMEN_PARTS, get_internal_semen
        _DRIP_MAP = {"음부": "음부", "항문": "엉덩이"}  # 체내→체외 매핑
        for ip in INTERNAL_SEMEN_PARTS:
            iv = get_internal_semen(unit_id, ip)
            if iv > 0:
                decay = min(iv, 10)
                morld.set_unit_prop(unit_id, f"체내:정액:{ip}", max(0, iv - decay))
                # 흘러나옴 (구강 제외)
                drip_target = _DRIP_MAP.get(ip)
                if drip_target:
                    drip_amount = min(5, decay)
                    ext_val = morld.get_unit_prop(unit_id, f"오염물:정액:{drip_target}") or 0
                    morld.set_unit_prop(unit_id, f"오염물:정액:{drip_target}",
                                        min(100, ext_val + drip_amount))
    except ImportError:
        pass

    # 사회: 혼자이면 증가
    if _is_alone(unit_id):
        current_social = get_social(unit_id)
        morld.set_unit_prop(unit_id, PROP_SOCIAL,
                            min(100, current_social + SOCIAL_RATE))

    # 성욕: 자연 증가 (욕망 기반 동적 상한) + 상한 초과 시 클램프
    arousal_cap = _get_arousal_cap(unit_id)
    current_arousal = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
    if current_arousal < arousal_cap:
        arousal_rate = AROUSAL_NATURAL_RATE
        # 성적 지향성 배율
        player_id_h = morld.get_player_id()
        if player_id_h:
            try:
                import gender as gender_mod
                arousal_rate *= gender_mod.get_orientation_multiplier(unit_id, player_id_h)
            except ImportError:
                pass
        morld.set_unit_prop(unit_id, PROP_AROUSAL,
                            min(arousal_cap,
                                current_arousal + arousal_rate))
    elif current_arousal > arousal_cap:
        morld.set_unit_prop(unit_id, PROP_AROUSAL, arousal_cap)

    # 관계 항상성: 호감/반발/복종 basin 수렴
    player_id_h = morld.get_player_id()
    if player_id_h:
        player_info_h = morld.get_unit_info(player_id_h)
        player_name_h = player_info_h.get("name", "주인공") if player_info_h else "주인공"
        _apply_homeostasis(unit_id, f"관계:{player_name_h}:호감", AFFECTION_BASINS)
        _apply_homeostasis(unit_id, f"관계:{player_name_h}:반발", REBELLION_BASINS)
        _apply_homeostasis(unit_id, f"관계:{player_name_h}:복종", SUBMISSION_BASINS)

    # 모성 욕구: 아이가 있는 경우 증가
    try:
        import pregnancy
        children = pregnancy.get_children(unit_id)
        if children:
            mother_loc = morld.get_unit_location(unit_id)
            child_loc = morld.get_unit_location(children[-1])  # 막내 기준
            current_maternal = morld.get_unit_prop(unit_id, "욕구:모성") or 0
            if mother_loc != child_loc:
                morld.set_unit_prop(unit_id, "욕구:모성",
                                    min(100, current_maternal + 3))
            else:
                morld.set_unit_prop(unit_id, "욕구:모성",
                                    min(100, current_maternal + 1))
    except ImportError:
        pass


def _process_accumulated(unit_id, millis):
    """시간 누적 후 1시간 단위로 처리"""
    _accumulated[unit_id] = _accumulated.get(unit_id, 0) + millis
    if _accumulated[unit_id] >= MILLIS_PER_HOUR:
        hours = _accumulated[unit_id] // MILLIS_PER_HOUR
        _accumulated[unit_id] %= MILLIS_PER_HOUR
        for _ in range(int(hours)):
            _process_hourly(unit_id)


# ========================================
# 이벤트 구독
# ========================================

def _age_all_characters():
    """모든 등록 캐릭터 나이 +1 (연도 변경 시 호출)"""
    # 플레이어
    player_id = morld.get_player_id()
    if player_id:
        current_age = morld.get_unit_prop(player_id, "나이")
        if current_age is not None:
            morld.set_unit_prop(player_id, "나이", current_age + 1)

    # NPC
    for unit_id in _npc_registry:
        current_age = morld.get_unit_prop(unit_id, "나이")
        if current_age is not None:
            morld.set_unit_prop(unit_id, "나이", current_age + 1)


def _on_time_elapsed(millis):
    """on_time_elapsed 핸들러 (1시간 간격)"""
    global _last_year

    # 연도 변경 감지 → 나이 증가
    time_info = morld.get_time_info()
    if time_info:
        current_year = time_info.get("year", 0)
        if _last_year is None:
            _last_year = current_year
        elif current_year != _last_year:
            _last_year = current_year
            _age_all_characters()

    # 플레이어 처리 (등록 불필요)
    player_id = morld.get_player_id()
    if player_id is not None:
        _process_accumulated(player_id, millis)

    # 등록된 NPC 처리
    for unit_id in _npc_registry:
        _process_accumulated(unit_id, millis)


# 모듈 로드 시 이벤트 구독 (1시간 간격)
subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
