# assets/objects/vehicles.py - 탈것 관련 오브젝트
#
# Vehicle: Object 기반 차량 시스템 (v2)
# 기존 Region 방식(CarDriverSeat 등)은 마이그레이션 전까지 유지.
#
# Unit ID 할당 (레거시):
# - 자전거 (Bicycle): 230
# - 운전석 (CarDriverSeat): 231
# - 조수석 (CarPassengerSeat): 232
# - 트렁크 (CarTrunk): 233

import morld
import ui
from assets.base import Object
from ui_style import style_muted


# ========================================
# Vehicle 기반 클래스 (v2)
# ========================================

class Vehicle(Object):
    """차량 Object 기반 클래스

    서브클래스에서 unique_id, name, props, actions, focus_text를 정의.
    vehicle.py 모듈의 유틸 함수와 연동.
    """

    def drive(self):
        """운전 — 목적지 선택 → 이동"""
        import vehicle as veh
        player_id = morld.get_player_id()

        # 운전석 탑승 확인
        if not veh.is_driver(self.instance_id, player_id):
            yield ui.dialog("운전석에 앉아야 운전할 수 있다.")
            return

        # 차량 상태 확인
        status = morld.get_unit_prop(self.instance_id, "vehicle:status") or "normal"
        if status == "wrecked":
            yield ui.dialog("차량이 완파되어 운전할 수 없다.")
            return
        if status == "disabled":
            yield ui.dialog("차량이 고장나 운전할 수 없다.")
            return

        # 목적지 목록 조회 (C# 탐색: 직접 연결된 실외 Location)
        destinations = morld.get_vehicle_destinations(self.instance_id)
        if not destinations:
            yield ui.dialog("갈 수 있는 곳이 없다.")
            return

        # 연료 확인 후 목적지 표시
        fuel = veh.get_fuel(self.instance_id)

        state = {"dest": None}

        def handle_choice(action):
            if action == "init":
                return None
            if action == "cancel":
                return True
            state["dest"] = action
            return True

        lines = ["[b]어디로 갈까?[/b]\n"]
        for i, dest in enumerate(destinations):
            distance = dest["distance"]
            fuel_cost = veh.estimate_fuel_cost(self.instance_id, distance)
            speed = veh.get_speed(self.instance_id)
            travel_min = int(distance * 60_000 / max(speed, 0.1)) // 60_000
            fuel_tag = f" (연료 {fuel_cost:.1f}L)" if fuel_cost > 0 else ""
            if fuel < fuel_cost:
                lines.append(style_muted(f"{dest['name']} ({travel_min}분){fuel_tag} — 연료 부족"))
            else:
                lines.append(f"[url=@proc:{i}]{dest['name']} ({travel_min}분){fuel_tag}[/url]")
        lines.append(f"\n현재 연료: {fuel:.0f}/{veh.get_fuel_max(self.instance_id):.0f}L")
        lines.append("\n[url=@proc:cancel]취소[/url]")

        yield ui.dialog("\n".join(lines), autofill="off", proc=handle_choice, result=state)

        if state["dest"] is not None and state["dest"] != "cancel":
            idx = int(state["dest"])
            dest = destinations[idx]
            distance = dest["distance"]

            # 이동 실행
            result = veh.vehicle_move_to(
                self.instance_id,
                dest["region_id"], dest["location_id"], distance)

            if result["success"]:
                travel_ms = result.get("travel_time_ms", 5 * 60_000)
                morld.advance_time_des(travel_ms)
                yield ui.dialog(f"{dest['name']}(으)로 이동했다.")
            else:
                yield ui.dialog(f"이동 실패: {result['message']}")

    def inspect(self):
        """차량 상태 점검"""
        import vehicle as veh
        parts = veh.get_vehicle_parts_status(self.instance_id)
        hp = morld.get_unit_prop(self.instance_id, "vehicle:hp") or 0
        hp_max = morld.get_unit_prop(self.instance_id, "vehicle:hp_max") or 0
        status = morld.get_unit_prop(self.instance_id, "vehicle:status") or "normal"
        fuel = veh.get_fuel(self.instance_id)
        fuel_max = veh.get_fuel_max(self.instance_id)

        status_label = {"normal": "정상", "disabled": "기동 불가", "wrecked": "완파"}
        lines = [
            f"상태: {status_label.get(status, status)}",
            f"내구도: {hp}/{hp_max}",
            f"연료: {fuel:.0f}/{fuel_max:.0f}L",
            "",
        ]
        for p in parts:
            ess = " [필수]" if p["essential"] else ""
            lines.append(f"  {p['name']}{ess}: {p['status']} ({p['hp']}/{p['hp_max']})")

        yield ui.dialog(f"{self.name} 점검", "\n".join(lines))

    def refuel(self):
        """제리캔으로 주유 (인벤토리의 제리캔 자동 탐색)"""
        import vehicle as veh
        player_id = morld.get_player_id()

        fuel = veh.get_fuel(self.instance_id)
        fuel_max = veh.get_fuel_max(self.instance_id)
        if fuel >= fuel_max:
            yield ui.dialog("주유", "연료가 이미 가득 찼습니다.")
            return

        # 인벤토리에서 제리캔 탐색
        from assets.registry import get_or_create_item_id
        jerry_id = get_or_create_item_id("jerry_can")
        inv = morld.get_unit_inventory(player_id)
        if not inv or jerry_id not in inv or inv[jerry_id] <= 0:
            yield ui.dialog("주유", "제리캔이 없습니다.")
            return

        jerry_fuel = morld.get_unit_prop(jerry_id, "jerrycan:fuel")
        if jerry_fuel is None:
            jerry_fuel = veh.JERRYCAN_FUEL
        if jerry_fuel <= 0:
            yield ui.dialog("주유", "빈 제리캔입니다.")
            return

        result = veh.refuel_from_jerrycan(self.instance_id, jerry_fuel)
        if result["amount"] <= 0:
            yield ui.dialog("주유", "연료가 이미 가득 찼습니다.")
            return

        remaining = result["remaining_jerrycan_fuel"]
        if remaining <= 0:
            morld.remove_item(player_id, jerry_id, 1)
        else:
            morld.set_unit_prop(jerry_id, "jerrycan:fuel", remaining)

        morld.advance_time_des(veh.JERRYCAN_REFUEL_TIME_MS)
        yield ui.dialog("주유", f"{result['amount']:.0f}L 주유 완료. "
                       f"(연료: {veh.get_fuel(self.instance_id):.0f}/"
                       f"{fuel_max:.0f}L)")

    def repair(self):
        """차량 수리 — 부품 선택 → 재료 체크 → 수리"""
        import vehicle as veh
        player_id = morld.get_player_id()

        damaged = veh.get_damaged_parts(self.instance_id)
        if not damaged:
            yield ui.dialog("수리", "수리할 부분이 없습니다.")
            return

        # 부품 선택 메뉴
        options = []
        for p in damaged:
            status_tag = "파손" if p["hp"] <= 0 else "손상"
            recipe = veh.REPAIR_RECIPES.get(p["part_id"], {})
            mat_text = ", ".join(f"{uid}×{cnt}" for uid, cnt in recipe.get("materials", {}).items())
            options.append(f"{p['name']} [{status_tag}] ({p['hp']}/{p['hp_max']}) — 재료: {mat_text}")

        choice = yield ui.select("수리할 부품을 선택하세요.", options)
        if choice is None:
            return

        part = damaged[choice]
        part_id = part["part_id"]

        # 재료 체크
        ok, missing = veh.check_repair_materials(player_id, part_id)
        if not ok:
            lines = ["재료가 부족합니다:"]
            for m in missing:
                lines.append(f"  {m['uid']}: {m['have']}/{m['need']}")
            yield ui.dialog("수리", "\n".join(lines))
            return

        # 재료 소비 + 수리
        veh.consume_repair_materials(player_id, part_id)
        result = veh.repair_part(self.instance_id, part_id)
        if result:
            time_min = veh.REPAIR_RECIPES[part_id]["time_min"]
            morld.advance_time_des(time_min * 60_000)
            yield ui.dialog("수리", f"{result['name']} 수리 완료. "
                          f"({result['new_hp']}/{result['hp_max']})")


