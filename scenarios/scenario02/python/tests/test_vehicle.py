# test_vehicle.py — 차량 시스템 유틸리티 테스트
"""
Part A: relocate_object (오브젝트 위치 이동 인덱스)
Part B: 연료 시스템 (소비/충전/이동가능 판정)
Part C: 부품 데미지 (가중 랜덤 분배, 상태 전환)
Part D: 수리 시스템
Part E: 탑승자 조회
Part F: 유틸리티 (parse_interior_key 등)
"""
import sys
import os
import types

# ============================================
# 1. 경로 설정
# ============================================

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

# ============================================
# 2. morld mock
# ============================================

import morld

# ============================================
# 3. 외부 모듈 stub
# ============================================

_events = sys.modules.get("events") or types.ModuleType("events")
_events.subscribe_time_elapsed = lambda callback, min_interval=0: None
_events.on_game_start = lambda f: f
_events.on_reach = lambda f: f
_events.on_leave = lambda f: f
sys.modules.setdefault("events", _events)
for _sub in ["events.game_start", "events.scripts",
             "events.game_start.prologue", "events.scripts.player_creation"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

# ui stub
_ui = sys.modules.get("ui") or types.ModuleType("ui")
_ui.dialog = lambda *a, **kw: None
sys.modules.setdefault("ui", _ui)

# sound stub
_sound = sys.modules.get("sound") or types.ModuleType("sound")
_sound.emit_sound = lambda *a, **kw: None
sys.modules.setdefault("sound", _sound)


# ============================================
# 4. Import
# ============================================

# assets.objects 내부 dict 직접 참조 (다른 테스트의 import 캐시 회피)
try:
    from assets.objects import (
        _instances, _location_objects,
        register_location_object, get_location_objects, relocate_object
    )
except ImportError:
    # 다른 테스트가 assets.objects를 부분 로드한 경우 → 내부 dict 직접 구성
    _instances = {}
    _location_objects = {}

    def register_location_object(region_id, location_id, instance_id):
        key = (region_id, location_id)
        if key not in _location_objects:
            _location_objects[key] = []
        _location_objects[key].append(instance_id)

    def get_location_objects(region_id, location_id):
        return _location_objects.get((region_id, location_id), [])

    def relocate_object(instance_id, old_r, old_l, new_r, new_l):
        if instance_id not in _instances:
            return False
        old_key = (old_r, old_l)
        new_key = (new_r, new_l)
        old_list = _location_objects.get(old_key)
        if old_list and instance_id in old_list:
            old_list.remove(instance_id)
        if new_key not in _location_objects:
            _location_objects[new_key] = []
        if instance_id not in _location_objects[new_key]:
            _location_objects[new_key].append(instance_id)
        return True

import vehicle


# ============================================
# 테스트 기반
# ============================================

class _T:
    def __init__(self):
        _setup()


def _setup():
    morld.reset()
    _instances.clear()
    _location_objects.clear()
    # vehicle.py가 relocate_object를 찾을 수 있도록 주입
    vehicle.set_relocate_object(relocate_object)


# ============================================
# Part A: relocate_object
# ============================================

class TestRelocateObject(_T):

    def test_basic_relocate(self):
        """오브젝트를 (0,1) → (2,4)로 이동"""
        obj_id = 300
        # 인스턴스 등록 (간단한 더미)
        _instances[obj_id] = "dummy_vehicle"
        register_location_object(0, 1, obj_id)

        assert obj_id in get_location_objects(0, 1)

        result = relocate_object(obj_id, 0, 1, 2, 4)
        assert result is True
        assert obj_id not in get_location_objects(0, 1)
        assert obj_id in get_location_objects(2, 4)

    def test_relocate_unregistered_instance(self):
        """미등록 인스턴스는 False"""
        result = relocate_object(999, 0, 0, 1, 1)
        assert result is False

    def test_relocate_not_in_old_location(self):
        """이전 location에 없어도 새 location에는 추가"""
        obj_id = 301
        _instances[obj_id] = "dummy"
        # old location에 등록하지 않음

        result = relocate_object(obj_id, 0, 0, 2, 4)
        assert result is True
        assert obj_id in get_location_objects(2, 4)

    def test_relocate_idempotent(self):
        """같은 위치로 이동해도 중복 추가 안 됨"""
        obj_id = 302
        _instances[obj_id] = "dummy"
        register_location_object(0, 1, obj_id)

        relocate_object(obj_id, 0, 1, 0, 1)  # 같은 곳
        count = get_location_objects(0, 1).count(obj_id)
        assert count == 1

    def test_multiple_objects_in_location(self):
        """여러 오브젝트 중 하나만 이동"""
        _instances[310] = "a"
        _instances[311] = "b"
        register_location_object(0, 1, 310)
        register_location_object(0, 1, 311)

        relocate_object(310, 0, 1, 2, 4)
        assert 310 not in get_location_objects(0, 1)
        assert 311 in get_location_objects(0, 1)
        assert 310 in get_location_objects(2, 4)


# ============================================
# Part B: 연료 시스템
# ============================================

def _make_vehicle(vid=500, fuel=40, fuel_max=40, fuel_rate=0.5,
                  status="normal", vtype="car", parts=True):
    """테스트용 차량 등록"""
    props = {
        "vehicle:type": vtype,
        "vehicle:fuel": fuel,
        "vehicle:fuel_max": fuel_max,
        "vehicle:fuel_rate": fuel_rate,
        "vehicle:speed": 3.0,
        "vehicle:seats": 4,
        "vehicle:status": status,
        "vehicle:exposed": 1 if vtype == "motorcycle" else 0,
        "driver_seat": 1,
        "seated_by:driver": -1,
        "seated_by:passenger1": -1,
    }
    if parts:
        props.update({
            "vehicle:hp": 200,
            "vehicle:hp_max": 200,
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
        })
    morld.register_unit(vid, name="TestVehicle", props=props,
                        location=(2, 4), is_object=True)
    return vid


class TestFuel(_T):

    def test_get_fuel(self):
        vid = _make_vehicle(fuel=25)
        assert vehicle.get_fuel(vid) == 25
        assert vehicle.get_fuel_max(vid) == 40

    def test_estimate_fuel_cost(self):
        vid = _make_vehicle(fuel_rate=0.5)
        cost = vehicle.estimate_fuel_cost(vid, 20)
        assert cost == 10.0  # 20 * 0.5

    def test_fuel_cost_with_damaged_tank(self):
        """연료탱크 50% 미만 손상 시 소비 2배"""
        vid = _make_vehicle(fuel_rate=0.5)
        # tank_max=20, 50%=10 미만으로 설정
        morld.set_unit_prop(vid, "vehicle:part:fuel_tank", 5)
        cost = vehicle.estimate_fuel_cost(vid, 20)
        assert cost == 20.0  # 20 * 0.5 * 2

    def test_can_travel_normal(self):
        vid = _make_vehicle(fuel=40, fuel_rate=0.5)
        ok, reason = vehicle.can_travel(vid, 60)
        assert ok is True  # 소비 30, 잔량 40

    def test_can_travel_insufficient_fuel(self):
        vid = _make_vehicle(fuel=10, fuel_rate=0.5)
        ok, reason = vehicle.can_travel(vid, 60)
        assert ok is False
        assert "연료" in reason

    def test_can_travel_disabled(self):
        vid = _make_vehicle(status="disabled")
        ok, reason = vehicle.can_travel(vid, 10)
        assert ok is False
        assert "기동" in reason

    def test_can_travel_wrecked(self):
        vid = _make_vehicle(status="wrecked")
        ok, reason = vehicle.can_travel(vid, 10)
        assert ok is False

    def test_consume_fuel(self):
        vid = _make_vehicle(fuel=40, fuel_rate=0.5)
        consumed = vehicle.consume_fuel(vid, 20)
        assert consumed == 10.0
        assert vehicle.get_fuel(vid) == 30.0

    def test_consume_fuel_clamp_zero(self):
        """연료가 비용보다 적어도 0으로 클램프"""
        vid = _make_vehicle(fuel=5, fuel_rate=0.5)
        consumed = vehicle.consume_fuel(vid, 20)
        assert vehicle.get_fuel(vid) == 0

    def test_refuel(self):
        vid = _make_vehicle(fuel=10, fuel_max=40)
        actual = vehicle.refuel(vid, 20)
        assert actual == 20
        assert vehicle.get_fuel(vid) == 30

    def test_refuel_clamp_max(self):
        vid = _make_vehicle(fuel=35, fuel_max=40)
        actual = vehicle.refuel(vid, 20)
        assert actual == 5
        assert vehicle.get_fuel(vid) == 40

    def test_refuel_already_full(self):
        vid = _make_vehicle(fuel=40, fuel_max=40)
        actual = vehicle.refuel(vid, 10)
        assert actual == 0

    def test_prepare_move_success(self):
        vid = _make_vehicle(fuel=40, fuel_rate=0.5)
        ok, msg, consumed = vehicle.prepare_move(vid, 20)
        assert ok is True
        assert consumed == 10.0
        assert vehicle.get_fuel(vid) == 30.0

    def test_prepare_move_fail(self):
        vid = _make_vehicle(fuel=5, fuel_rate=0.5)
        ok, msg, consumed = vehicle.prepare_move(vid, 60)
        assert ok is False
        assert consumed == 0
        assert vehicle.get_fuel(vid) == 5  # 변화 없음


# ============================================
# Part C: 부품 데미지
# ============================================

class TestDamage(_T):

    def test_apply_damage_reduces_part(self):
        vid = _make_vehicle()
        import random
        random.seed(42)
        result = vehicle.apply_damage(vid, 10)
        assert result is not None
        assert result["damage"] == 10
        assert result["new_hp"] >= 0

    def test_apply_damage_recalculates_total(self):
        vid = _make_vehicle()
        import random
        random.seed(42)
        vehicle.apply_damage(vid, 10)
        total = morld.get_unit_prop(vid, "vehicle:hp")
        assert total == 190  # 200 - 10

    def test_damage_causes_disabled(self):
        """필수 부품 HP 0 → disabled"""
        vid = _make_vehicle()
        # 엔진 직접 파괴
        morld.set_unit_prop(vid, "vehicle:part:engine", 0)
        vehicle._recalculate_total_hp(vid)
        vehicle.update_status(vid)
        assert morld.get_unit_prop(vid, "vehicle:status") == "disabled"

    def test_damage_causes_exposed(self):
        """HP 50% 이하 → exposed (자동차)"""
        vid = _make_vehicle()
        # 전체 HP를 100 이하로 (max=200)
        morld.set_unit_prop(vid, "vehicle:part:engine", 20)
        morld.set_unit_prop(vid, "vehicle:part:body", 20)
        morld.set_unit_prop(vid, "vehicle:part:tire", 20)
        morld.set_unit_prop(vid, "vehicle:part:window", 10)
        morld.set_unit_prop(vid, "vehicle:part:fuel_tank", 10)
        vehicle._recalculate_total_hp(vid)
        vehicle.update_status(vid)
        assert morld.get_unit_prop(vid, "vehicle:hp") == 80
        assert morld.get_unit_prop(vid, "vehicle:exposed") == 1

    def test_motorcycle_always_exposed(self):
        """오토바이는 update_status에서 exposed 변경 안 함"""
        vid = _make_vehicle(vtype="motorcycle")
        assert morld.get_unit_prop(vid, "vehicle:exposed") == 1
        vehicle.update_status(vid)
        # motorcycle은 exposed 로직 스킵 → 초기값 유지
        assert morld.get_unit_prop(vid, "vehicle:exposed") == 1

    def test_wrecked_status(self):
        """전체 HP 0 → wrecked"""
        vid = _make_vehicle()
        for part_id in vehicle.VEHICLE_PARTS:
            morld.set_unit_prop(vid, f"vehicle:part:{part_id}", 0)
        vehicle._recalculate_total_hp(vid)
        vehicle.update_status(vid)
        assert morld.get_unit_prop(vid, "vehicle:status") == "wrecked"
        assert morld.get_unit_prop(vid, "vehicle:exposed") == 1

    def test_damage_all_parts_zero_returns_none(self):
        """모든 부품 HP 0 → apply_damage returns None"""
        vid = _make_vehicle()
        for part_id in vehicle.VEHICLE_PARTS:
            morld.set_unit_prop(vid, f"vehicle:part:{part_id}", 0)
        result = vehicle.apply_damage(vid, 10)
        assert result is None

    def test_parts_status_query(self):
        vid = _make_vehicle()
        parts = vehicle.get_vehicle_parts_status(vid)
        assert len(parts) == 5
        for p in parts:
            assert p["status"] == "양호"

    def test_damaged_parts_query(self):
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "vehicle:part:tire", 0)
        damaged = vehicle.get_damaged_parts(vid)
        assert len(damaged) == 1
        assert damaged[0]["part_id"] == "tire"
        assert damaged[0]["status"] == "파손"

    def test_no_window_motorcycle(self):
        """오토바이: window 부품 없으면 parts_status에서 제외"""
        vid = _make_vehicle(vtype="motorcycle")
        # window 제거
        morld.set_unit_prop(vid, "vehicle:part:window_max", 0)
        parts = vehicle.get_vehicle_parts_status(vid)
        part_ids = [p["part_id"] for p in parts]
        assert "window" not in part_ids


