# vehicle.py - 차량 시스템 유틸리티
#
# 차량 Object의 연료/부품/수리/상태/이동 로직.
# UI/C# 의존 없이 순수 prop 조작만 수행.
#
# 차량 Object는 아래 prop 사용:
#   vehicle:type        motorcycle | car | bus
#   vehicle:seats       최대 탑승 인원
#   vehicle:speed       이동속도 배율
#   vehicle:exposed     0=보호, 1=노출
#   vehicle:hp          현재 HP (전 부품 합산)
#   vehicle:hp_max      최대 HP
#   vehicle:status      normal | disabled | wrecked
#   vehicle:fuel        현재 연료 (리터)
#   vehicle:fuel_max    최대 연료
#   vehicle:fuel_rate   리터/거리단위
#   vehicle:interior    대형 차량 내부 Location ("R{n}:L{n}")
#   vehicle:part:{id}       부품 HP
#   vehicle:part:{id}_max   부품 최대 HP
#   seated_by:{seat}        좌석별 탑승자 (-1=빈)

import morld

# ========================================
# 부품 정의
# ========================================

# (이름, 기동필수, 피격가중치)
VEHICLE_PARTS = {
    "engine":    ("엔진",    True,  0.15),
    "tire":      ("타이어",  True,  0.25),
    "body":      ("차체",    False, 0.35),
    "window":    ("유리창",  False, 0.15),
    "fuel_tank": ("연료탱크", True,  0.10),
}

# 수리 레시피: {재료 unique_id: 수량}, 복구량, 소요시간(분)
REPAIR_RECIPES = {
    "engine":    {"materials": {"iron_ore": 2, "copper_ore": 1}, "restore": 30, "time_min": 60},
    "tire":      {"materials": {"cloth": 2, "cord": 1},         "restore": 25, "time_min": 30},
    "body":      {"materials": {"iron_ore": 1, "plank": 2},     "restore": 30, "time_min": 45},
    "window":    {"materials": {"copper_ore": 1},                "restore": 20, "time_min": 20},
    "fuel_tank": {"materials": {"iron_ore": 1, "copper_ore": 1}, "restore": 20, "time_min": 40},
}

# 주유 가격
FUEL_PRICE_PER_LITER = 2  # 코인/L


# ========================================
# 연료 시스템
# ========================================

def get_fuel(vehicle_id):
    """현재 연료량"""
    return morld.get_unit_prop(vehicle_id, "vehicle:fuel") or 0


def get_fuel_max(vehicle_id):
    """최대 연료량"""
    return morld.get_unit_prop(vehicle_id, "vehicle:fuel_max") or 0


def estimate_fuel_cost(vehicle_id, distance):
    """이동 거리에 대한 예상 연료 소비량

    연료탱크 손상 시 소비량 2배.
    """
    rate = morld.get_unit_prop(vehicle_id, "vehicle:fuel_rate") or 0
    tank_hp = get_part_hp(vehicle_id, "fuel_tank")
    tank_max = get_part_max_hp(vehicle_id, "fuel_tank")
    if tank_max and tank_max > 0 and tank_hp < tank_max * 0.5:
        rate *= 2.0
    return distance * rate


def can_travel(vehicle_id, distance):
    """이동 가능 여부 판정

    Returns:
        (bool, str): (가능 여부, 실패 사유)
    """
    status = morld.get_unit_prop(vehicle_id, "vehicle:status")
    if status == "disabled":
        return False, "기동 불가"
    if status == "wrecked":
        return False, "완파"

    fuel = get_fuel(vehicle_id)
    cost = estimate_fuel_cost(vehicle_id, distance)
    if fuel < cost:
        return False, "연료 부족"

    return True, ""


def consume_fuel(vehicle_id, distance):
    """연료 소비 (이동 실행 시 호출)

    Returns:
        float: 실제 소비량
    """
    cost = estimate_fuel_cost(vehicle_id, distance)
    current = get_fuel(vehicle_id)
    new_fuel = max(0, current - cost)
    morld.set_unit_prop(vehicle_id, "vehicle:fuel", new_fuel)
    return current - new_fuel