class Motorcycle(Vehicle):
    """오토바이 — 항상 노출, 2인승"""
    unique_id = "motorcycle_01"
    name = "오토바이"
    actions = [
        "sit@driver:운전석 탑승",
        "sit@passenger1:뒷좌석 탑승",
        "call:drive:운전",
        "call:inspect:점검",
        "call:refuel:주유@near",
        "call:repair:수리@near",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        "vehicle:type": "motorcycle",
        "vehicle:seats": 2,
        "vehicle:speed": 4.0,
        "vehicle:exposed": 1,
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
        "vehicle:fuel_rate": 0.5,
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
    }
    focus_text = {"default": "상태가 나쁘지 않은 오토바이. 빠르게 이동할 수 있을 것 같다."}


class OldBus(Vehicle):
    """낡은 버스 — 대형 차량, 내부 Location 연결

    외부 Object (운전석 + 조수석) + 내부 Location (R1:L0, 별도 Region).
    RegionGate로 내부↔외부 연결, 차량 이동 시 Gate 재연결.
    """
    unique_id = "old_bus"
    name = "낡은 버스"
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
        "vehicle:type": "bus",
        "vehicle:seats": 2,         # 외부 직접 탑승분 (운전석+조수석)
        "vehicle:speed": 2.0,
        "vehicle:exposed": 0,
        "driver_seat": 1,
        "vehicle:hp": 300,
        "vehicle:hp_max": 300,
        "vehicle:status": "disabled",  # 디버그용: 초기 기동 불가
        "vehicle:part:engine": 0,      # 엔진 파손 (기동 불가 원인)
        "vehicle:part:engine_max": 80,
        "vehicle:part:tire": 50,
        "vehicle:part:tire_max": 50,
        "vehicle:part:body": 100,
        "vehicle:part:body_max": 100,
        "vehicle:part:window": 30,
        "vehicle:part:window_max": 30,
        "vehicle:part:fuel_tank": 40,
        "vehicle:part:fuel_tank_max": 40,
        "vehicle:fuel": 0,
        "vehicle:fuel_max": 80,
        "vehicle:fuel_rate": 0.8,      # 대형 = 연비 나쁨
        "vehicle:interior": "R1:L0",   # 내부 Location (Region 1)
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
    }
    focus_text = {
        "default": "도로변에 버려진 낡은 버스. 녹이 심하지만 골격은 튼튼해 보인다.",
    }