# ============================================
# Part D: 수리 시스템
# ============================================

class TestRepair(_T):

    def test_repair_restores_hp(self):
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "vehicle:part:engine", 20)
        vehicle._recalculate_total_hp(vid)

        result = vehicle.repair_part(vid, "engine")
        assert result is not None
        assert result["old_hp"] == 20
        assert result["new_hp"] == 50  # 20 + 30(restore)
        assert result["hp_max"] == 60

    def test_repair_clamp_max(self):
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "vehicle:part:engine", 50)

        result = vehicle.repair_part(vid, "engine")
        assert result["new_hp"] == 60  # min(50+30, 60)

    def test_repair_full_hp_returns_none(self):
        vid = _make_vehicle()
        result = vehicle.repair_part(vid, "engine")
        assert result is None  # 이미 최대

    def test_repair_invalid_part(self):
        vid = _make_vehicle()
        result = vehicle.repair_part(vid, "nonexistent")
        assert result is None

    def test_repair_restores_status(self):
        """엔진 파손 → disabled → 수리 → normal"""
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "vehicle:part:engine", 0)
        vehicle._recalculate_total_hp(vid)
        vehicle.update_status(vid)
        assert morld.get_unit_prop(vid, "vehicle:status") == "disabled"

        vehicle.repair_part(vid, "engine")
        assert morld.get_unit_prop(vid, "vehicle:status") == "normal"

    def test_repair_restores_exposed(self):
        """HP 50% 이하 → exposed → 수리로 50% 초과 → 보호 복원"""
        vid = _make_vehicle()
        # HP를 100 이하로 (max=200, 50%=100)
        morld.set_unit_prop(vid, "vehicle:part:body", 0)    # -60
        morld.set_unit_prop(vid, "vehicle:part:window", 0)  # -20
        morld.set_unit_prop(vid, "vehicle:part:engine", 20) # -40
        vehicle._recalculate_total_hp(vid)
        # HP = 20+40+0+0+20 = 80 < 100
        vehicle.update_status(vid)
        assert morld.get_unit_prop(vid, "vehicle:exposed") == 1

        # body 수리 (0 → 30), engine 수리 (20 → 50)
        vehicle.repair_part(vid, "body")
        vehicle.repair_part(vid, "engine")
        # HP = 50+40+30+0+20 = 140 > 100 → 보호
        assert morld.get_unit_prop(vid, "vehicle:exposed") == 0

    def test_repair_updates_total_hp(self):
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "vehicle:part:tire", 0)
        vehicle._recalculate_total_hp(vid)
        assert morld.get_unit_prop(vid, "vehicle:hp") == 160

        vehicle.repair_part(vid, "tire")
        assert morld.get_unit_prop(vid, "vehicle:hp") == 185  # 160 + 25


