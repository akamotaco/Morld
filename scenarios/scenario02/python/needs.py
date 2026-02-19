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
PROP_CLIMAX = "상태:절정"   # 상시 절정 prop (0-100)

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

# === 절정 상시 관리 ===
CLIMAX_NATURAL_DECAY = 3      # 기본 자연 감소 (-3/h, 성인용품 없을 때)
CLIMAX_PASSIVE_AROUSAL_DROP = 30  # 수동 절정 시 성욕 감소량
CLIMAX_PASSIVE_FATIGUE = 5    # 수동 절정 시 피로 증가량

# === 순수/욕망 효과 ===
# 순수 (desire < 40): 성욕 감소, 욕망 (desire >= 40): 성욕 증가 가속
INNOCENCE_DECAY_RATE = 1.0    # desire=0일 때 최대 성욕 감소율 (/h)
DESIRE_BONUS_RATE = 0.5       # desire=100일 때 최대 성욕 증가 보너스 (/h)
DES_BOUNDARY = 40             # 순수/욕망 경계선 (DES_LABEL_THRESHOLD과 동일)

# 호감→욕망 자연 이동
AFFECTION_DESIRE_SHIFT_RATE = 0.5  # 최대 시간당 욕망 이동량
AFFECTION_DESIRE_SHIFT_MIN = 50    # 호감 임계치 (이상일 때만 이동)

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


def get_climax(unit_id):
    """절정 수치 조회 (0-100)"""
    return morld.get_unit_prop(unit_id, PROP_CLIMAX) or 0


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
    units = morld.get_characters_at_location(loc[0], loc[1])
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


# 삽입 오리피스 → 감각 경험 부위 매핑
_ORIFICE_EXP_MAP = {
    "음부": "음부",
    "항문": "엉덩이",
    "클리토리스": "클리토리스",
}