def refuel(vehicle_id, amount):
    """연료 충전

    Args:
        amount: 충전량 (리터)

    Returns:
        float: 실제 충전량
    """
    current = get_fuel(vehicle_id)
    fuel_max = get_fuel_max(vehicle_id)
    if fuel_max <= 0:
        return 0
    new_fuel = min(current + amount, fuel_max)
    actual = new_fuel - current
    if actual > 0:
        morld.set_unit_prop(vehicle_id, "vehicle:fuel", new_fuel)
    return actual


# ========================================
# 부품 시스템
# ========================================

def get_part_hp(vehicle_id, part_id):
    """부품 현재 HP"""
    return morld.get_unit_prop(vehicle_id, f"vehicle:part:{part_id}") or 0


def get_part_max_hp(vehicle_id, part_id):
    """부품 최대 HP"""
    return morld.get_unit_prop(vehicle_id, f"vehicle:part:{part_id}_max") or 0


def get_vehicle_parts_status(vehicle_id):
    """전 부품 상태 조회

    Returns:
        list of dict: [{part_id, name, hp, hp_max, essential, status}]
    """
    result = []
    for part_id, (name, essential, _weight) in VEHICLE_PARTS.items():
        hp_max = get_part_max_hp(vehicle_id, part_id)
        if not hp_max:
            continue  # 이 차량에 없는 부품 (예: 이륜차에 window 없음)
        hp = get_part_hp(vehicle_id, part_id)
        if hp <= 0:
            status = "파손"
        elif hp < hp_max * 0.5:
            status = "손상"
        else:
            status = "양호"
        result.append({
            "part_id": part_id, "name": name,
            "hp": hp, "hp_max": hp_max,
            "essential": essential, "status": status,
        })
    return result


def get_damaged_parts(vehicle_id):
    """손상/파손된 부품 목록"""
    return [p for p in get_vehicle_parts_status(vehicle_id)
            if p["status"] != "양호"]


# ========================================
# 데미지 시스템
# ========================================

def apply_damage(vehicle_id, damage):
    """차량에 데미지 적용 (랜덤 부품에 분배)

    Args:
        damage: 데미지량

    Returns:
        dict: {part_id, name, damage, new_hp} or None
    """
    import random

    # 살아있는 부품만
    alive = []
    weights = []
    for part_id, (name, _essential, weight) in VEHICLE_PARTS.items():
        hp_max = get_part_max_hp(vehicle_id, part_id)
        if not hp_max:
            continue
        hp = get_part_hp(vehicle_id, part_id)
        if hp > 0:
            alive.append(part_id)
            weights.append(weight)

    if not alive:
        return None

    # 가중 랜덤 선택
    target = random.choices(alive, weights=weights, k=1)[0]
    name = VEHICLE_PARTS[target][0]

    hp = get_part_hp(vehicle_id, target)
    new_hp = max(0, hp - damage)
    morld.set_unit_prop(vehicle_id, f"vehicle:part:{target}", new_hp)

    # 전체 HP 재계산
    _recalculate_total_hp(vehicle_id)

    # 상태 업데이트
    update_status(vehicle_id)

    return {"part_id": target, "name": name, "damage": hp - new_hp, "new_hp": new_hp}


def _recalculate_total_hp(vehicle_id):
    """부품 HP 합산으로 전체 HP 갱신"""
    total = 0
    for part_id in VEHICLE_PARTS:
        total += get_part_hp(vehicle_id, part_id)
    morld.set_unit_prop(vehicle_id, "vehicle:hp", total)


# ========================================
# 상태 판정
# ========================================