# ============================================
# Part E: 탑승자 조회
# ============================================

class TestPassengers(_T):

    def test_no_passengers(self):
        vid = _make_vehicle()
        assert vehicle.get_passengers(vid) == []

    def test_with_passengers(self):
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "seated_by:driver", 100)
        morld.set_unit_prop(vid, "seated_by:passenger1", 101)
        passengers = vehicle.get_passengers(vid)
        assert 100 in passengers
        assert 101 in passengers
        assert len(passengers) == 2

    def test_empty_seats_counted(self):
        vid = _make_vehicle()
        assert vehicle.get_seat_count(vid) == 4
        assert vehicle.get_empty_seat_count(vid) == 4

        morld.set_unit_prop(vid, "seated_by:driver", 100)
        assert vehicle.get_empty_seat_count(vid) == 3

    def test_is_driver(self):
        vid = _make_vehicle()
        morld.set_unit_prop(vid, "seated_by:driver", 100)
        assert vehicle.is_driver(vid, 100) is True
        assert vehicle.is_driver(vid, 101) is False


# ============================================
# Part F: 유틸리티
# ============================================

class TestUtility(_T):

    def test_is_vehicle(self):
        vid = _make_vehicle()
        assert vehicle.is_vehicle(vid) is True
        morld.register_unit(600, name="NotVehicle")
        assert vehicle.is_vehicle(600) is False

    def test_get_speed(self):
        vid = _make_vehicle()
        assert vehicle.get_speed(vid) == 3.0

    def test_parse_interior_key(self):
        assert vehicle.parse_interior_key("R4:L10") == (4, 10)
        assert vehicle.parse_interior_key("R0:L0") == (0, 0)
        assert vehicle.parse_interior_key(None) is None
        assert vehicle.parse_interior_key("") is None
        assert vehicle.parse_interior_key("invalid") is None

    def test_parse_interior_key_edge(self):
        assert vehicle.parse_interior_key("R12:L99") == (12, 99)


