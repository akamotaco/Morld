# 신규 차량 제작 가이드

## 개요

차량은 **Vehicle 클래스**를 상속하여 만듭니다. Vehicle은 Object 기반이므로 Location에 배치되고, 좌석(seated_by) prop으로 탑승을 관리합니다.

차량 분류에 따라 구현 범위가 다릅니다:

| 분류 | 예시 | 구조 | 추가 작업 |
|------|------|------|----------|
| 이륜 | 오토바이, 자전거 | Vehicle 서브클래스만 | 없음 |
| 소형 | 승용차, 트럭 | Vehicle 서브클래스만 | 없음 |
| 대형 | 버스, 수송차 | Vehicle + 내부 Location + Region + Gate | Region/Location/Gate 등록 |

---

## 파일 구조

```
assets/objects/vehicles.py          # 차량 Object 정의 (Vehicle 서브클래스)
assets/locations/vehicles.py        # 대형 차량 내부 Location 정의
world/vehicle.py                    # 대형 차량 내부 Region 초기화
world/__init__.py                   # Region 등록 + RegionGate 연결
vehicle.py                          # 차량 유틸 (이동/연료/수리 — 수정 불필요)
```

---

## Step 1: 소형/이륜 차량 만들기

### 1.1 Vehicle 서브클래스 정의

`assets/objects/vehicles.py`에 추가:

```python
class PickupTruck(Vehicle):
    """픽업 트럭 — 3인승, 적재함"""
    unique_id = "pickup_truck"
    name = "픽업 트럭"
    actions = [
        "sit@driver:운전석 탑승",
        "sit@passenger1:조수석 탑승",
        "sit@passenger2:적재함 탑승",
        "call:drive:운전",
        "call:inspect:점검",
        "call:refuel:주유@near",
        "call:repair:수리@near",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        # 차량 기본
        "vehicle:type": "car",         # motorcycle | car | bus
        "vehicle:seats": 3,            # 최대 탑승 인원 (Object 직접 탑승)
        "vehicle:speed": 2.5,          # 이동속도 배율 (1.0=도보)
        "vehicle:exposed": 0,          # 0=차체 보호, 1=항상 노출
        "driver_seat": 1,              # C# 운전 연동

        # 내구도
        "vehicle:hp": 250,
        "vehicle:hp_max": 250,
        "vehicle:status": "normal",    # normal | disabled | wrecked

        # 부품별 HP
        "vehicle:part:engine": 70,     "vehicle:part:engine_max": 70,
        "vehicle:part:tire": 50,       "vehicle:part:tire_max": 50,
        "vehicle:part:body": 80,       "vehicle:part:body_max": 80,
        "vehicle:part:window": 20,     "vehicle:part:window_max": 20,
        "vehicle:part:fuel_tank": 30,  "vehicle:part:fuel_tank_max": 30,

        # 연료
        "vehicle:fuel": 50,            # 현재 연료 (리터)
        "vehicle:fuel_max": 50,        # 최대 용량
        "vehicle:fuel_rate": 0.4,      # 소비량 (리터/이동 1단위거리)

        # 좌석 (seated_by:{seat_name}: -1 = 빈 좌석)
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
        "seated_by:passenger2": -1,
    }
    focus_text = {"default": "튼튼한 픽업 트럭. 뒤쪽 적재함에 짐을 실을 수 있다."}
```

### 1.2 Props 설명

#### 필수 props

| prop | 설명 | 비고 |
|------|------|------|
| `vehicle:type` | 차량 유형 | `motorcycle`(이륜), `car`(소형), `bus`(대형) |
| `vehicle:seats` | Object 직접 탑승 좌석 수 | 대형은 운전석 좌석만 (내부는 별도) |
| `vehicle:speed` | 속도 배율 | 1.0=도보, 높을수록 빠름 |
| `vehicle:exposed` | 노출 여부 | 이륜=1(항상), 소형/대형=0 |
| `driver_seat` | 운전석 표시 | C# `CanDrive` 연동, 항상 1 |
| `vehicle:hp` / `hp_max` | 전체 HP | 부품 HP 합산 |
| `vehicle:status` | 기동 상태 | `normal`/`disabled`/`wrecked` |
| `vehicle:fuel` / `fuel_max` | 연료 | 리터 단위 |
| `vehicle:fuel_rate` | 연료 소비율 | 리터/거리단위 |
| `seated_by:{seat}` | 좌석별 탑승자 | -1=빈 좌석, 좌석 수만큼 정의 |

#### 부품 props

5가지 부품, 각각 `vehicle:part:{id}`와 `vehicle:part:{id}_max` 쌍으로 정의:

