# humidity.py - 습도 시스템
#
# Location별 습도를 관리하고, 비/눈에 의한 캐릭터 젖음을 처리
# 온도와 달리 region → 실외 location 단방향 (인접 영향 없음, 실내는 고정)
#
# 날씨 강도 시스템: 기본 날씨(비/눈/맑음)에 강도(가랑비/소나기/폭우/폭설/폭염)를 추가
# UI 표시: "비(소나기)", "맑음(폭염)" 등. C# 태그(날씨:비)는 변경 없이 호환
#
# 구독: subscribe_time_elapsed(_on_time_elapsed, min_interval=1h)

import random
import morld
from events import subscribe_time_elapsed


# === 상수 ===

MILLIS_PER_HOUR = 3_600_000

# 날씨별 기본 실외 습도 (0-100)
WEATHER_BASE_HUMIDITY = {"맑음": 30, "흐림": 50, "비": 80, "눈": 60}

# 강도별 습도 보정 (기본 날씨에 가산)
INTENSITY_HUMIDITY_MOD = {
    "가랑비": -20,   # 비 80 - 20 = 60
    "소나기": +10,   # 비 80 + 10 = 90
    "폭우": +20,     # 비 80 + 20 = 100
    "폭설": +15,     # 눈 60 + 15 = 75
    "폭염": -15,     # 맑음 30 - 15 = 15
}

# 강도별 젖음 증가량 (시간당, 실외)
WETNESS_GAIN = {
    "비": 15,        # 기본 비
    "가랑비": 5,
    "소나기": 25,
    "폭우": 40,
    "눈": 5,         # 기본 눈 (천천히)
    "폭설": 10,
}

# 날씨별 가능한 강도 + 확률 가중치 (None = 기본)
WEATHER_INTENSITIES = {
    "비": [(None, 5), ("가랑비", 3), ("소나기", 2), ("폭우", 1)],
    "눈": [(None, 7), ("폭설", 3)],
    "맑음": [(None, 8), ("폭염", 2)],
}

# 건조
WETNESS_DRY_BASE = 5           # 기본 건조 속도 (시간당)
WETNESS_DRY_TEMP_BONUS = 0.2   # 온도 1도(>20℃)당 추가 건조
WETNESS_DRY_INDOOR_BONUS = 5   # 실내 추가 건조
WETNESS_MAX = 100

# 실내 습도 (비 영향 없음, 고정)
INDOOR_HUMIDITY = 35

WATERPROOF_REDUCTION = 0.4  # 방수 1당 40% 젖음 감소

PROP_WETNESS = "습도:젖음"
from region_registry import get_region_ids


# === 데이터 저장 ===

# (region_id, location_id) → float (현재 습도 0~100)
_location_humidity = {}

# (region_id, location_id) → bool
_location_indoor = {}

_initialized = False

# 날씨 강도
_current_intensity = None  # 현재 강도 (None = 기본)
_last_weather = None       # 날씨 변경 감지용


# === 계절 ===

def _get_season(month):
    """월 → 계절"""
    if month in (3, 4, 5):
        return "봄"
    elif month in (6, 7, 8):
        return "여름"
    elif month in (9, 10, 11):
        return "가을"
    else:
        return "겨울"


# === 강도 시스템 ===

def _roll_intensity(weather, season=None):
    """날씨에 맞는 강도를 가중치 랜덤으로 결정"""
    options = WEATHER_INTENSITIES.get(weather)
    if not options:
        return None

    # 폭염은 여름에만
    if weather == "맑음" and season != "여름":
        return None

    choices, weights = zip(*options)
    return random.choices(choices, weights=weights, k=1)[0]


def _get_wetness_key(weather, intensity):
    """현재 날씨+강도에 해당하는 WETNESS_GAIN 키 반환"""
    if intensity and intensity in WETNESS_GAIN:
        return intensity
    if weather in WETNESS_GAIN:
        return weather
    return None


# === 초기화 ===

def reset():
    """챕터 전환 시 호출 — 모든 상태 초기화 (다음 접근 시 재초기화)"""
    global _initialized, _current_intensity, _last_weather
    _initialized = False
    _location_humidity.clear()
    _location_indoor.clear()
    _current_intensity = None
    _last_weather = None