# ============================================
# Part G: 탑승/하차 (mount/dismount)
# ============================================

class TestMount(_T):

    def test_mount_basic(self):
        """기본 탑승 — 빈 좌석에 자동 배정"""
        vid = _make_vehicle()
        char_id = 100
        morld.register_unit(char_id, name="Driver", location=(2, 4))

        ok, seat = vehicle.mount(char_id, vid)
        assert ok is True
        assert seat == "driver"  # prefer_driver=True
        assert morld.get_unit_prop(vid, "seated_by:driver") == char_id

    def test_mount_second_passenger(self):
        """운전석 점유 → 다음 빈 좌석 배정"""
        vid = _make_vehicle()
        morld.register_unit(100, name="Driver", location=(2, 4))
        morld.register_unit(101, name="Passenger", location=(2, 4))

        vehicle.mount(100, vid)
        ok, seat = vehicle.mount(101, vid)
        assert ok is True
        assert seat == "passenger1"

    def test_mount_specific_seat(self):
        """특정 좌석 지정 탑승"""
        vid = _make_vehicle()
        morld.register_unit(100, name="Char", location=(2, 4))

        ok, seat = vehicle.mount(100, vid, seat_name="passenger1")
        assert ok is True
        assert seat == "passenger1"
        assert morld.get_unit_prop(vid, "seated_by:passenger1") == 100

    def test_mount_occupied_seat(self):
        """점유된 좌석 지정 시 실패"""
        vid = _make_vehicle()
        morld.register_unit(100, name="A", location=(2, 4))
        morld.register_unit(101, name="B", location=(2, 4))

        vehicle.mount(100, vid, seat_name="driver")
        ok, reason = vehicle.mount(101, vid, seat_name="driver")
        assert ok is False
        assert "점유" in reason

    def test_mount_full_vehicle(self):
        """만석 시 탑승 실패"""
        vid = _make_vehicle()  # seats=4, but only driver+passenger1 props
        # 2좌석만 prop 등록되어 있으므로 2명이면 만석
        morld.register_unit(100, name="A", location=(2, 4))
        morld.register_unit(101, name="B", location=(2, 4))
        morld.register_unit(102, name="C", location=(2, 4))

        vehicle.mount(100, vid)
        vehicle.mount(101, vid)
        ok, reason = vehicle.mount(102, vid)
        assert ok is False
        assert "빈 좌석" in reason

    def test_mount_not_vehicle(self):
        """차량이 아닌 유닛에 탑승 시도"""
        morld.register_unit(600, name="NotVehicle")
        morld.register_unit(100, name="Char", location=(0, 0))
        ok, reason = vehicle.mount(100, 600)
        assert ok is False
        assert "차량" in reason

    def test_dismount_basic(self):
        """기본 하차"""
        vid = _make_vehicle()
        morld.register_unit(100, name="Driver", location=(2, 4))
        vehicle.mount(100, vid)

        result = vehicle.dismount(100, vid)
        assert result is True
        assert morld.get_unit_prop(vid, "seated_by:driver") == -1

    def test_dismount_not_passenger(self):
        """탑승하지 않은 캐릭터 하차 시도"""
        vid = _make_vehicle()
        morld.register_unit(100, name="Char", location=(2, 4))
        result = vehicle.dismount(100, vid)
        assert result is False

    def test_dismount_all(self):
        """전원 하차"""
        vid = _make_vehicle()
        morld.register_unit(100, name="A", location=(2, 4))
        morld.register_unit(101, name="B", location=(2, 4))
        vehicle.mount(100, vid)
        vehicle.mount(101, vid)

        ejected = vehicle.dismount_all(vid)
        assert len(ejected) == 2
        assert 100 in ejected
        assert 101 in ejected
        assert vehicle.get_passengers(vid) == []

    def test_find_empty_seat_prefer_driver(self):
        """빈 좌석 탐색 — 운전석 우선"""
        vid = _make_vehicle()
        seat = vehicle.find_empty_seat(vid, prefer_driver=True)
        assert seat == "driver"

    def test_find_empty_seat_no_prefer(self):
        """빈 좌석 탐색 — passenger 우선"""
        vid = _make_vehicle()
        seat = vehicle.find_empty_seat(vid, prefer_driver=False)
        assert seat == "passenger1"  # passenger 우선

    def test_get_driver(self):
        """운전자 조회"""
        vid = _make_vehicle()
        assert vehicle.get_driver(vid) is None
        morld.set_unit_prop(vid, "seated_by:driver", 100)
        assert vehicle.get_driver(vid) == 100

    def test_can_drive(self):
        """운전 가능 여부 (운전석 점유 + driver_seat prop)"""
        vid = _make_vehicle()
        assert vehicle.can_drive(vid) is False  # 운전석 비어있음
        morld.register_unit(100, name="A", location=(2, 4))
        vehicle.mount(100, vid, seat_name="driver")
        assert vehicle.can_drive(vid) is True  # 운전석 점유


