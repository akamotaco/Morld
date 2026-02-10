# temperature.py - Location 온도 + 캐릭터 체온 시스템
#
# Location별 온도를 시뮬레이션하여 헤더에 표시
# 계절/날씨/시간대에 따라 실외 온도가 결정되고,
# 실내는 인접 공간과의 평활화 + 열원(난로 등)으로 결정됨
#
# 캐릭터 체온: location 온도 + 젖음에 따라 매시간 수렴 (표시 전용)
#
# 구독: subscribe_time_elapsed(_on_time_elapsed, min_interval=1h)
# 매시간 전체 location 온도 + 캐릭터 체온 업데이트

import morld
from events import subscribe_time_elapsed


# === 상수 ===

MILLIS_PER_HOUR = 3_600_000

# 계절별 기본 온도 (°C)
SEASON_BASE = {"봄": 15, "여름": 28, "가을": 12, "겨울": -5}

# 날씨 보정값
WEATHER_MODIFIER = {"맑음": 2, "흐림": 0, "비": -3, "눈": -5}

# 시간대별 온도 오프셋 (index = hour, 0~23)
HOUR_OFFSETS = [
    -4, -4, -5, -5, -5, -5,   # 00~05: 새벽 최저
    -3, -2, -1,  0,            # 06~09: 아침 상승
    +2, +3, +4, +5, +5,       # 10~14: 낮 최고
    +4, +3, +2, +1,  0,       # 15~19: 저녁 하강
    -1, -2, -3, -3,            # 20~23: 밤
]

# 실내 온도 수렴률 (시간당 30%)
CONVERGENCE_RATE = 0.3

# 온도 범위 제한
TEMP_MIN = -30
TEMP_MAX = 50

# 알려진 Region ID 목록
REGION_IDS = [0, 2, 3]

# === 캐릭터 체온 상수 ===

PROP_BODY_TEMP = "체온"
NORMAL_BODY_TEMP = 36.5         # 정상 체온 (°C)
BODY_CONVERGENCE_RATE = 0.3     # 시간당 30% 수렴
TEMP_SENSITIVITY = 0.1          # location 온도 → 체온 영향 계수
WETNESS_TEMP_PENALTY = 2.0      # 100% 젖으면 target -2℃
INSULATION_BONUS = 0.5          # 보온 1당 target +0.5℃
BODY_TEMP_MIN = 34.0
BODY_TEMP_MAX = 40.0


# === 데이터 저장 ===

# (region_id, location_id) → float (현재 온도)
_location_temps = {}

# (region_id, location_id) → [(r, l, weight), ...]
_adjacency = {}

# (region_id, location_id) → [(unit_id, output, depth)]
_heat_sources = {}

# (region_id, location_id) → bool
_location_indoor = {}

# 체온 추적 대상: set of unit_id
_tracked_characters = set()

_initialized = False


# === 계절/날씨/시간 ===

def _get_season(month):
    """월 → 계절 (3-5: 봄, 6-8: 여름, 9-11: 가을, 12,1,2: 겨울)"""
    if month in (3, 4, 5):
        return "봄"
    elif month in (6, 7, 8):
        return "여름"
    elif month in (9, 10, 11):
        return "가을"
    else:
        return "겨울"


def _get_outdoor_temp(season, weather, hour):
    """실외 온도 계산: 계절 기본 + 날씨 보정 + 시간대 오프셋"""
    base = SEASON_BASE.get(season, 15)
    mod = WEATHER_MODIFIER.get(weather, 0)
    offset = HOUR_OFFSETS[hour] if 0 <= hour < 24 else 0
    return base + mod + offset


# === 초기화 ===

def reset():
    """챕터 전환 시 호출 — 모든 상태 초기화 (다음 접근 시 재초기화)"""
    global _initialized
    _initialized = False
    _location_temps.clear()
    _adjacency.clear()
    _heat_sources.clear()
    _location_indoor.clear()
    _tracked_characters.clear()


