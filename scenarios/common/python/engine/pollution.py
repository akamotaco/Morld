# pollution.py - 오염도 시스템
#
# Location별 오염도를 관리하고, 오브젝트/캐릭터/아이템으로 전파하는 시스템.
# 오염 소스는 location이며, 매시간 rate만큼 증가 (max까지).
# 오브젝트는 location rate만큼 오염되고, 캐릭터는 rate × factor만큼 누적됨.
# item_visible 오브젝트는 컨테이너 아이템에 즉시 전파.
#
# 구독: subscribe_time_elapsed(_on_time_elapsed, min_interval=1h)
# on_reach: events/__init__.py에서 on_unit_reach() 호출

import random
import morld
from engine.event_core import subscribe_time_elapsed


# === 상수 ===

MILLIS_PER_HOUR = 3_600_000

# 캐릭터가 받는 오염 비율 (location rate × factor)
CHAR_POLLUTION_FACTOR = 0.3

# 장비 오염 확률 (매시간, 각 장비별)
EQUIP_CONTAMINATION_CHANCE = 0.3

# prop 이름
PROP_POLLUTION = "오염:수치"


# === Location 오염 데이터 (Python dict) ===

# (region_id, location_id) → {"max": float, "rate": float, "current": float}
_location_pollution = {}


# === Public API: Location 등록 ===

def register_location(region_id, location_id, max_pollution, rate):
    """
    오염 소스 location 등록 (시나리오 초기화에서 호출)

    Args:
        region_id: Region ID
        location_id: Location ID
        max_pollution: 최대 오염도
        rate: 시간당 오염 증가량
    """
    key = (region_id, location_id)
    _location_pollution[key] = {
        "max": float(max_pollution),
        "rate": float(rate),
        "current": 0.0,
    }
    print(f"[pollution] Location registered: ({region_id},{location_id}) max={max_pollution} rate={rate}")


# === Public API: 조회/설정 ===

def get_location_pollution(region_id, location_id):
    """
    Location 현재 오염도 조회

    Returns:
        float (오염도) 또는 0.0 (미등록 location)
    """
    key = (region_id, location_id)
    data = _location_pollution.get(key)
    if data is None:
        return 0.0
    return data["current"]


def set_location_pollution(region_id, location_id, value):
    """Location 오염도 직접 설정 (외부 이벤트 등)"""
    key = (region_id, location_id)
    data = _location_pollution.get(key)
    if data is None:
        return
    data["current"] = max(0.0, float(value))


def get_unit_pollution(unit_id):
    """
    Unit/Item 오염도 조회 (prop 래퍼)

    Returns:
        float (오염도, 없으면 0.0)
    """
    val = morld.get_unit_prop(unit_id, PROP_POLLUTION)
    if val is None:
        return 0.0
    return float(val)


def set_unit_pollution(unit_id, value):
    """Unit/Item 오염도 설정"""
    if value <= 0:
        morld.clear_prop(unit_id, PROP_POLLUTION)
    else:
        morld.set_unit_prop(unit_id, PROP_POLLUTION, float(value))


# === Public API: 청소/세정 ===

def clean_location(region_id, location_id, amount):
    """
    Location 오염도 감소 (NPC 청소, 정화 등)

    Args:
        amount: 감소량 (양수)
    """
    key = (region_id, location_id)
    data = _location_pollution.get(key)
    if data is None:
        return
    data["current"] = max(0.0, data["current"] - abs(amount))


def clean_unit(unit_id, amount):
    """
    Unit/Item 오염도 감소 (세탁, 세정 등)

    Args:
        amount: 감소량 (양수)
    """
    current = get_unit_pollution(unit_id)
    new_val = max(0.0, current - abs(amount))
    set_unit_pollution(unit_id, new_val)


# === on_reach: 즉시 오염 ===

def on_unit_reach(unit_id, region_id, location_id):
    """
    캐릭터가 오염 location에 도착 시 즉시 부분 오염
    events/__init__.py의 on_reach에서 호출
    """
    key = (region_id, location_id)
    loc_data = _location_pollution.get(key)
    if not loc_data or loc_data["current"] <= 0:
        return

    addition = loc_data["rate"] * CHAR_POLLUTION_FACTOR
    if addition <= 0:
        return

    current = morld.get_unit_prop(unit_id, PROP_POLLUTION) or 0
    morld.set_unit_prop(unit_id, PROP_POLLUTION, current + addition)


# === 매시간 업데이트 ===

def _on_time_elapsed(millis):
    """매시간: location 오염 증가 → object 전파 → character 누적"""
    if not _location_pollution:
        return

    # 1. Location 오염 증가
    for key, data in _location_pollution.items():
        current = data["current"]
        max_pol = data["max"]
        rate = data["rate"]

        # max 초과 시 유지 (증가도 감소도 없음)
        if current > max_pol:
            continue

        data["current"] = min(current + rate, max_pol)

    # 2. Object 오염 전파 + 컨테이너 아이템 전파
    for key, data in _location_pollution.items():
        if data["current"] <= 0:
            continue

        region_id, location_id = key
        rate = data["rate"]
        loc_current = data["current"]

        try:
            obj_ids = morld.get_objects_at_location(region_id, location_id)
        except Exception:
            obj_ids = []

        for obj_id in obj_ids:
            # object 오염: += rate, cap at location current
            obj_pol = morld.get_unit_prop(obj_id, PROP_POLLUTION) or 0
            new_obj_pol = min(obj_pol + rate, loc_current)
            if new_obj_pol > obj_pol:
                morld.set_unit_prop(obj_id, PROP_POLLUTION, new_obj_pol)

            # item_visible인 object → 컨테이너 아이템 즉시 전파
            try:
                from assets.objects import get_instance
                instance = get_instance(obj_id)
                if instance and getattr(instance, "item_visible", False):
                    inventory = morld.get_unit_inventory(obj_id)
                    if inventory:
                        for item_id in inventory:
                            item_pol = morld.get_unit_prop(item_id, PROP_POLLUTION) or 0
                            if item_pol < new_obj_pol:
                                morld.set_unit_prop(item_id, PROP_POLLUTION, new_obj_pol)
            except Exception:
                pass

    # 3. Character 오염 누적 + 장비 오염
    for key, data in _location_pollution.items():
        if data["current"] <= 0:
            continue

        region_id, location_id = key
        rate = data["rate"]

        try:
            unit_ids = morld.get_characters_at_location(region_id, location_id)
        except Exception:
            unit_ids = []

        for char_id in unit_ids:
            # character 오염: += rate × factor
            char_pol = morld.get_unit_prop(char_id, PROP_POLLUTION) or 0
            addition = rate * CHAR_POLLUTION_FACTOR
            new_char_pol = char_pol + addition
            morld.set_unit_prop(char_id, PROP_POLLUTION, new_char_pol)

            # 장비 오염 (확률 기반)
            try:
                equipped = morld.get_equipped_items(char_id)
            except Exception:
                equipped = []

            for item_id in equipped:
                if random.random() < EQUIP_CONTAMINATION_CHANCE:
                    item_pol = morld.get_unit_prop(item_id, PROP_POLLUTION) or 0
                    if item_pol < new_char_pol:
                        morld.set_unit_prop(item_id, PROP_POLLUTION, new_char_pol)


# === 리셋 ===

def reset():
    """챕터 전환 시 리셋"""
    _location_pollution.clear()


# === 모듈 로드 시 이벤트 구독 (1시간 간격) ===

subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