# ============================================
# Part H: control_target + 차량 이동
# ============================================

class TestControlTarget(_T):

    def test_set_and_get_control_target(self):
        """control_target prop 설정/조회"""
        morld.register_unit(1, name="Player")
        vid = _make_vehicle()

        assert vehicle.get_control_target(1) is None
        vehicle.set_control_target(1, vid)
        assert vehicle.get_control_target(1) == vid
        vehicle.clear_control_target(1)
        assert vehicle.get_control_target(1) is None

    def test_player_mount_auto_control_target(self):
        """플레이어가 운전석 탑승 시 control_target 자동 전환"""
        vid = _make_vehicle()
        morld.register_unit(1, name="Player", location=(2, 4))

        ok, seat = vehicle.player_mount(1, vid)
        assert ok is True
        assert seat == "driver"
        assert vehicle.get_control_target(1) == vid

    def test_player_mount_passenger_no_control(self):
        """플레이어가 동승석 탑승 시 control_target 변경 안 됨"""
        vid = _make_vehicle()
        morld.register_unit(1, name="Player", location=(2, 4))

        ok, seat = vehicle.player_mount(1, vid, seat_name="passenger1")
        assert ok is True
        assert seat == "passenger1"
        assert vehicle.get_control_target(1) is None

    def test_player_dismount_clears_control_target(self):
        """플레이어 하차 시 control_target 해제"""
        vid = _make_vehicle()
        morld.register_unit(1, name="Player", location=(2, 4))

        vehicle.player_mount(1, vid)
        assert vehicle.get_control_target(1) == vid

        vehicle.player_dismount(1, vid)
        assert vehicle.get_control_target(1) is None


