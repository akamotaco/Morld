# 차량 시스템 설계

> **상태: Phase 9 마이그레이션 완료 (Region 1 폐기, Object 기반 전환)**
>
> 기존 Region 방식(OldCar)을 폐기하고 Object 중심으로 재설계.
>
> **구현 이력:**
> - Phase 1: 차량 유틸리티 모듈 + relocate_object + 테스트 44개
> - Phase 2: 탑승/하차 시스템 + Vehicle 기반 클래스 + 테스트 57개
> - Phase 3: control_target + vehicle_move_to + 테스트 69개
> - Phase 4: 연료 시스템 (주유소 + 제리캔) + 테스트 81개
> - Phase 5: 전투 연동 (부품 데미지 + 노출 + 탑승자 피격) + 테스트 92개
> - Phase 6: 수리 시스템 (재료 체크/소비 + 부품 선택 UI) + 테스트 102개
> - Phase 8: NPC 운전 Activity (5-phase 핸들러 + 도보 fallback) + 테스트 112개
> - Phase 9: 마이그레이션 (OldCar→SedanCar, Region 1 폐기, C# API 교체) + 테스트 118개

---

## 1. 개요

차량은 **Object** 기반 탈것으로, 플레이어/NPC가 탑승하여 실외 Location 간 이동에 사용한다.

**차량 분류:**

| 분류 | 예시 | 구조 | 노출 | 좌석 |
|------|------|------|------|------|
| 이륜 | 오토바이, 자전거 | Object only | 항상 노출 | 1~2 |
| 소형 | 승용차 | Object only | HP 50% 이하 시 노출 | 2~4 |
| 대형 | 버스, 수송차량 | Object + Location | HP 50% 이하 시 노출 | 운전석 2 + 내부 다수 |

---

## 2. 차량 Object 구조

### 2.1 Props

```python
# 공통
"vehicle:type"        # "motorcycle" | "car" | "bus"
"vehicle:seats"       # 최대 탑승 인원 (Object 직접 탑승분)
"vehicle:speed"       # 이동속도 배율 (1.0 = 도보, 3.0 = 3배속)
"vehicle:exposed"     # 0=차체 보호, 1=탑승자 노출
"driver_seat"         # 1 (기존 C# CanDrive 연동)

# 내구도
"vehicle:hp"          # 현재 HP (전체)
"vehicle:hp_max"      # 최대 HP
"vehicle:status"      # "normal" | "disabled" | "wrecked"

# 부품별 HP
"vehicle:part:engine"         # 엔진 HP
"vehicle:part:engine_max"     # 엔진 최대 HP
"vehicle:part:tire"           # 타이어 HP
"vehicle:part:tire_max"
"vehicle:part:body"           # 차체 HP
"vehicle:part:body_max"
"vehicle:part:window"         # 유리창 HP (이륜은 없음)
"vehicle:part:window_max"
"vehicle:part:fuel_tank"      # 연료탱크 HP
"vehicle:part:fuel_tank_max"

# 연료
"vehicle:fuel"        # 현재 연료 (리터)
"vehicle:fuel_max"    # 최대 용량 (리터)
"vehicle:fuel_rate"   # 소비량 (리터/이동 1단위거리)

# 대형 차량 전용
"vehicle:interior"    # 연결된 내부 Location ("R{n}:L{n}" 형식)

# 탑승자 (기존 seated_by 패턴)
"seated_by:driver"     # 운전자 unit_id (-1=빈 좌석)
"seated_by:passenger1" # 동승자 1
"seated_by:passenger2" # 동승자 2 (좌석 수에 따라)
```

### 2.2 Actions

```python
actions = [
    "sit@driver",                    # 운전석 탑승
    "sit@passenger1",               # 동승석 탑승
    "call:drive:운전@seated",        # 탑승 중에만 표시
    "call:look:살펴보기",            # 인벤토리 (트렁크)
    "call:store:보관하기@near",      # 아이템 보관
    "call:inspect:점검@near",       # 상태 확인
    "call:repair:수리@near",        # 수리
    "call:refuel:주유@near",        # 제리캔으로 주유
]
```

### 2.3 예시: 오토바이

```python
class Motorcycle(Vehicle):
    unique_id = "motorcycle_01"
    name = "오토바이"
    position_x = 80
    props = {
        "vehicle:type": "motorcycle",
        "vehicle:seats": 2,
        "vehicle:speed": 4.0,
        "vehicle:exposed": 1,       # 항상 노출
        "driver_seat": 1,
        "vehicle:hp": 80,
        "vehicle:hp_max": 80,
        "vehicle:status": "normal",
        "vehicle:part:engine": 30,
        "vehicle:part:engine_max": 30,
        "vehicle:part:tire": 25,
        "vehicle:part:tire_max": 25,
        "vehicle:part:body": 15,
        "vehicle:part:body_max": 15,
        "vehicle:part:fuel_tank": 10,
        "vehicle:part:fuel_tank_max": 10,
        "vehicle:fuel": 20,
        "vehicle:fuel_max": 20,
        "vehicle:fuel_rate": 0.5,    # 이동 1단위당 0.5L
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
    }
```

### 2.4 예시: 승용차

```python
class OldCar(Vehicle):
    unique_id = "old_car"
    name = "낡은 승용차"
    position_x = 120
    props = {
        "vehicle:type": "car",
        "vehicle:seats": 4,
        "vehicle:speed": 3.0,
        "vehicle:exposed": 0,       # 차체 보호
        "driver_seat": 1,
        "vehicle:hp": 200,
        "vehicle:hp_max": 200,
        "vehicle:status": "normal",
        "vehicle:part:engine": 60,
        "vehicle:part:engine_max": 60,
        "vehicle:part:tire": 40,
        "vehicle:part:tire_max": 40,
        "vehicle:part:body": 60,
        "vehicle:part:body_max": 60,
        "vehicle:part:window": 20,
        "vehicle:part:window_max": 20,
        "vehicle:part:fuel_tank": 20,
        "vehicle:part:fuel_tank_max": 20,
        "vehicle:fuel": 40,
        "vehicle:fuel_max": 40,
        "vehicle:fuel_rate": 0.3,
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
        "seated_by:passenger2": -1,
        "seated_by:passenger3": -1,
    }
```

### 2.5 예시: 버스 (대형)

```python
class OldBus(Vehicle):
    unique_id = "old_bus"
    name = "낡은 버스"
    position_x = 160
    props = {
        "vehicle:type": "bus",
        "vehicle:seats": 2,          # 운전석 직접 탑승분
        "vehicle:speed": 2.0,
        "vehicle:exposed": 0,
        "driver_seat": 1,
        "vehicle:hp": 300,
        "vehicle:hp_max": 300,
        "vehicle:status": "normal",
        # 부품 생략 (패턴 동일)
        "vehicle:fuel": 80,
        "vehicle:fuel_max": 80,
        "vehicle:fuel_rate": 0.8,    # 대형 = 연비 나쁨
        "vehicle:interior": "R4:L10", # 내부 Location 연결
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
    }
```

---

## 3. 이동 시스템

### 3.1 차량 이동 흐름

```
플레이어가 이동 명령 발행
  ↓
탑승 상태 감지 (seated_on + driver_seat)
  ↓                           ↓
[탑승 중]                    [도보]
  ↓                           ↓
차량 이동 가능 체크            기존 이동 로직
  ├─ 목적지 is_indoor? → 불가
  ├─ vehicle:status == "disabled"? → 불가
  ├─ vehicle:fuel <= 0? → 불가
  └─ 통과
  ↓
이동 실행
  ├─ 이동시간 = 거리 / (BaseSpeed × vehicle:speed)
  ├─ 연료소비 = 거리 × vehicle:fuel_rate
  ├─ 차량 Object 텔레포트
  ├─ 운전석 탑승자 텔레포트
  └─ 대형: 내부 Location Gate 재연결
```

### 3.2 차량 X 좌표

차량은 Location 내에서 X 좌표를 가진다.

- 이동 후 목적지 Location의 Gate 근처 X에 배치
- 차량이 큰 경우 (버스) 공간 점유 고려 가능 (나중)
- 탑승자의 X 좌표는 차량 X에 고정

### 3.3 탑승자 동시 이동

```python
def vehicle_move_to(vehicle_id, dest_r, dest_l, dest_x):
    """차량 + 탑승자 + 내부 Location 일괄 이동"""
    # 0. 연료 체크 (예상 소비량 > 잔량이면 출발 불가)
    current_fuel = get_prop(vehicle_id, "vehicle:fuel")
    distance = calculate_distance(vehicle_id, dest_r, dest_l)
    fuel_cost = distance * get_prop(vehicle_id, "vehicle:fuel_rate")
    if current_fuel < fuel_cost:
        return False, "연료 부족"

    # 1. 연료 소비
    set_prop(vehicle_id, "vehicle:fuel", current_fuel - fuel_cost)

    # 2. 차량 Object 이동
    morld.set_unit_location(vehicle_id, dest_r, dest_l, dest_x)
    update_location_index(vehicle_id, dest_r, dest_l)

    # 3. 직접 탑승자 (seated_by:*) 이동
    for seat_prop in get_seat_props(vehicle_id):
        pid = get_prop(vehicle_id, seat_prop)
        if pid and pid > 0:
            morld.set_unit_location(pid, dest_r, dest_l, dest_x)

    # 4. 대형 차량: 내부 Location Gate 재연결
    interior = get_prop(vehicle_id, "vehicle:interior")
    if interior:
        int_r, int_l = parse_location_key(interior)
        update_gate_connection(int_r, int_l, dest_r, dest_l, dest_x)
        # 내부 탑승자는 이동 불필요 (Location 안에 있으므로)
```

### 3.4 실외 제한

```python
def get_vehicle_destinations(vehicle_id):
    """차량으로 갈 수 있는 목적지 (실외만)"""
    current_loc = morld.get_unit_location(vehicle_id)
    all_dests = get_reachable_locations(current_loc)
    return [d for d in all_dests if not d["is_indoor"]]
```

기존 C# `GetDrivableDestinations()`에 이미 실외 필터링 로직 있음.

---

## 4. 연료 시스템

### 4.1 연료 소비

- 이동 시마다 `거리 × vehicle:fuel_rate` 만큼 소비
- 정차 중에는 연료 소비 없음
- **출발 전 연료 체크**: 목적지까지의 예상 소비량을 계산, 잔량이 부족하면 출발 불가
- 연료 부족 시 UI에 "연료가 부족합니다" 표시

### 4.2 주유 방법

#### A. 주유소 직접 주유

```
주유소(R2:L1)에 차량으로 이동
  → GasStationPump 오브젝트와 상호작용
  → "주유" 액션 → 연료 충전 (코인 소비)
```

```python
class GasStationPump(Object):
    unique_id = "gas_pump"
    name = "주유기"
    props = {"fuel:supply": 1}   # 주유 가능 표시
    actions = [
        "call:refuel_vehicle:주유@near",
        "call:buy_jerrycan:제리캔 구매@near",
    ]

    def refuel_vehicle(self):
        """차량 직접 주유 (주유소에서)"""
        # 근처 차량 탐색
        vehicle = find_nearby_vehicle(self.instance_id)
        if not vehicle:
            yield ui.dialog("주유", "근처에 차량이 없습니다.")
            return

        fuel = get_prop(vehicle, "vehicle:fuel")
        fuel_max = get_prop(vehicle, "vehicle:fuel_max")
        if fuel >= fuel_max:
            yield ui.dialog("주유", "연료가 가득 찼습니다.")
            return

        needed = fuel_max - fuel
        cost = int(needed * FUEL_PRICE_PER_LITER)  # 리터당 가격

        choice = yield ui.confirm(f"주유 ({needed:.0f}L, {cost} 코인)")
        if choice:
            if not has_coins(player_id, cost):
                yield ui.dialog("주유", "코인이 부족합니다.")
                return
            spend_coins(player_id, cost)
            set_prop(vehicle, "vehicle:fuel", fuel_max)
            morld.advance_time_des(5 * 60000)  # 5분 소요
            yield ui.dialog("주유", "주유 완료.")
```

#### B. 제리캔 주유 (어디서든)

```python
class JerryCan(Item):
    unique_id = "jerry_can"
    name = "제리캔"
    category = "tool"
    props = {}
    passive_props = {}
    equip_props = {}
    value = 30
    actions = [
        "take@container",
        "call:use:사용@inventory",
    ]

    def __init__(self):
        super().__init__()
        self.fuel_amount = 10  # 10L 분량

    def use(self):
        """인벤토리에서 사용 → 근처 차량에 주유"""
        vehicle = find_nearby_vehicle_for_player()
        if not vehicle:
            yield ui.dialog("제리캔", "근처에 차량이 없습니다.")
            return

        fuel = get_prop(vehicle, "vehicle:fuel")
        fuel_max = get_prop(vehicle, "vehicle:fuel_max")
        added = min(self.fuel_amount, fuel_max - fuel)
        set_prop(vehicle, "vehicle:fuel", fuel + added)

        morld.remove_item(player_id, self.instance_id, 1)  # 소비
        morld.advance_time_des(2 * 60000)  # 2분 소요
        yield ui.dialog("제리캔", f"{added:.0f}L 주유 완료.")
```

#### C. 주유소에서 제리캔 구매

```python
def buy_jerrycan(self):
    """제리캔 구매"""
    cost = 20  # 코인
    if not has_coins(player_id, cost):
        yield ui.dialog("구매", "코인이 부족합니다.")
        return
    spend_coins(player_id, cost)
    # 제리캔 아이템 생성 → 플레이어 인벤토리
    jerry = JerryCan()
    jerry_id = morld.create_id("item")
    jerry.instantiate(jerry_id)
    morld.give_item(player_id, jerry_id, 1)
    yield ui.dialog("구매", "제리캔을 구매했습니다.")
```

### 4.3 연료탱크 파손

연료탱크(`vehicle:part:fuel_tank`) HP가 0이면:
- 연료 누출: 매 이동마다 추가 소비 × 2
- 또는: 연료탱크 파손 시 잔여 연료 전부 유실

```python
def consume_fuel(vehicle_id, distance):
    rate = get_prop(vehicle_id, "vehicle:fuel_rate")
    tank_hp = get_prop(vehicle_id, "vehicle:part:fuel_tank") or 0
    tank_max = get_prop(vehicle_id, "vehicle:part:fuel_tank_max") or 1

    # 연료탱크 손상 → 소비 증가
    if tank_hp < tank_max * 0.5:
        rate *= 2.0  # 누출로 인한 2배 소비

    cost = distance * rate
    current = get_prop(vehicle_id, "vehicle:fuel")
    set_prop(vehicle_id, "vehicle:fuel", max(0, current - cost))
```

---

## 5. 전투 연동

### 5.1 공격 대상 판정

```
공격 대상이 차량 Object인 경우:
  ├─ vehicle:exposed == 1 (오토바이 or 파손 차)
  │     → 탑승자에게 직접 데미지 (랜덤 선택)
  │
  └─ vehicle:exposed == 0 (보호 상태)
        → 차체에 데미지 (부품 분배)
        → HP 50% 이하 → vehicle:exposed = 1 전환
```

### 5.2 부품별 데미지 분배

```python
_VEHICLE_PARTS = {
    #  part_id      (이름,     HP비중, 기동필수, 피격가중치)
    "engine":       ("엔진",    0.30,  True,    0.15),
    "tire":         ("타이어",  0.20,  True,    0.25),
    "body":         ("차체",    0.30,  False,   0.35),
    "window":       ("유리창",  0.10,  False,   0.15),
    "fuel_tank":    ("연료탱크", 0.10, True,    0.10),
}

def apply_vehicle_damage(vehicle_id, damage):
    alive_parts = [p for p in _VEHICLE_PARTS if get_part_hp(vehicle_id, p) > 0]
    if not alive_parts:
        return

    # 가중 랜덤으로 피격 부품 선택
    weights = [_VEHICLE_PARTS[p][3] for p in alive_parts]
    target = random.choices(alive_parts, weights=weights, k=1)[0]

    part_hp = get_part_hp(vehicle_id, target)
    new_hp = max(0, part_hp - damage)
    set_part_hp(vehicle_id, target, new_hp)

    # 전체 HP 재계산
    total = sum(get_part_hp(vehicle_id, p) for p in _VEHICLE_PARTS)
    set_prop(vehicle_id, "vehicle:hp", total)

    update_vehicle_status(vehicle_id)
```

### 5.3 상태 전환

```python
def update_vehicle_status(vehicle_id):
    hp = get_prop(vehicle_id, "vehicle:hp")
    hp_max = get_prop(vehicle_id, "vehicle:hp_max")
    vtype = get_prop(vehicle_id, "vehicle:type")

    # 노출 판정 (자동차/버스: HP 50% 이하에서 노출)
    if vtype != "motorcycle":
        if hp <= hp_max * 0.5:
            set_prop(vehicle_id, "vehicle:exposed", 1)
        # 수리 후 복구는 별도 로직 (body+window 모두 50% 이상)

    # 기동 판정 (필수 부품 하나라도 0이면 불가)
    can_move = True
    for part_id, (name, ratio, essential, weight) in _VEHICLE_PARTS.items():
        if essential and get_part_hp(vehicle_id, part_id) <= 0:
            can_move = False
            break

    if not can_move:
        set_prop(vehicle_id, "vehicle:status", "disabled")
    elif hp <= 0:
        set_prop(vehicle_id, "vehicle:status", "wrecked")
    else:
        set_prop(vehicle_id, "vehicle:status", "normal")
```

---

## 6. 수리 시스템

### 6.1 수리 레시피

```python
_REPAIR_RECIPES = {
    "engine":    {"materials": {"iron_ore": 2, "copper_ore": 1}, "restore": 30, "time_min": 60},
    "tire":      {"materials": {"cloth": 2, "cord": 1},         "restore": 25, "time_min": 30},
    "body":      {"materials": {"iron_ore": 1, "plank": 2},     "restore": 30, "time_min": 45},
    "window":    {"materials": {"copper_ore": 1},                "restore": 20, "time_min": 20},
    "fuel_tank": {"materials": {"iron_ore": 1, "copper_ore": 1}, "restore": 20, "time_min": 40},
}
```

### 6.2 수리 액션

```python
def repair(self):
    """차량 수리 — 부품 선택 → 재료 확인 → 수리"""
    damaged = []
    for part_id, (name, ratio, essential, weight) in _VEHICLE_PARTS.items():
        hp = get_part_hp(self.instance_id, part_id)
        hp_max = get_part_max(self.instance_id, part_id)
        if hp_max and hp < hp_max:
            status = "파손" if hp <= 0 else "손상"
            damaged.append((part_id, name, hp, hp_max, status))

    if not damaged:
        yield ui.dialog("수리", "수리할 부분이 없습니다.")
        return

    # 부품 선택 메뉴
    options = [f"{name} [{status}] ({hp}/{hp_max})" for _, name, hp, hp_max, status in damaged]
    choice = yield ui.select("수리할 부품", options)
    if choice is None:
        return

    part_id = damaged[choice][0]
    recipe = _REPAIR_RECIPES[part_id]

    # 도구 체크 (SmallToolbox 필요)
    if not has_item(player_id, "small_toolbox"):
        yield ui.dialog("수리", "공구함이 필요합니다.")
        return

    # 재료 체크
    for mat_uid, count in recipe["materials"].items():
        if not has_item_count(player_id, mat_uid, count):
            yield ui.dialog("수리", f"재료 부족: {mat_uid} × {count}")
            return

    # 재료 소비 + 수리
    for mat_uid, count in recipe["materials"].items():
        consume_item(player_id, mat_uid, count)

    hp = get_part_hp(self.instance_id, part_id)
    hp_max = get_part_max(self.instance_id, part_id)
    new_hp = min(hp_max, hp + recipe["restore"])
    set_part_hp(self.instance_id, part_id, new_hp)

    update_vehicle_status(self.instance_id)
    morld.advance_time_des(recipe["time_min"] * 60000)
    yield ui.dialog("수리", f"{damaged[choice][1]} 수리 완료. ({new_hp}/{hp_max})")
```

### 6.3 차량 점검 (상태 확인)

```python
def inspect(self):
    """차량 상태 표시"""
    lines = []
    hp = get_prop(self.instance_id, "vehicle:hp")
    hp_max = get_prop(self.instance_id, "vehicle:hp_max")
    status = get_prop(self.instance_id, "vehicle:status")
    fuel = get_prop(self.instance_id, "vehicle:fuel")
    fuel_max = get_prop(self.instance_id, "vehicle:fuel_max")

    status_label = {"normal": "정상", "disabled": "기동 불가", "wrecked": "완파"}
    lines.append(f"상태: {status_label.get(status, status)}")
    lines.append(f"내구도: {hp}/{hp_max}")
    lines.append(f"연료: {fuel:.0f}/{fuel_max:.0f}L")
    lines.append("")

    for part_id, (name, ratio, essential, weight) in _VEHICLE_PARTS.items():
        p_hp = get_part_hp(self.instance_id, part_id)
        p_max = get_part_max(self.instance_id, part_id)
        if p_max is None:
            continue  # 이 차량에 없는 부품 (이륜: window 없음)
        if p_hp <= 0:
            tag = "파손"
        elif p_hp < p_max * 0.5:
            tag = "손상"
        else:
            tag = "양호"
        ess = " [필수]" if essential else ""
        lines.append(f"  {name}{ess}: {tag} ({p_hp}/{p_max})")

    yield ui.dialog(f"{self.name} 점검", "\n".join(lines))
```

---

## 7. 대형 차량 — 내부 Location

### 7.1 구조

```
대형 차량 Object (운전석, 외부에 위치)
  ↕ Gate 연결
내부 Location (별도 Region 내, is_indoor=True)
  ├── 좌석 Object들 (승객용)
  ├── 화물칸 Object (storage:material 등)
  └── 기타 오브젝트
```

### 7.2 Gate 재연결

차량이 이동하면 내부 Location의 Gate 연결점을 새 외부 Location으로 변경:

```python
def update_gate_connection(interior_r, interior_l, new_ext_r, new_ext_l, new_ext_x):
    """내부 Location의 Gate가 가리키는 외부 Location을 변경"""
    gate_id = find_gate_between(interior_r, interior_l, ANY)
    if gate_id:
        # C# API로 Gate 연결점 변경
        morld.update_region_gate(gate_id, new_ext_r, new_ext_l, new_ext_x)
```

### 7.3 탑승 vs 진입

- **탑승** (sit 액션): 차량 Object의 좌석에 앉음 → 운전 가능
- **진입** (Gate 이동): 내부 Location으로 이동 → 내부 오브젝트 상호작용
- 내부에 있는 캐릭터도 차량 이동 시 함께 이동 (Location 자체가 이동하므로)

---

## 8. NPC 운전

> **상태: 구현 완료** — `think/activities/drive.py`, 테스트 11개

### 8.1 Activity Phase

```
idle → going_to_vehicle → mounting → driving → dismounting → idle
```

### 8.2 핸들러 구조

```python
# think/activities/drive.py
# 스케줄 entry: {"activity": "운전", "dest_region": int, "dest_location": int, "distance": float}

def handle_drive(agent, entry):
    phase = agent._activity_phase
    if phase == "idle":       _phase_idle(agent, entry)
    elif phase == "going_to_vehicle": _phase_going_to_vehicle(agent)
    elif phase == "mounting":  _phase_mounting(agent)
    elif phase == "driving":   _phase_driving(agent, entry)
    elif phase == "dismounting": _phase_dismounting(agent)
```

### 8.3 idle → 차량 탐색 로직

1. 목적지 없음 → 대기
2. 이미 목적지 → 대기
3. `find_nearby_vehicle()` → 차량 없음 → **도보 fallback** (`_move_to`)
4. 차량 `disabled`/`wrecked` → 도보 fallback
5. `can_travel()` 연료 부족 → 도보 fallback
6. 차량과 같은 location → 즉시 `mounting`
7. 차량이 다른 location → `going_to_vehicle` (이동)

### 8.4 도보 Fallback

차량 사용 불가 시 `_move_to(dest, "이동")`으로 자연스럽게 도보 이동.
NPC 스케줄에서 `"운전"` activity를 지정해도 차량 없으면 도보로 동작.

---

## 9. 주유소 (R2:L1)

기존 도시 `gas_station` Location(R2:L1)에 주유기 오브젝트 배치.

### 9.1 오브젝트

```python
class GasStationPump(Object):
    unique_id = "gas_pump"
    name = "주유기"
    position_x = 100
    props = {"fuel:supply": 1}
    actions = [
        "call:refuel_vehicle:차량 주유@near",
        "call:buy_jerrycan:제리캔 구매@near",
        "call:fill_jerrycan:제리캔 충전@near",
    ]
```

### 9.2 제리캔 충전

빈 제리캔을 주유소에서 다시 채울 수 있음:

```python
def fill_jerrycan(self):
    """빈 제리캔 충전"""
    empty_can = find_empty_jerrycan(player_id)
    if not empty_can:
        yield ui.dialog("충전", "빈 제리캔이 없습니다.")
        return
    cost = 15  # 구매보다 저렴
    if not has_coins(player_id, cost):
        yield ui.dialog("충전", "코인이 부족합니다.")
        return
    spend_coins(player_id, cost)
    set_jerrycan_fuel(empty_can, 10)  # 10L 충전
    morld.advance_time_des(2 * 60000)
    yield ui.dialog("충전", "제리캔 충전 완료.")
```

---

## 10. C# 변경 범위

| 파일 | 변경 내용 |
|------|----------|
| `action_system.cs` | 탑승 상태 이동 분기: 속도 적용, 실외 필터, 연료 체크 |
| `data_api.cs` | `vehicle_move_to()` API — Object+탑승자 텔레포트+Gate 재연결 |
| `data_api.cs` | `update_region_gate()` API — Gate 연결점 동적 변경 |
| `MetaActionHandler` | 탑승 중 이동 UI에서 실내 목적지 제외 |
| combat 관련 | 차량 대상 공격 → exposed 분기 → 부품 데미지 |

---

## 11. Python 파일 구조

| 파일 | 역할 |
|------|------|
| `assets/objects/vehicles.py` | Vehicle 기반 클래스 + 구체 차량 (Motorcycle, Car, Bus) |
| `assets/items/tools.py` | JerryCan 아이템 |
| `assets/objects/city_objects.py` (또는 별도) | GasStationPump 오브젝트 |
| `assets/locations/vehicles.py` | 대형 차량 내부 Location (재활용) |
| `think/activities/drive.py` | NPC 운전 Activity 핸들러 |
| `vehicle.py` (신규, 모듈) | 차량 유틸: 이동/연료소비/데미지/수리 공용 함수 |
| `combat.py` | 차량 전투 연동 (데미지 분배/노출 판정) |

---

## 12. 기존 차량 코드 마이그레이션

현재 Region 방식의 OldCar를 Object 방식으로 전환:

| 현재 | 변경 후 |
|------|---------|
| Region 1 (차량) | **삭제** |
| OldCar Location (R1:L0) | **삭제** |
| CarDriverSeat Object | OldCar Vehicle Object에 통합 |
| CarPassengerSeat Object | OldCar Vehicle Object에 통합 |
| CarTrunk Object | OldCar Vehicle Object 인벤토리로 대체 |
| Bicycle Object | Vehicle 기반으로 리팩토링 |
| Gate R2:L4 ↔ R1:L0 | **삭제** (차량이 Object로 주차장에 직접 배치) |

---

## 13. 조작 방식 — 조작 대상 전환 (control_target)

차량 탑승 시 플레이어의 조작 대상이 캐릭터에서 차량 Object로 전환된다.
이 패턴은 시나리오 03의 원격 분대 조작(CCTV 할당)에도 재활용된다.

```
현재:    플레이어 → [캐릭터] → 이동/액션/인벤토리
차량:    플레이어 → [차량 Object] ←연결→ 운전자(캐릭터)
시나03:  플레이어 → [CCTV Object] ←연결→ 분대들
```

- 탑승 → control_target을 차량으로 전환
- 하차 → control_target을 캐릭터로 복원
- C# 측에서 control_target prop 기반으로 UI/카메라/이동 대상 결정

> **C# 선행 작업 필요.** Python 로직은 먼저 구현 가능.

---

## 14. 구현 이슈

| # | 이슈 | 심각도 | 해결 방향 | 상태 |
|---|------|--------|----------|------|
| 1 | `_location_objects` 갱신 | 높음 | `relocate_object()` 추가 | **완료** |
| 2 | 전투 Object 미지원 | 중간 | 차량 전용 데미지 함수 분리 | 대기 |
| 3 | 조작 방식 | 설계 | control_target 전환 방식 채택 | **확정** |
| 4 | `set_unit_location` 자동 하차 | 높음 | C# 전용 API 필수 | 대기 |
| 5 | Gate 연결점 변경 API | 중간 | ExecuteDrive 로직 일반화 | 대기 |
| 6 | 탑승 중 전투 | 설계 | 후순위 (미정) | 대기 |
| 7 | NPC 차량 판단 | 낮음 | 스케줄 명시 | 대기 |

---

## 15. 구현 순서

| Phase | 내용 | 의존성 | 상태 |
|-------|------|--------|------|
| 1 | 차량 유틸 모듈 + relocate_object + 테스트 | 없음 | **완료** |
| 2 | 탑승/하차 시스템 (seated_by 확장) | Phase 1 | **완료** |
| 3 | control_target + 이동 API (Python 완료, C# 대기) | Phase 2 | **Python 완료** |
| 4 | 연료 시스템 (소비 + 주유소 + 제리캔) | Phase 3 | **완료** |
| 5 | 전투 연동 (부품 데미지 + 노출) | Phase 1 | **완료** |
| 6 | 수리 시스템 | Phase 5 | **완료** |
| 7 | 대형 차량 (내부 Location + Gate 재연결) | Phase 3 | 대기 |
| 8 | NPC 운전 Activity | Phase 3 | **완료** |
| 9 | 기존 코드 마이그레이션 | Phase 1~4 | **완료** |

---

## 16. 구현 파일 현황

| 파일 | 역할 | 상태 |
|------|------|------|
| `vehicle.py` | 차량 유틸: 연료/부품/수리/탑승/이동/control_target/주유 | **구현** |
| `assets/objects/__init__.py` | `relocate_object()` + Vehicle/GasStationPump import | **구현** |
| `tests/test_vehicle.py` | 차량 유틸 테스트 118개 (13파트) | **구현** |
| `assets/objects/vehicles.py` | Vehicle 기반 클래스 + drive/inspect/refuel/repair + GasStationPump | **구현** |
| `assets/items/tools.py` | JerryCan 아이템 | **구현** |
| `assets/locations/vehicles.py` | 레거시 OldCar Location (폐기 예정) | **폐기** |
| `think/activities/drive.py` | NPC 운전 Activity 핸들러 | **구현** |
| `assets/locations/city.py` | 주차장에 SedanCar 배치 | **구현** |
| `scripts/system/action_system.cs` | GetVehicleDestinations + VehicleRelocate | **구현** |
| `scripts/system/script_system_data_api.cs` | get_vehicle_destinations + vehicle_relocate API | **구현** |
| `combat.py` | 차량 전투 연동 (execute_attack 차량 분기) | **구현** |

---

## 17. 시나리오03 호환성

- `vehicle:*` prop 없으면 일반 Object로 동작 (무해)
- `driver_seat` prop은 기존 C# 연동 유지
- NPC `_vehicle_capable` 속성 없으면 차량 사용 안 함 (기본값 False)
- 주유소/제리캔은 시나리오별 챕터에서 선택적 배치
- C# 변경은 prop 존재 여부로 분기 → 시나리오03에 영향 없음
