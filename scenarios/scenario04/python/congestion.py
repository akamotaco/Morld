# congestion.py - Location 혼잡도 시스템 (S04)
#
# S02 기반. 혼잡도 = 인구 / 수용력.
# congestion > 1 이면 이동속도 감소.
# on_reach / on_leave 이벤트 기반 (효율적).

import morld
from events import subscribe_time_elapsed

SPACE_PER_UNIT = 5   # 캐릭터 1명당 점유 공간
MIN_CAPACITY = 2     # 최소 수용 인원

PROP_CONGESTION = "이동:혼잡"
MILLIS_PER_HOUR = 3_600_000

_initialized = False
_capacity = {}       # (region_id, location_id) -> int
_population = {}     # (region_id, location_id) -> int
_last_sync_day = -1


def reset():
    """챕터 전환 시 리셋"""
    global _initialized, _last_sync_day
    _initialized = False
    _capacity.clear()
    _population.clear()
    _last_sync_day = -1


def _get_region_ids():
    """활성 region ID 목록 (S04는 region_registry 없이 직접 조회)"""
    ids = []
    for rid in range(10):
        try:
            info = morld.get_region_info(rid)
            if info:
                ids.append(rid)
        except Exception:
            pass
    return ids


def _ensure_initialized():
    """lazy init: location별 capacity 구축 + 초기 인구 스캔"""
    global _initialized
    if _initialized:
        return

    for region_id in _get_region_ids():
        info = morld.get_region_info(region_id)
        if not info:
            continue
        for loc in info.get("locations", []):
            local_id = loc["id"] if isinstance(loc, dict) else int(loc)
            key = (region_id, local_id)
            length = loc.get("length", 0) if isinstance(loc, dict) else 0
            _capacity[key] = max(MIN_CAPACITY, int(length / SPACE_PER_UNIT))
            _population[key] = 0

    if not _capacity:
        return

    _initialized = True
    _sync_population()


def _sync_population():
    """전체 location 인구 재스캔"""
    global _last_sync_day

    for key in _population:
        region_id, location_id = key
        try:
            units = morld.get_characters_at_location(region_id, location_id)
            _population[key] = len(units) if units else 0
        except Exception:
            _population[key] = 0

    try:
        time_info = morld.get_time_info()
        if time_info:
            _last_sync_day = time_info.get("day", -1)
    except Exception:
        pass

    for key in _population:
        _apply_congestion(key)


def _on_time_elapsed(millis):
    """자정 전체 동기화"""
    global _last_sync_day
    _ensure_initialized()
    if not _initialized:
        return

    try:
        time_info = morld.get_time_info()
        if not time_info:
            return
        hour = time_info.get("hour", -1)
        day = time_info.get("day", -1)
        if hour == 0 and day != _last_sync_day:
            _sync_population()
    except Exception:
        pass


def on_unit_reach(unit_id, region_id, location_id):
    """유닛 도착 → 인구 증가"""
    _ensure_initialized()
    key = (region_id, location_id)
    if key not in _population:
        return
    _population[key] += 1
    _apply_congestion(key)


def on_unit_leave(unit_id, region_id, location_id):
    """유닛 출발 → 인구 감소"""
    _ensure_initialized()
    key = (region_id, location_id)
    if key not in _population:
        return
    _population[key] = max(0, _population[key] - 1)
    _apply_congestion(key)


def _apply_congestion(key):
    """혼잡 속도 적용"""
    region_id, location_id = key
    congestion = get_congestion(region_id, location_id)
    units = morld.get_characters_at_location(region_id, location_id)
    if not units:
        return

    if congestion is not None and congestion > 1.0:
        speed_pct = max(20, int(100 / congestion))
        for uid in units:
            morld.set_unit_prop(uid, PROP_CONGESTION, speed_pct)
    else:
        for uid in units:
            morld.clear_prop(uid, PROP_CONGESTION)


def get_congestion(region_id, location_id):
    """혼잡도 반환 (1.0 = 정상)"""
    _ensure_initialized()
    key = (region_id, location_id)
    if key not in _capacity:
        return None
    pop = _population.get(key, 0)
    cap = _capacity.get(key, MIN_CAPACITY)
    if cap <= 0:
        return 0.0
    return pop / cap


def get_population(region_id, location_id):
    """현재 인구"""
    _ensure_initialized()
    return _population.get((region_id, location_id), 0)


def get_capacity(region_id, location_id):
    """수용력"""
    _ensure_initialized()
    return _capacity.get((region_id, location_id), MIN_CAPACITY)


subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