def _update_climax(unit_id):
    """절정 상시 업데이트 (시간당)

    성인용품(삽입물+착용형) 자극 합산 - 자연 감소.
    100 도달 시 수동 절정 이벤트 발동.
    삽입물/장착 자극에 의한 감각 경험치도 매 시간 축적.
    """
    climax = morld.get_unit_prop(unit_id, PROP_CLIMAX) or 0

    # 성인용품 자극 합산
    try:
        from assets.items.adult_toys import (
            get_total_climax_rate, INSERTABLE_ORIFICES, get_inserted_toy_info,
        )
        toy_rate = get_total_climax_rate(unit_id)
    except ImportError:
        toy_rate = 0
        INSERTABLE_ORIFICES = ()
        get_inserted_toy_info = None

    # 삽입물/장착 자극에 의한 감각 경험치 축적 (매 시간)
    if toy_rate > 0 and get_inserted_toy_info:
        for orifice in INSERTABLE_ORIFICES:
            info = get_inserted_toy_info(unit_id, orifice)
            if info:
                exp_part = _ORIFICE_EXP_MAP.get(orifice)
                if exp_part:
                    exp_gain = max(1, info["vibration_rate"] // 3)
                    morld.modify_prop(unit_id, f"경험:{exp_part}", exp_gain)

        # 착용형 자극 (니플클램프 등)
        import equipment
        for item_id in equipment.get_equipped_items(unit_id):
            item_info = morld.get_item_info(item_id)
            if item_info:
                stim = item_info.get("equip_props", {}).get("성인용품:자극", 0)
                if stim > 0:
                    morld.modify_prop(unit_id, "경험:유두", max(1, stim // 2))

    # 정력제: 절정 -5/h
    stamina_active = morld.get_unit_prop(unit_id, "상태:정력제") or 0
    stamina_mod = -5 if stamina_active else 0

    # 총 변화량: 장비 자극 - 자연 감소 + 정력제
    delta = toy_rate - CLIMAX_NATURAL_DECAY + stamina_mod

    # 자극원 없으면 0 미만으로 감소만
    new_climax = max(0, min(100, climax + delta))

    if new_climax >= 100:
        _trigger_passive_climax(unit_id)
        new_climax = 0

    morld.set_unit_prop(unit_id, PROP_CLIMAX, new_climax)


def _trigger_passive_climax(unit_id):
    """비로맨스 상태에서 성인용품에 의한 절정 이벤트

    성욕 감소, 피로 증가, 결박:입 없으면 신음 발생.
    """
    # 성욕 감소
    current_arousal = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
    morld.set_unit_prop(unit_id, PROP_AROUSAL,
                        max(0, current_arousal - CLIMAX_PASSIVE_AROUSAL_DROP))

    # 피로 증가
    current_fatigue = morld.get_unit_prop(unit_id, PROP_FATIGUE) or 0
    morld.set_unit_prop(unit_id, PROP_FATIGUE,
                        min(100, current_fatigue + CLIMAX_PASSIVE_FATIGUE))

    # 소리 발생 (입이 자유로운 경우만)
    gagged = morld.get_unit_prop(unit_id, "결박:입")
    if not gagged:
        try:
            import sound
            sound.emit_sound(unit_id, "moan", 30)
        except ImportError:
            pass


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

    # 피임약: 남은시간 감소
    contraceptive_remaining = morld.get_unit_prop(unit_id, "상태:피임남은시간") or 0
    if contraceptive_remaining > 0:
        contraceptive_remaining -= 1
        morld.set_unit_prop(unit_id, "상태:피임남은시간", contraceptive_remaining)
        if contraceptive_remaining <= 0:
            morld.set_unit_prop(unit_id, "상태:피임", 0)

    # 미약: 남은시간 감소 + 성욕 증가
    aphrodisiac_remaining = morld.get_unit_prop(unit_id, "상태:미약남은시간") or 0
    if aphrodisiac_remaining > 0:
        aphrodisiac_remaining -= 1
        morld.set_unit_prop(unit_id, "상태:미약남은시간", aphrodisiac_remaining)
        current_arousal_a = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
        morld.set_unit_prop(unit_id, PROP_AROUSAL, min(100, current_arousal_a + 5))
        if aphrodisiac_remaining <= 0:
            morld.set_unit_prop(unit_id, "상태:미약", 0)

    # 배란유도제: 남은시간 감소
    ovulation_remaining = morld.get_unit_prop(unit_id, "상태:배란유도남은시간") or 0
    if ovulation_remaining > 0:
        ovulation_remaining -= 1
        morld.set_unit_prop(unit_id, "상태:배란유도남은시간", ovulation_remaining)
        if ovulation_remaining <= 0:
            morld.set_unit_prop(unit_id, "상태:배란유도", 0)

    # 정력제: 남은시간 감소
    stamina_remaining = morld.get_unit_prop(unit_id, "상태:정력제남은시간") or 0
    if stamina_remaining > 0:
        stamina_remaining -= 1
        morld.set_unit_prop(unit_id, "상태:정력제남은시간", stamina_remaining)
        # 정력제 활성: 성욕 +3/h (미약과 별도)
        current_arousal_s = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
        morld.set_unit_prop(unit_id, PROP_AROUSAL, min(100, current_arousal_s + 3))
        if stamina_remaining <= 0:
            morld.set_unit_prop(unit_id, "상태:정력제", 0)

    # 절정 상시 관리 (성인용품 자극 + 자연 감소)
    import settings
    if settings.is_romance_enabled():
        _update_climax(unit_id)

    # 사회: 혼자이면 증가
    if _is_alone(unit_id):
        current_social = get_social(unit_id)
        morld.set_unit_prop(unit_id, PROP_SOCIAL,
                            min(100, current_social + SOCIAL_RATE))

    # 성욕: 연애 모드 OFF → 항상 0
    import settings
    if not settings.is_romance_enabled():
        current_arousal = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
        if current_arousal > 0:
            morld.set_unit_prop(unit_id, PROP_AROUSAL, 0)
    else:
        # 성욕: 순수/욕망에 따른 변화율 + 욕망 기반 동적 상한
        arousal_cap = _get_arousal_cap(unit_id)
        current_arousal = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
        desire = _get_max_desire(unit_id)

        # 순수/욕망에 따른 변화율 계산
        if desire < DES_BOUNDARY:
            # 순수 zone: 성욕 감소 (desire=0 → -0.5, desire=20 → 0.0)
            factor = 1.0 - desire / DES_BOUNDARY
            effective_rate = AROUSAL_NATURAL_RATE - factor * INNOCENCE_DECAY_RATE
        else:
            # 욕망 zone: 성욕 증가 가속 (desire=40 → 0.5, desire=100 → 1.0)
            factor = (desire - DES_BOUNDARY) / (100 - DES_BOUNDARY)
            effective_rate = AROUSAL_NATURAL_RATE + factor * DESIRE_BONUS_RATE

        # 성적 지향성 배율
        player_id_h = morld.get_player_id()
        if player_id_h:
            try:
                import gender as gender_mod
                effective_rate *= gender_mod.get_orientation_multiplier(unit_id, player_id_h)
            except ImportError:
                pass

        if effective_rate > 0:
            # 증가: cap까지만
            if current_arousal < arousal_cap:
                morld.set_unit_prop(unit_id, PROP_AROUSAL,
                                    min(arousal_cap,
                                        current_arousal + effective_rate))
            elif current_arousal > arousal_cap:
                morld.set_unit_prop(unit_id, PROP_AROUSAL, arousal_cap)
        elif effective_rate < 0:
            # 감소: 0까지만 (순수 zone)
            morld.set_unit_prop(unit_id, PROP_AROUSAL,
                                max(0, current_arousal + effective_rate))

    # 관계 항상성: 호감/반발/복종 basin 수렴
    player_id_h = morld.get_player_id()
    if player_id_h:
        player_info_h = morld.get_unit_info(player_id_h)
        player_name_h = player_info_h.get("name", "주인공") if player_info_h else "주인공"
        _apply_homeostasis(unit_id, f"관계:{player_name_h}:호감", AFFECTION_BASINS)
        _apply_homeostasis(unit_id, f"관계:{player_name_h}:반발", REBELLION_BASINS)
        _apply_homeostasis(unit_id, f"관계:{player_name_h}:복종", SUBMISSION_BASINS)

        # 호감→욕망 자연 이동: 호감 높고 성욕 있으면 순수→욕망으로 이동
        aff_h = morld.get_unit_prop(unit_id, f"관계:{player_name_h}:호감") or 0
        des_h = morld.get_unit_prop(unit_id, f"관계:{player_name_h}:욕망") or 0
        aro_h = morld.get_unit_prop(unit_id, PROP_AROUSAL) or 0
        if aff_h >= AFFECTION_DESIRE_SHIFT_MIN and aro_h > 0 and des_h < 100:
            shift = (aff_h / 100) * (aro_h / 100) * AFFECTION_DESIRE_SHIFT_RATE
            morld.set_unit_prop(unit_id, f"관계:{player_name_h}:욕망",
                                min(100, des_h + shift))

    # TODO: 전투 시스템 추가 후 구현
    # 반발 효과: 적대치 증가 → 적대적으로 변화
    # - 적대적인 캐릭터를 먼저 공격하거나 같은 공간에 있는 경우 도주

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
