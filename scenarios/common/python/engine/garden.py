# garden.py - 텃밭 생장 시스템
#
# 텃밭(GardenBed) 오브젝트의 매시간 성장 처리
# - 수분 감소, 비료 감소, 식물 성장 진행
# - 비 오면 자동 수분 공급
# - 계절 제한: 비수기엔 성장 정지
# - 시듦 메커니즘: 수확 가능 상태로 방치 시 시들어 갈아 엎어야 함
#
# 패턴: resource_agent.py / temperature.py와 동일한 subscribe_time_elapsed 방식

import random
import morld

MILLIS_PER_HOUR = 3_600_000

# ========================================
# 씨앗 종류 레지스트리
# ========================================
# code → {name, seed_unique_id, crop_unique_id, growth_rate, harvest_min, harvest_max,
#          seed_chance, seasons}
# 시나리오 초기화 시 register_seed()로 등록 (시나리오별 작물 분리)

SEED_REGISTRY = {}

# seed_unique_id → code 역매핑
SEED_CODE_MAP = {}


def register_seed(code, name, seed_unique_id, crop_unique_id,
                  growth_rate, harvest_min, harvest_max, seed_chance,
                  seasons=None):
    """씨앗 종류 등록 (시나리오 초기화 시 호출)

    Args:
        seasons: 재배 가능 계절 리스트 (["봄", "여름"] 등). None이면 사계절.
    """
    SEED_REGISTRY[code] = {
        "name": name,
        "seed_unique_id": seed_unique_id,
        "crop_unique_id": crop_unique_id,
        "growth_rate": growth_rate,
        "harvest_min": harvest_min,
        "harvest_max": harvest_max,
        "seed_chance": seed_chance,
        "seasons": seasons,
    }
    SEED_CODE_MAP[seed_unique_id] = code

# ========================================
# 상수
# ========================================

MOISTURE_DECAY_PER_HOUR = 3         # 시간당 수분 감소
FERTILIZER_DECAY_PER_HOUR = 2       # 시간당 비료 감소
MOISTURE_THRESHOLD = 10             # 이 이하면 성장 정지
WATERING_AMOUNT = 20                # 1회 물주기 수분 증가량
FERTILIZER_AMOUNT = 30              # 1회 비료 주기 증가량
MAX_MOISTURE = 100
MAX_FERTILIZER = 100
MAX_GROWTH = 100

WITHER_HOURS = 72                   # 수확 가능 상태 유지 시간 → 초과 시 시듦 (3일)
TILL_FERTILIZER_BONUS = 20          # 갈아 엎기 비료 보너스 (수확 가능/시든 작물)

# 비에 의한 수분 공급량
RAIN_MOISTURE = {
    "가랑비": 5,
    "소나기": 15,
    "폭우": 25,
}
RAIN_MOISTURE_DEFAULT = 10          # 강도 정보 없을 때

# Prop 이름
PROP_FURROW_COUNT = "이랑수"
PROP_MOISTURE = "수분"
PROP_FERTILIZER = "비료"
PROP_SEED_PREFIX = "씨앗"           # "씨앗:0", "씨앗:1", ...
PROP_GROWTH_PREFIX = "성장"         # "성장:0", "성장:1", ...
PROP_WITHER_PREFIX = "시듦"         # "시듦:0", "시듦:1", ...  (1=시든 상태)
PROP_WITHER_TIMER_PREFIX = "시듦시간"  # "시듦시간:0" (수확 가능 후 경과 시간)


# ========================================
# 등록 관리
# ========================================

_registered_gardens = {}     # instance_id → True
_subscribed = False


def register_garden(instance_id: int):
    """텃밭 오브젝트 등록 (instantiate 시 호출)"""
    _ensure_subscribed()
    _registered_gardens[instance_id] = True
    print(f"[garden] Registered garden bed (id={instance_id})")


def unregister_garden(instance_id: int):
    """텃밭 오브젝트 등록 해제"""
    _registered_gardens.pop(instance_id, None)


def reset():
    """챕터 전환용 초기화"""
    _registered_gardens.clear()
    SEED_REGISTRY.clear()
    SEED_CODE_MAP.clear()
    print("[garden] Reset.")


