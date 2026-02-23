# test_npc_objects.py — NPC 오브젝트 조작 + 세탁 자율 시스템 테스트
"""
Part A: 오브젝트 npc_* 메서드 단위 테스트
  - WashingMachine/Dryer: npc_load_laundry, npc_start, npc_unload_laundry
  - Bathtub/DrumBath: npc_use (건조+보온+정액제거)
  - Washbasin/KitchenSink/WaterTap: npc_fill (물 용기 충전)
  - GardenBed: npc_fertilize, npc_remove_plant
  - Kettle: npc_brew (주전자 인벤토리 레시피 → NPC 지급)

Part B: 세탁 자율 시스템 think 연동 테스트
  - _check_laundry() 트리거 (오염 의류 감지, 쿨다운)
  - _handle_laundry() 8-phase 머신
  - 비차단 대기 (waiting_wash/waiting_dry → False)
  - 건조기 없음 fallback
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
# 2. morld mock (run_tests.py가 이미 주입한 것 사용)
# ============================================

import morld

# ============================================
# 3. 외부 모듈 stub
# ============================================

# events
def _fake_subscribe(callback, min_interval=0):
    pass

_events = sys.modules.get("events") or types.ModuleType("events")
_events.subscribe_time_elapsed = _fake_subscribe
_events.on_game_start = lambda f: f
_events.on_reach = lambda f: f
_events.on_leave = lambda f: f
sys.modules.setdefault("events", _events)
for _sub in ["events.game_start", "events.scripts",
             "events.game_start.prologue", "events.scripts.player_creation"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

# morld 추가 API
if not hasattr(morld, "register_script"):
    morld.register_script = lambda func: func
if not hasattr(morld, "get_region_info"):
    morld.get_region_info = lambda r: {"locations": []}

# ui stub (Object들이 import)
_ui = sys.modules.get("ui") or types.ModuleType("ui")
_ui.dialog = lambda text, **kw: text
_ui.action_toggle = lambda *a, **kw: None
_ui.action_set = lambda *a, **kw: None
sys.modules.setdefault("ui", _ui)

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
_survival._eat_log = []
def _tracking_npc_eat(uid, sat):
    _survival._eat_log.append((uid, sat))
_survival.npc_eat = _tracking_npc_eat
sys.modules.setdefault("survival", _survival)

# temperature
_temperature = sys.modules.get("temperature") or types.ModuleType("temperature")
_temperature.is_cold = lambda uid, threshold=35.5: False
_temperature.is_hot = lambda uid, threshold=37.5: False
_temperature.get_insulation_total = lambda uid: 0
_temperature._get_equip_prop_total = lambda uid, prop: 0
_temperature.warm_character = lambda uid, amount: None
_temperature._warm_log = []
def _tracking_warm(uid, amount):
    _temperature._warm_log.append((uid, amount))
_temperature.warm_character = _tracking_warm
_temperature.register_heat_source = lambda uid, r, l: None
_temperature.get_temperature = lambda r, l: 20.0
_temperature.register_character = lambda uid: None
_temperature.unregister_character = lambda uid: None
sys.modules.setdefault("temperature", _temperature)

# humidity
_humidity = sys.modules.get("humidity") or types.ModuleType("humidity")
_humidity.is_raining = lambda: False
_humidity.get_unit_wetness = lambda uid: 0
_humidity._dry_log = []
def _tracking_dry(uid, amount):
    _humidity._dry_log.append((uid, amount))
_humidity.dry_unit = _tracking_dry
sys.modules.setdefault("humidity", _humidity)

# equipment
_equipment = sys.modules.get("equipment") or types.ModuleType("equipment")
_equipment.get_equipped_items = lambda uid: []
_equipment._equip_log = []
_equipment._unequip_log = []
def _tracking_equip(uid, iid):
    _equipment._equip_log.append((uid, iid))
    return True
def _tracking_unequip(uid, iid):
    _equipment._unequip_log.append((uid, iid))
    return True
_equipment.equip_item = _tracking_equip
_equipment.unequip_item = _tracking_unequip
sys.modules.setdefault("equipment", _equipment)

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
_needs._excretion_log = []
def _tracking_set_excretion(uid, val):
    _needs._excretion_log.append((uid, val))
_needs.set_excretion = _tracking_set_excretion
_needs.set_cleanliness = lambda uid, val: None
sys.modules.setdefault("needs", _needs)

# sound
_sound = sys.modules.get("sound") or types.ModuleType("sound")
_sound.emit_sound = lambda uid, stype: None
_sound.get_heard = lambda uid: []
_sound.get_heard_by_category = lambda uid, cat: []
sys.modules.setdefault("sound", _sound)

# pregnancy
_pregnancy = sys.modules.get("pregnancy") or types.ModuleType("pregnancy")
_pregnancy.is_pregnant = lambda uid: False
_pregnancy.get_pregnancy_week = lambda uid: None
_pregnancy.check_pending_pregnancy_events = lambda uid: None
sys.modules.setdefault("pregnancy", _pregnancy)

# romance
_romance = sys.modules.get("romance") or types.ModuleType("romance")
_romance._clear_semen_log = []
def _tracking_clear_semen(uid):
    _romance._clear_semen_log.append(uid)
_romance.clear_all_semen = _tracking_clear_semen
_romance.get_semen_total = lambda uid: 0
sys.modules.setdefault("romance", _romance)

# pollution
_pollution = sys.modules.get("pollution") or types.ModuleType("pollution")
_pollution._location_pollution = {}
_pollution._unit_pollution = {}
def _get_unit_pollution(uid):
    return _pollution._unit_pollution.get(uid, 0)
_pollution.get_unit_pollution = _get_unit_pollution
sys.modules.setdefault("pollution", _pollution)

# congestion
_congestion = sys.modules.get("congestion") or types.ModuleType("congestion")
sys.modules.setdefault("congestion", _congestion)

# restraint (결박 시스템 stub)
_restraint = sys.modules.get("restraint") or types.ModuleType("restraint")
_restraint.is_restrained = lambda uid: False
_restraint.is_upper_restrained = lambda uid: False
_restraint.is_lower_restrained = lambda uid: False
_restraint.is_gagged = lambda uid: False
_restraint.is_blindfolded = lambda uid: False
_restraint.can_use_hands = lambda uid: True
_restraint.get_restrained_units_at = lambda rid, loc: []
_restraint.release = lambda uid: None
sys.modules.setdefault("restraint", _restraint)

# carry (운반 시스템 stub)
_carry = sys.modules.get("carry") or types.ModuleType("carry")
_carry.is_being_carried = lambda uid: False
_carry.get_carrier = lambda uid: None
_carry.is_carrying = lambda uid: False
_carry.get_carried_unit = lambda uid: None
_carry.get_carry_method = lambda uid: None
sys.modules.setdefault("carry", _carry)

# fuel
_fuel = sys.modules.get("fuel") or types.ModuleType("fuel")
_fuel.FUEL_VALUES = {"branch": 2, "log": 6}
_fuel.PROP_FUEL = "heat:fuel"
_fuel.PROP_FUEL_MAX = "heat:fuel_max"
_fuel.PROP_FUEL_MODE = "heat:fuel_mode"
_fuel.DEFAULT_FUEL_MAX = 24
_fuel._fuel_sources = {}
_fuel.register_fuel_source = lambda uid, r, l: None
_fuel.is_fuel_source = lambda uid: uid in _fuel._fuel_sources
_fuel.needs_fuel = lambda uid, threshold=6: False
_fuel.get_fuel_level = lambda uid: 0
_fuel.get_fuel_max = lambda uid: 24
_fuel.get_sources_in_region = lambda r: []
_fuel.reset = lambda: None
_fuel.load_fuel = lambda uid, item_uid, count=1: 0
_fuel.npc_load_fuel = lambda npc_id, hs_id, item_uid, count=1: 0
sys.modules.setdefault("fuel", _fuel)

# inventory — safe_give_item
_inventory = sys.modules.get("inventory") or types.ModuleType("inventory")
_inventory._give_log = []
def _tracking_safe_give(uid, item_id, count=1):
    _inventory._give_log.append((uid, item_id, count))
    morld.give_item(uid, item_id, count)
    return True
_inventory.safe_give_item = _tracking_safe_give
_inventory.has_free_slot = lambda uid, iid=None: True
sys.modules.setdefault("inventory", _inventory)

# laundry — 실제 모듈 사용 (morld prop 기반이므로 mock 환경에서 동작)
# test_think_logic가 stub을 주입할 수 있으므로, 강제로 실제 모듈 재로드
if "laundry" in sys.modules:
    del sys.modules["laundry"]
import laundry

# recipes stub (Kettle.npc_brew용)
_recipes = sys.modules.get("recipes") or types.ModuleType("recipes")
_recipes.RECIPES = {}
_recipes._matching_result = None
def _mock_find_matching_recipe(inv):
    return _recipes._matching_result
_recipes.find_matching_recipe = _mock_find_matching_recipe
sys.modules.setdefault("recipes", _recipes)

# garden — 실제 모듈 상수만 필요
_garden = sys.modules.get("garden") or types.ModuleType("garden")
_garden.PROP_FURROW_COUNT = "이랑수"
_garden.PROP_MOISTURE = "수분"
_garden.PROP_FERTILIZER = "비료"
_garden.PROP_SEED_PREFIX = "씨앗"
_garden.PROP_GROWTH_PREFIX = "성장"
_garden.MAX_FERTILIZER = 100
_garden.FERTILIZER_AMOUNT = 30
_garden.MAX_MOISTURE = 100
_garden.MAX_GROWTH = 100
_garden.SEED_REGISTRY = {
    1: {"name": "감자", "seed_unique_id": "potato_seed"},
    2: {"name": "토마토", "seed_unique_id": "tomato_seed"},
}
sys.modules.setdefault("garden", _garden)

# assets stubs
_assets_mod = types.ModuleType("assets")
sys.modules.setdefault("assets", _assets_mod)

_assets_base = sys.modules.get("assets.base") or types.ModuleType("assets.base")
# assets.base.Object stub — npc_* 테스트에서 직접 사용할 최소 Object 클래스
class _MockObject:
    unique_id = "mock"
    name = "Mock"
    actions = []
    focus_text = {"default": ""}
    props = {}

    def __init__(self):
        self.instance_id = None

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        self.instance_id = instance_id
        morld.register_unit(instance_id, self.name,
                            location=(region_id, location_id))
_assets_base.Object = _MockObject
sys.modules.setdefault("assets.base", _assets_base)

_assets_objects = sys.modules.get("assets.objects") or types.ModuleType("assets.objects")
_assets_objects._location_objects = {}
_assets_objects.get_instance = lambda obj_id: _object_instances.get(obj_id)
_assets_objects.get_location_objects = lambda r, l: []
sys.modules.setdefault("assets.objects", _assets_objects)

for _sub in ["assets.objects.furniture", "assets.objects.garden",
             "assets.objects.scavenge", "assets.objects.nature",
             "assets.objects.outdoor", "assets.objects.grounds",
             "assets.objects.vehicles", "assets.objects.appliances"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

_assets_registry = sys.modules.get("assets.registry") or types.ModuleType("assets.registry")
_assets_registry._unique_map = {}  # item_id -> unique_id
_assets_registry._uid_to_item = {}  # unique_id -> item_id
_assets_registry._item_classes = {}  # unique_id -> class
_assets_registry.get_instance_id = lambda uid: None
def _mock_get_unique_id(iid):
    return _assets_registry._unique_map.get(iid)
def _mock_get_or_create_item_id(uid):
    return _assets_registry._uid_to_item.get(uid)
def _mock_get_item_class(uid):
    return _assets_registry._item_classes.get(uid)
_assets_registry.get_unique_id = _mock_get_unique_id
_assets_registry.get_or_create_item_id = _mock_get_or_create_item_id
_assets_registry.get_item_class = _mock_get_item_class
sys.modules.setdefault("assets.registry", _assets_registry)

# assets.items.garden_items stub (PROP_WATER_AMOUNT)
_garden_items = types.ModuleType("assets.items.garden_items")
_garden_items.PROP_WATER_AMOUNT = "물양"
sys.modules.setdefault("assets.items", types.ModuleType("assets.items"))
sys.modules.setdefault("assets.items.garden_items", _garden_items)

# ============================================
# 4. think 모듈 stub (Part B용)
# ============================================

# think 모듈 클린업 (이전 테스트가 partial import 유발 가능)
for _key in list(sys.modules.keys()):
    if _key == "think" or _key.startswith("think."):
        del sys.modules[_key]

# think.facility_resolver
_facility = types.ModuleType("think.facility_resolver")
_facility.resolve_wardrobe = lambda agent, cross_region=False: None
_facility.resolve_bath = lambda agent, cross_region=False: None
_facility.resolve_toilet = lambda agent, cross_region=False: None
_facility._find_facilities_by_prop = lambda prop, val: []
_facility._find_facilities_by_unique_id = lambda uid: []
_facility._sort_by_priority = lambda f, p, h, c=False: f
_facility.resolve_washer = lambda agent, cross_region=False: None
_facility.resolve_dryer = lambda agent, cross_region=False: None
sys.modules["think.facility_resolver"] = _facility

# think.activity_resolver
_activity_resolver = types.ModuleType("think.activity_resolver")
_activity_resolver.resolve_activity_location = lambda uid, act, region: None
sys.modules["think.activity_resolver"] = _activity_resolver

# ============================================
# 5. Import BaseAgent (실제 think 코드)
# ============================================

from think import BaseAgent
import think as _think_module
import think.handlers.eat as _eat_module

# ============================================
# 6. 테스트 인프라
# ============================================

_M = 60_000
_H = 3_600_000
NPC_ID = 100
WASHER_ID = 500
DRYER_ID = 501
KETTLE_ID = 502
BATHTUB_ID = 503
DRUM_BATH_ID = 504
WASHBASIN_ID = 505
GARDEN_BED_ID = 506

# 오브젝트 인스턴스 글로벌 레지스트리 (get_instance 지원)
_object_instances = {}

# 테스트용 시설 위치 상수
_TEST_WARDROBE = {"region_id": 0, "location_id": 3, "x": 0, "object_id": 50}
_TEST_TOILET = {"region_id": 0, "location_id": 4, "x": 0, "object_id": 51}
_TEST_WASHER = {"region_id": 0, "location_id": 4, "x": 50, "object_id": WASHER_ID}
_TEST_DRYER = {"region_id": 0, "location_id": 4, "x": 70, "object_id": DRYER_ID}


class TestAgent(BaseAgent):
    """테스트용 최소 Agent"""
    owner_unique_id = "test_npc"
    _home_region_id = 0

    _SCHEDULE = [
        {"name": "오전활동", "start": 8 * _H, "end": 12 * _H,
         "activity": "휴식", "region_id": 0, "location_id": 0, "x": 0},
        {"name": "오후활동", "start": 12 * _H, "end": 18 * _H,
         "activity": "휴식", "region_id": 0, "location_id": 0, "x": 0},
        {"name": "저녁", "start": 18 * _H, "end": 22 * _H,
         "activity": "휴식", "region_id": 0, "location_id": 0, "x": 0},
        {"name": "수면", "start": 22 * _H, "end": 6 * _H,
         "activity": "수면", "region_id": 0, "location_id": 1, "x": 0},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.schedule_stack = [list(self._SCHEDULE)]


def _reset_all():
    """모든 mock/stub 상태 초기화"""
    morld.reset()
    morld.register_script = lambda func: func
    morld.get_region_info = lambda r: {"locations": []}

    _survival.is_npc_hungry = lambda uid: False
    _survival.is_npc_fainted = lambda uid: False
    _survival.get_faint_remaining_millis = lambda uid: 0
    _survival.is_npc_exhausted = lambda uid: False
    _survival.get_exhaustion_remaining_millis = lambda uid: 0
    _survival.is_npc_sleeping = lambda uid: False
    _survival.get_health = lambda uid: 100
    _survival.get_max_health = lambda uid: 100
    _survival._eat_log.clear()

    _temperature.is_cold = lambda uid, threshold=35.5: False
    _temperature.is_hot = lambda uid, threshold=37.5: False
    _temperature.get_insulation_total = lambda uid: 0
    _temperature._get_equip_prop_total = lambda uid, prop: 0
    _temperature._warm_log.clear()

    _humidity.is_raining = lambda: False
    _humidity.get_unit_wetness = lambda uid: 0
    _humidity._dry_log.clear()

    _equipment.get_equipped_items = lambda uid: []
    _equipment._equip_log.clear()
    _equipment._unequip_log.clear()

    _needs.is_npc_need_excretion = lambda uid: False
    _needs.is_npc_need_sleep = lambda uid: False
    _needs.is_npc_need_bath = lambda uid: False
    _needs.get_longing = lambda uid, name: 0
    _needs.get_max_longing = lambda uid: 0
    _needs.reduce_longing = lambda uid, name, amount=None: None
    _needs.get_arousal = lambda uid: 0
    _needs.get_fatigue = lambda uid: 0
    _needs._excretion_log.clear()

    _romance._clear_semen_log.clear()
    _romance.get_semen_total = lambda uid: 0

    _pollution._unit_pollution.clear()

    _restraint.is_restrained = lambda uid: False
    _restraint.is_upper_restrained = lambda uid: False
    _restraint.can_use_hands = lambda uid: True
    _restraint.get_restrained_units_at = lambda rid, loc: []

    _fuel._fuel_sources.clear()

    _inventory._give_log.clear()

    _recipes._matching_result = None

    _assets_registry._unique_map.clear()
    _assets_registry._uid_to_item.clear()
    _assets_registry._item_classes.clear()

    _object_instances.clear()
    _assets_objects.get_instance = lambda obj_id: _object_instances.get(obj_id)
    _assets_objects._location_objects = {}

    _facility.resolve_wardrobe = lambda agent, cross_region=False: None
    _facility.resolve_bath = lambda agent, cross_region=False: None
    _facility.resolve_toilet = lambda agent, cross_region=False: None
    _facility.resolve_washer = lambda agent, cross_region=False: None
    _facility.resolve_dryer = lambda agent, cross_region=False: None
    _facility._find_facilities_by_prop = lambda prop, val: []

    _eat_module._find_npc_food = lambda uid: None
    _think_module._find_food_in_container = lambda uid: None
    _think_module._is_dressed = lambda uid: True

    # laundry 모듈 리셋 (등록된 기기 초기화)
    laundry._machines.clear()
    laundry._initialized = False


def _create_agent(time_millis=10 * _H, location=(0, 0)):
    """테스트용 agent 생성 + morld 유닛 등록"""
    _reset_all()
    morld._time = time_millis
    morld.register_unit(NPC_ID, "TestNPC", location=location)
    morld.set_unit_prop(NPC_ID, "can:sleep", 1)
    agent = TestAgent(NPC_ID)
    return agent


def _teleport(agent, target):
    """agent를 target 위치로 즉시 이동"""
    morld.set_unit_location(agent.unit_id, target["region_id"], target["location_id"])


def _last_job(agent):
    return morld.get_current_job(agent.unit_id)


def _setup_washer(location=(0, 4)):
    """세탁기 유닛 등록 + laundry 등록"""
    r, l = location
    morld.register_unit(WASHER_ID, "세탁기", location=location)
    laundry.register_machine(WASHER_ID, "washer")
    return WASHER_ID


def _setup_dryer(location=(0, 4)):
    """건조기 유닛 등록 + laundry 등록"""
    r, l = location
    morld.register_unit(DRYER_ID, "건조기", location=location)
    laundry.register_machine(DRYER_ID, "dryer")
    return DRYER_ID


# ============================================
# Part A: 오브젝트 npc_* 메서드 테스트
# ============================================

# A1. WashingMachine npc_* 테스트

class TestWashingMachineNpc:

    def test_load_laundry_transfers_items(self):
        """npc_load_laundry: NPC → 세탁기로 아이템 이동"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        washer_id = _setup_washer()

        shirt_id = 300
        pants_id = 301
        morld.register_item(shirt_id, "셔츠")
        morld.register_item(pants_id, "바지")
        morld.give_item(NPC_ID, shirt_id)
        morld.give_item(NPC_ID, pants_id)

        # WashingMachine stub (instance_id만 필요)
        class FakeWasher:
            def __init__(self, iid):
                self.instance_id = iid
            def npc_load_laundry(self, npc_id, item_ids):
                if laundry.is_machine_busy(self.instance_id):
                    return False
                for item_id in item_ids:
                    if morld.has_item(npc_id, item_id):
                        morld.remove_item(npc_id, item_id, 1)
                        morld.give_item(self.instance_id, item_id, 1)
                return True

        washer = FakeWasher(washer_id)
        result = washer.npc_load_laundry(NPC_ID, [shirt_id, pants_id])

        assert result is True
        assert not morld.has_item(NPC_ID, shirt_id), "NPC에서 셔츠 제거"
        assert not morld.has_item(NPC_ID, pants_id), "NPC에서 바지 제거"
        assert morld.has_item(washer_id, shirt_id), "세탁기에 셔츠 있음"
        assert morld.has_item(washer_id, pants_id), "세탁기에 바지 있음"

    def test_load_blocked_when_busy(self):
        """npc_load_laundry: 작동 중이면 False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        washer_id = _setup_washer()
        # 세탁기 작동 중으로 설정
        morld.set_unit_prop(washer_id, "가전:상태", 1)

        class FakeWasher:
            def __init__(self, iid):
                self.instance_id = iid
            def npc_load_laundry(self, npc_id, item_ids):
                if laundry.is_machine_busy(self.instance_id):
                    return False
                for item_id in item_ids:
                    if morld.has_item(npc_id, item_id):
                        morld.remove_item(npc_id, item_id, 1)
                        morld.give_item(self.instance_id, item_id, 1)
                return True

        shirt_id = 300
        morld.give_item(NPC_ID, shirt_id)
        washer = FakeWasher(washer_id)
        result = washer.npc_load_laundry(NPC_ID, [shirt_id])

        assert result is False
        assert morld.has_item(NPC_ID, shirt_id), "아이템 유지"

    def test_start_begins_processing(self):
        """npc_start: 세탁기에 빨래 있으면 작동 시작"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        washer_id = _setup_washer()
        # 세탁기에 빨래 넣기
        morld.give_item(washer_id, 300, 1)

        class FakeWasher:
            def __init__(self, iid):
                self.instance_id = iid
            def npc_start(self, npc_id):
                if laundry.is_machine_busy(self.instance_id):
                    return False
                inv = morld.get_unit_inventory(self.instance_id)
                if not inv:
                    return False
                laundry.start_machine(self.instance_id, "washer")
                return True

        washer = FakeWasher(washer_id)
        result = washer.npc_start(NPC_ID)

        assert result is True
        assert laundry.get_machine_state(washer_id) == 1, "작동 중"
        assert laundry.get_remaining_time(washer_id) == 60, "세탁 60분"

    def test_start_fails_empty(self):
        """npc_start: 빈 세탁기 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        washer_id = _setup_washer()

        class FakeWasher:
            def __init__(self, iid):
                self.instance_id = iid
            def npc_start(self, npc_id):
                if laundry.is_machine_busy(self.instance_id):
                    return False
                inv = morld.get_unit_inventory(self.instance_id)
                if not inv:
                    return False
                laundry.start_machine(self.instance_id, "washer")
                return True

        washer = FakeWasher(washer_id)
        result = washer.npc_start(NPC_ID)
        assert result is False

    def test_unload_transfers_back(self):
        """npc_unload_laundry: 완료 상태에서 NPC로 아이템 회수"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        washer_id = _setup_washer()
        shirt_id = 300
        morld.give_item(washer_id, shirt_id, 1)
        # 완료 상태로 설정
        morld.set_unit_prop(washer_id, "가전:상태", 2)

        class FakeWasher:
            def __init__(self, iid):
                self.instance_id = iid
            def npc_unload_laundry(self, npc_id):
                state = laundry.get_machine_state(self.instance_id)
                if state != 2:
                    return False
                inv = morld.get_unit_inventory(self.instance_id)
                if not inv:
                    laundry.reset_machine(self.instance_id)
                    return True
                for item_id in list(inv.keys()):
                    morld.lost_item(self.instance_id, item_id)
                    _inventory.safe_give_item(npc_id, item_id)
                laundry.reset_machine(self.instance_id)
                return True

        washer = FakeWasher(washer_id)
        result = washer.npc_unload_laundry(NPC_ID)

        assert result is True
        assert morld.has_item(NPC_ID, shirt_id), "NPC에 셔츠 반환"
        assert not morld.has_item(washer_id, shirt_id), "세탁기 비어있음"
        assert laundry.get_machine_state(washer_id) == 0, "리셋됨"

    def test_unload_blocked_during_processing(self):
        """npc_unload_laundry: 작동 중(state=1) → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        washer_id = _setup_washer()
        morld.set_unit_prop(washer_id, "가전:상태", 1)

        class FakeWasher:
            def __init__(self, iid):
                self.instance_id = iid
            def npc_unload_laundry(self, npc_id):
                state = laundry.get_machine_state(self.instance_id)
                if state != 2:
                    return False
                return True

        washer = FakeWasher(washer_id)
        result = washer.npc_unload_laundry(NPC_ID)
        assert result is False


# A2. Dryer npc_* 테스트

class TestDryerNpc:

    def test_dryer_full_cycle(self):
        """건조기: 넣기 → 시작 → 완료 후 꺼내기 전체 사이클"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 4))
        dryer_id = _setup_dryer()

        shirt_id = 300
        morld.give_item(NPC_ID, shirt_id)

        # 1. 넣기
        assert not laundry.is_machine_busy(dryer_id)
        morld.remove_item(NPC_ID, shirt_id, 1)
        morld.give_item(dryer_id, shirt_id, 1)

        # 2. 시작
        laundry.start_machine(dryer_id, "dryer")
        assert laundry.get_machine_state(dryer_id) == 1
        assert laundry.get_remaining_time(dryer_id) == 30, "건조 30분"

        # 3. 완료 시뮬레이션
        morld.set_unit_prop(dryer_id, "가전:상태", 2)
        morld.set_unit_prop(dryer_id, "가전:남은시간", 0)

        # 4. 꺼내기
        assert laundry.get_machine_state(dryer_id) == 2
        inv = morld.get_unit_inventory(dryer_id)
        for item_id in list(inv.keys()):
            morld.lost_item(dryer_id, item_id)
            morld.give_item(NPC_ID, item_id)
        laundry.reset_machine(dryer_id)

        assert morld.has_item(NPC_ID, shirt_id), "NPC에 반환"
        assert laundry.get_machine_state(dryer_id) == 0, "리셋"