def update_status(vehicle_id):
    """차량 상태 재판정 (데미지/수리 후 호출)

    - 필수 부품 하나라도 HP 0 → disabled
    - 전체 HP 0 → wrecked
    - HP <= 50% → exposed (자동차/버스만)
    """
    hp = morld.get_unit_prop(vehicle_id, "vehicle:hp") or 0
    hp_max = morld.get_unit_prop(vehicle_id, "vehicle:hp_max") or 1

    # 완파
    if hp <= 0:
        morld.set_unit_prop(vehicle_id, "vehicle:status", "wrecked")
        morld.set_unit_prop(vehicle_id, "vehicle:exposed", 1)
        return

    # 기동 판정 (필수 부품)
    can_move = True
    for part_id, (name, essential, _w) in VEHICLE_PARTS.items():
        if not essential:
            continue
        part_max = get_part_max_hp(vehicle_id, part_id)
        if not part_max:
            continue  # 이 차량에 없는 부품
        if get_part_hp(vehicle_id, part_id) <= 0:
            can_move = False
            break

    if not can_move:
        morld.set_unit_prop(vehicle_id, "vehicle:status", "disabled")
    else:
        morld.set_unit_prop(vehicle_id, "vehicle:status", "normal")

    # 노출 판정 (오토바이는 항상 exposed, 별도 설정)
    vtype = morld.get_unit_prop(vehicle_id, "vehicle:type")
    if vtype and vtype != "motorcycle":
        if hp <= hp_max * 0.5:
            morld.set_unit_prop(vehicle_id, "vehicle:exposed", 1)
        else:
            # 수리로 HP 50% 초과 복구 시 보호 복원
            morld.set_unit_prop(vehicle_id, "vehicle:exposed", 0)


# ========================================
# 수리 시스템
# ========================================

def repair_part(vehicle_id, part_id):
    """부품 수리 (재료 체크 없이 로직만)

    Returns:
        dict: {part_id, name, old_hp, new_hp, hp_max} or None
    """
    recipe = REPAIR_RECIPES.get(part_id)
    if not recipe:
        return None

    hp = get_part_hp(vehicle_id, part_id)
    hp_max = get_part_max_hp(vehicle_id, part_id)
    if not hp_max:
        return None
    if hp >= hp_max:
        return None  # 이미 최대

    name = VEHICLE_PARTS[part_id][0]
    new_hp = min(hp_max, hp + recipe["restore"])
    morld.set_unit_prop(vehicle_id, f"vehicle:part:{part_id}", new_hp)

    _recalculate_total_hp(vehicle_id)
    update_status(vehicle_id)

    return {"part_id": part_id, "name": name,
            "old_hp": hp, "new_hp": new_hp, "hp_max": hp_max}


# ========================================
# 탑승자 조회
# ========================================

def get_passengers(vehicle_id):
    """차량 탑승자 unit_id 목록 (seated_by:* prop 기반)"""
    props = morld.get_unit_props(vehicle_id)
    if not props:
        return []
    passengers = []
    for key, val in props.items():
        if key.startswith("seated_by:") and val is not None and val > 0:
            passengers.append(val)
    return passengers


def get_seat_count(vehicle_id):
    """좌석 수"""
    return morld.get_unit_prop(vehicle_id, "vehicle:seats") or 0


def get_empty_seat_count(vehicle_id):
    """빈 좌석 수"""
    total = get_seat_count(vehicle_id)
    occupied = len(get_passengers(vehicle_id))
    return max(0, total - occupied)


def is_driver(vehicle_id, unit_id):
    """해당 유닛이 운전석에 앉아있는지"""
    driver = morld.get_unit_prop(vehicle_id, "seated_by:driver")
    return driver is not None and driver == unit_id


# ========================================
# 탑승 / 하차
# ========================================

# 좌석 이름 우선순위 (빈 좌석 탐색 시 사용)
_SEAT_PRIORITY = ["driver", "passenger1", "passenger2", "passenger3",
                  "front", "rear"]


def _get_seat_names(vehicle_id):
    """차량에 정의된 좌석 이름 목록 (seated_by:* prop에서 추출)"""
    props = morld.get_unit_props(vehicle_id)
    if not props:
        return []
    return [k.split(":", 1)[1] for k in props if k.startswith("seated_by:")]


