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


# ========================================
# Vehicle 기반 클래스 (v2)
# ========================================

class Vehicle(Object):
    """차량 Object 기반 클래스

    서브클래스에서 unique_id, name, props, actions, focus_text를 정의.
    vehicle.py 모듈의 유틸 함수와 연동.
    """

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

    def repair(self):
        """차량 수리 — 부품 선택 → 수리"""
        import vehicle as veh
        damaged = veh.get_damaged_parts(self.instance_id)
        if not damaged:
            yield ui.dialog("수리", "수리할 부분이 없습니다.")
            return

        # TODO: 재료 체크 + 소비 (Phase 6에서 구현)
        # 현재는 첫 번째 손상 부품 자동 수리 (테스트용)
        part = damaged[0]
        result = veh.repair_part(self.instance_id, part["part_id"])
        if result:
            yield ui.dialog("수리", f"{result['name']} 수리 완료. "
                          f"({result['new_hp']}/{result['hp_max']})")
            morld.advance_time_des(veh.REPAIR_RECIPES[part["part_id"]]["time_min"] * 60_000)


class Motorcycle(Vehicle):
    """오토바이 — 항상 노출, 2인승"""
    unique_id = "motorcycle_01"
    name = "오토바이"
    actions = [
        "sit@driver:운전석 탑승",
        "sit@passenger1:뒷좌석 탑승",
        "call:inspect:점검",
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


class SedanCar(Vehicle):
    """승용차 — 4인승, 차체 보호"""
    unique_id = "sedan_car"
    name = "낡은 승용차"
    actions = [
        "sit@driver:운전석 탑승",
        "sit@passenger1:조수석 탑승",
        "sit@passenger2:뒷좌석(좌) 탑승",
        "sit@passenger3:뒷좌석(우) 탑승",
        "call:inspect:점검",
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