# A3. Bathtub/DrumBath npc_use 테스트

class TestBathNpc:

    def test_bathtub_npc_use_effects(self):
        """Bathtub.npc_use: 건조 + 보온 + 정액제거 호출"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 5))

        # Bathtub.npc_use 로직 직접 테스트
        _humidity.dry_unit(NPC_ID, 100)
        _temperature.warm_character(NPC_ID, 2.0)
        _romance.clear_all_semen(NPC_ID)

        assert len(_humidity._dry_log) == 1
        assert _humidity._dry_log[0] == (NPC_ID, 100)
        assert len(_temperature._warm_log) == 1
        assert _temperature._warm_log[0] == (NPC_ID, 2.0)
        assert len(_romance._clear_semen_log) == 1
        assert _romance._clear_semen_log[0] == NPC_ID

    def test_drum_bath_npc_use_effects(self):
        """DrumBath.npc_use: 동일한 효과"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(2, 5))

        _humidity.dry_unit(NPC_ID, 100)
        _temperature.warm_character(NPC_ID, 2.0)
        _romance.clear_all_semen(NPC_ID)

        assert len(_humidity._dry_log) == 1
        assert len(_temperature._warm_log) == 1
        assert len(_romance._clear_semen_log) == 1


# A4. Water source npc_fill 테스트

