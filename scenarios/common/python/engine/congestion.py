# congestion.py - Location 혼잡도 시스템
#
# 혼잡도(congestion) = 인구(population) / 수용력(capacity)
# congestion > 1 이면 해당 Location 내 캐릭터 이동속도 감소
# on_reach / on_leave 이벤트에서만 계산 (효율적)
#
# ┌─────────────────────────────────────────────────────┐
# │  C# EventSystem (event_system.cs)                   │
# │  DetectLocationChanges()                             │
# │    currentLoc != lastLoc                             │
# │    → OnLeave(old_r, old_l)                           │
# │    → OnReach(new_r, new_l)                           │
# └──────────┬──────────────────────────┬────────────────┘
#            │                          │
#   ┌────────▼────────┐       ┌────────▼────────┐
#   │    on_leave      │       │    on_reach      │
#   │  population--    │       │  population++    │
#   │  _apply_cong()   │       │  _apply_cong()   │
#   └────────┬────────┘       └────────┬────────┘
#            │                          │
#            └──────────┬───────────────┘
#                       ▼
#   ┌───────────────────────────────────────────┐
#   │  _apply_congestion(key)                   │
#   │  congestion = population / capacity       │
#   │                                           │
#   │  congestion > 1:                          │
#   │    speed_pct = max(20, 100/congestion)    │
#   │    set_unit_prop("이동:혼잡", speed_pct)  │
#   │  else:                                    │
#   │    clear_prop("이동:혼잡")                │
#   └───────────────────────────────────────────┘
#                       │
#                       ▼
#   ┌───────────────────────────────────────────┐
#   │  C# Unit.GetMovementSpeed()               │
#   │  result *= 이동:혼잡 / 100                │
#   │  (100=보통, 50=반감, 최소 10%)            │
#   └───────────────────────────────────────────┘
#
# lazy init: get_region_info() → capacity = max(2, length / 5)
# 초기 인구: _sync_population()으로 전체 스캔
# 자정 동기화: 매일 00:00에 drift 보정
import morld
from engine.event_core import subscribe_time_elapsed

from engine.region_registry import get_region_ids
SPACE_PER_UNIT = 5   # 캐릭터 1명당 점유 공간
MIN_CAPACITY = 2     # 최소 수용 인원

PROP_CONGESTION = "이동:혼잡"
MILLIS_PER_HOUR = 3_600_000

_initialized = False
_capacity = {}       # (region_id, location_id) -> int
_population = {}     # (region_id, location_id) -> int
_last_sync_day = -1  # 마지막 동기화 날짜 (자정 동기화용)


def reset():
    """챕터 전환 시 호출 — 모든 상태 초기화 (다음 접근 시 재초기화)"""
    global _initialized, _last_sync_day
    _initialized = False
    _capacity.clear()
    _population.clear()
    _last_sync_day = -1
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)


def _ensure_initialized():
    """lazy init: get_region_info()로 location별 capacity 구축 + 초기 인구 스캔"""
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

        for loc in info.get("locations", []):
            local_id = loc["id"]
            key = (region_id, local_id)
            length = loc.get("length", 0)
            _capacity[key] = max(MIN_CAPACITY, int(length / SPACE_PER_UNIT))
            _population[key] = 0

    # region 데이터가 없으면 초기화 연기 (다음 호출 시 재시도)
    if not _capacity:
        return

    _initialized = True

    # 초기 인구 스캔 (게임 시작 시 on_reach 미발생 보정)
    _sync_population()


def _sync_population():
    """전체 location 인구 재스캔 (drift 보정)"""
    global _last_sync_day

    for key in _population:
        region_id, location_id = key
        try:
            units = morld.get_characters_at_location(region_id, location_id)
            _population[key] = len(units) if units else 0
        except Exception:
            _population[key] = 0

    # 동기화 날짜 기록
    try:
        time_info = morld.get_time_info()
        if time_info:
            _last_sync_day = time_info.get("day", -1)
    except Exception:
        pass

    # 동기화 후 혼잡도 재적용
    for key in _population:
        _apply_congestion(key)


def _on_time_elapsed(millis):
    """자정(00:00) 전체 동기화 — drift 보정"""
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

        # 자정(hour=0) + 날짜 변경 시 1회 동기화
        if hour == 0 and day != _last_sync_day:
            _sync_population()
    except Exception:
        pass


def on_unit_reach(unit_id, region_id, location_id):
    """유닛 도착 -> 인구 증가 -> 혼잡도 반영"""
    _ensure_initialized()
    key = (region_id, location_id)
    if key not in _population:
        return
    _population[key] += 1
    _apply_congestion(key)


def on_unit_leave(unit_id, region_id, location_id):
    """유닛 출발 -> 인구 감소 -> 혼잡도 반영"""
    _ensure_initialized()
    key = (region_id, location_id)
    if key not in _population:
        return
    _population[key] = max(0, _population[key] - 1)
    _apply_congestion(key)


def _apply_congestion(key):
    """해당 location의 모든 유닛에 혼잡 속도 적용"""
    region_id, location_id = key
    congestion = get_congestion(region_id, location_id)

    units = morld.get_characters_at_location(region_id, location_id)
    if not units:
        return

    if congestion > 1.0:
        speed_pct = max(20, int(100 / congestion))
        for uid in units:
            morld.set_unit_prop(uid, PROP_CONGESTION, speed_pct)
    else:
        for uid in units:
            morld.clear_prop(uid, PROP_CONGESTION)


def _check_location(key):
    """초기화 완료 후 location 존재 여부 검증 — 미등록 시 False 반환"""
    if _initialized and key not in _capacity:
        return False
    return True


def get_congestion(region_id, location_id):
    """혼잡도 반환 (1.0 = 정상, 2.0 = 2배 혼잡, None = 미등록)"""
    _ensure_initialized()
    key = (region_id, location_id)
    if not _check_location(key):
        return None
    pop = _population.get(key, 0)
    cap = _capacity.get(key, MIN_CAPACITY)
    if cap <= 0:
        return 0.0
    return pop / cap


def get_population(region_id, location_id):
    """현재 인구 반환"""
    _ensure_initialized()
    key = (region_id, location_id)
    if not _check_location(key):
        return 0
    return _population.get(key, 0)


def get_capacity(region_id, location_id):
    """수용력 반환"""
    _ensure_initialized()
    key = (region_id, location_id)
    if not _check_location(key):
        return MIN_CAPACITY
    return _capacity.get(key, MIN_CAPACITY)


# NOTE: subscribe_time_elapsed는 reset()에서 호출 (모듈 로드 시 구독 제거)
