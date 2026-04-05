# sound.py - 소리 전파 시스템
#
# 캐릭터 중심 소리 전파: emit → BFS 전파 → 청력별 필터 → heard 리스트
# 거리 모델: location length + gate distance (통일된 location units)
#
# 감쇠: attenuated = intensity / (1 + distance / ATTENUATION_HALF)
# 실내/실외 경계 통과 시 INDOOR_BOUNDARY_FACTOR 추가 감쇠
#
# 구독: 없음 (emit_sound 호출 시 즉시 전파, tick별 flush)

import morld


# === 상수 ===

# 소리 강도 (소리 타입별 기본 강도)
SOUND_INTENSITIES = {
    # 이동
    "footstep": 20,
    "footstep_run": 40,
    "footstep_crouch": 10,
    # 전투
    "combat": 80,
    "scream": 100,
    "gunshot": 120,
    # 작업
    "chop": 50,
    "cooking": 10,
    "splash": 25,
    "craft": 35,
    # 사고/환경
    "animal": 60,
    "crash": 70,
    # 생활
    "door": 30,
    "talk": 15,
    "whisper": 5,
    "stand_up": 35,
    "sit_down": 30,
    "pickup": 15,
    "equip": 20,
    "eat": 10,
    # 친밀
    "moan": 20,
}

# 소리 카테고리 (NPC 리액션 디스패치용)
SOUND_CATEGORIES = {
    "footstep": "이동",
    "footstep_run": "이동",
    "footstep_crouch": "이동",
    "combat": "전투",
    "scream": "전투",
    "gunshot": "전투",
    "chop": "작업",
    "cooking": "작업",
    "splash": "작업",
    "craft": "작업",
    "animal": "자연",
    "crash": "사고",
    "door": "생활",
    "talk": "생활",
    "whisper": "생활",
    "stand_up": "생활",
    "sit_down": "생활",
    "pickup": "생활",
    "equip": "생활",
    "eat": "생활",
    "moan": "친밀",
}

# 청력 threshold (감쇠 후 강도가 이 값 이상이면 들림)
HEARING_THRESHOLD = {
    "keen": 5,
    "normal": 15,
    "dull": 30,
}

# 은신 자동 해제 threshold (이 강도 이상의 소리를 내면 은신 해제)
STEALTH_BREAK_THRESHOLD = 30

# 감쇠 상수: 이 거리에서 강도 절반 (location units)
ATTENUATION_HALF = 500

# 실내↔실외 경계 통과 시 추가 감쇠 (0.7 = 30% 감소)
INDOOR_BOUNDARY_FACTOR = 0.7

from engine.region_registry import get_region_ids


# === 소리 묘사 텍스트 ===

# (sound_type, distance_category) → 텍스트
# distance_category: "near" (같은 위치), "mid" (1-2홉), "far" (3+홉)
SOUND_DESCRIPTIONS = {
    "footstep": {
        "near": "가까운 곳에서 발소리가 들린다.",
        "mid": "어딘가에서 발소리가 들린다.",
        "far": "먼 곳에서 희미한 발소리가 들린다.",
    },
    "footstep_run": {
        "near": "가까이에서 빠른 발소리가 들린다.",
        "mid": "어딘가에서 뛰어오는 소리가 들린다.",
        "far": "먼 곳에서 다급한 발소리가 들린다.",
    },
    "combat": {
        "near": "가까운 곳에서 격렬한 전투 소리가 들린다.",
        "mid": "어딘가에서 싸우는 소리가 들린다.",
        "far": "먼 곳에서 희미한 전투 소리가 들린다.",
    },
    "scream": {
        "near": "가까이에서 비명이 들린다.",
        "mid": "어딘가에서 비명이 들린다.",
        "far": "먼 곳에서 희미한 비명이 들린다.",
    },
    "gunshot": {
        "near": "가까이에서 총성이 울린다.",
        "mid": "어딘가에서 총성이 들린다.",
        "far": "먼 곳에서 희미한 총소리가 들린다.",
    },
    "chop": {
        "near": "가까운 곳에서 나무를 찍는 소리가 들린다.",
        "mid": "어딘가에서 도끼질 소리가 들린다.",
        "far": "먼 곳에서 나무를 찍는 소리가 들린다.",
    },
    "cooking": {
        "near": "가까이에서 요리하는 소리가 들린다.",
        "mid": "어딘가에서 요리 소리가 들린다.",
    },
    "splash": {
        "near": "가까이에서 물소리가 들린다.",
        "mid": "어딘가에서 물소리가 들린다.",
    },
    "animal": {
        "near": "가까이에서 동물 소리가 들린다.",
        "mid": "어딘가에서 동물 소리가 들린다.",
        "far": "먼 곳에서 동물 울음소리가 들린다.",
    },
    "crash": {
        "near": "가까이에서 무언가 부서지는 소리가 들린다.",
        "mid": "어딘가에서 큰 소리가 들린다.",
        "far": "먼 곳에서 희미한 소리가 들린다.",
    },
    "door": {
        "near": "가까이에서 문이 열리는 소리가 들린다.",
        "mid": "어딘가에서 문소리가 들린다.",
    },
    "talk": {
        "near": "가까이에서 말소리가 들린다.",
        "mid": "어딘가에서 대화 소리가 들린다.",
    },
}