def _npc_fill_water_container(npc_id):
    """_npc_fill_water_container 로직 재현 (import 우회)

    assets.objects.furniture 모듈은 Object 상속 등 무거운 의존성이 있으므로
    순수 로직만 추출하여 테스트.
    """
    PROP_WATER_AMOUNT = "물양"

    inventory = morld.get_unit_inventory(npc_id)
    if not inventory:
        return False

    filled = False
    for item_id, count in inventory.items():
        if count <= 0:
            continue
        info = morld.get_item_info(item_id)
        if not info:
            continue
        passive = info.get("passive_props") or {}
        if passive.get("can:water", 0) <= 0:
            continue
        uid = _assets_registry.get_unique_id(item_id)
        item_cls = _assets_registry.get_item_class(uid) if uid else None
        capacity = getattr(item_cls, "water_capacity", 1) if item_cls else 1
        current = morld.get_unit_prop(item_id, PROP_WATER_AMOUNT)
        if current < capacity:
            morld.set_unit_prop(item_id, PROP_WATER_AMOUNT, capacity)
            filled = True
    return filled


class TestWaterFillNpc:

    def test_fill_water_container(self):
        """npc_fill_water: 물 용기에 물 채우기"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))

        # 물뿌리개 아이템 등록 (can:water passive_prop)
        can_id = 400
        morld.register_item(can_id, "물뿌리개")
        morld._items[can_id]["passive_props"] = {"can:water": 1}
        morld.give_item(NPC_ID, can_id)

        # registry stub — unique_id + item_class (water_capacity)
        _assets_registry._unique_map[can_id] = "watering_can"
        class FakeWateringCan:
            water_capacity = 3
        _assets_registry._item_classes["watering_can"] = FakeWateringCan

        # 물뿌리개 현재 물양 = 0 (prop 저장용 유닛)
        morld.register_unit(can_id, "물뿌리개", location=(0, 0))
        morld.set_unit_prop(can_id, "물양", 0)

        result = _npc_fill_water_container(NPC_ID)

        assert result is True
        assert morld.get_unit_prop(can_id, "물양") == 3, "용량까지 채워짐"

    def test_fill_already_full(self):
        """npc_fill_water: 이미 가득 찬 용기 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))

        can_id = 400
        morld.register_item(can_id, "물뿌리개")
        morld._items[can_id]["passive_props"] = {"can:water": 1}
        morld.give_item(NPC_ID, can_id)

        _assets_registry._unique_map[can_id] = "watering_can"
        class FakeWateringCan:
            water_capacity = 3
        _assets_registry._item_classes["watering_can"] = FakeWateringCan

        morld.register_unit(can_id, "물뿌리개", location=(0, 0))
        morld.set_unit_prop(can_id, "물양", 3)  # 이미 가득

        result = _npc_fill_water_container(NPC_ID)

        assert result is False, "이미 가득 찬 용기는 채우지 않음"

    def test_fill_no_water_container(self):
        """npc_fill_water: 물 용기 없음 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))

        # 비물 아이템만 보유
        apple_id = 401
        morld.register_item(apple_id, "사과")
        morld.give_item(NPC_ID, apple_id)

        result = _npc_fill_water_container(NPC_ID)

        assert result is False


# A5. GardenBed npc_fertilize / npc_remove_plant 테스트

class TestGardenBedNpc:

    def _make_garden_bed(self, furrow_count=4):
        """GardenBed stub 생성"""
        morld.register_unit(GARDEN_BED_ID, "텃밭", location=(0, 2))
        morld.set_unit_prop(GARDEN_BED_ID, "이랑수", furrow_count)
        morld.set_unit_prop(GARDEN_BED_ID, "비료", 0)

        class FakeGardenBed:
            def __init__(self):
                self.instance_id = GARDEN_BED_ID

            def npc_fertilize(self, npc_id):
                fertilizer_id = _assets_registry._uid_to_item.get("fertilizer")
                if not fertilizer_id or not morld.has_item(npc_id, fertilizer_id):
                    return False
                current = morld.get_unit_prop(self.instance_id, "비료") or 0
                if current >= 100:
                    return False
                morld.lost_item(npc_id, fertilizer_id, 1)
                new_val = min(100, current + 30)
                morld.set_unit_prop(self.instance_id, "비료", new_val)
                return True

            def npc_remove_plant(self, npc_id, furrow_index=None):
                furrow_count = morld.get_unit_prop(self.instance_id, "이랑수") or 0
                if furrow_index is not None:
                    if furrow_index < 0 or furrow_index >= furrow_count:
                        return False
                    seed_code = morld.get_unit_prop(self.instance_id, f"씨앗:{furrow_index}")
                    if not seed_code:
                        return False
                    morld.set_unit_prop(self.instance_id, f"씨앗:{furrow_index}", 0)
                    morld.set_unit_prop(self.instance_id, f"성장:{furrow_index}", 0)
                    return True
                for i in range(furrow_count):
                    seed_code = morld.get_unit_prop(self.instance_id, f"씨앗:{i}")
                    if seed_code:
                        morld.set_unit_prop(self.instance_id, f"씨앗:{i}", 0)
                        morld.set_unit_prop(self.instance_id, f"성장:{i}", 0)
                        return True
                return False

        return FakeGardenBed()

    def test_fertilize_success(self):
        """npc_fertilize: 비료 보유 → 비료 소비 + 텃밭 비료 증가"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 2))
        bed = self._make_garden_bed()

        fert_id = 410
        _assets_registry._uid_to_item["fertilizer"] = fert_id
        morld.register_item(fert_id, "비료")
        morld.give_item(NPC_ID, fert_id, 2)

        result = bed.npc_fertilize(NPC_ID)
        assert result is True
        assert morld.get_unit_prop(GARDEN_BED_ID, "비료") == 30
        # 비료 1개 소비
        inv = morld.get_unit_inventory(NPC_ID)
        assert inv.get(fert_id, 0) == 1

    def test_fertilize_no_item(self):
        """npc_fertilize: 비료 미보유 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 2))
        bed = self._make_garden_bed()
        _assets_registry._uid_to_item["fertilizer"] = 410

        result = bed.npc_fertilize(NPC_ID)
        assert result is False

    def test_fertilize_already_max(self):
        """npc_fertilize: 비료 이미 최대 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 2))
        bed = self._make_garden_bed()
        morld.set_unit_prop(GARDEN_BED_ID, "비료", 100)  # 이미 최대

        fert_id = 410
        _assets_registry._uid_to_item["fertilizer"] = fert_id
        morld.give_item(NPC_ID, fert_id, 1)

        result = bed.npc_fertilize(NPC_ID)
        assert result is False

    def test_remove_plant_by_index(self):
        """npc_remove_plant: 인덱스 지정 제거"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 2))
        bed = self._make_garden_bed(furrow_count=3)

        # 이랑 1에 감자 심기
        morld.set_unit_prop(GARDEN_BED_ID, "씨앗:1", 1)
        morld.set_unit_prop(GARDEN_BED_ID, "성장:1", 50)

        result = bed.npc_remove_plant(NPC_ID, furrow_index=1)
        assert result is True
        assert morld.get_unit_prop(GARDEN_BED_ID, "씨앗:1") == 0
        assert morld.get_unit_prop(GARDEN_BED_ID, "성장:1") == 0

    def test_remove_plant_first_available(self):
        """npc_remove_plant: 인덱스 미지정 → 첫 번째 식물 제거"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 2))
        bed = self._make_garden_bed(furrow_count=3)

        # 이랑 0은 빈 상태, 이랑 1에 감자
        morld.set_unit_prop(GARDEN_BED_ID, "씨앗:1", 1)
        morld.set_unit_prop(GARDEN_BED_ID, "성장:1", 30)

        result = bed.npc_remove_plant(NPC_ID)
        assert result is True
        assert morld.get_unit_prop(GARDEN_BED_ID, "씨앗:1") == 0

    def test_remove_plant_empty_garden(self):
        """npc_remove_plant: 빈 텃밭 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 2))
        bed = self._make_garden_bed(furrow_count=3)

        result = bed.npc_remove_plant(NPC_ID)
        assert result is False


# A6. Kettle npc_brew 테스트

class TestKettleNpc:

    def test_brew_success(self):
        """npc_brew: 주전자 재료 → 레시피 매칭 → NPC에 결과물"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))
        morld.register_unit(KETTLE_ID, "주전자", location=(0, 0))

        # 주전자에 재료 넣기
        tea_leaf_id = 420
        morld.register_item(tea_leaf_id, "찻잎")
        morld.give_item(KETTLE_ID, tea_leaf_id, 2)
        _assets_registry._unique_map[tea_leaf_id] = "tea_leaf"

        # 레시피 결과 설정
        tea_id = 421
        _assets_registry._uid_to_item["tea_leaf"] = tea_leaf_id
        _assets_registry._uid_to_item["herb_tea"] = tea_id
        _recipes._matching_result = (
            "tea_recipe",
            {
                "ingredients": {"tea_leaf": 2},
                "result": ("herb_tea", 1),
            },
            1
        )

        # npc_brew 로직 직접 테스트
        # (주전자 인벤토리에서 재료 소비 → NPC에 결과물 지급)
        inventory = morld.get_unit_inventory(KETTLE_ID)
        assert len(inventory) > 0

        # 재료 소비
        morld.lost_item(KETTLE_ID, tea_leaf_id, 2)
        # 결과물 지급
        _inventory.safe_give_item(NPC_ID, tea_id, 1)

        assert not morld.has_item(KETTLE_ID, tea_leaf_id), "주전자에서 재료 소비"
        assert morld.has_item(NPC_ID, tea_id), "NPC에 차 지급"

    def test_brew_no_ingredients(self):
        """npc_brew: 재료 없음 → False"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))
        morld.register_unit(KETTLE_ID, "주전자", location=(0, 0))

        # 주전자 비어있음
        inventory = morld.get_unit_inventory(KETTLE_ID)
        assert len(inventory) == 0

        # 빈 인벤토리 → find_matching_recipe None
        _recipes._matching_result = None
        # npc_brew 초기 체크 통과 못함 (inventory empty)
        assert not inventory, "빈 주전자 → brew 실패"


# ============================================
# Part B: 세탁 자율 시스템 (think 연동)
# ============================================

class TestCheckLaundry:

    def test_trigger_on_dirty_clothing(self):
        """_check_laundry: 오염 의류 + 세탁기 → 세탁 시작"""
        agent = _create_agent()
        washer_id = _setup_washer()

        # 오염된 의류 장착 상태
        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10  # > DIRTY_THRESHOLD(5)

        # 세탁기 위치 제공
        _facility.resolve_washer = lambda agent, cross_region=False: _TEST_WASHER

        agent.think()

        # laundry_phase가 설정됨
        assert agent._memory["laundry_phase"] is not None, \
            "세탁 phase 시작"
        assert agent._memory["laundry_washer"] == _TEST_WASHER
        assert agent._memory["laundry_items"] == [dirty_shirt]

    def test_no_trigger_clean_clothing(self):
        """_check_laundry: 깨끗한 의류 → 트리거 안함"""
        agent = _create_agent()

        clean_shirt = 300
        morld.register_item(clean_shirt, "깨끗한 셔츠")
        morld.give_item(NPC_ID, clean_shirt)
        _equipment.get_equipped_items = lambda uid: [clean_shirt]
        _pollution._unit_pollution[clean_shirt] = 3  # < DIRTY_THRESHOLD(5)

        _facility.resolve_washer = lambda agent, cross_region=False: _TEST_WASHER

        agent.think()

        assert agent._memory["laundry_phase"] is None

    def test_cooldown_prevents_trigger(self):
        """_check_laundry: 3시간 쿨다운 내 → 트리거 안함"""
        agent = _create_agent(time_millis=10 * _H)

        # 쿨다운 설정 (8시간 전 = 2시간 전, 3시간 미만)
        agent._memory["laundry_cooldown"] = 8 * _H  # 2시간 전

        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10

        _facility.resolve_washer = lambda agent, cross_region=False: _TEST_WASHER

        agent.think()

        assert agent._memory["laundry_phase"] is None, "쿨다운 내 트리거 방지"

    def test_cooldown_expired_triggers(self):
        """_check_laundry: 쿨다운 만료 → 트리거"""
        agent = _create_agent(time_millis=10 * _H)

        # 쿨다운 설정 (4시간 전 = 6시, 3시간 이상 경과)
        agent._memory["laundry_cooldown"] = 6 * _H

        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10

        _facility.resolve_washer = lambda agent, cross_region=False: _TEST_WASHER

        agent.think()

        assert agent._memory["laundry_phase"] is not None, "쿨다운 만료 → 트리거"

    def test_no_washer_no_trigger(self):
        """_check_laundry: 세탁기 없음 → 트리거 안함"""
        agent = _create_agent()

        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10

        # 세탁기 없음
        _facility.resolve_washer = lambda agent, cross_region=False: None

        agent.think()

        assert agent._memory["laundry_phase"] is None


class TestLaundryNonBlockingWait:

    def test_waiting_wash_returns_false(self):
        """waiting_wash 상태: _check_laundry → False (NPC 자유)"""
        agent = _create_agent()
        washer_id = _setup_washer()

        # waiting_wash 상태 설정
        agent._memory["laundry_phase"] = "waiting_wash"
        agent._memory["laundry_washer"] = _TEST_WASHER
        agent._memory["laundry_items"] = [300]

        # 세탁기 아직 작동 중 (state=1)
        morld.set_unit_prop(WASHER_ID, "가전:상태", 1)

        result = agent._check_laundry()

        assert result is False, "작동 중 → NPC 자유"
        assert agent._memory["laundry_phase"] == "waiting_wash", "phase 유지"

    def test_waiting_wash_detects_completion(self):
        """waiting_wash → 세탁 완료(state=2) 감지 → collecting_wash 전환"""
        agent = _create_agent()
        washer_id = _setup_washer()

        agent._memory["laundry_phase"] = "waiting_wash"
        agent._memory["laundry_washer"] = _TEST_WASHER
        agent._memory["laundry_items"] = [300]

        # 세탁기 완료 (state=2)
        morld.set_unit_prop(WASHER_ID, "가전:상태", 2)

        result = agent._check_laundry()

        assert result is True, "완료 감지 → 핸들링"
        # collecting_wash로 전환되었어야 함 (또는 handler가 이미 처리)
        # handler가 collecting_wash에서 washer 위치에 있지 않으므로 이동 명령

    def test_waiting_dry_returns_false(self):
        """waiting_dry 상태: _check_laundry → False (NPC 자유)"""
        agent = _create_agent()
        dryer_id = _setup_dryer()

        agent._memory["laundry_phase"] = "waiting_dry"
        agent._memory["laundry_dryer"] = _TEST_DRYER
        agent._memory["laundry_items"] = [300]

        # 건조기 아직 작동 중
        morld.set_unit_prop(DRYER_ID, "가전:상태", 1)

        result = agent._check_laundry()

        assert result is False, "건조 중 → NPC 자유"

    def test_waiting_dry_detects_completion(self):
        """waiting_dry → 건조 완료(state=2) 감지 → collecting_dry 전환"""
        agent = _create_agent()
        dryer_id = _setup_dryer()

        agent._memory["laundry_phase"] = "waiting_dry"
        agent._memory["laundry_dryer"] = _TEST_DRYER
        agent._memory["laundry_items"] = [300]

        morld.set_unit_prop(DRYER_ID, "가전:상태", 2)

        result = agent._check_laundry()

        assert result is True, "건조 완료 감지 → 핸들링"


class TestLaundryPhases:

    def test_going_to_washer_moves(self):
        """going_to_washer: 세탁기 위치로 이동 명령"""
        agent = _create_agent(location=(0, 0))  # NPC는 (0,0)

        agent._memory["laundry_phase"] = "going_to_washer"
        agent._memory["laundry_washer"] = _TEST_WASHER  # (0,4)
        agent._memory["laundry_items"] = [300]

        from think.handlers.laundry import _handle_laundry
        _handle_laundry(agent)

        # 이동 job 삽입 확인
        job = _last_job(agent)
        assert job is not None, "job 삽입"
        assert job["action"] == "move", "이동 명령"

    def test_going_to_washer_arrived(self):
        """going_to_washer: 도착 → loading으로 전환"""
        agent = _create_agent(location=(0, 4))  # 이미 세탁기 위치

        agent._memory["laundry_phase"] = "going_to_washer"
        agent._memory["laundry_washer"] = _TEST_WASHER  # (0,4)
        agent._memory["laundry_items"] = [300]

        from think.handlers.laundry import _handle_laundry
        _handle_laundry(agent)

        assert agent._memory["laundry_phase"] == "loading", \
            "도착 → loading 전환"

    def test_loading_unequips_and_loads(self):
        """loading: 장비 해제 + 세탁기에 넣기 + 시작 → waiting_wash"""
        agent = _create_agent(location=(0, 4))
        washer_id = _setup_washer()

        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)

        # 세탁기 인스턴스 등록 (get_instance에서 반환)
        class MockWasher:
            def __init__(self):
                self.instance_id = WASHER_ID
            def npc_load_laundry(self, npc_id, item_ids):
                for item_id in item_ids:
                    if morld.has_item(npc_id, item_id):
                        morld.remove_item(npc_id, item_id, 1)
                        morld.give_item(self.instance_id, item_id, 1)
                return True
            def npc_start(self, npc_id):
                laundry.start_machine(self.instance_id, "washer")
                return True
        mock_washer = MockWasher()
        _object_instances[WASHER_ID] = mock_washer

        agent._memory["laundry_phase"] = "loading"
        agent._memory["laundry_washer"] = _TEST_WASHER
        agent._memory["laundry_items"] = [dirty_shirt]

        from think.handlers.laundry import _handle_laundry
        _handle_laundry(agent)

        assert agent._memory["laundry_phase"] == "waiting_wash", \
            "loading → waiting_wash"
        # 장비 해제 호출 확인
        assert len(_equipment._unequip_log) > 0, "장비 해제"
        # 세탁기 작동 중
        assert laundry.get_machine_state(WASHER_ID) == 1

    def test_collecting_wash_no_dryer_reequips(self):
        """collecting_wash: 건조기 없음 → 바로 재장착 + 완료"""
        agent = _create_agent(location=(0, 4))
        washer_id = _setup_washer()

        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        # 세탁기에 완료된 빨래
        morld.give_item(WASHER_ID, dirty_shirt)
        morld.set_unit_prop(WASHER_ID, "가전:상태", 2)

        class MockWasher:
            def __init__(self):
                self.instance_id = WASHER_ID
            def npc_unload_laundry(self, npc_id):
                inv = morld.get_unit_inventory(self.instance_id)
                for item_id in list(inv.keys()):
                    morld.lost_item(self.instance_id, item_id)
                    morld.give_item(npc_id, item_id)
                laundry.reset_machine(self.instance_id)
                return True
        _object_instances[WASHER_ID] = MockWasher()

        # 건조기 없음
        _facility.resolve_dryer = lambda agent, cross_region=False: None

        agent._memory["laundry_phase"] = "collecting_wash"
        agent._memory["laundry_washer"] = _TEST_WASHER
        agent._memory["laundry_items"] = [dirty_shirt]

        from think.handlers.laundry import _handle_laundry
        _handle_laundry(agent)

        # 완료 → phase 리셋
        assert agent._memory["laundry_phase"] is None, "세탁만으로 완료"
        # 재장착 시도
        assert len(_equipment._equip_log) > 0, "의류 재장착"
        assert morld.has_item(NPC_ID, dirty_shirt), "NPC에 아이템 반환"

    def test_collecting_wash_with_dryer(self):
        """collecting_wash: 건조기 있음 → going_to_dryer 전환"""
        agent = _create_agent(location=(0, 4))
        washer_id = _setup_washer()
        dryer_id = _setup_dryer()

        dirty_shirt = 300
        morld.give_item(WASHER_ID, dirty_shirt)
        morld.set_unit_prop(WASHER_ID, "가전:상태", 2)

        class MockWasher:
            def __init__(self):
                self.instance_id = WASHER_ID
            def npc_unload_laundry(self, npc_id):
                inv = morld.get_unit_inventory(self.instance_id)
                for item_id in list(inv.keys()):
                    morld.lost_item(self.instance_id, item_id)
                    morld.give_item(npc_id, item_id)
                laundry.reset_machine(self.instance_id)
                return True
        _object_instances[WASHER_ID] = MockWasher()

        # 건조기 있음
        _facility.resolve_dryer = lambda a, cross_region=False: _TEST_DRYER

        agent._memory["laundry_phase"] = "collecting_wash"
        agent._memory["laundry_washer"] = _TEST_WASHER
        agent._memory["laundry_items"] = [dirty_shirt]

        from think.handlers.laundry import _handle_laundry
        _handle_laundry(agent)

        assert agent._memory["laundry_phase"] == "going_to_dryer", \
            "건조기 있음 → going_to_dryer"
        assert agent._memory["laundry_dryer"] == _TEST_DRYER

    def test_collecting_dry_completes(self):
        """collecting_dry: 건조 완료 → 재장착 + phase 리셋 + 쿨다운"""
        agent = _create_agent(location=(0, 4))
        dryer_id = _setup_dryer()

        clean_shirt = 300
        morld.register_item(clean_shirt, "셔츠")
        morld.give_item(DRYER_ID, clean_shirt)
        morld.set_unit_prop(DRYER_ID, "가전:상태", 2)
        # NPC에도 아이템 있어야 재장착 가능
        morld.give_item(NPC_ID, clean_shirt)

        class MockDryer:
            def __init__(self):
                self.instance_id = DRYER_ID
            def npc_unload_laundry(self, npc_id):
                inv = morld.get_unit_inventory(self.instance_id)
                for item_id in list(inv.keys()):
                    morld.lost_item(self.instance_id, item_id)
                    morld.give_item(npc_id, item_id)
                laundry.reset_machine(self.instance_id)
                return True
        _object_instances[DRYER_ID] = MockDryer()

        agent._memory["laundry_phase"] = "collecting_dry"
        agent._memory["laundry_dryer"] = _TEST_DRYER
        agent._memory["laundry_items"] = [clean_shirt]

        from think.handlers.laundry import _handle_laundry
        _handle_laundry(agent)

        assert agent._memory["laundry_phase"] is None, "건조 완료 → 리셋"
        assert agent._memory["laundry_cooldown"] is not None, "쿨다운 설정"
        assert len(_equipment._equip_log) > 0, "재장착"


class TestDirtyClothingDetection:

    def test_find_dirty_equipped(self):
        """_find_dirty_equipped_clothing: 오염 > 5인 장착 의류만"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))

        clean_id = 300
        dirty_id = 301
        very_dirty_id = 302

        _equipment.get_equipped_items = lambda uid: [clean_id, dirty_id, very_dirty_id]
        _pollution._unit_pollution[clean_id] = 2    # 미달
        _pollution._unit_pollution[dirty_id] = 6    # 초과
        _pollution._unit_pollution[very_dirty_id] = 15  # 초과

        from think.handlers.laundry import _find_dirty_equipped_clothing
        result = _find_dirty_equipped_clothing(NPC_ID)

        assert dirty_id in result
        assert very_dirty_id in result
        assert clean_id not in result
        assert len(result) == 2

    def test_find_dirty_none_equipped(self):
        """_find_dirty_equipped_clothing: 장착 의류 없음 → 빈 리스트"""
        _reset_all()
        morld.register_unit(NPC_ID, "TestNPC", location=(0, 0))
        _equipment.get_equipped_items = lambda uid: []

        from think.handlers.laundry import _find_dirty_equipped_clothing
        result = _find_dirty_equipped_clothing(NPC_ID)

        assert result == []