def find_empty_seat(vehicle_id, prefer_driver=False):
    """빈 좌석 탐색

    Args:
        prefer_driver: True면 driver 우선, False면 passenger 우선

    Returns:
        str or None: 좌석 이름 (e.g. "driver", "passenger1")
    """
    seats = _get_seat_names(vehicle_id)
    if not seats:
        return None

    # 우선순위 정렬
    if prefer_driver:
        ordered = sorted(seats, key=lambda s: _SEAT_PRIORITY.index(s)
                         if s in _SEAT_PRIORITY else 99)
    else:
        # passenger 우선
        ordered = sorted(seats, key=lambda s: (
            0 if s != "driver" else 1,
            _SEAT_PRIORITY.index(s) if s in _SEAT_PRIORITY else 99
        ))

    for seat in ordered:
        val = morld.get_unit_prop(vehicle_id, f"seated_by:{seat}")
        if val is None or val <= 0:
            return seat
    return None


def mount(unit_id, vehicle_id, seat_name=None):
    """차량 탑승

    Args:
        unit_id: 탑승할 캐릭터
        vehicle_id: 차량 Object
        seat_name: 좌석 지정 (None이면 자동 배정, driver 우선)

    Returns:
        (bool, str): (성공, 실패 사유 또는 배정된 좌석명)
    """
    if not is_vehicle(vehicle_id):
        return False, "차량이 아님"

    # 좌석 결정
    if seat_name is None:
        seat_name = find_empty_seat(vehicle_id, prefer_driver=True)
    if seat_name is None:
        return False, "빈 좌석 없음"

    # 해당 좌석이 비어있는지 확인
    current = morld.get_unit_prop(vehicle_id, f"seated_by:{seat_name}")
    if current is not None and current > 0:
        return False, "좌석 점유"

    # C# sit_on 호출 (prop 설정 포함)
    result = morld.sit_on(unit_id, vehicle_id, seat_name)
    if not result:
        return False, "탑승 실패"

    return True, seat_name


def dismount(unit_id, vehicle_id):
    """차량 하차

    Args:
        unit_id: 하차할 캐릭터
        vehicle_id: 차량 Object

    Returns:
        bool: 성공 여부
    """
    # 탑승 중인지 확인
    passengers = get_passengers(vehicle_id)
    if unit_id not in passengers:
        return False

    # C# stand_up 호출
    morld.stand_up(unit_id)
    return True


def dismount_all(vehicle_id):
    """전원 하차

    Returns:
        list: 하차한 unit_id 목록
    """
    passengers = get_passengers(vehicle_id)
    for pid in passengers:
        morld.stand_up(pid)
    return passengers


def get_driver(vehicle_id):
    """운전자 unit_id 반환 (없으면 None)"""
    driver = morld.get_unit_prop(vehicle_id, "seated_by:driver")
    if driver is not None and driver > 0:
        return driver
    # front 좌석도 driver_seat 역할 (자전거 호환)
    front = morld.get_unit_prop(vehicle_id, "seated_by:front")
    if front is not None and front > 0:
        return front
    return None


def can_drive(vehicle_id):
    """운전 가능 여부 (운전자 있음 + driver_seat prop)"""
    has_seat = morld.get_unit_prop(vehicle_id, "driver_seat")
    if not has_seat:
        return False
    return get_driver(vehicle_id) is not None


# ========================================
# 조작 대상 전환 (control_target)
# ========================================

def set_control_target(player_id, target_id):
    """플레이어 조작 대상을 target_id로 전환

    탑승 시 차량 Object로, 시나리오03에서는 CCTV로 전환.
    C# 측에서 이 prop을 읽어 UI/카메라/입력을 라우팅.
    """
    morld.set_unit_prop(player_id, "control_target", target_id)


def get_control_target(player_id):
    """현재 조작 대상 (None이면 자기 자신)"""
    return morld.get_unit_prop(player_id, "control_target")


