# garden.py - 텃밭 생장 시스템
#
# 텃밭(GardenBed) 오브젝트의 매시간 성장 처리
# - 수분 감소, 비료 감소, 식물 성장 진행
# - 비 오면 자동 수분 공급
#
# 패턴: resource_agent.py / temperature.py와 동일한 subscribe_time_elapsed 방식

import random
import morld

MILLIS_PER_HOUR = 3_600_000

# ========================================
# 씨앗 종류 레지스트리
# ========================================
# code → {name, seed_unique_id, crop_unique_id, growth_rate, harvest_min, harvest_max, seed_chance}

SEED_REGISTRY = {
    1: {
        "name": "감자",
        "seed_unique_id": "seed_potato",
        "crop_unique_id": "food_potato",
        "growth_rate": 3,       # 시간당 성장량
        "harvest_min": 2,
        "harvest_max": 4,
        "seed_chance": 0.30,
    },
    2: {
        "name": "토마토",
        "seed_unique_id": "seed_tomato",
        "crop_unique_id": "food_tomato",
        "growth_rate": 2,
        "harvest_min": 3,
        "harvest_max": 5,
        "seed_chance": 0.25,
    },
    3: {
        "name": "당근",
        "seed_unique_id": "seed_carrot",
        "crop_unique_id": "food_carrot",
        "growth_rate": 4,
        "harvest_min": 2,
        "harvest_max": 3,
        "seed_chance": 0.20,
    },
    4: {
        "name": "약초",
        "seed_unique_id": "seed_herb",
        "crop_unique_id": "food_herb",     # 기존 약초 아이템 재사용
        "growth_rate": 3,
        "harvest_min": 1,
        "harvest_max": 3,
        "seed_chance": 0.35,
    },
    5: {
        "name": "양배추",
        "seed_unique_id": "seed_cabbage",
        "crop_unique_id": "food_cabbage",
        "growth_rate": 2,
        "harvest_min": 1,
        "harvest_max": 2,
        "seed_chance": 0.40,
    },
}

# seed_unique_id → code 역매핑
SEED_CODE_MAP = {v["seed_unique_id"]: k for k, v in SEED_REGISTRY.items()}

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
    print("[garden] Reset.")


# ========================================
# 매시간 성장 처리
# ========================================

def _on_time_elapsed(millis: int):
    """매 시간 호출: 모든 등록된 텃밭의 수분/비료/성장 업데이트"""
    import humidity

    is_rain = humidity.is_raining()
    intensity = humidity.get_intensity() if is_rain else None

    for instance_id in list(_registered_gardens.keys()):
        _process_garden(instance_id, is_rain, intensity)


def _process_garden(instance_id: int, is_rain: bool, intensity):
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

    # 식물 성장 처리 (수분 충분할 때만)
    has_plants = False
    for i in range(furrow_count):
        seed_code = morld.get_unit_prop(instance_id, f"{PROP_SEED_PREFIX}:{i}")
        if not seed_code:
            continue

        has_plants = True
        growth = morld.get_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{i}")

        if growth >= MAX_GROWTH:
            continue    # 이미 수확 가능 상태

        if moisture >= MOISTURE_THRESHOLD:
            seed_info = SEED_REGISTRY.get(seed_code)
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
        morld.give_item(player_id, crop_id, crop_count)

    # 씨앗 확률 지급
    seed_count = 0
    seed_name = None
    if random.random() < seed_info["seed_chance"]:
        seed_count = 1
        seed_name = f'{seed_info["name"]} 씨앗'
        seed_item_id = get_or_create_item_id(seed_info["seed_unique_id"])
        if seed_item_id:
            morld.give_item(player_id, seed_item_id, seed_count)

    # 이랑 초기화
    morld.set_unit_prop(instance_id, f"{PROP_SEED_PREFIX}:{furrow_index}", 0)
    morld.set_unit_prop(instance_id, f"{PROP_GROWTH_PREFIX}:{furrow_index}", 0)

    return {
        "crop_name": seed_info["name"],
        "crop_count": crop_count,
        "seed_name": seed_name,
        "seed_count": seed_count,
    }


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