# ========================================
# 매시간 성장 처리
# ========================================

def _on_time_elapsed(millis: int):
    """매 시간 호출: 모든 등록된 텃밭의 수분/비료/성장 업데이트"""
    import humidity

    is_rain = humidity.is_raining()
    intensity = humidity.get_intensity() if is_rain else None
    current_season = get_current_season()

    for instance_id in list(_registered_gardens.keys()):
        _process_garden(instance_id, is_rain, intensity, current_season)


def _process_garden(instance_id: int, is_rain: bool, intensity, current_season: str):
    """개별 텃밭의 매시간 처리"""
    # 현재 수분/비료 읽기
    moisture = morld.get_unit_prop(instance_id, PROP_MOISTURE)
    fertilizer = morld.get_unit_prop(instance_id, PROP_FERTILIZER)
    furrow_count = morld.get_unit_prop(instance_id, PROP_FURROW_COUNT)

    if not furrow_count:
        return

    # 비에 의한 수분 공급 (실외 텃밭)
    if is_rain:
        rain_amount = RAIN_MOISTURE.get(intensity, RAIN_MOISTURE_DEFAULT)
        moisture = min(MAX_MOISTURE, moisture + rain_amount)

    # 식물 성장/시듦 처리
    has_plants = False
    for i in range(furrow_count):
        seed_code = morld.get_unit_prop(instance_id, f"{PROP_SEED_PREFIX}:{i}")
        if not seed_code:
            continue

        has_plants = True
        growth = morld.get_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{i}")
        withered = morld.get_unit_prop(instance_id, f"{PROP_WITHER_PREFIX}:{i}")

        if withered:
            continue  # 이미 시든 작물 — 갈아 엎기 전까지 처리 없음

        if growth >= MAX_GROWTH:
            # 수확 가능 상태: 시듦 타이머 증가
            wither_timer = (morld.get_unit_prop(instance_id, f"{PROP_WITHER_TIMER_PREFIX}:{i}") or 0) + 1
            if wither_timer >= WITHER_HOURS:
                morld.set_unit_prop(instance_id, f"{PROP_WITHER_PREFIX}:{i}", 1)
                morld.set_unit_prop(instance_id, f"{PROP_WITHER_TIMER_PREFIX}:{i}", 0)
                print(f"[garden] 작물 시듦: 이랑 {i} (id={instance_id})")
            else:
                morld.set_unit_prop(instance_id, f"{PROP_WITHER_TIMER_PREFIX}:{i}", wither_timer)
            continue  # 수확 가능/시든 상태 — 성장 처리 불필요

        # 계절 확인
        seed_info = SEED_REGISTRY.get(seed_code)
        if seed_info:
            seasons = seed_info.get("seasons")
            if seasons and current_season not in seasons:
                continue  # 비수기 — 성장 정지

        # 성장 처리
        if moisture >= MOISTURE_THRESHOLD:
            if seed_info:
                base_rate = seed_info["growth_rate"]
                fertilizer_bonus = 1.0 + fertilizer / 100.0
                new_growth = min(MAX_GROWTH, growth + int(base_rate * fertilizer_bonus))
                morld.set_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{i}", new_growth)

    # 수분/비료 감소 (식물이 있을 때만 수분 소모)
    if has_plants and moisture >= MOISTURE_THRESHOLD:
        moisture = max(0, moisture - MOISTURE_DECAY_PER_HOUR)
    if fertilizer > 0:
        fertilizer = max(0, fertilizer - FERTILIZER_DECAY_PER_HOUR)

    # 저장
    morld.set_unit_prop(instance_id, PROP_MOISTURE, moisture)
    morld.set_unit_prop(instance_id, PROP_FERTILIZER, fertilizer)


# ========================================
# Public API
# ========================================

def get_current_season() -> str:
    """현재 계절 반환 (봄/여름/가을/겨울)"""
    time_info = morld.get_time_info()
    month = time_info.get("month", 1) if time_info else 1
    if month in (3, 4, 5):
        return "봄"
    elif month in (6, 7, 8):
        return "여름"
    elif month in (9, 10, 11):
        return "가을"
    else:
        return "겨울"