class TestVehicleMoveTo(_T):

    def _setup_driving(self, vid=500, fuel=40, driver_id=100):
        """운전 준비된 차량 반환"""
        vid = _make_vehicle(vid=vid, fuel=fuel)
        _instances[vid] = "vehicle_obj"  # relocate_object용
        register_location_object(2, 4, vid)
        morld.register_unit(driver_id, name="Driver", location=(2, 4))
        vehicle.mount(driver_id, vid, seat_name="driver")
        return vid

    def test_move_basic(self):
        """기본 이동 — 차량+운전자 위치 변경"""
        vid = self._setup_driving()
        result = vehicle.vehicle_move_to(vid, 3, 1, 20)

        assert result["success"] is True
        assert result["fuel_consumed"] > 0
        assert result["travel_time_ms"] > 0

        # 차량 위치 확인
        loc = morld.get_unit_location(vid)
        assert loc[0] == 3 and loc[1] == 1

        # 운전자 위치도 같이 이동
        driver_loc = morld.get_unit_location(100)
        assert driver_loc[0] == 3 and driver_loc[1] == 1

    def test_move_with_passengers(self):
        """탑승자 전원 함께 이동"""
        vid = self._setup_driving()
        morld.register_unit(101, name="Passenger", location=(2, 4))
        vehicle.mount(101, vid, seat_name="passenger1")

        vehicle.vehicle_move_to(vid, 3, 1, 20)

        # 탑승자도 이동
        p_loc = morld.get_unit_location(101)
        assert p_loc[0] == 3 and p_loc[1] == 1

        # 탑승 상태 유지 (하차 안 됨)
        assert morld.get_unit_prop(vid, "seated_by:driver") == 100
        assert morld.get_unit_prop(vid, "seated_by:passenger1") == 101

    def test_move_no_driver(self):
        """운전자 없으면 이동 실패"""
        vid = _make_vehicle()
        result = vehicle.vehicle_move_to(vid, 3, 1, 20)
        assert result["success"] is False
        assert "운전자" in result["message"]

    def test_move_insufficient_fuel(self):
        """연료 부족 시 이동 실패 + 연료 미소비"""
        vid = self._setup_driving(fuel=1, driver_id=100)
        result = vehicle.vehicle_move_to(vid, 3, 1, 100)  # 큰 거리

        assert result["success"] is False
        assert "연료" in result["message"]
        assert result["fuel_consumed"] == 0
        # 위치 변경 없음
        loc = morld.get_unit_location(vid)
        assert loc[0] == 2 and loc[1] == 4

    def test_move_disabled_vehicle(self):
        """기동불가 차량 이동 실패"""
        vid = self._setup_driving()
        morld.set_unit_prop(vid, "vehicle:status", "disabled")

        result = vehicle.vehicle_move_to(vid, 3, 1, 20)
        assert result["success"] is False

    def test_move_fuel_consumption(self):
        """이동 거리에 비례한 연료 소비"""
        vid = self._setup_driving(fuel=40)
        result = vehicle.vehicle_move_to(vid, 3, 1, 20)

        # fuel_rate=0.5, distance=20 → cost=10
        assert result["fuel_consumed"] == 10.0
        assert vehicle.get_fuel(vid) == 30.0

    def test_move_travel_time_speed(self):
        """속도에 반비례하는 이동시간"""
        vid = self._setup_driving()
        result = vehicle.vehicle_move_to(vid, 3, 1, 20)

        # speed=3.0, distance=20 → base=20*60000=1200000ms
        # travel_time = 1200000 / 3.0 = 400000ms
        assert result["travel_time_ms"] == 400_000

    def test_move_updates_location_index(self):
        """이동 후 location_objects 인덱스 갱신"""
        vid = self._setup_driving()

        assert vid in get_location_objects(2, 4)

        vehicle.vehicle_move_to(vid, 3, 1, 20)

        assert vid not in get_location_objects(2, 4)
        assert vid in get_location_objects(3, 1)