def _ensure_initialized():
    """lazy init: get_region_info()로 location 목록 구축"""
    global _initialized
    if _initialized:
        return

    for region_id in get_region_ids():
        try:
            info = morld.get_region_info(region_id)
        except Exception:
            continue
        if not info:
            continue

        locations = info.get("locations", [])
        for loc in locations:
            local_id = loc["id"]
            key = (region_id, local_id)
            _location_indoor[key] = loc.get("is_indoor", False)

    # region 데이터가 없으면 초기화 연기 (다음 호출 시 재시도)
    if not _location_indoor:
        return

    _initialized = True

    # 초기 습도 설정
    time_info = morld.get_time_info()
    weather = time_info.get("weather", "흐림") if time_info else "흐림"
    outdoor_humidity = WEATHER_BASE_HUMIDITY.get(weather, 50)

    for key, is_indoor in _location_indoor.items():
        _location_humidity[key] = INDOOR_HUMIDITY if is_indoor else float(outdoor_humidity)

    print(f"[humidity] Initialized: {len(_location_indoor)} locations, "
          f"outdoor={outdoor_humidity}%, indoor={INDOOR_HUMIDITY}%")


# === 시간 경과 업데이트 ===

def _on_time_elapsed(millis):
    """1시간마다 습도 업데이트 + 캐릭터 젖음 처리"""
    global _current_intensity, _last_weather

    _ensure_initialized()

    if not _location_humidity:
        return

    time_info = morld.get_time_info()
    if not time_info:
        return

    weather = time_info.get("weather", "흐림")
    month = time_info.get("month", 3)
    season = _get_season(month)

    # 날씨 변경 감지 → 강도 재결정
    if weather != _last_weather:
        _current_intensity = _roll_intensity(weather, season)
        _last_weather = weather
        if _current_intensity:
            print(f"[humidity] Weather intensity: {weather}({_current_intensity})")

    # 1. 실외 습도 계산
    base = WEATHER_BASE_HUMIDITY.get(weather, 50)
    mod = INTENSITY_HUMIDITY_MOD.get(_current_intensity, 0) if _current_intensity else 0
    outdoor_humidity = max(0, min(100, base + mod))

    # 2. location 습도 업데이트
    for key, is_indoor in _location_indoor.items():
        if is_indoor:
            _location_humidity[key] = float(INDOOR_HUMIDITY)
        else:
            _location_humidity[key] = float(outdoor_humidity)

    # 3. 젖음 처리 (캐릭터 + 오브젝트 + 아이템)
    wetness_key = _get_wetness_key(weather, _current_intensity)
    gain = WETNESS_GAIN.get(wetness_key, 0) if wetness_key else 0

    for key, is_indoor in _location_indoor.items():
        region_id, location_id = key
        raining = not is_indoor and gain > 0

        # 3a. 오브젝트 + item_visible 컨테이너 내 아이템
        if raining:
            try:
                obj_ids = morld.get_objects_at_location(region_id, location_id)
            except Exception:
                obj_ids = []

            for obj_id in obj_ids:
                current = _get_wetness(obj_id)
                _set_wetness(obj_id, min(WETNESS_MAX, current + gain))

                # item_visible 오브젝트 → 내부 아이템도 젖음
                try:
                    from assets.objects import get_instance
                    instance = get_instance(obj_id)
                    if instance and getattr(instance, "item_visible", False):
                        inventory = morld.get_unit_inventory(obj_id)
                        if inventory:
                            for item_id in inventory:
                                item_wet = _get_wetness(item_id)
                                _set_wetness(item_id, min(WETNESS_MAX, item_wet + gain))
                except Exception:
                    pass

        # 3b. 캐릭터 + 장비
        try:
            units = morld.get_characters_at_location(region_id, location_id)
        except Exception:
            continue
        if not units:
            continue

        for unit_id in units:
            current = _get_wetness(unit_id)

            if raining:
                # 방수 보정
                waterproof = _get_equip_prop_total(unit_id, "방수")
                reduction = min(0.9, waterproof * WATERPROOF_REDUCTION)
                actual_gain = gain * (1 - reduction)
                # 실외 + 비/눈: 캐릭터 젖음 증가
                _set_wetness(unit_id, min(WETNESS_MAX, current + actual_gain))

                # 장비도 젖음
                try:
                    equipped = morld.get_equipped_items(unit_id)
                except Exception:
                    equipped = []
                for item_id in equipped:
                    item_wet = _get_wetness(item_id)
                    _set_wetness(item_id, min(WETNESS_MAX, item_wet + gain))

            elif current > 0:
                # 건조
                dry_rate = WETNESS_DRY_BASE
                # 온도 보너스
                try:
                    import temperature
                    temp = temperature.get_temperature(region_id, location_id)
                    if temp is not None and temp > 20:
                        dry_rate += (temp - 20) * WETNESS_DRY_TEMP_BONUS
                except ImportError:
                    pass
                # 실내 보너스
                if is_indoor:
                    dry_rate += WETNESS_DRY_INDOOR_BONUS

                new_val = max(0, current - dry_rate)
                _set_wetness(unit_id, new_val)