def is_withered(instance_id: int, furrow_index: int) -> bool:
    """해당 이랑이 시든 상태인지 확인"""
    return morld.get_unit_prop(instance_id, f"{PROP_WITHER_PREFIX}:{furrow_index}") == 1


def get_seed_seasons(code: int):
    """씨앗 코드 → 계절 리스트 (None이면 사계절)"""
    info = SEED_REGISTRY.get(code)
    return info.get("seasons") if info else None


def get_seed_name(code: int) -> str:
    """씨앗 코드 → 이름"""
    info = SEED_REGISTRY.get(code)
    return info["name"] if info else "알 수 없음"


def get_growth_stage_text(growth: int) -> str:
    """성장도 → 단계 텍스트"""
    if growth <= 0:
        return "씨앗"
    elif growth < 25:
        return "새싹"
    elif growth < 50:
        return "자라는 중"
    elif growth < 75:
        return "꽃이 핌"
    elif growth < MAX_GROWTH:
        return "열매 맺는 중"
    else:
        return "수확 가능"


def get_moisture_text(moisture: int) -> str:
    """수분 → 상태 텍스트"""
    if moisture <= 0:
        return "메마름"
    elif moisture < 20:
        return "건조"
    elif moisture < 50:
        return "보통"
    elif moisture < 80:
        return "촉촉"
    else:
        return "흠뻑"


def do_harvest(instance_id: int, furrow_index: int, player_id: int) -> dict:
    """
    수확 실행

    Returns:
        {"crop_name": str, "crop_count": int, "seed_name": str|None, "seed_count": int}
    """
    from assets.registry import get_or_create_item_id

    seed_code = morld.get_unit_prop(instance_id, f"{PROP_SEED_PREFIX}:{furrow_index}")
    seed_info = SEED_REGISTRY.get(seed_code)
    if not seed_info:
        return None

    # 작물 지급
    crop_count = random.randint(seed_info["harvest_min"], seed_info["harvest_max"])
    crop_id = get_or_create_item_id(seed_info["crop_unique_id"])
    if crop_id:
        import inventory as inv_module
        inv_module.safe_give_item(player_id, crop_id, crop_count)

    # 씨앗 확률 지급
    seed_count = 0
    seed_name = None
    if random.random() < seed_info["seed_chance"]:
        seed_count = 1
        seed_name = f'{seed_info["name"]} 씨앗'
        seed_item_id = get_or_create_item_id(seed_info["seed_unique_id"])
        if seed_item_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, seed_item_id, seed_count)

    # 이랑 초기화 (시듦 관련 prop 포함)
    morld.set_unit_prop(instance_id, f"{PROP_SEED_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_WITHER_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_WITHER_TIMER_PREFIX}:{furrow_index}", 0)

    return {
        "crop_name": seed_info["name"],
        "crop_count": crop_count,
        "seed_name": seed_name,
        "seed_count": seed_count,
    }


def do_till(instance_id: int, furrow_index: int) -> bool:
    """
    갈아 엎기 실행 — 비료 보너스 판정 후 이랑 초기화

    Returns:
        True if fertilizer bonus was applied
    """
    growth = morld.get_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{furrow_index}")
    withered = morld.get_unit_prop(instance_id, f"{PROP_WITHER_PREFIX}:{furrow_index}")
    can_bonus = withered or (growth >= MAX_GROWTH)

    if can_bonus:
        current = morld.get_unit_prop(instance_id, PROP_FERTILIZER) or 0
        morld.set_unit_prop(instance_id, PROP_FERTILIZER,
                            min(MAX_FERTILIZER, current + TILL_FERTILIZER_BONUS))

    # 이랑 초기화
    morld.set_unit_prop(instance_id, f"{PROP_SEED_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_WITHER_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_WITHER_TIMER_PREFIX}:{furrow_index}", 0)

    return can_bonus


# ========================================
# 이벤트 구독
# ========================================

def _ensure_subscribed():
    """이벤트 구독 (최초 1회)"""
    global _subscribed
    if _subscribed:
        return
    _subscribed = True

    from events import subscribe_time_elapsed
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
    print("[garden] Subscribed to time_elapsed events (hourly)")
