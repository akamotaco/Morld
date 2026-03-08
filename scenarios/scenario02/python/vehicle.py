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


# ========================================
# 유틸리티
# ========================================

def is_vehicle(unit_id):
    """차량 Object인지 판정 (vehicle:type prop 존재 여부)"""
    vtype = morld.get_unit_prop(unit_id, "vehicle:type")
    return vtype is not None


def get_speed(vehicle_id):
    """차량 속도 배율"""
    return morld.get_unit_prop(vehicle_id, "vehicle:speed") or 1.0


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
