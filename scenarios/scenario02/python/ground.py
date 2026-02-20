# ground.py - 동적 바닥 관리 시스템
#
# 아이템 드롭 시에만 바닥 오브젝트를 동적 생성하고,
# 아이템이 모두 제거되면 자동으로 소멸.
#
# 병합 규칙: 같은 location 내 X좌표 거리 ≤ MERGE_THRESHOLD → 기존 바닥에 추가
#
# 레지스트리: (region_id, location_id) → [{"unit_id": int, "x": float}, ...]
#
# API:
#   reset()                                   — 챕터 전환
#   ensure_ground_at(region_id, loc_id, x)    — 생성 or 기존 반환
#   drop_item_at(unit_id, item_id, count, x)  — 드롭 (위치 자동)
#   check_empty_ground(ground_unit_id)         — 비었으면 제거
#   get_grounds_at(region_id, loc_id)          — 조회
#   register_ground(region_id, loc_id, uid, x) — 챕터 초기화용

import morld

# === 상수 ===

MERGE_THRESHOLD = 3.0   # X좌표 거리 이내면 기존 바닥에 병합

# === 레지스트리 ===

# (region_id, location_id) → [{"unit_id": int, "x": float}, ...]
_grounds = {}

# unit_id → (region_id, location_id)  역방향 인덱스
_ground_locations = {}


# ========================================
# 초기화
# ========================================

def reset():
    """챕터 전환 시 레지스트리 초기화"""
    _grounds.clear()
    _ground_locations.clear()
    print("[ground] reset")


# ========================================
# 조회 API
# ========================================

def get_grounds_at(region_id, location_id):
    """특정 location의 동적 바닥 목록 반환 (복사본)"""
    key = (region_id, location_id)
    entries = _grounds.get(key, [])
    return [dict(e) for e in entries]


def is_dynamic_ground(unit_id):
    """unit_id가 동적 바닥인지 확인"""
    return unit_id in _ground_locations


# ========================================
# 생성/병합
# ========================================

def ensure_ground_at(region_id, location_id, x):
    """
    해당 위치에 바닥 확보. 병합 가능하면 기존 반환, 없으면 새로 생성.

    Args:
        region_id: Region ID
        location_id: Location ID
        x: X좌표

    Returns:
        int — 바닥 오브젝트 unit_id
    """
    key = (region_id, location_id)
    entries = _grounds.get(key, [])

    # 병합 대상 탐색: 가장 가까운 바닥
    best = None
    best_dist = MERGE_THRESHOLD + 1
    for entry in entries:
        dist = abs(entry["x"] - x)
        if dist <= MERGE_THRESHOLD and dist < best_dist:
            best = entry
            best_dist = dist

    if best is not None:
        return best["unit_id"]

    # 새로 생성
    return _create_ground(region_id, location_id, x)


def _resolve_ground_class(region_id, location_id):
    """Location의 ground_type에 맞는 Ground 클래스와 인스턴스 반환"""
    from assets.objects import grounds as grounds_module
    from assets.objects.grounds import DynamicGround
    from assets.registry import get_unique_id, get_location_class

    # location_id → unique_id → Location 클래스 → ground_type
    unique_id = get_unique_id(location_id)
    if unique_id:
        loc_cls = get_location_class(unique_id)
        if loc_cls:
            ground_type_name = getattr(loc_cls, "ground_type", None)
            if ground_type_name:
                ground_cls = getattr(grounds_module, ground_type_name, None)
                if ground_cls:
                    return ground_cls, ground_cls()

    return DynamicGround, DynamicGround()


def _copy_env_props(ground_id, region_id, location_id):
    """생성 직후 현재 환경 prop을 바닥에 복사 (다음 hourly 전까지 동기화)"""
    # 오염도
    try:
        import pollution
        loc_pol = pollution.get_location_pollution(region_id, location_id)
        if loc_pol and loc_pol > 0:
            morld.set_unit_prop(ground_id, "오염:수치", loc_pol)
    except ImportError:
        pass

    # 젖음 (비 올 때만)
    try:
        import humidity
        if humidity.is_raining():
            loc_hum = humidity.get_humidity(region_id, location_id)
            if loc_hum and loc_hum > 0:
                morld.set_unit_prop(ground_id, "습도:젖음", round(loc_hum * 0.5, 1))
    except ImportError:
        pass