def clear_control_target(player_id):
    """조작 대상 해제 (자기 자신으로 복원)"""
    morld.set_unit_prop(player_id, "control_target", None)


def player_mount(player_id, vehicle_id, seat_name=None):
    """플레이어 차량 탑승 (mount + control_target 자동 전환)

    Returns:
        (bool, str): mount()와 동일
    """
    ok, result = mount(player_id, vehicle_id, seat_name)
    if ok and result == "driver":
        set_control_target(player_id, vehicle_id)
    return ok, result


def player_dismount(player_id, vehicle_id):
    """플레이어 차량 하차 (dismount + control_target 자동 해제)

    Returns:
        bool: dismount()와 동일
    """
    result = dismount(player_id, vehicle_id)
    if result:
        clear_control_target(player_id)
    return result


# ========================================
# 차량 이동 (Python 로직 — C# API 호출 전 검증)
# ========================================

def prepare_move(vehicle_id, distance):
    """이동 준비 (검증 + 연료 소비)

    실제 텔레포트는 C# API가 담당. 이 함수는 검증 + 연료만 처리.

    Returns:
        (bool, str, float): (성공, 메시지, 소비된 연료)
    """
    ok, reason = can_travel(vehicle_id, distance)
    if not ok:
        return False, reason, 0

    consumed = consume_fuel(vehicle_id, distance)
    return True, "", consumed


def vehicle_move_to(vehicle_id, dest_region, dest_location, distance):
    """차량 이동 실행 (검증 + 연료소비 + 위치변경)

    1. 이동 가능 판정 (상태/연료)
    2. 연료 소비
    3. 차량 Object 위치 변경 (C# vehicle_relocate)
    4. _location_objects 인덱스 갱신
    5. 이동시간 계산

    Args:
        vehicle_id: 차량 Object ID
        dest_region: 목적지 region_id
        dest_location: 목적지 location_id
        distance: 이동 거리

    Returns:
        dict: {success, message, fuel_consumed, travel_time_ms}
    """
    # 1. 운전자 확인
    if not can_drive(vehicle_id):
        return {"success": False, "message": "운전자가 없습니다.",
                "fuel_consumed": 0, "travel_time_ms": 0}

    # 2. 이동 가능 판정 + 연료 소비
    ok, reason, consumed = prepare_move(vehicle_id, distance)
    if not ok:
        return {"success": False, "message": reason,
                "fuel_consumed": 0, "travel_time_ms": 0}

    # 3. 현재 위치 조회
    loc = morld.get_unit_location(vehicle_id)
    if not loc:
        return {"success": False, "message": "차량 위치 불명",
                "fuel_consumed": consumed, "travel_time_ms": 0}
    old_region, old_location = loc[0], loc[1]

    # 4. C# API로 차량+탑승자 일괄 이동 (자동하차 없음)
    morld.vehicle_relocate(vehicle_id, dest_region, dest_location)

    # 5. Python 인덱스 갱신
    _relocate = _get_relocate_object()
    if _relocate:
        _relocate(vehicle_id, old_region, old_location,
                  dest_region, dest_location)

    # 6. 이동시간 계산 (속도 기반)
    speed = get_speed(vehicle_id)
    # 기본 도보 이동시간 = distance * 1분, 차량은 속도만큼 단축
    base_time_ms = distance * 60_000
    travel_time_ms = int(base_time_ms / max(speed, 0.1))

    return {"success": True,
            "message": f"목적지에 도착했습니다.",
            "fuel_consumed": consumed,
            "travel_time_ms": travel_time_ms}


# ========================================
# 유틸리티
# ========================================

def is_vehicle(unit_id):
    """차량 Object인지 판정 (vehicle:type prop 존재 여부)"""
    vtype = morld.get_unit_prop(unit_id, "vehicle:type")
    return vtype is not None


# relocate_object 함수 참조 (테스트에서 주입 가능)
_relocate_object_fn = None