# === 데이터 ===

# adjacency graph: (region_id, location_id) → [(nr, nl, edge_distance, crosses_boundary), ...]
# edge_distance = src.length/2 + gate.distance + dest.length/2
# crosses_boundary = True if indoor/outdoor boundary crossed
_adjacency = {}

# location info: (region_id, location_id) → {"length": float, "is_indoor": bool}
_location_info = {}

# 캐릭터 청력: unit_id → "keen" / "normal" / "dull"
_hearing = {}

# 현재 step의 heard 이벤트: unit_id → [SoundEvent, ...]
_heard_events = {}

_initialized = False


# === SoundEvent ===

class SoundEvent:
    """전파된 소리 이벤트"""
    __slots__ = ("sound_type", "category", "intensity", "source_id", "source_location", "distance", "hops")

    def __init__(self, sound_type, intensity, source_id, source_location, distance, hops):
        self.sound_type = sound_type
        self.category = SOUND_CATEGORIES.get(sound_type, "기타")
        self.intensity = intensity       # 감쇠 후 강도
        self.source_id = source_id       # 소리를 낸 unit_id
        self.source_location = source_location  # (region_id, location_id)
        self.distance = distance         # 총 전파 거리
        self.hops = hops                 # 경유한 location 수


# === 초기화 ===

def reset():
    """챕터 전환 시 호출 — 모든 상태 초기화 (다음 접근 시 재초기화)"""
    global _initialized
    _initialized = False
    _adjacency.clear()
    _location_info.clear()
    # _hearing, _heard_events는 유지 (캐릭터 등록은 챕터 초기화에서 다시 됨)


def _ensure_initialized():
    """lazy init: get_region_info()로 adjacency graph 구축"""
    global _initialized
    if _initialized:
        return

    # 1. location 정보 수집
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
            length = loc.get("length", 0)
            is_indoor = loc.get("is_indoor", False)
            _location_info[key] = {"length": length, "is_indoor": is_indoor}

            # Gate 기반 인접 (같은 region)
            gates = loc.get("gates", [])
            if key not in _adjacency:
                _adjacency[key] = []
            for gate in gates:
                cr = gate.get("connected_region", region_id)
                cl = gate.get("connected_local")
                if cl is None:
                    continue
                gate_dist = gate.get("distance", 0)
                _adjacency[key].append((cr, cl, gate_dist))

            # RegionGate 레거시 제거 — cross-region도 Gate에서 처리
            # (Gate의 connected_region이 다른 region이면 자동으로 인접 등록됨)

    # region 데이터가 없으면 초기화 연기 (다음 호출 시 재시도)
    if not _location_info:
        return

    _initialized = True

    # 2. edge_distance 계산 (src.length/2 + gate_dist + dest.length/2)
    final_adjacency = {}
    for key, neighbors in _adjacency.items():
        src_info = _location_info.get(key)
        src_half = (src_info["length"] / 2) if src_info else 0

        final_neighbors = []
        for cr, cl, gate_dist in neighbors:
            dest_key = (cr, cl)
            dest_info = _location_info.get(dest_key)
            dest_half = (dest_info["length"] / 2) if dest_info else 0

            edge_distance = src_half + gate_dist + dest_half
            # 실내↔실외 경계 검사
            src_indoor = src_info["is_indoor"] if src_info else True
            dest_indoor = dest_info["is_indoor"] if dest_info else True
            crosses_boundary = src_indoor != dest_indoor

            final_neighbors.append((cr, cl, edge_distance, crosses_boundary))

        final_adjacency[key] = final_neighbors

    _adjacency.clear()
    _adjacency.update(final_adjacency)

    print(f"[sound] Initialized: {len(_location_info)} locations, "
          f"{sum(len(v) for v in _adjacency.values())} edges")