def _ensure_initialized():
    """lazy init: get_region_info()로 인접 그래프 + 초기 온도 구축"""
    global _initialized
    if _initialized:
        return

    for region_id in REGION_IDS:
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
            is_indoor = loc.get("is_indoor", False)
            _location_indoor[key] = is_indoor

            # gate 기반 인접 관계 구축
            neighbors = []
            for gate in loc.get("gates", []):
                cr = gate["connected_region"]
                cl = gate["connected_local"]
                neighbors.append((cr, cl))

            # region_gates (다른 Region으로의 연결)
            for rg in loc.get("region_gates", []):
                cr = rg[0]
                cl = rg[1]
                if (cr, cl) not in neighbors:
                    neighbors.append((cr, cl))

            _adjacency[key] = neighbors

    # region 데이터가 없으면 초기화 연기 (다음 호출 시 재시도)
    if not _location_indoor:
        return

    _initialized = True

    # 초기 온도 설정 (현재 실외 온도로 전체 초기화)
    time_info = morld.get_time_info()
    if time_info:
        month = time_info.get("month", 3)
        hour = time_info.get("hour", 12)
        weather = time_info.get("weather", "흐림")
        season = _get_season(month)
        outdoor = _get_outdoor_temp(season, weather, hour)
    else:
        outdoor = 15.0

    for key in _location_indoor:
        _location_temps[key] = float(outdoor)

    print(f"[temperature] Initialized: {len(_location_indoor)} locations, outdoor={outdoor:.1f}°C")


# === 열원 관리 ===

def register_heat_source(unit_id, region_id, location_id):
    """열원 오브젝트 등록 (Fireplace.instantiate에서 호출)"""
    key = (region_id, location_id)
    if key not in _heat_sources:
        _heat_sources[key] = []

    # 중복 방지
    for src in _heat_sources[key]:
        if src[0] == unit_id:
            return

    # 열원 속성 조회
    output = morld.get_unit_prop(unit_id, "heat:output") or 0
    depth = morld.get_unit_prop(unit_id, "heat:depth") or 0

    _heat_sources[key] = _heat_sources.get(key, [])
    _heat_sources[key].append((unit_id, output, depth))
    print(f"[temperature] Heat source registered: unit={unit_id} at ({region_id},{location_id}) output={output} depth={depth}")


def _calculate_heat_contributions():
    """
    열원별 BFS 확산 계산

    Returns:
        dict: (region_id, location_id) → float (추가 열량)
    """
    contributions = {}

    for loc_key, sources in _heat_sources.items():
        for unit_id, output, max_depth in sources:
            # light:on 체크 (꺼져있으면 열 없음)
            is_on = morld.get_unit_prop(unit_id, "light:on")
            if not is_on:
                continue

            # BFS: depth 0 = 현재 위치 (full), depth 1 = 인접 (0.5×), ...
            visited = set()
            queue = [(loc_key, 0)]  # (location_key, depth)
            visited.add(loc_key)

            while queue:
                current_key, depth = queue.pop(0)
                # 감쇠: 1.0 / (2 ** depth)
                heat = output / (2 ** depth)
                contributions[current_key] = contributions.get(current_key, 0) + heat

                # max_depth까지만 확산
                if depth < max_depth:
                    for neighbor in _adjacency.get(current_key, []):
                        if neighbor not in visited and neighbor in _location_indoor:
                            visited.add(neighbor)
                            queue.append((neighbor, depth + 1))

    return contributions


# === 시간 경과 업데이트 ===

def _on_time_elapsed(millis):
    """1시간마다 전체 location 온도 업데이트"""
    _ensure_initialized()

    if not _location_temps:
        return

    time_info = morld.get_time_info()
    if not time_info:
        return

    month = time_info.get("month", 3)
    hour = time_info.get("hour", 12)
    weather = time_info.get("weather", "흐림")
    season = _get_season(month)
    outdoor_temp = _get_outdoor_temp(season, weather, hour)

    # 0. 캐릭터 체온 업데이트
    _update_characters()

    # 1. 스냅샷
    old_temps = dict(_location_temps)

    # 2. 열원 기여도 계산
    heat_contrib = _calculate_heat_contributions()

    # 3. 각 location 업데이트
    for key, is_indoor in _location_indoor.items():
        if not is_indoor:
            # 실외: 직접 적용
            _location_temps[key] = float(outdoor_temp)
        else:
            # 실내: 인접 평균 + 열원 → 수렴
            neighbors = _adjacency.get(key, [])
            if not neighbors:
                # 인접 없으면 실외 온도로 수렴
                target = outdoor_temp + heat_contrib.get(key, 0)
            else:
                total_weight = 0.0
                weighted_sum = 0.0
                for nr, nl in neighbors:
                    nkey = (nr, nl)
                    ntemp = old_temps.get(nkey, outdoor_temp)
                    n_indoor = _location_indoor.get(nkey, False)
                    # indoor↔indoor: 1.0, indoor↔outdoor: 0.5
                    weight = 1.0 if n_indoor else 0.5
                    weighted_sum += ntemp * weight
                    total_weight += weight

                neighbor_avg = weighted_sum / total_weight if total_weight > 0 else outdoor_temp
                target = neighbor_avg + heat_contrib.get(key, 0)

            # 수렴: old + (target - old) × rate
            old = old_temps.get(key, outdoor_temp)
            new_temp = old + (target - old) * CONVERGENCE_RATE
            _location_temps[key] = max(TEMP_MIN, min(TEMP_MAX, new_temp))