# ============================================
# Part I: 주유 시스템 (find_nearby + refuel)
# ============================================

class TestFindNearbyVehicle(_T):

    def test_find_vehicle_same_location(self):
        """같은 location의 차량 탐색"""
        vid = _make_vehicle()
        morld.register_unit(1, name="Player", location=(2, 4))
        found = vehicle.find_nearby_vehicle(1)
        assert found == vid

    def test_find_vehicle_different_location(self):
        """다른 location이면 None"""
        _make_vehicle()  # (2, 4)
        morld.register_unit(1, name="Player", location=(0, 0))
        found = vehicle.find_nearby_vehicle(1)
        assert found is None

    def test_find_vehicle_seated(self):
        """탑승 중이면 탑승 차량 반환"""
        vid = _make_vehicle()
        morld.register_unit(1, name="Player", location=(2, 4))
        vehicle.mount(1, vid, seat_name="driver")
        found = vehicle.find_nearby_vehicle(1)
        assert found == vid

    def test_find_vehicle_no_vehicles(self):
        """차량 없으면 None"""
        morld.register_unit(1, name="Player", location=(0, 0))
        found = vehicle.find_nearby_vehicle(1)
        assert found is None


class TestRefuelLogic(_T):

    def test_calculate_refuel_cost(self):
        """주유 비용 계산"""
        vid = _make_vehicle(fuel=10, fuel_max=40)
        needed, cost = vehicle.calculate_refuel_cost(vid)
        assert needed == 30
        assert cost == 60  # 30 * 2(FUEL_PRICE_PER_LITER)

    def test_calculate_refuel_cost_full(self):
        """만탱이면 0"""
        vid = _make_vehicle(fuel=40, fuel_max=40)
        needed, cost = vehicle.calculate_refuel_cost(vid)
        assert needed == 0
        assert cost == 0

    def test_refuel_from_pump(self):
        """주유소 주유 — 만탱"""
        vid = _make_vehicle(fuel=10, fuel_max=40)
        result = vehicle.refuel_from_pump(vid)
        assert result is not None
        assert result["amount"] == 30
        assert result["cost"] == 60
        assert vehicle.get_fuel(vid) == 40

    def test_refuel_from_pump_already_full(self):
        """만탱이면 None"""
        vid = _make_vehicle(fuel=40, fuel_max=40)
        result = vehicle.refuel_from_pump(vid)
        assert result is None

    def test_refuel_from_jerrycan_basic(self):
        """제리캔 주유 — 기본 10L"""
        vid = _make_vehicle(fuel=25, fuel_max=40)
        result = vehicle.refuel_from_jerrycan(vid)
        assert result["amount"] == 10
        assert result["remaining_jerrycan_fuel"] == 0
        assert vehicle.get_fuel(vid) == 35

    def test_refuel_from_jerrycan_partial(self):
        """제리캔 주유 — 남은 용량 < 제리캔"""
        vid = _make_vehicle(fuel=35, fuel_max=40)
        result = vehicle.refuel_from_jerrycan(vid)
        assert result["amount"] == 5  # 5L만 충전 가능
        assert result["remaining_jerrycan_fuel"] == 5
        assert vehicle.get_fuel(vid) == 40

    def test_refuel_from_jerrycan_full(self):
        """만탱이면 0"""
        vid = _make_vehicle(fuel=40, fuel_max=40)
        result = vehicle.refuel_from_jerrycan(vid)
        assert result["amount"] == 0
        assert result["remaining_jerrycan_fuel"] == 10

    def test_refuel_from_jerrycan_custom_fuel(self):
        """제리캔 잔량 지정"""
        vid = _make_vehicle(fuel=30, fuel_max=40)
        result = vehicle.refuel_from_jerrycan(vid, jerrycan_fuel=3)
        assert result["amount"] == 3
        assert result["remaining_jerrycan_fuel"] == 0
        assert vehicle.get_fuel(vid) == 33