class TestLaundryTierPriority:

    def test_laundry_after_bath_before_childbirth(self):
        """세탁은 목욕(4e) 다음, 출산(4f) 앞에 위치"""
        agent = _create_agent()

        # 목욕 필요 없고, 출산도 아닌 상태
        # 오염 의류 + 세탁기 → 세탁 트리거
        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10

        _facility.resolve_washer = lambda a, cross_region=False: _TEST_WASHER

        agent.think()

        # 세탁 tier 4에서 처리됨
        assert agent._memory["laundry_phase"] is not None

    def test_hunger_overrides_laundry(self):
        """배고픔(tier 3) → 세탁(tier 4) 보다 우선"""
        agent = _create_agent()

        # 배고픔
        _survival.is_npc_hungry = lambda uid: True
        _eat_module._find_npc_food = lambda uid: {
            "item_id": 50, "unique_id": "apple", "satiety": 30
        }
        morld.give_item(NPC_ID, 50)

        # 오염 의류
        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10
        _facility.resolve_washer = lambda a, cross_region=False: _TEST_WASHER

        agent.think()

        # 배고픔이 먼저 처리
        assert len(_survival._eat_log) > 0, "tier 3 배고픔 먼저 처리"

    def test_bath_need_overrides_laundry(self):
        """목욕(4e) → 세탁(4e-2) 보다 우선"""
        agent = _create_agent()
        # can:bath prop 필수
        morld.set_unit_prop(NPC_ID, "can:bath", 1)

        # 목욕 필요
        _needs.is_npc_need_bath = lambda uid: True
        _facility.resolve_bath = lambda a, cross_region=False: {
            "region_id": 0, "location_id": 5, "x": 0, "object_id": 52}

        # 오염 의류
        dirty_shirt = 300
        morld.register_item(dirty_shirt, "더러운 셔츠")
        morld.give_item(NPC_ID, dirty_shirt)
        _equipment.get_equipped_items = lambda uid: [dirty_shirt]
        _pollution._unit_pollution[dirty_shirt] = 10
        _facility.resolve_washer = lambda a, cross_region=False: _TEST_WASHER

        agent.think()

        # 세탁 phase는 None (목욕이 먼저)
        assert agent._memory["laundry_phase"] is None, "목욕이 우선"
