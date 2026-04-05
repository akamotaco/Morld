# fuel.py - 열원 연료 소비 시스템
#
# 소비형 열원(PortableStove, DrumBath)의 연료를 매시간 감소.
# 연료 소진 시 light:on = 0 → temperature에서 열 기여 자동 중단.
#
# 무한 열원(Fireplace): heat:fuel_mode prop 없음 → 자동 스킵.
# Scenario 03 호환: prop 없으면 무한 모드 (기본값).
#
# 구독: subscribe_time_elapsed(_on_time_elapsed, min_interval=1h)

import morld
from engine.event_core import subscribe_time_elapsed

MILLIS_PER_HOUR = 3_600_000

# 아이템 1개당 연소 시간 (시간 단위)
FUEL_VALUES = {
    "branch": 2,        # 나뭇가지 = 2시간
    "wood_chip": 3,     # 나무조각 = 3시간
    "log": 6,           # 통나무 = 6시간
}

# prop 이름
PROP_FUEL = "heat:fuel"
PROP_FUEL_MAX = "heat:fuel_max"
PROP_FUEL_MODE = "heat:fuel_mode"   # 1=소비형, 0/없음=무한

DEFAULT_FUEL_MAX = 24   # 기본 최대 연료 (24시간)

# 등록된 소비형 열원: {unit_id: {"region_id", "location_id"}}
_fuel_sources = {}

def register_fuel_source(unit_id, region_id, location_id):
    """소비형 열원 등록 (PortableStove/DrumBath instantiate에서 호출)"""
    _fuel_sources[unit_id] = {
        "region_id": region_id,
        "location_id": location_id,
    }
    print(f"[fuel] Fuel source registered: unit={unit_id} at ({region_id},{location_id})")



def _on_time_elapsed(millis):
    """매시간 연료 소비"""
    for unit_id in list(_fuel_sources.keys()):
        mode = morld.get_unit_prop(unit_id, PROP_FUEL_MODE)
        if not mode:    # 0 or None = 무한
            continue

        fuel = morld.get_unit_prop(unit_id, PROP_FUEL) or 0
        if fuel > 0:
            fuel -= 1
            morld.set_unit_prop(unit_id, PROP_FUEL, fuel)

        if fuel <= 0:
            is_on = morld.get_unit_prop(unit_id, "light:on")
            if is_on:
                morld.set_unit_prop(unit_id, "light:on", 0)
                info = _fuel_sources.get(unit_id, {})
                print(f"[fuel] Heat source {unit_id} at "
                      f"({info.get('region_id')},{info.get('location_id')}) "
                      f"ran out of fuel — turned off")


# ========================================
# 연료 장전 API
# ========================================

def load_fuel(unit_id, item_unique_id, count=1):
    """열원에 연료 장전

    Args:
        unit_id: 열원 unit_id
        item_unique_id: 아이템 unique_id ("branch" 또는 "log")
        count: 아이템 개수

    Returns:
        int: 추가된 연료량 (시간)
    """
    fuel_per_item = FUEL_VALUES.get(item_unique_id, 0)
    if fuel_per_item <= 0:
        return 0

    added = fuel_per_item * count
    current = morld.get_unit_prop(unit_id, PROP_FUEL) or 0
    max_fuel = morld.get_unit_prop(unit_id, PROP_FUEL_MAX) or DEFAULT_FUEL_MAX

    new_fuel = min(current + added, max_fuel)
    actual_added = new_fuel - current
    morld.set_unit_prop(unit_id, PROP_FUEL, new_fuel)

    # 연료가 있으면 자동 점화
    if new_fuel > 0:
        is_on = morld.get_unit_prop(unit_id, "light:on")
        if not is_on:
            morld.set_unit_prop(unit_id, "light:on", 1)

    return actual_added


def npc_load_fuel(npc_id, heat_source_id, item_unique_id, count=1):
    """NPC가 인벤토리에서 아이템을 꺼내 열원에 장전

    Args:
        npc_id: NPC unit_id
        heat_source_id: 열원 unit_id
        item_unique_id: 아이템 unique_id ("branch" 또는 "log")
        count: 아이템 개수

    Returns:
        int: 추가된 연료량 (시간)
    """
    from assets.registry import get_or_create_item_id
    item_id = get_or_create_item_id(item_unique_id)
    if not item_id:
        return 0

    # 인벤토리에서 아이템 제거
    inv = morld.get_unit_inventory(npc_id)
    available = inv.get(item_id, 0) if inv else 0
    actual_count = min(count, available)
    if actual_count <= 0:
        return 0

    morld.remove_item(npc_id, item_id, actual_count)
    return load_fuel(heat_source_id, item_unique_id, actual_count)


# ========================================
# 조회 API
# ========================================

def get_fuel_level(unit_id):
    """현재 연료 레벨 (시간 단위)"""
    return morld.get_unit_prop(unit_id, PROP_FUEL) or 0


def get_fuel_max(unit_id):
    """최대 연료 용량 (시간 단위)"""
    return morld.get_unit_prop(unit_id, PROP_FUEL_MAX) or DEFAULT_FUEL_MAX


def needs_fuel(unit_id, threshold=6):
    """연료 보충 필요 여부 (threshold 시간 미만이면 True)"""
    mode = morld.get_unit_prop(unit_id, PROP_FUEL_MODE)
    if not mode:    # 무한 모드
        return False
    return get_fuel_level(unit_id) < threshold


def is_fuel_source(unit_id):
    """등록된 소비형 열원인지"""
    return unit_id in _fuel_sources


def get_sources_in_region(region_id):
    """특정 region의 소비형 열원 unit_id 목록"""
    return [uid for uid, info in _fuel_sources.items()
            if info["region_id"] == region_id]


# ========================================
# 챕터 전환
# ========================================

def reset():
    """챕터 전환 시 초기화"""
    _fuel_sources.clear()
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