# === 소리 전파 ===

def _attenuate(intensity, distance):
    """거리에 의한 감쇠"""
    if distance <= 0:
        return intensity
    return intensity / (1.0 + distance / ATTENUATION_HALF)


def emit_sound(source_id, sound_type, intensity=None, location=None):
    """
    소리 발생 및 BFS 전파

    Args:
        source_id: 소리를 낸 unit_id
        sound_type: 소리 타입 (SOUND_INTENSITIES 키)
        intensity: 강도 (None이면 기본값 사용)
        location: (region_id, location_id) 또는 None (unit 위치 자동)
    """
    _ensure_initialized()

    if intensity is None:
        intensity = SOUND_INTENSITIES.get(sound_type, 20)

    # 의류 소음 보정: 이동/자세 계열 소리는 장비 소음 속성에 따라 강도 변동
    if sound_type in _EQUIPMENT_NOISE_TYPES:
        intensity = _apply_equipment_noise(source_id, intensity)

    # 은신 자동 판정: 소리 발생자가 은신 중이고 강도가 threshold 이상이면 해제
    _check_stealth_break(source_id, intensity)

    # source 위치 확인
    if location is None:
        info = morld.get_unit_info(source_id)
        if not info:
            return
        location = (info.get("region_id"), info.get("location_id"))

    if location not in _location_info:
        return

    # BFS 전파
    # visited: (region_id, location_id) → (total_distance, hops)
    visited = {location: (0.0, 0)}
    queue = [(location, 0.0, 0)]  # (location_key, total_distance, hops)

    while queue:
        current, dist, hops = queue.pop(0)

        neighbors = _adjacency.get(current, [])
        for cr, cl, edge_distance, crosses_boundary in neighbors:
            neighbor_key = (cr, cl)
            new_dist = dist + edge_distance

            # 이미 더 짧은 경로로 방문했으면 스킵
            if neighbor_key in visited and visited[neighbor_key][0] <= new_dist:
                continue

            # 감쇠 계산
            attenuated = _attenuate(intensity, new_dist)
            if crosses_boundary:
                attenuated *= INDOOR_BOUNDARY_FACTOR

            # keen threshold 이하면 더 이상 전파 불필요
            min_threshold = HEARING_THRESHOLD.get("keen", 5)
            if attenuated < min_threshold:
                continue

            visited[neighbor_key] = (new_dist, hops + 1)
            queue.append((neighbor_key, new_dist, hops + 1))

    # 각 위치의 unit들에게 SoundEvent 전달
    for loc_key, (total_dist, total_hops) in visited.items():
        if loc_key == location and total_dist == 0:
            # 같은 location: 시각으로 확인 가능, 텍스트 미생성 (NPC는 받음)
            pass

        attenuated = _attenuate(intensity, total_dist)
        # 경계 감쇠는 BFS 과정에서 이미 적용됨 (최종값은 distance 기반만)
        # Note: BFS에서 boundary 체크로 전파 제한했으므로 여기선 단순 거리 감쇠

        region_id, location_id = loc_key
        try:
            units = morld.get_characters_at_location(region_id, location_id)
        except Exception:
            continue
        if not units:
            continue

        for unit_id in units:
            if unit_id == source_id:
                continue  # 자기 소리는 안 들림

            hearing = _hearing.get(unit_id)
            if not hearing:
                continue  # 미등록 unit은 무시

            threshold = HEARING_THRESHOLD.get(hearing, 15)
            if attenuated >= threshold:
                event = SoundEvent(
                    sound_type=sound_type,
                    intensity=attenuated,
                    source_id=source_id,
                    source_location=location,
                    distance=total_dist,
                    hops=total_hops,
                )
                if unit_id not in _heard_events:
                    _heard_events[unit_id] = []
                _heard_events[unit_id].append(event)


