# test_inspect.py — 점검/취미 활동 단위 테스트
"""
v0.2.4 자원 수집 리팩토링 검증:
1. scan_faction_needs — 세력 매칭 need 스캔
2. reserve/release/is_need_reserved — 소프트 예약 시스템
3. handle_inspect — 점검 핸들러 phase 전환
4. hobby mode — 취미 활동 storing 스킵
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

# events
_events = sys.modules.get("events") or types.ModuleType("events")
_events.subscribe_time_elapsed = lambda callback, min_interval=0: None
_events.on_game_start = lambda f: f
_events.on_reach = lambda f: f
_events.on_leave = lambda f: f
sys.modules.setdefault("events", _events)
for _sub in ["events.game_start", "events.scripts",
             "events.game_start.prologue", "events.scripts.player_creation"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

if not hasattr(morld, "register_script"):
    morld.register_script = lambda func: func
if not hasattr(morld, "get_region_info"):
    morld.get_region_info = lambda r: {"locations": []}

# survival
_survival = sys.modules.get("survival") or types.ModuleType("survival")
_survival.is_npc_hungry = lambda uid: False
_survival.is_npc_fainted = lambda uid: False
_survival.get_faint_remaining_millis = lambda uid: 0
_survival.is_npc_exhausted = lambda uid: False
_survival.get_exhaustion_remaining_millis = lambda uid: 0
_survival.is_npc_sleeping = lambda uid: False
_survival.get_health = lambda uid: 100
_survival.get_max_health = lambda uid: 100
_survival.npc_eat = lambda uid, sat: None
_survival.register_npc = lambda uid: None
sys.modules["survival"] = _survival

# temperature
_temperature = sys.modules.get("temperature") or types.ModuleType("temperature")
_temperature.is_cold = lambda uid, threshold=35.5: False
_temperature.is_hot = lambda uid, threshold=37.5: False
_temperature.get_insulation_total = lambda uid: 0
_temperature._get_equip_prop_total = lambda uid, prop: 0
_temperature.register_character = lambda uid: None
sys.modules["temperature"] = _temperature

# humidity
_humidity = sys.modules.get("humidity") or types.ModuleType("humidity")
_humidity.is_raining = lambda: False
_humidity.get_unit_wetness = lambda uid: 0
sys.modules["humidity"] = _humidity

# equipment
_equipment = sys.modules.get("equipment") or types.ModuleType("equipment")
_equipment.get_equipped_items = lambda uid: []
_equipment.equip_item = lambda uid, iid: True
_equipment.unequip_item = lambda uid, iid: True
sys.modules["equipment"] = _equipment

# needs
_needs = sys.modules.get("needs") or types.ModuleType("needs")
_needs.is_npc_need_excretion = lambda uid: False
_needs.is_npc_need_sleep = lambda uid: False
_needs.is_npc_need_bath = lambda uid: False
_needs.get_longing = lambda uid, name: 0
_needs.get_max_longing = lambda uid: 0
_needs.reduce_longing = lambda uid, name, amount=None: None
_needs.get_arousal = lambda uid: 0
_needs.get_fatigue = lambda uid: 0
_needs.set_excretion = lambda uid, val: None
_needs.set_cleanliness = lambda uid, val: None
_needs.register_character = lambda uid: None
sys.modules["needs"] = _needs

# sound
_sound = sys.modules.get("sound") or types.ModuleType("sound")
_sound.emit_sound = lambda uid, stype: None
_sound.get_heard = lambda uid: []
_sound.get_heard_by_category = lambda uid, cat: []
sys.modules["sound"] = _sound

# pregnancy
_pregnancy = sys.modules.get("pregnancy") or types.ModuleType("pregnancy")
_pregnancy.is_pregnant = lambda uid: False
_pregnancy.get_pregnancy_week = lambda uid: None
_pregnancy.check_pending_pregnancy_events = lambda uid: None
_pregnancy.register_character = lambda uid: None
sys.modules["pregnancy"] = _pregnancy

# romance
_romance = sys.modules.get("romance") or types.ModuleType("romance")
_romance.clear_all_semen = lambda uid: None
_romance.get_semen_total = lambda uid: 0
sys.modules["romance"] = _romance

# pollution
_pollution = sys.modules.get("pollution") or types.ModuleType("pollution")
_pollution._location_pollution = {}
_pollution.get_unit_pollution = lambda uid: 0
sys.modules["pollution"] = _pollution

# congestion
_congestion = sys.modules.get("congestion") or types.ModuleType("congestion")
sys.modules["congestion"] = _congestion

# restraint
_restraint = sys.modules.get("restraint") or types.ModuleType("restraint")
_restraint.is_restrained = lambda uid: False
_restraint.is_upper_restrained = lambda uid: False
_restraint.is_lower_restrained = lambda uid: False
_restraint.is_gagged = lambda uid: False
_restraint.is_blindfolded = lambda uid: False
_restraint.can_use_hands = lambda uid: True
_restraint.get_restrained_units_at = lambda rid, loc: []
sys.modules.setdefault("restraint", _restraint)

# carry
_carry = sys.modules.get("carry") or types.ModuleType("carry")
_carry.is_being_carried = lambda uid: False
_carry.get_carrier = lambda uid: None
_carry.is_carrying = lambda uid: False
_carry.get_carried_unit = lambda uid: None
_carry.get_carry_method = lambda uid: None
sys.modules.setdefault("carry", _carry)

# laundry
_laundry = sys.modules.get("laundry") or types.ModuleType("laundry")
_laundry.is_npc_need_laundry = lambda uid: False
sys.modules.setdefault("laundry", _laundry)

# fuel
_fuel = sys.modules.get("fuel") or types.ModuleType("fuel")
_fuel._fuel_sources = {}
_fuel.find_heat_source_needing_fuel = lambda uid: None
_fuel.get_sources_in_region = lambda region_id: []
sys.modules.setdefault("fuel", _fuel)

# assets.objects
_assets_objects = sys.modules.get("assets.objects") or types.ModuleType("assets.objects")
_assets_objects._location_objects = {}
_assets_objects.get_instance = lambda obj_id: None
_assets_objects.get_location_objects = lambda r, l: []
sys.modules["assets.objects"] = _assets_objects

for _sub in ["assets.objects.furniture", "assets.objects.scavenge",
             "assets.objects.nature", "assets.objects.outdoor",
             "assets.objects.grounds", "assets.objects.garden"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

# assets.registry
_assets_registry = sys.modules.get("assets.registry") or types.ModuleType("assets.registry")
_unique_id_map = {}
_assets_registry.get_unique_id = lambda iid: _unique_id_map.get(iid)
_assets_registry.get_instance_id = lambda uid: None
_assets_registry.get_or_create_item_id = lambda uid: None
_assets_registry.get_item_class = lambda uid: None
sys.modules.setdefault("assets.registry", _assets_registry)

# assets — package
sys.modules.setdefault("assets", types.ModuleType("assets"))
sys.modules.setdefault("assets.characters", types.ModuleType("assets.characters"))
sys.modules.setdefault("assets.locations", types.ModuleType("assets.locations"))

# gender
_gender = sys.modules.get("gender") or types.ModuleType("gender")
_gender.get_gender = lambda uid: "female"
sys.modules.setdefault("gender", _gender)

# ============================================
# 4. think 모듈 import
# ============================================

# test_combat/test_creature가 sys.modules["think"]를 stub으로 교체하므로
# 실제 think 패키지를 다시 로드해야 함
_think_stub = sys.modules.get("think")
if _think_stub and not hasattr(_think_stub, "__file__"):
    # stub module (types.ModuleType)이면 제거 → 실제 패키지 재import
    for _k in list(sys.modules):
        if _k == "think" or _k.startswith("think."):
            del sys.modules[_k]

from think import BaseAgent
import think as _think_module
import think.handlers.eat as _eat_module
from think.activities.helpers import (
    scan_faction_needs, reserve_need, release_need, is_need_reserved,
    get_object_x_from_info,
)
# facility resolver stub
import think.facility_resolver as _facility

# ============================================
# 5. 테스트 상수 + 헬퍼
# ============================================

NPC_ID = 100
STORAGE_ID = 200
_H = 3_600_000
_M = 60_000


class InspectAgent(BaseAgent):
    """테스트용 최소 Agent"""
    owner_unique_id = "test_npc"
    _home_region_id = 0

    _SCHEDULE = [
        {"name": "점검", "start": 9 * _H, "end": 10 * _H,
         "activity": "점검", "region_id": 0, "location_id": 0, "x": 90},
        {"name": "오후활동", "start": 10 * _H, "end": 18 * _H,
         "activity": "휴식", "region_id": 0, "location_id": 0, "x": 0},
        {"name": "수면", "start": 22 * _H, "end": 6 * _H,
         "activity": "수면", "region_id": 0, "location_id": 1, "x": 0},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.schedule_stack = [list(self._SCHEDULE)]


def _register_test_map():
    morld.add_region(0, "테스트리전")
    for loc_id in range(5):
        morld.add_location(0, loc_id, f"테스트방{loc_id}", length=200)
    for loc_id in range(4):
        morld.add_gate(0, loc_id, loc_id * 2 + 1, 200, 0, loc_id + 1, 0)
        morld.add_gate(0, loc_id + 1, loc_id * 2 + 2, 0, 0, loc_id, 200)


def _reset_all():
    morld.reset()
    morld.register_script = lambda func: func
    _register_test_map()

    _survival.is_npc_hungry = lambda uid: False
    _survival.is_npc_fainted = lambda uid: False
    _survival.get_faint_remaining_millis = lambda uid: 0
    _survival.is_npc_exhausted = lambda uid: False
    _survival.get_exhaustion_remaining_millis = lambda uid: 0
    _survival.is_npc_sleeping = lambda uid: False

    _temperature.is_cold = lambda uid, threshold=35.5: False
    _temperature.is_hot = lambda uid, threshold=37.5: False

    _humidity.is_raining = lambda: False
    _humidity.get_unit_wetness = lambda uid: 0

    _equipment.get_equipped_items = lambda uid: []

    _needs.is_npc_need_excretion = lambda uid: False
    _needs.is_npc_need_sleep = lambda uid: False
    _needs.is_npc_need_bath = lambda uid: False
    _needs.get_longing = lambda uid, name: 0
    _needs.get_max_longing = lambda uid: 0
    _needs.get_arousal = lambda uid: 0
    _needs.get_fatigue = lambda uid: 0

    _romance.get_semen_total = lambda uid: 0

    _restraint.is_restrained = lambda uid: False
    _restraint.can_use_hands = lambda uid: True
    _restraint.get_restrained_units_at = lambda rid, loc: []

    _fuel._fuel_sources.clear()

    _assets_objects._location_objects = {}
    _assets_objects.get_instance = lambda obj_id: None

    _unique_id_map.clear()

    # think module patches (test_think_logic와 동일)
    _eat_module._find_npc_food = lambda uid: None
    _think_module._find_food_in_container = lambda uid: None
    _think_module._is_dressed = lambda uid: True

    _facility.resolve_wardrobe = lambda agent, cross_region=False: None
    _facility.resolve_bath = lambda agent, cross_region=False: None
    _facility.resolve_toilet = lambda agent, cross_region=False: None
    _facility.resolve_washer = lambda agent, cross_region=False: None
    _facility.resolve_dryer = lambda agent, cross_region=False: None


def _create_agent(time_millis=9 * _H + 30 * _M, location=(0, 0)):
    _reset_all()
    morld._time = time_millis
    morld.register_unit(NPC_ID, "TestNPC", location=location,
                        props={"세력": "숲속 저택"})
    morld.set_unit_prop(NPC_ID, "can:sleep", 1)
    agent = InspectAgent(NPC_ID)
    return agent


class FakeStorageObject:
    """세력 + need prop을 가진 보관소 오브젝트 mock"""
    def __init__(self, obj_id, inventory=None):
        self.obj_id = obj_id
        self._inventory = inventory or {}

    def get_item_count(self, item_uid):
        return self._inventory.get(item_uid, 0)


def _setup_storage(agent, obj_id, faction, needs, inventory=None, location=(0, 0)):
    """보관소 오브젝트를 mock 등록"""
    r, l = location
    props = {"세력": faction}
    for item_uid, threshold in needs.items():
        props[f"need:{item_uid}"] = threshold
    morld.register_unit(obj_id, "Storage", location=location,
                        is_object=True, props=props)
    morld.set_unit_position(obj_id, 90)

    fake_obj = FakeStorageObject(obj_id, inventory or {})
    _assets_objects._location_objects[(r, l)] = \
        _assets_objects._location_objects.get((r, l), []) + [obj_id]

    old_get = _assets_objects.get_instance
    def _get(oid, _old=old_get, _fake=fake_obj, _target=obj_id):
        if oid == _target:
            return _fake
        return _old(oid)
    _assets_objects.get_instance = _get

    return fake_obj


# ============================================
# A. TestScanFactionNeeds
# ============================================

class TestScanFactionNeeds:
    def test_empty_when_no_objects(self):
        """오브젝트 없으면 빈 리스트"""
        agent = _create_agent()
        needs = scan_faction_needs(agent)
        assert needs == [], f"Expected empty, got {needs}"

    def test_finds_needs_same_faction(self):
        """같은 세력 오브젝트의 need를 감지"""
        agent = _create_agent()
        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 2})
        needs = scan_faction_needs(agent)
        assert len(needs) == 1, f"Expected 1 need, got {len(needs)}"
        assert needs[0]["item_uid"] == "food_fish"
        assert needs[0]["current"] == 2
        assert needs[0]["threshold"] == 5

    def test_ignores_different_faction(self):
        """다른 세력 오브젝트는 무시"""
        agent = _create_agent()
        _setup_storage(agent, STORAGE_ID, "도시",
                       {"food_fish": 5}, {"food_fish": 0})
        needs = scan_faction_needs(agent)
        assert needs == [], f"Expected empty for different faction, got {needs}"

    def test_ignores_sufficient_items(self):
        """충분한 아이템은 need로 감지하지 않음"""
        agent = _create_agent()
        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 3}, {"food_fish": 5})
        needs = scan_faction_needs(agent)
        assert needs == [], f"Expected empty when sufficient, got {needs}"

    def test_multiple_needs(self):
        """여러 need를 동시에 감지"""
        agent = _create_agent()
        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5, "log": 3},
                       {"food_fish": 1, "log": 0})
        needs = scan_faction_needs(agent)
        assert len(needs) == 2, f"Expected 2 needs, got {len(needs)}"
        uids = {n["item_uid"] for n in needs}
        assert "food_fish" in uids
        assert "log" in uids

    def test_no_faction_prop_returns_empty(self):
        """NPC에 세력 prop 없으면 빈 리스트"""
        agent = _create_agent()
        morld.set_unit_prop(NPC_ID, "세력", None)
        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 0})
        needs = scan_faction_needs(agent)
        assert needs == [], f"Expected empty without faction, got {needs}"


# ============================================
# B. TestReservation
# ============================================

class TestReservation:
    def test_reserve_and_check(self):
        """예약 → 다른 NPC가 예약 확인"""
        agent = _create_agent()
        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 0})
        OTHER_NPC = 999
        morld.register_unit(OTHER_NPC, "OtherNPC", props={"세력": "숲속 저택"})

        reserve_need(STORAGE_ID, "food_fish", NPC_ID)
        # NPC 자신은 통과
        assert not is_need_reserved(STORAGE_ID, "food_fish", NPC_ID)
        # 다른 NPC는 차단
        assert is_need_reserved(STORAGE_ID, "food_fish", OTHER_NPC)

    def test_release(self):
        """예약 해제 → 다른 NPC 통과"""
        agent = _create_agent()
        OTHER_NPC = 999
        morld.register_unit(STORAGE_ID, "Storage", is_object=True)
        morld.register_unit(OTHER_NPC, "OtherNPC")

        reserve_need(STORAGE_ID, "food_fish", NPC_ID)
        release_need(STORAGE_ID, "food_fish")
        assert not is_need_reserved(STORAGE_ID, "food_fish", OTHER_NPC)

    def test_expiry_after_2_hours(self):
        """2시간 경과 → 자동 해제"""
        agent = _create_agent()
        OTHER_NPC = 999
        morld.register_unit(STORAGE_ID, "Storage", is_object=True)
        morld.register_unit(OTHER_NPC, "OtherNPC")

        reserve_need(STORAGE_ID, "food_fish", NPC_ID)
        # 2시간 1분 후
        morld._time += 2 * _H + _M
        assert not is_need_reserved(STORAGE_ID, "food_fish", OTHER_NPC), \
            "Reservation should expire after 2 hours"

    def test_scan_excludes_reserved(self):
        """예약된 need는 scan에서 제외"""
        agent = _create_agent()
        OTHER_NPC = 999
        morld.register_unit(OTHER_NPC, "OtherNPC",
                            location=(0, 0), props={"세력": "숲속 저택"})
        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 0})

        # 다른 NPC가 예약
        reserve_need(STORAGE_ID, "food_fish", OTHER_NPC)

        # agent 스캔 → 제외됨
        needs = scan_faction_needs(agent)
        assert len(needs) == 0, f"Reserved need should be excluded, got {needs}"


# ============================================
# C. TestInspectHandler — Phase 전환
# ============================================

class TestInspectHandler:
    def test_idle_no_needs_inserts_idle_job(self):
        """need 없으면 idle job 삽입"""
        agent = _create_agent()
        entry = {"name": "점검", "start": 9 * _H, "end": 10 * _H,
                 "activity": "점검", "region_id": 0, "location_id": 0, "x": 90}
        from think.activities.inspect import handle_inspect
        handle_inspect(agent, entry)
        job = morld.get_current_job(NPC_ID)
        assert job is not None, "Should insert idle job"
        assert agent._activity_phase == "idle"

    def test_idle_with_need_transitions_to_delivering(self):
        """need 감지 + 인벤에 아이템 있으면 delivering으로 전환"""
        agent = _create_agent()
        agent._responsibility = 1.0  # 항상 통과
        agent._collectible_items = None  # 제한 없음

        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 0})

        # NPC 인벤토리에 food_fish 아이템 보유
        FISH_ITEM_ID = 500
        _unique_id_map[FISH_ITEM_ID] = "food_fish"
        morld.give_item(NPC_ID, FISH_ITEM_ID, 1)

        entry = {"name": "점검", "start": 9 * _H, "end": 10 * _H,
                 "activity": "점검", "region_id": 0, "location_id": 0, "x": 90}
        from think.activities.inspect import handle_inspect
        handle_inspect(agent, entry)

        assert agent._activity_phase == "supply_delivering", \
            f"Expected supply_delivering, got {agent._activity_phase}"

    def test_idle_collectible_filter(self):
        """_collectible_items에 없는 아이템은 수집 안 함"""
        agent = _create_agent()
        agent._responsibility = 1.0
        agent._collectible_items = {"log"}  # food_fish 불가

        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 0})

        entry = {"name": "점검", "start": 9 * _H, "end": 10 * _H,
                 "activity": "점검", "region_id": 0, "location_id": 0, "x": 90}
        from think.activities.inspect import handle_inspect
        handle_inspect(agent, entry)

        # food_fish는 collectible에 없으므로 idle 유지
        assert agent._activity_phase == "idle", \
            f"Expected idle (filtered out), got {agent._activity_phase}"

    def test_responsibility_zero_skips(self):
        """_responsibility=0 → 확률 미통과 → idle 대기"""
        agent = _create_agent()
        agent._responsibility = 0.0  # 항상 미통과

        _setup_storage(agent, STORAGE_ID, "숲속 저택",
                       {"food_fish": 5}, {"food_fish": 0})

        entry = {"name": "점검", "start": 9 * _H, "end": 10 * _H,
                 "activity": "점검", "region_id": 0, "location_id": 0, "x": 90}
        from think.activities.inspect import handle_inspect
        handle_inspect(agent, entry)

        assert agent._activity_phase == "idle"
        job = morld.get_current_job(NPC_ID)
        assert job is not None, "Should insert idle job on skip"


# ============================================
# D. TestHobbyMode
# ============================================

class TestHobbyMode:
    def test_tool_activity_hobby_skips_storing(self):
        """취미 모드에서 storing phase → returning_tool로 직행"""
        agent = _create_agent(time_millis=10 * _H)
        agent._activity_phase = "storing"

        cfg = {
            "activity_name": "취미낚시",
            "mode": "hobby",
            "storage_need": ("food_ingredient", "food_fish", 3),
            "store_categories": ["food_ingredient"],
            "store_resolve": ["food_ingredient"],
            "store_label": "보관",
            "capability": "can:fish",
            "work_method": "npc_fish",
            "sound_id": "splash",
            "action_key": "fish",
            "resolve": "낚시",
        }

        entry = {"name": "취미낚시", "start": 10 * _H, "end": 12 * _H,
                 "activity": "취미낚시"}
        from think.activities.tool_activity import handle_tool_activity
        handle_tool_activity(agent, entry, cfg)

        assert agent._activity_phase == "returning_tool", \
            f"Hobby mode storing should go to returning_tool, got {agent._activity_phase}"

    def test_resource_activity_hobby_skips_storing(self):
        """취미 채집 모드에서 storing phase → idle로 직행"""
        agent = _create_agent(time_millis=10 * _H)
        agent._activity_phase = "storing"

        cfg = {
            "activity_name": "취미채집",
            "mode": "hobby",
            "resolve_target": lambda a: None,
            "do_work": lambda a, t: None,
            "action_key": "gather",
            "work_label": "채집",
            "store_categories": ["food_ingredient"],
            "store_resolve": ["food_ingredient"],
            "store_label": "보관",
        }

        entry = {"name": "취미채집", "start": 10 * _H, "end": 12 * _H,
                 "activity": "취미채집"}
        from think.activities.resource_activity import handle_resource_activity
        handle_resource_activity(agent, entry, cfg)

        assert agent._activity_phase == "idle", \
            f"Hobby resource storing should go to idle, got {agent._activity_phase}"

    def test_hobby_mode_idle_skips_storage_need(self):
        """취미 모드에서 idle phase → storage_need 체크 스킵"""
        agent = _create_agent(time_millis=10 * _H)
        agent._activity_phase = "idle"

        cfg = {
            "activity_name": "취미낚시",
            "mode": "hobby",
            "storage_need": ("food_ingredient", "food_fish", 3),
            "store_categories": ["food_ingredient"],
            "store_resolve": ["food_ingredient"],
            "store_label": "보관",
            "capability": "can:fish",
            "work_method": "npc_fish",
            "sound_id": "splash",
            "action_key": "fish",
            "resolve": "낚시",
        }

        entry = {"name": "취미낚시", "start": 10 * _H, "end": 12 * _H,
                 "activity": "취미낚시"}
        from think.activities.tool_activity import handle_tool_activity

        # storage에 food_fish가 충분해도 취미 모드는 실행 (check 스킵)
        # 도구가 없으면 다음 phase 못 감 → idle 유지 확인
        handle_tool_activity(agent, entry, cfg)
        # 도구 없으면 idle 유지 (tool missing)
        assert agent._activity_phase == "idle"


# ============================================
# E. TestScheduleConditions — 레거시 정리 확인
# ============================================

class TestScheduleConditions:
    def test_removed_conditions_return_false(self):
        """제거된 need_* 조건들은 False 반환"""
        agent = _create_agent()
        removed = ["need_fish", "need_logs", "need_food",
                    "need_supplies", "need_wood_chip", "need_fuel_material"]
        for cond in removed:
            result = agent._evaluate_condition(cond)
            assert result is False, \
                f"Removed condition '{cond}' should return False, got {result}"

    def test_kept_conditions_exist(self):
        """유지된 조건들은 에러 없이 평가 가능"""
        agent = _create_agent()
        kept = ["can_cook", "should_clean", "need_fuel"]
        for cond in kept:
            # 에러 없이 평가만 되면 OK (True/False 무관)
            result = agent._evaluate_condition(cond)
            assert isinstance(result, bool), \
                f"Condition '{cond}' should return bool, got {type(result)}"