def _create_ground(region_id, location_id, x):
    """동적 바닥 오브젝트 생성"""
    ground_id = morld.create_id("unit")

    # Location에 맞는 바닥 클래스 결정
    ground_cls, ground_instance = _resolve_ground_class(region_id, location_id)

    # C# UnitSystem에 유닛 등록
    morld.add_unit(
        ground_id,
        ground_instance.name,  # location에 맞는 바닥 이름
        region_id,
        location_id,
        "object",          # type
        ground_instance.actions,  # 바닥 클래스의 액션
        [],                # mood
        f"dynamic_ground:{ground_id}",  # unique_id (고유)
        None,              # action_props
        None,              # owner
        True               # item_visible (아이템 개수 항상 표시)
    )

    # X좌표 설정
    morld.set_unit_position(ground_id, x, 0)

    # Python 인스턴스 등록 (call: 액션, focus_text용)
    from assets.objects import register_instance
    ground_instance.instance_id = ground_id
    ground_instance.region_id = region_id
    ground_instance.location_id = location_id
    register_instance(ground_id, ground_instance)

    # 환경 prop 초기 복사
    _copy_env_props(ground_id, region_id, location_id)

    # 레지스트리 등록
    key = (region_id, location_id)
    if key not in _grounds:
        _grounds[key] = []
    entry = {"unit_id": ground_id, "x": x}
    _grounds[key].append(entry)
    _ground_locations[ground_id] = (region_id, location_id)

    # Location의 ground_id 설정 (기존 ground가 없으면)
    existing_ground = morld.get_location_ground_id(region_id, location_id)
    if not existing_ground:
        morld.set_location_ground_id(region_id, location_id, ground_id)

    print(f"[ground] created: id={ground_id} at R{region_id},L{location_id},x={x}")
    return ground_id


# ========================================
# 드롭
# ========================================

def drop_item_at(unit_id, item_id, count=1, x=None):
    """
    유닛의 현재 위치에 아이템 드롭.

    Args:
        unit_id: 드롭 주체 (캐릭터) unit_id — 위치 추출용
        item_id: 드롭할 아이템 ID
        count: 개수 (기본 1)
        x: X좌표 (None이면 유닛 위치에서 추출)

    Returns:
        int — 바닥 오브젝트 unit_id
    """
    # 유닛 위치 추출
    loc = morld.get_unit_location(unit_id)
    if not loc:
        print(f"[ground] drop_item_at: unit {unit_id} has no location")
        return None
    region_id, location_id = loc[0], loc[1]

    # X좌표 추출
    if x is None:
        pos = morld.get_unit_position(unit_id)
        x = pos[0] if pos else 0

    # 바닥 확보 (생성 or 기존)
    ground_id = ensure_ground_at(region_id, location_id, x)

    # 아이템 추가
    morld.give_item(ground_id, item_id, count)

    return ground_id


# ========================================
# 제거 (빈 바닥 정리)
# ========================================

def check_empty_ground(ground_unit_id):
    """
    동적 바닥의 인벤토리가 비었으면 제거.

    Args:
        ground_unit_id: 바닥 오브젝트 unit_id

    Returns:
        bool — True if removed, False if still has items or not a dynamic ground
    """
    if ground_unit_id not in _ground_locations:
        return False  # 동적 바닥이 아님

    # 인벤토리 확인
    inventory = morld.get_unit_inventory(ground_unit_id)
    if inventory:
        return False  # 아이템이 남아있음

    _remove_ground(ground_unit_id)
    return True


def _remove_ground(ground_unit_id):
    """동적 바닥 오브젝트 제거"""
    loc_key = _ground_locations.pop(ground_unit_id, None)
    if loc_key is None:
        return

    region_id, location_id = loc_key

    # 레지스트리에서 제거
    key = (region_id, location_id)
    entries = _grounds.get(key, [])
    _grounds[key] = [e for e in entries if e["unit_id"] != ground_unit_id]
    if not _grounds[key]:
        del _grounds[key]

    # Location ground_id 업데이트
    current_ground = morld.get_location_ground_id(region_id, location_id)
    if current_ground == ground_unit_id:
        # 남은 동적 바닥이 있으면 그것으로 교체, 없으면 None
        remaining = _grounds.get(key, [])
        new_ground = remaining[0]["unit_id"] if remaining else None
        morld.set_location_ground_id(region_id, location_id, new_ground)

    # Python 인스턴스 정리
    from assets.objects import _instances
    _instances.pop(ground_unit_id, None)

    # C# 유닛 제거
    morld.remove_unit(ground_unit_id)

    print(f"[ground] removed: id={ground_unit_id} from R{region_id},L{location_id}")


# ========================================
# 챕터 초기화 헬퍼
# ========================================

def register_ground(region_id, location_id, unit_id, x):
    """
    챕터 초기화에서 이미 생성된 바닥을 레지스트리에 등록.
    (Chapter 코드에서 직접 add_unit + 이 함수로 등록할 때 사용)

    Args:
        region_id: Region ID
        location_id: Location ID
        unit_id: 바닥 오브젝트 unit_id
        x: X좌표
    """
    key = (region_id, location_id)
    if key not in _grounds:
        _grounds[key] = []
    _grounds[key].append({"unit_id": unit_id, "x": x})
    _ground_locations[unit_id] = (region_id, location_id)