# === Public API ===

def register_hearing(unit_id, hearing_type="normal"):
    """
    캐릭터 청력 등록

    Args:
        unit_id: 캐릭터 unit_id
        hearing_type: "keen" / "normal" / "dull"
    """
    _hearing[unit_id] = hearing_type


def unregister_hearing(unit_id):
    """캐릭터 청력 해제"""
    _hearing.pop(unit_id, None)
    _heard_events.pop(unit_id, None)


def get_heard(unit_id):
    """
    캐릭터가 들은 소리 이벤트 반환 (이번 step)

    Args:
        unit_id: 캐릭터 unit_id

    Returns:
        list[SoundEvent]
    """
    return _heard_events.get(unit_id, [])


def get_heard_by_category(unit_id, category):
    """
    특정 카테고리의 소리만 필터링하여 반환

    Args:
        unit_id: 캐릭터 unit_id
        category: "전투" / "이동" / "작업" / "자연" / "사고" / "생활" / "친밀"

    Returns:
        list[SoundEvent]
    """
    return [e for e in _heard_events.get(unit_id, []) if e.category == category]


def flush():
    """
    step 종료 시 heard 이벤트 초기화
    C# 또는 Python에서 step 끝에 호출
    """
    _heard_events.clear()


def get_heard_texts(unit_id):
    """
    캐릭터가 들은 소리를 텍스트로 반환 (UI 표시용)

    같은 location의 소리는 텍스트 미생성 (눈으로 봄)

    Args:
        unit_id: 플레이어 unit_id

    Returns:
        list[str]: 소리 묘사 텍스트 목록
    """
    events = _heard_events.get(unit_id, [])
    if not events:
        return []

    texts = []
    seen_types = set()  # 중복 방지

    for event in events:
        if event.distance == 0 and event.hops == 0:
            continue  # 같은 location: 시각 확인

        key = event.sound_type
        if key in seen_types:
            continue
        seen_types.add(key)

        # 거리 카테고리 결정
        if event.hops <= 1:
            category = "near"
        elif event.hops <= 3:
            category = "mid"
        else:
            category = "far"

        desc = SOUND_DESCRIPTIONS.get(event.sound_type, {})
        text = desc.get(category) or desc.get("mid") or desc.get("near")
        if text:
            texts.append(text)

    return texts


# === 의류 소음 보정 ===

# 장비 소음 속성의 영향을 받는 소리 타입
_EQUIPMENT_NOISE_TYPES = {
    "footstep", "footstep_run", "footstep_crouch",
    "stand_up", "sit_down",
}


def _apply_equipment_noise(unit_id, base_intensity):
    """장비 소음 속성으로 강도 보정

    equip_props '소음' 합산:
      0 (기본/맨몸): 보정 없음
      양수 (갑옷/금속): 강도 증가 (1당 +10%)
      음수 (천/가죽): 강도 감소 (1당 -10%)
    """
    try:
        equipped = morld.get_equipped_items(unit_id)
        if not equipped:
            return base_intensity
        noise_mod = 0
        for item_id in equipped:
            info = morld.get_item_info(item_id)
            if info:
                noise_mod += info.get("equip_props", {}).get("소음", 0)
        if noise_mod == 0:
            return base_intensity
        # 1당 ±10%, 최소 10% 유지
        factor = max(0.1, 1.0 + noise_mod * 0.1)
        return int(base_intensity * factor)
    except Exception:
        return base_intensity


# === 은신 연동 ===

def _check_stealth_break(source_id, intensity):
    """소리 강도가 threshold 이상이면 은신 자동 해제

    소리의 물리적 결과로 은신이 깨지는 시스템.
    시나리오별 확장은 stealth.on_stealth_noise() 콜백으로 위임.
    """
    if intensity < STEALTH_BREAK_THRESHOLD:
        return

    from engine import stealth
    if not stealth.is_unit_stealthed(source_id):
        return

    stealth.on_stealth_noise(source_id, intensity)