| 부품 | 기동 필수 | 설명 |
|------|----------|------|
| `engine` | O | HP 0이면 기동 불가 |
| `tire` | O | HP 0이면 기동 불가 |
| `body` | X | HP 50% 이하 → 노출 전환 (이륜 제외) |
| `window` | X | HP 50% 이하 → 노출 전환 (이륜은 생략 가능) |
| `fuel_tank` | O | HP 50% 미만 → 연료 소비 2배 |

> **HP 합산**: `vehicle:hp` = 모든 부품 HP 합. `vehicle:hp_max` = 모든 부품 max 합.
> 반드시 일치시키세요.

#### 이륜 차량 특수사항

```python
# 이륜: window 부품 생략, 항상 노출
props = {
    "vehicle:type": "motorcycle",
    "vehicle:exposed": 1,
    # window 부품 없음 → 생략 (vehicle.py가 None이면 무시)
}
```

### 1.3 Actions 설명

| 액션 | 설명 |
|------|------|
| `sit@{seat}:{라벨}` | 좌석 탑승 (seated_by:{seat} prop과 이름 일치) |
| `call:drive:운전` | 목적지 선택 → 이동 (Vehicle.drive() 기본 구현) |
| `call:inspect:점검` | 차량 상태 표시 (Vehicle.inspect() 기본 구현) |
| `call:refuel:주유@near` | 제리캔 주유 (Vehicle.refuel() 기본 구현) |
| `call:repair:수리@near` | 부품 수리 (Vehicle.repair() 기본 구현) |

`@near`: 차량 근처에 있을 때만 표시. `@seated`: 탑승 중에만 표시.

> Vehicle 기반 클래스가 drive/inspect/refuel/repair를 이미 구현하고 있으므로,
> 서브클래스에서는 **props/actions/focus_text만 정의하면 됩니다**.

### 1.4 Location에 배치

차량을 배치할 Location의 `instantiate()` 메서드에 추가:

```python
# assets/locations/city.py (예시)
from assets.objects.vehicles import PickupTruck

class ParkingLot(Location):
    def instantiate(self, location_id, region_id):
        super().instantiate(location_id, region_id)
        # ...기존 오브젝트...
        self.add_object(PickupTruck(), x=120)
```

이것만으로 소형/이륜 차량은 완성입니다. drive/inspect/refuel/repair 액션이 자동으로 동작합니다.

---

## Step 2: 대형 차량 만들기

대형 차량은 **외부 Object + 내부 Location** 구조입니다.

```
외부 Object (운전석/조수석)          ← 실외 Location에 배치
   ↕ RegionGate 연결
내부 Location (좌석/화물칸/침대 등)  ← 별도 Region
```

차량이 이동하면 Gate 연결점이 새 외부 Location으로 자동 변경됩니다.

### 2.1 내부 Location 정의

`assets/locations/vehicles.py`에 추가:

```python
from assets.base import Location, Object


class TruckBed(Object):
    """적재칸 좌석"""
    unique_id = "truck_bed_seat"
    name = "적재칸 좌석"
    actions = ["sit@seat:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {"seated_by:seat": -1}
    focus_text = {"default": "적재칸에 마련된 간이 좌석."}


class TruckCargo(Object):
    """적재 공간"""
    unique_id = "truck_cargo"
    name = "적재 공간"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "넓은 적재 공간. 물자를 보관할 수 있다."}

    def look(self):
        import ui
        yield ui.dialog("적재 공간을 확인했다. 물건을 넣거나 꺼낼 수 있겠다.")


class TruckInterior(Location):
    """수송 트럭 내부"""
    unique_id = "truck_interior"
    name = "트럭 내부"
    is_indoor = True
    stay_duration = 0
    geometry = 1      # line
    length = 150

    describe_text = {
        "default": "수송 트럭의 내부. 적재칸에 좌석과 짐을 실을 공간이 있다.",
    }

    def instantiate(self, location_id, region_id):
        super().instantiate(location_id, region_id)

        # 좌석 6개
        for i, x in enumerate([20, 40, 60, 80, 100, 120]):
            seat = TruckBed()
            seat.unique_id = f"truck_bed_seat_{i}"
            seat.name = f"적재칸 좌석 {i + 1}"
            self.add_object(seat, x=x)

        # 적재 공간
        self.add_object(TruckCargo(), x=140)
```

### 2.2 내부 Region 등록

대형 차량의 내부 Location은 **별도 Region**에 배치합니다.

#### 방법 A: 기존 차량 Region (Region 1) 사용

Region 1은 대형 차량 내부 전용으로 예약되어 있습니다. 현재 `BusInterior`가 L0을 사용 중이므로, 새 Location은 L1부터 할당:

```python
# world/vehicle.py 수정
def initialize_terrain():
    from assets.locations.vehicles import BusInterior, TruckInterior

    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"], r["weather"])

    locations = {
        0: BusInterior(),       # 버스 내부 (기존)
        1: TruckInterior(),     # 트럭 내부 (신규)
    }

    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)
```

#### 방법 B: 새 Region 할당

차량별 독립 Region이 필요한 경우 (예: 시나리오 03 전철):

```python
# world/train.py (신규)
import morld

REGION_ID = 11  # 새 Region ID

REGION = {
    "id": REGION_ID,
    "name": "전철 내부",
    "describe_text": {"default": "전철의 내부 공간."},
    "weather": "맑음"
}

def initialize_terrain():
    from assets.locations.vehicles import TrainInterior
    morld.add_region(REGION["id"], REGION["name"],
                     REGION["describe_text"], REGION["weather"])
    locations = {0: TrainInterior()}
    for location_id, loc in locations.items():
        loc.instantiate(location_id, REGION_ID)
```

### 2.3 RegionGate 등록

`world/__init__.py`의 `REGION_GATES` 리스트에 Gate를 추가합니다.

```python
REGION_GATES = [
    # ...기존 Gate들...

    # 버스 내부(R1:L0) ↔ 주차장(R2:L4) — 즉시
    (1, vehicle.REGION_ID, 0, city.REGION_ID, 4, 0),

    # 트럭 내부(R1:L1) ↔ 주차장(R2:L4) — 즉시 (신규)
    (5, vehicle.REGION_ID, 1, city.REGION_ID, 4, 0),
]
```

Gate 파라미터: `(gate_id, region_a, location_a, region_b, location_b, distance)`
- `distance=0`: 즉시 이동 (차량 탑승/하차)

### 2.4 외부 Object 정의

`assets/objects/vehicles.py`에 대형 차량 Object 추가:

```python
class TransportTruck(Vehicle):
    """수송 트럭 — 대형, 내부 Location 연결"""
    unique_id = "transport_truck"
    name = "수송 트럭"
    actions = [
        "sit@driver:운전석 탑승",
        "sit@passenger1:조수석 탑승",
        "call:drive:운전",
        "call:inspect:점검",
        "call:refuel:주유@near",
        "call:repair:수리@near",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        "vehicle:type": "bus",        # 대형은 "bus" 타입
        "vehicle:seats": 2,           # 외부 직접 탑승분만
        "vehicle:speed": 1.5,
        "vehicle:exposed": 0,
        "driver_seat": 1,

        "vehicle:hp": 350,
        "vehicle:hp_max": 350,
        "vehicle:status": "normal",

        "vehicle:part:engine": 100,   "vehicle:part:engine_max": 100,
        "vehicle:part:tire": 60,      "vehicle:part:tire_max": 60,
        "vehicle:part:body": 120,     "vehicle:part:body_max": 120,
        "vehicle:part:window": 20,    "vehicle:part:window_max": 20,
        "vehicle:part:fuel_tank": 50, "vehicle:part:fuel_tank_max": 50,

        "vehicle:fuel": 60,
        "vehicle:fuel_max": 100,
        "vehicle:fuel_rate": 1.0,     # 대형 = 연비 나쁨

        # ★ 대형 차량 핵심: 내부 Location 연결
        "vehicle:interior": "R1:L1",  # Region 1, Location 1

        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
    }
    focus_text = {"default": "군용 수송 트럭. 내부에 병력을 태울 수 있다."}
```

**핵심**: `"vehicle:interior": "R{n}:L{n}"` — 이 prop이 있으면 대형 차량으로 인식됩니다. 차량 이동 시 `vehicle.py`의 `vehicle_move_to()`가 자동으로 Gate를 재연결합니다.

### 2.5 Location에 배치

```python
# assets/locations/city.py
from assets.objects.vehicles import TransportTruck

class MilitaryBase(Location):
    def instantiate(self, location_id, region_id):
        super().instantiate(location_id, region_id)
        self.add_object(TransportTruck(), x=80)
```

### 2.6 world/__init__.py 갱신 (필요 시)

새 Region을 추가한 경우:

```python
# world/__init__.py
from . import train  # Region 11: 전철 내부 (예시)

def initialize_world():
    # ...기존 Region 초기화...
    train.initialize_terrain()

    # RegionGate - 안전한 등록
    initialize_region_gates()
```

---

## Step 3: 커스텀 동작 추가

Vehicle 기반 클래스의 기본 메서드(drive/inspect/refuel/repair)를 override하거나
새 메서드를 추가할 수 있습니다.

### 3.1 커스텀 액션 추가