# === 캐릭터 체온 헬퍼 ===

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


# === 캐릭터 체온 업데이트 ===

def _update_characters():
    """등록된 캐릭터 + 플레이어의 체온 업데이트 (매시간 _on_time_elapsed에서 호출)"""
    # 플레이어 + 등록된 NPC
    targets = set(_tracked_characters)
    player_id = morld.get_player_id()
    if player_id is not None:
        targets.add(player_id)

    if not targets:
        return

    for unit_id in targets:
        info = morld.get_unit_info(unit_id)
        if not info:
            continue

        region_id = info.get("region_id")
        location_id = info.get("location_id")
        if region_id is None or location_id is None:
            continue

        # location 온도 조회
        loc_temp = _location_temps.get((region_id, location_id))
        if loc_temp is None:
            continue

        # 현재 체온
        current = get_body_temperature(unit_id)

        # 목표 체온: 정상 + (location 온도 - 20) × 감도
        target = NORMAL_BODY_TEMP + (loc_temp - 20) * TEMP_SENSITIVITY

        # 보온 보정: 장비의 보온 prop 합산
        insulation = _get_equip_prop_total(unit_id, "보온")
        if insulation > 0:
            target += insulation * INSULATION_BONUS

        # 젖음 보정: 젖을수록 체감 온도 하락
        try:
            import humidity
            wetness = humidity.get_unit_wetness(unit_id)
            if wetness and wetness > 0:
                target -= (wetness / 100) * WETNESS_TEMP_PENALTY
        except ImportError:
            pass

        # 수렴
        new_temp = current + (target - current) * BODY_CONVERGENCE_RATE
        new_temp = max(BODY_TEMP_MIN, min(BODY_TEMP_MAX, new_temp))

        set_body_temperature(unit_id, new_temp)


# === Public API ===

def register_character(unit_id):
    """체온 추적 대상 등록 (survival.register_npc 등에서 호출)"""
    _tracked_characters.add(unit_id)


def unregister_character(unit_id):
    """체온 추적 대상 해제"""
    _tracked_characters.discard(unit_id)


def get_body_temperature(unit_id):
    """
    캐릭터 체온 조회

    Returns:
        float: 체온 (기본값 36.5)
    """
    val = morld.get_unit_prop(unit_id, PROP_BODY_TEMP)
    if val is None:
        return NORMAL_BODY_TEMP
    return float(val)


def set_body_temperature(unit_id, value):
    """캐릭터 체온 설정 (정상 범위면 prop 제거)"""
    if abs(value - NORMAL_BODY_TEMP) < 0.05:
        morld.clear_prop(unit_id, PROP_BODY_TEMP)
    else:
        morld.set_unit_prop(unit_id, PROP_BODY_TEMP, round(value, 1))


def get_temperature(region_id, location_id):
    """
    현재 location 온도 조회 (ui.py에서 호출)

    Returns:
        float 또는 None (초기화 전)

    Raises:
        KeyError: 초기화 완료 후 해당 location이 등록되지 않은 경우
    """
    _ensure_initialized()
    key = (region_id, location_id)
    if _initialized and key not in _location_temps:
        raise KeyError(f"[temperature] Unknown location {key}. {len(_location_temps)} locations registered")
    return _location_temps.get(key)


# === 모듈 로드 시 이벤트 구독 (1시간 간격) ===

subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