# === 방수 헬퍼 ===

def _get_equip_prop_total(unit_id, prop_name):
    """장착 아이템의 equip_prop 합산"""
    try:
        equipped = morld.get_equipped_items(unit_id)
    except Exception:
        return 0
    if not equipped:
        return 0
    total = 0
    for item_id in equipped:
        try:
            info = morld.get_item_info(item_id)
            if info:
                total += info.get("equip_props", {}).get(prop_name, 0)
        except Exception:
            pass
    return total


# === on_reach ===

def on_unit_reach(unit_id, region_id, location_id):
    """실외 + 비/눈 → 즉시 젖음 소량 증가"""
    _ensure_initialized()

    key = (region_id, location_id)
    if _location_indoor.get(key, True):
        return  # 실내면 무시

    time_info = morld.get_time_info()
    if not time_info:
        return

    weather = time_info.get("weather", "")
    if weather not in ("비", "눈"):
        return

    # on_reach 즉시 효과: 시간당 gain의 1/4
    wetness_key = _get_wetness_key(weather, _current_intensity)
    gain = WETNESS_GAIN.get(wetness_key, 0) if wetness_key else 0
    if gain <= 0:
        return

    # 방수 보정
    waterproof = _get_equip_prop_total(unit_id, "방수")
    reduction = min(0.9, waterproof * WATERPROOF_REDUCTION)
    immediate = gain * 0.25 * (1 - reduction)
    current = _get_wetness(unit_id)
    new_val = min(WETNESS_MAX, current + immediate)
    _set_wetness(unit_id, new_val)


# === 내부 헬퍼 ===

def _get_wetness(unit_id):
    """unit 젖음 수치 조회"""
    val = morld.get_unit_prop(unit_id, PROP_WETNESS)
    if val is None:
        return 0.0
    return float(val)


def _set_wetness(unit_id, value):
    """unit 젖음 수치 설정 (0이면 prop 제거)"""
    if value <= 0:
        morld.clear_prop(unit_id, PROP_WETNESS)
    else:
        morld.set_unit_prop(unit_id, PROP_WETNESS, round(value, 1))


# === Public API ===

def get_humidity(region_id, location_id):
    """
    현재 location 습도 조회 (0-100)

    Returns:
        float 또는 None (초기화 전)

    Raises:
        KeyError: 초기화 완료 후 해당 location이 등록되지 않은 경우
    """
    _ensure_initialized()
    key = (region_id, location_id)
    if _initialized and key not in _location_humidity:
        raise KeyError(f"[humidity] Unknown location {key}. {len(_location_humidity)} locations registered")
    return _location_humidity.get(key)


def get_unit_wetness(unit_id):
    """
    unit 젖음 정도 조회 (0-100, 0=건조)

    Returns:
        float
    """
    return _get_wetness(unit_id)


def dry_unit(unit_id, amount):
    """unit 건조 (모닥불, 목욕 등에서 사용)"""
    current = _get_wetness(unit_id)
    if current > 0:
        _set_wetness(unit_id, max(0, current - amount))


def is_raining():
    """현재 비가 오는지"""
    time_info = morld.get_time_info()
    if not time_info:
        return False
    return time_info.get("weather", "") == "비"


def get_weather_display():
    """
    날씨 + 강도 표시 (UI용)

    Returns:
        str: "비(소나기)" 또는 "비" 또는 "" (날씨 없음)
    """
    time_info = morld.get_time_info()
    if not time_info:
        return ""
    weather = time_info.get("weather", "")
    if not weather:
        return ""
    if _current_intensity:
        return f"{weather}({_current_intensity})"
    return weather


def get_intensity():
    """현재 날씨 강도 조회 (None이면 기본)"""
    return _current_intensity


# === 모듈 로드 시 이벤트 구독 (1시간 간격) ===

subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