```python
class IceCreamTruck(Vehicle):
    unique_id = "ice_cream_truck"
    name = "아이스크림 트럭"
    actions = [
        "sit@driver:운전석 탑승",
        "call:drive:운전",
        "call:inspect:점검",
        "call:sell_ice_cream:아이스크림 판매@near",  # 커스텀 액션
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        # ...차량 기본 props...
        "ice_cream:stock": 20,  # 커스텀 prop
    }

    def sell_ice_cream(self):
        """아이스크림 판매"""
        stock = morld.get_unit_prop(self.instance_id, "ice_cream:stock") or 0
        if stock <= 0:
            yield ui.dialog("재고가 없습니다.")
            return
        morld.set_unit_prop(self.instance_id, "ice_cream:stock", stock - 1)
        yield ui.dialog("아이스크림 하나를 받았다.")
```

### 3.2 drive() override

기본 drive()를 변경하여 특수 이동 로직을 추가할 수 있습니다:

```python
class EmergencyVehicle(Vehicle):
    def drive(self):
        """긴급 차량 — 연료 소비 0"""
        # 기본 drive() 호출 전에 사이렌 효과 등 추가 가능
        yield from super().drive()
```

---

## Step 4: NPC 운전 (선택)

NPC가 차량을 사용하게 하려면 스케줄에 `"운전"` 활동을 추가합니다.

### 4.1 NPC 스케줄

```python
class MyNPCAgent(BaseAgent):
    _vehicle_capable = True  # NPC 운전 가능 표시

    SCHEDULE = [
        # ...
        {"name": "이동", "start": 600*_M, "end": 660*_M,
         "activity": "운전",
         "dest_region": 2, "dest_location": 0,  # 목적지
         "distance": 3600},                      # 거리 (location units)
    ]
```

### 4.2 도보 Fallback

차량이 없거나 사용 불가능하면 NPC는 자동으로 도보 이동합니다. 별도 처리 불필요.

---

## 수치 설계 가이드

### 속도 배율 기준

| 유형 | speed | 체감 |
|------|-------|------|
| 자전거 | 1.5 | 도보 1.5배 |
| 오토바이 | 4.0 | 매우 빠름 |
| 승용차 | 3.0 | 빠름 |
| 버스/트럭 | 1.5~2.0 | 도보보다 빠르지만 무거움 |

### 연료 소비율 기준

| 유형 | fuel_rate | 비고 |
|------|-----------|------|
| 오토바이 | 0.5 | 경량, 효율적 |
| 승용차 | 0.3 | 표준 |
| 버스/트럭 | 0.8~1.0 | 대형, 비효율 |

### HP 배분 기준

전체 HP = 모든 부품 HP 합산. 부품별 비중:

| 부품 | 비중 | 설명 |
|------|------|------|
| engine | ~30% | 핵심 동력 |
| tire | ~20% | 가장 자주 파손 |
| body | ~30% | 방어력 |
| window | ~10% | 파손 시 노출 전환 기여 |
| fuel_tank | ~10% | 파손 시 연비 악화 |

---

## 시나리오03 호환성

- `vehicle:*` prop 없으면 일반 Object로 동작 (무해)
- `vehicle:interior` prop 없으면 소형 차량으로 동작
- `_vehicle_capable` 없는 NPC는 차량 미사용 (기본값 False)
- Region/Gate가 없으면 `_safe_add_region_gate()`가 조용히 무시

---

## 체크리스트

### 소형/이륜 차량

- [ ] Vehicle 서브클래스 정의 (`unique_id` 고유성)
- [ ] props에 필수 키 포함 (vehicle:type/seats/speed/hp/hp_max/status/fuel/fuel_max/fuel_rate)
- [ ] `vehicle:hp` = 부품 HP 합산 일치 확인
- [ ] `seated_by:{seat}` 개수 = `vehicle:seats` 일치
- [ ] Location에 `add_object()` 배치
- [ ] 테스트: `python tests/run_tests.py test_vehicle`

### 대형 차량 (위 항목 + 추가)

- [ ] 내부 Location 클래스 정의 (`assets/locations/vehicles.py`)
- [ ] 내부 Region 초기화 (`world/vehicle.py`)
- [ ] RegionGate 등록 (`world/__init__.py` → `REGION_GATES`)
- [ ] `vehicle:interior` prop 설정 (`"R{n}:L{n}"` 형식)
- [ ] Gate 재연결 동작 확인 (차량 이동 후 내부↔외부 연결 변경)

---

## 참고 문서

| 문서 | 내용 |
|------|------|
| [vehicle-system.md](vehicle-system.md) | 차량 시스템 설계 명세 (부품/연료/전투/수리 상세) |
| [terrain.md](terrain.md) | Region/Location/Gate 구조 |
| [system-api.md](system-api.md) | morld Python API |
| [make_activity.md](make_activity.md) | NPC 활동 핸들러 제작 (운전 Activity 참조) |