class SedanCar(Vehicle):
    """승용차 — 4인승, 차체 보호"""
    unique_id = "sedan_car"
    name = "낡은 승용차"
    actions = [
        "sit@driver:운전석 탑승",
        "sit@passenger1:조수석 탑승",
        "sit@passenger2:뒷좌석(좌) 탑승",
        "sit@passenger3:뒷좌석(우) 탑승",
        "call:drive:운전",
        "call:inspect:점검",
        "call:refuel:주유@near",
        "call:repair:수리@near",
        "call:look:트렁크 살펴보기",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        "vehicle:type": "car",
        "vehicle:seats": 4,
        "vehicle:speed": 3.0,
        "vehicle:exposed": 0,
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
    focus_text = {"default": "낡았지만 아직 굴러가는 승용차. 트렁크에 물건을 실을 수 있다."}

    def look(self):
        """트렁크 살펴보기"""
        yield ui.dialog([
            "트렁크를 열어보았다.",
            "물건을 넣거나 꺼낼 수 있겠다."
        ])


# ========================================
# 레거시: 자전거 (개방형 탈것 - Object 타입)
# ========================================

class Bicycle(Object):
    """
    자전거 - 뒷마당에 배치

    앞좌석: SittingOn 설정 + driver_seat 효과 (운전 가능)
    뒷좌석: SittingOn 설정만 (탑승만)

    좌석 Prop 시스템:
    - seated_by:front → 앉은 캐릭터 ID (-1이면 빈 좌석)
    - seated_by:rear → 앉은 캐릭터 ID (-1이면 빈 좌석)
    """
    unique_id = "bicycle"
    name = "자전거"
    actions = [
        "sit@front:앞좌석 앉기",  # driver_seat 효과
        "sit@rear:뒷좌석 앉기",   # 단순 탑승
        "call:debug_props:(디버그) 속성 보기#"
    ]
    props = {
        "driver_seat": 1,       # 앞좌석 앉으면 운전 가능
        "seated_by:front": -1,  # 앞좌석 (빈 좌석)
        "seated_by:rear": -1    # 뒷좌석 (빈 좌석)
    }
    focus_text = {"default": "녹이 조금 슬었지만 아직 탈 수 있어 보이는 자전거."}


# ========================================
# 자동차 내부 오브젝트 (밀폐형 탈것의 내부 구성요소)
# ========================================

class CarDriverSeat(Object):
    """
    운전석 - 자동차 Location 내부

    앉으면 운전 가능 (driver_seat Prop)
    - sit@seat:앉기 → 앉으면 운전 메뉴가 나타남
    - call:drive:운전 → 목적지 선택 다이얼로그

    좌석 Prop 시스템:
    - seated_by:seat → 앉은 캐릭터 ID (-1이면 빈 좌석)
    """
    unique_id = "car_driver_seat"
    name = "운전석"
    actions = [
        "sit@seat:앉기",
        "call:drive:운전",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    props = {
        "driver_seat": 1,      # 앉으면 운전 가능
        "seated_by:seat": -1   # 좌석 (빈 좌석)
    }
    focus_text = {"default": "낡은 가죽 시트의 운전석. 핸들이 손때가 묻어 있다."}

    def drive(self):
        """운전 메뉴 - 목적지 선택"""
        player_id = morld.get_player_id()

        # 운전 가능 여부 확인
        if not morld.can_drive(player_id):
            yield ui.dialog("운전석에 앉아야 운전할 수 있다.")
            return

        # 목적지 목록 조회
        destinations = morld.get_drivable_destinations(player_id)
        if not destinations:
            yield ui.dialog("갈 수 있는 곳이 없다.")
            return

        # 목적지 선택 다이얼로그 생성
        state = {"dest": None}

        def handle_choice(action):
            if action == "init":
                return None
            if action == "cancel":
                return True
            # region_id:location_id 형식
            state["dest"] = action
            return True

        lines = ["[b]어디로 갈까?[/b]\n"]
        for dest in destinations:
            region_id = dest["region_id"]
            location_id = dest["location_id"]
            name = dest["name"]
            travel_time_millis = dest["travel_time"]  # 밀리초
            travel_time_min = travel_time_millis // 60_000
            lines.append(f"[url=@proc:{region_id}:{location_id}]{name} ({travel_time_min}분)[/url]")
        lines.append("\n[url=@proc:cancel]취소[/url]")

        yield ui.dialog("\n".join(lines), autofill="off", proc=handle_choice, result=state)

        if state["dest"] and state["dest"] != "cancel":
            parts = state["dest"].split(":")
            region_id = int(parts[0])
            location_id = int(parts[1])
            result = morld.drive_to(player_id, region_id, location_id)
            yield ui.dialog(result["message"])
            if result["success"]:
                morld.advance_time_des(result["time_consumed"])  # 이미 밀리초 단위


class CarPassengerSeat(Object):
    """
    조수석 - 자동차 Location 내부

    앉기만 가능, 운전 불가

    좌석 Prop 시스템:
    - seated_by:seat → 앉은 캐릭터 ID (-1이면 빈 좌석)
    """
    unique_id = "car_passenger_seat"
    name = "조수석"
    actions = ["sit@seat:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {"seated_by:seat": -1}  # 좌석 (빈 좌석)
    focus_text = {"default": "낡은 가죽 시트의 조수석. 편히 앉을 수 있다."}


class CarTrunk(Object):
    """
    트렁크 - 자동차 Location 내부

    인벤토리 보유, 아이템 보관용
    """
    unique_id = "car_trunk"
    name = "트렁크"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "넓은 트렁크 공간. 물건을 보관할 수 있다."}

    def look(self):
        """트렁크 살펴보기"""
        yield ui.dialog([
            "차 트렁크를 열어보았다.",
            "물건을 넣거나 꺼낼 수 있겠다."
        ])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 주유기 (주유소 오브젝트)
# ========================================

class GasStationPump(Object):
    """주유기 — 주유소(R2:L1)에 배치, 차량 주유 및 제리캔 구매"""
    unique_id = "gas_pump"
    name = "주유기"
    position_x = 100
    props = {"fuel:supply": 1}
    actions = [
        "call:refuel_vehicle:차량 주유@near",
        "call:buy_jerrycan:제리캔 구매@near",
        "call:fill_jerrycan:제리캔 충전@near",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    focus_text = {"default": "오래됐지만 아직 작동하는 주유기. 연료를 넣을 수 있다."}

    def refuel_vehicle(self):
        """차량 직접 주유 (만탱, 코인 소비)"""
        import vehicle as veh
        player_id = morld.get_player_id()
        target = veh.find_nearby_vehicle(player_id)
        if not target:
            yield ui.dialog("주유", "근처에 차량이 없습니다.")
            return

        needed, cost = veh.calculate_refuel_cost(target)
        if needed <= 0:
            yield ui.dialog("주유", "연료가 이미 가득 찼습니다.")
            return

        # 코인 확인
        coin_count = _get_coin_count(player_id)
        if coin_count < cost:
            yield ui.dialog("주유",
                            f"코인이 부족합니다. (필요: {cost}, 보유: {coin_count})")
            return

        # 주유 실행
        _spend_coins(player_id, cost)
        veh.refuel_from_pump(target)
        morld.advance_time_des(veh.PUMP_REFUEL_TIME_MS)
        yield ui.dialog("주유", f"{needed:.0f}L 주유 완료. ({cost} 코인)")

    def buy_jerrycan(self):
        """제리캔 구매"""
        import vehicle as veh
        player_id = morld.get_player_id()
        cost = 20  # 코인

        coin_count = _get_coin_count(player_id)
        if coin_count < cost:
            yield ui.dialog("구매",
                            f"코인이 부족합니다. (필요: {cost}, 보유: {coin_count})")
            return

        _spend_coins(player_id, cost)

        from assets.registry import get_or_create_item_id
        jerry_id = get_or_create_item_id("jerry_can")
        morld.give_item(player_id, jerry_id, 1)
        morld.advance_time_des(1 * 60_000)
        yield ui.dialog("구매", "제리캔을 구매했습니다. (20 코인)")

    def fill_jerrycan(self):
        """빈 제리캔 충전"""
        import vehicle as veh
        player_id = morld.get_player_id()
        cost = 15  # 구매보다 저렴

        # 빈 제리캔 탐색
        jerry_id = _find_empty_jerrycan(player_id)
        if not jerry_id:
            yield ui.dialog("충전", "빈 제리캔이 없습니다.")
            return

        coin_count = _get_coin_count(player_id)
        if coin_count < cost:
            yield ui.dialog("충전",
                            f"코인이 부족합니다. (필요: {cost}, 보유: {coin_count})")
            return

        _spend_coins(player_id, cost)
        morld.set_unit_prop(jerry_id, "jerrycan:fuel", veh.JERRYCAN_FUEL)
        morld.advance_time_des(2 * 60_000)
        yield ui.dialog("충전", f"제리캔 충전 완료. ({cost} 코인)")


def _get_coin_count(player_id):
    """플레이어의 코인 보유량"""
    from assets.registry import get_or_create_item_id
    coin_id = get_or_create_item_id("coin")
    inv = morld.get_unit_inventory(player_id)
    if not inv:
        return 0
    return inv.get(coin_id, 0)


def _spend_coins(player_id, amount):
    """코인 소비"""
    from assets.registry import get_or_create_item_id
    coin_id = get_or_create_item_id("coin")
    morld.remove_item(player_id, coin_id, amount)


def _find_empty_jerrycan(player_id):
    """빈 제리캔 아이템 ID 탐색"""
    from assets.registry import get_or_create_item_id
    jerry_id = get_or_create_item_id("jerry_can")
    inv = morld.get_unit_inventory(player_id)
    if not inv or jerry_id not in inv or inv[jerry_id] <= 0:
        return None
    fuel = morld.get_unit_prop(jerry_id, "jerrycan:fuel")
    if fuel is not None and fuel > 0:
        return None  # 아직 연료가 있음
    return jerry_id