def set_relocate_object(fn):
    """relocate_object 함수 주입 (테스트용)"""
    global _relocate_object_fn
    _relocate_object_fn = fn


def _get_relocate_object():
    """relocate_object 함수 반환 (주입 우선, 없으면 assets.objects에서 가져옴)"""
    if _relocate_object_fn:
        return _relocate_object_fn
    try:
        from assets.objects import relocate_object
        return relocate_object
    except (ImportError, AttributeError):
        return None


def get_speed(vehicle_id):
    """차량 속도 배율"""
    return morld.get_unit_prop(vehicle_id, "vehicle:speed") or 1.0


def find_nearby_vehicle(unit_id):
    """유닛과 같은 location에 있는 차량 ID 반환 (첫 번째)

    플레이어가 탑승 중이면 탑승 차량 우선 반환.

    Returns:
        int or None: 차량 unit_id
    """
    # 탑승 중인 차량 확인
    props = morld.get_unit_props(unit_id)
    if props:
        for key in props:
            if key.startswith("seated_on:"):
                target_id = int(key.split(":", 1)[1])
                if is_vehicle(target_id):
                    return target_id

    # 같은 location의 오브젝트 탐색
    loc = morld.get_unit_location(unit_id)
    if not loc:
        return None
    objects = morld.get_units_at_location(loc[0], loc[1], "object")
    for obj_id in objects:
        if is_vehicle(obj_id):
            return obj_id
    return None


# ========================================
# 주유 시스템
# ========================================

# 제리캔 연료량
JERRYCAN_FUEL = 10  # 리터

# 주유소 주유 시간 (밀리초)
PUMP_REFUEL_TIME_MS = 5 * 60_000   # 5분
JERRYCAN_REFUEL_TIME_MS = 2 * 60_000  # 2분


def calculate_refuel_cost(vehicle_id):
    """주유소 주유 비용 계산

    Returns:
        (float, int): (필요량L, 비용코인) — 이미 만탱이면 (0, 0)
    """
    fuel = get_fuel(vehicle_id)
    fuel_max = get_fuel_max(vehicle_id)
    needed = fuel_max - fuel
    if needed <= 0:
        return 0, 0
    cost = int(needed * FUEL_PRICE_PER_LITER)
    return needed, cost


def refuel_from_pump(vehicle_id):
    """주유소에서 만탱 주유 (코인 체크 없이 로직만)

    Returns:
        dict: {success, amount, cost} or None (이미 만탱)
    """
    needed, cost = calculate_refuel_cost(vehicle_id)
    if needed <= 0:
        return None
    actual = refuel(vehicle_id, needed)
    return {"success": True, "amount": actual, "cost": cost}


def refuel_from_jerrycan(vehicle_id, jerrycan_fuel=None):
    """제리캔으로 주유

    Args:
        jerrycan_fuel: 제리캔 연료량 (None이면 기본 JERRYCAN_FUEL)

    Returns:
        dict: {amount, remaining_jerrycan_fuel}
    """
    if jerrycan_fuel is None:
        jerrycan_fuel = JERRYCAN_FUEL
    fuel = get_fuel(vehicle_id)
    fuel_max = get_fuel_max(vehicle_id)
    space = fuel_max - fuel
    transfer = min(jerrycan_fuel, space)
    if transfer <= 0:
        return {"amount": 0, "remaining_jerrycan_fuel": jerrycan_fuel}
    refuel(vehicle_id, transfer)
    return {"amount": transfer,
            "remaining_jerrycan_fuel": jerrycan_fuel - transfer}


def parse_interior_key(key_str):
    """'R{n}:L{n}' 형식 파싱 → (region_id, location_id) or None"""
    if not key_str:
        return None
    try:
        parts = key_str.split(":")
        r = int(parts[0][1:])  # "R4" → 4
        l = int(parts[1][1:])  # "L10" → 10
        return (r, l)
    except (IndexError, ValueError):
        return None
