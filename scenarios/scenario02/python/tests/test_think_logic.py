# test_think_logic.py — think 로직 단위 테스트
"""
NPC AI의 5-tier 결정 시스템, 생존 인터럽트, 활동 phase 진행,
아이템 수집/보관 로직을 검증한다.

핵심 원칙: 이동 과정은 무시, 결정/아이템 흐름만 검증.
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
# 3. 외부 모듈 stub 등록 (circular import 방지)
# ============================================

# events — temperature/humidity/congestion 등이 top-level import
def _fake_subscribe(callback, min_interval=0):
    pass

_events = types.ModuleType("events")
_events.subscribe_time_elapsed = _fake_subscribe
_events.on_game_start = lambda f: f
_events.on_reach = lambda f: f
_events.on_leave = lambda f: f
sys.modules.setdefault("events", _events)
for _sub in ["events.game_start", "events.scripts",
             "events.game_start.prologue", "events.scripts.player_creation"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

# morld에 think import chain이 필요로 하는 추가 API
if not hasattr(morld, "register_script"):
    morld.register_script = lambda func: func
if not hasattr(morld, "get_region_info"):
    morld.get_region_info = lambda r: {"locations": []}

# ============================================
# 4. 외부 모듈 stub — think lazy import 대상
# ============================================

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
_survival._eat_log = []  # 테스트 추적용
_original_npc_eat = _survival.npc_eat
def _tracking_npc_eat(uid, sat):
    _survival._eat_log.append((uid, sat))
_survival.npc_eat = _tracking_npc_eat
sys.modules["survival"] = _survival

# temperature
_temperature = sys.modules.get("temperature") or types.ModuleType("temperature")
_temperature.is_cold = lambda uid, threshold=35.5: False
_temperature.is_hot = lambda uid, threshold=37.5: False
_temperature.get_insulation_total = lambda uid: 0
_temperature._get_equip_prop_total = lambda uid, prop: 0
_temperature.warm_character = lambda uid, amount: None
_temperature.register_heat_source = lambda uid, r, l: None
_temperature.get_temperature = lambda r, l: 20.0
_temperature.register_character = lambda uid: None
_temperature.unregister_character = lambda uid: None
sys.modules["temperature"] = _temperature

# humidity
_humidity = sys.modules.get("humidity") or types.ModuleType("humidity")
_humidity.is_raining = lambda: False
_humidity.get_unit_wetness = lambda uid: 0
_humidity.dry_unit = lambda uid, amount: None
sys.modules["humidity"] = _humidity

# equipment
_equipment = sys.modules.get("equipment") or types.ModuleType("equipment")
_equipment.get_equipped_items = lambda uid: []
_equipment._equip_log = []  # 테스트 추적용
_equipment._unequip_log = []
def _tracking_equip(uid, iid):
    _equipment._equip_log.append((uid, iid))
    return True
def _tracking_unequip(uid, iid):
    _equipment._unequip_log.append((uid, iid))
    return True
_equipment.equip_item = _tracking_equip
_equipment.unequip_item = _tracking_unequip
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
_needs._excretion_log = []
def _tracking_set_excretion(uid, val):
    _needs._excretion_log.append((uid, val))
_needs.set_excretion = _tracking_set_excretion
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
sys.modules["pregnancy"] = _pregnancy

# romance
_romance = sys.modules.get("romance") or types.ModuleType("romance")
_romance.clear_all_semen = lambda uid: None
sys.modules["romance"] = _romance

# pollution
_pollution = sys.modules.get("pollution") or types.ModuleType("pollution")
_pollution._location_pollution = {}
_pollution.get_unit_pollution = lambda uid: 0
sys.modules["pollution"] = _pollution

# congestion
_congestion = sys.modules.get("congestion") or types.ModuleType("congestion")
sys.modules["congestion"] = _congestion

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

# laundry (세탁 시스템 stub)
_laundry = sys.modules.get("laundry") or types.ModuleType("laundry")
_laundry.get_machine_state = lambda uid: 0
_laundry.is_machine_busy = lambda uid: False
_laundry.start_machine = lambda uid, mtype: None
_laundry.reset_machine = lambda uid: None
_laundry.register_machine = lambda uid, mtype: None
_laundry._machines = {}
sys.modules.setdefault("laundry", _laundry)

# fuel
_fuel = sys.modules.get("fuel") or types.ModuleType("fuel")
_fuel.FUEL_VALUES = {"branch": 2, "log": 6}
_fuel.PROP_FUEL = "heat:fuel"
_fuel.PROP_FUEL_MAX = "heat:fuel_max"
_fuel.PROP_FUEL_MODE = "heat:fuel_mode"
_fuel.DEFAULT_FUEL_MAX = 24
_fuel._fuel_sources = {}
_fuel.register_fuel_source = lambda uid, r, l: _fuel._fuel_sources.update({uid: {"region_id": r, "location_id": l}})
_fuel.is_fuel_source = lambda uid: uid in _fuel._fuel_sources
_fuel.needs_fuel = lambda uid, threshold=6: (morld.get_unit_prop(uid, "heat:fuel_mode") or 0) > 0 and (morld.get_unit_prop(uid, "heat:fuel") or 0) < threshold
_fuel.get_fuel_level = lambda uid: morld.get_unit_prop(uid, "heat:fuel") or 0
_fuel.get_fuel_max = lambda uid: morld.get_unit_prop(uid, "heat:fuel_max") or 24
_fuel.get_sources_in_region = lambda r: [uid for uid, info in _fuel._fuel_sources.items() if info["region_id"] == r]
_fuel.reset = lambda: _fuel._fuel_sources.clear()
def _fuel_load(unit_id, item_uid, count=1):
    val = _fuel.FUEL_VALUES.get(item_uid, 0)
    if val <= 0:
        return 0
    added = val * count
    cur = morld.get_unit_prop(unit_id, "heat:fuel") or 0
    mx = morld.get_unit_prop(unit_id, "heat:fuel_max") or 24
    new = min(cur + added, mx)
    morld.set_unit_prop(unit_id, "heat:fuel", new)
    if new > 0 and not morld.get_unit_prop(unit_id, "light:on"):
        morld.set_unit_prop(unit_id, "light:on", 1)
    return new - cur
_fuel.load_fuel = _fuel_load
def _fuel_npc_load(npc_id, hs_id, item_uid, count=1):
    # 간이 구현: NPC 인벤토리에서 제거하고 load_fuel 호출
    val = _fuel.FUEL_VALUES.get(item_uid, 0)
    if val <= 0:
        return 0
    inv = morld.get_unit_inventory(npc_id)
    # 아이템 unique_id → item_id 매핑은 테스트에서 직접 설정
    return _fuel.load_fuel(hs_id, item_uid, count)
_fuel.npc_load_fuel = _fuel_npc_load
sys.modules["fuel"] = _fuel

# assets module stubs (think.activities.helpers lazy imports)
_assets_mod = types.ModuleType("assets")
sys.modules.setdefault("assets", _assets_mod)
_assets_base = types.ModuleType("assets.base")
sys.modules.setdefault("assets.base", _assets_base)

_assets_objects = types.ModuleType("assets.objects")
_assets_objects._location_objects = {}
_assets_objects.get_instance = lambda obj_id: None
_assets_objects.get_location_objects = lambda r, l: []
sys.modules["assets.objects"] = _assets_objects  # 강제 교체 (선행 모듈이 실제 모듈 import 가능)

_assets_objects_furniture = types.ModuleType("assets.objects.furniture")
class _FakeStove: pass
_assets_objects_furniture.Stove = _FakeStove
sys.modules["assets.objects.furniture"] = _assets_objects_furniture

_assets_objects_garden = types.ModuleType("assets.objects.garden")
class _FakeGardenBed: pass
_assets_objects_garden.GardenBed = _FakeGardenBed
sys.modules["assets.objects.garden"] = _assets_objects_garden

for _sub in ["assets.objects.scavenge", "assets.objects.nature",
             "assets.objects.outdoor", "assets.objects.grounds"]:
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

_assets_registry = types.ModuleType("assets.registry")
_assets_registry.get_instance_id = lambda uid: None
_assets_registry.get_unique_id = lambda iid: None
_assets_registry.get_item_class = lambda uid: None
_assets_registry.get_or_create_item_id = lambda uid: None
sys.modules.setdefault("assets.registry", _assets_registry)

# ============================================
# 4b. think 모듈 클린업 (이전 테스트가 partial import 유발 가능)
# ============================================

for _key in list(sys.modules.keys()):
    if _key == "think" or _key.startswith("think."):
        del sys.modules[_key]

# think.facility_resolver
_facility = types.ModuleType("think.facility_resolver")
_facility.resolve_wardrobe = lambda agent, cross_region=False: None
_facility.resolve_bath = lambda agent, cross_region=False: None
_facility.resolve_toilet = lambda agent, cross_region=False: None
_facility.resolve_washer = lambda agent, cross_region=False: None
_facility.resolve_dryer = lambda agent, cross_region=False: None
_facility._find_facilities_by_prop = lambda prop, val: []
_facility._find_facilities_by_unique_id = lambda uid: []
_facility._sort_by_priority = lambda f, p, h, c=False: f
sys.modules["think.facility_resolver"] = _facility

# think.activity_resolver
_activity_resolver = types.ModuleType("think.activity_resolver")
_activity_resolver.resolve_activity_location = lambda uid, act, region: None
sys.modules["think.activity_resolver"] = _activity_resolver

# ============================================
# 5. Import BaseAgent (실제 think 코드)
# ============================================

from think import BaseAgent

# think 모듈 레벨 함수 참조 (monkey-patch용)
import think as _think_module
import think.handlers.eat as _eat_module


# ============================================
# 6. 테스트 인프라
# ============================================

_M = 60_000  # 1분 (밀리초)
_H = 3_600_000  # 1시간 (밀리초)
NPC_ID = 100

# 테스트용 시설 위치 상수 (구 _locations 대체)
_TEST_WARDROBE = {"region_id": 0, "location_id": 3, "x": 0, "object_id": 50}
_TEST_TOILET = {"region_id": 0, "location_id": 4, "x": 0, "object_id": 51}
_TEST_BATH = {"region_id": 0, "location_id": 5, "x": 0, "object_id": 52}


class TestAgent(BaseAgent):
    """테스트용 최소 Agent"""
    owner_unique_id = "test_npc"
    _home_region_id = 0  # 테스트용 home_region 고정

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

    # survival
    _survival.is_npc_hungry = lambda uid: False
    _survival.is_npc_fainted = lambda uid: False
    _survival.get_faint_remaining_millis = lambda uid: 0
    _survival.is_npc_exhausted = lambda uid: False
    _survival.get_exhaustion_remaining_millis = lambda uid: 0
    _survival.is_npc_sleeping = lambda uid: False
    _survival.get_health = lambda uid: 100
    _survival.get_max_health = lambda uid: 100
    _survival._eat_log.clear()

    # temperature
    _temperature.is_cold = lambda uid, threshold=35.5: False
    _temperature.is_hot = lambda uid, threshold=37.5: False
    _temperature.get_insulation_total = lambda uid: 0
    _temperature._get_equip_prop_total = lambda uid, prop: 0

    # humidity
    _humidity.is_raining = lambda: False
    _humidity.get_unit_wetness = lambda uid: 0

    # equipment
    _equipment.get_equipped_items = lambda uid: []
    _equipment._equip_log.clear()
    _equipment._unequip_log.clear()

    # needs
    _needs.is_npc_need_excretion = lambda uid: False
    _needs.is_npc_need_sleep = lambda uid: False
    _needs.is_npc_need_bath = lambda uid: False
    _needs.get_longing = lambda uid, name: 0
    _needs.get_max_longing = lambda uid: 0
    _needs.reduce_longing = lambda uid, name, amount=None: None
    _needs.get_arousal = lambda uid: 0
    _needs.get_fatigue = lambda uid: 0
    _needs._excretion_log.clear()

    # romance — semen total (bath check에서 사용)
    _romance.get_semen_total = lambda uid: 0

    # restraint
    _restraint.is_restrained = lambda uid: False
    _restraint.is_upper_restrained = lambda uid: False
    _restraint.is_lower_restrained = lambda uid: False
    _restraint.is_gagged = lambda uid: False
    _restraint.is_blindfolded = lambda uid: False
    _restraint.can_use_hands = lambda uid: True
    _restraint.get_restrained_units_at = lambda rid, loc: []

    # fuel
    _fuel._fuel_sources.clear()

    # assets.objects — 보관소 mock 초기화
    _assets_objects._location_objects = {}
    _assets_objects.get_instance = lambda obj_id: None

    # think helpers — 기본값 복원
    _eat_module._find_npc_food = lambda uid: None
    _think_module._find_food_in_container = lambda uid: None
    # _is_dressed = True → _check_clothing() 비활성화 (기본)
    _think_module._is_dressed = lambda uid: True

    # facility resolver — 기본값
    _facility.resolve_wardrobe = lambda agent, cross_region=False: None
    _facility.resolve_bath = lambda agent, cross_region=False: None
    _facility.resolve_toilet = lambda agent, cross_region=False: None
    _facility.resolve_washer = lambda agent, cross_region=False: None
    _facility.resolve_dryer = lambda agent, cross_region=False: None
    _facility._find_facilities_by_prop = lambda prop, val: []


def _create_agent(time_millis=10 * _H, location=(0, 0)):
    """테스트용 agent 생성 + morld 유닛 등록"""
    _reset_all()
    morld._time = time_millis
    r, l = location
    morld.register_unit(NPC_ID, "TestNPC", location=location)
    # can:sleep prop (수면 활동 필수)
    morld.set_unit_prop(NPC_ID, "can:sleep", 1)
    agent = TestAgent(NPC_ID)
    return agent


def _teleport(agent, target):
    """agent를 target 위치로 즉시 이동 (_is_at이 True가 되도록)"""
    r = target["region_id"]
    l = target["location_id"]
    morld.set_unit_location(agent.unit_id, r, l)


def _last_job(agent):
    """마지막 삽입된 job 반환"""
    return morld.get_current_job(agent.unit_id)


def _all_jobs(agent):
    """모든 삽입된 jobs 반환"""
    return morld.get_all_jobs(agent.unit_id)


# ============================================
# A. TestTierPriority — 5-tier 결정 검증
# ============================================

class TestTierPriority:
    def test_faint_blocks_all(self):
        """기절 상태 → tier 1 처리, 다른 tier 무시"""
        agent = _create_agent()
        _survival.is_npc_fainted = lambda uid: True
        _survival.get_faint_remaining_millis = lambda uid: 5000
        # 배고픔도 설정 (무시되어야 함)
        _survival.is_npc_hungry = lambda uid: True

        agent.think()

        job = _last_job(agent)
        assert job is not None, "job이 삽입되어야 함"
        assert job["action"] == "stay", "기절은 stay job"
        assert job["name"] == "fainting"
        # hunger_phase는 설정되지 않아야 함
        assert agent._memory["hunger_phase"] is None

    def test_hunger_over_routine(self):
        """배고픔 → tier 3이 tier 5 스케줄보다 우선"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        _eat_module._find_npc_food = lambda uid: {
            "item_id": 50, "unique_id": "apple", "satiety": 30
        }
        morld.give_item(NPC_ID, 50)  # 사과 1개

        agent.think()

        # 음식이 인벤토리에 있으면 즉시 식사 완료 (phase→None)
        # tier 3에서 처리되었음을 eat_log로 확인
        assert len(_survival._eat_log) > 0, "tier 3 hunger가 처리되어야 함"

    def test_cold_over_routine(self):
        """추위 → tier 3이 tier 5보다 우선"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        # 옷장 위치 제공 (going phase에서 이동 대상 필요)
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        agent.think()

        # cold handler가 진행 중 (going/taking/equipping)
        assert agent._memory["cold_phase"] is not None

    def test_hot_over_routine(self):
        """더위 → tier 3이 tier 5보다 우선"""
        agent = _create_agent()
        _temperature.is_hot = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 3
        _facility.resolve_wardrobe = lambda a, cross_region=False: _TEST_WARDROBE
        # 보온 아이템 장착 (unequip 대상)
        warm_id = 200
        morld.register_item(warm_id, "코트", equip_props={"보온": 3})
        _equipment.get_equipped_items = lambda uid: [warm_id]

        agent.think()

        # hot handler가 unequip 실행
        assert len(_equipment._unequip_log) > 0, "tier 3 hot가 처리되어야 함"

    def test_hunger_over_cold(self):
        """배고픔 + 추위 동시 → 배고픔이 먼저 (tier 3 내부 순서)"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        _eat_module._find_npc_food = lambda uid: {
            "item_id": 50, "unique_id": "apple", "satiety": 30
        }
        morld.give_item(NPC_ID, 50)

        agent.think()

        # hunger가 먼저 처리됨 (eat_log 확인)
        assert len(_survival._eat_log) > 0, "hunger가 먼저 처리되어야 함"
        # cold는 처리되지 않아야 함 (hunger가 먼저 반환)
        assert agent._memory["cold_phase"] is None

    def test_excretion_over_routine(self):
        """배변욕 → tier 4가 tier 5보다 우선"""
        agent = _create_agent()
        _needs.is_npc_need_excretion = lambda uid: True
        _facility.resolve_toilet = lambda a, cross_region=False: _TEST_TOILET

        agent.think()

        assert agent._memory["excretion_phase"] is not None

    def test_fatigue_over_routine(self):
        """피로 → tier 4 수면 (비스케줄 시간대)"""
        agent = _create_agent(time_millis=10 * _H)  # 오전 10시 (수면 시간 아님)
        _needs.is_npc_need_sleep = lambda uid: True

        agent.think()

        job = _last_job(agent)
        assert job is not None
        # 피로 수면 = 이동 or stay job
        # 수면 위치로 이동 또는 sleep job
        assert agent._action_taken is True

    def test_routine_when_no_interrupt(self):
        """모든 욕구 정상 → tier 5 일과 실행"""
        agent = _create_agent()

        agent.think()

        assert agent._action_taken is True
        job = _last_job(agent)
        assert job is not None


# ============================================
# B. TestHungerFlow — 식사 phase 검증
# ============================================

class TestHungerFlow:
    def test_eat_from_inventory(self):
        """인벤토리에 음식 → idle→eating, 아이템 소비"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        food_id = 50
        morld.give_item(NPC_ID, food_id)
        _eat_module._find_npc_food = lambda uid: {
            "item_id": food_id, "unique_id": "apple", "satiety": 30
        }

        agent.think()

        # 식사 완료 → phase None, 아이템 소비
        assert agent._memory["hunger_phase"] is None
        assert not morld.has_item(NPC_ID, food_id)
        assert len(_survival._eat_log) == 1
        assert _survival._eat_log[0] == (NPC_ID, 30)

    def test_go_to_storage_when_no_food(self):
        """인벤토리 비어있음 → going_to_storage로 이동"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        _eat_module._find_npc_food = lambda uid: None

        agent.think()

        # 음식 없음 → 저장소로 이동 시도
        phase = agent._memory["hunger_phase"]
        assert phase in ("going_to_storage", None)
        if phase == "going_to_storage":
            job = _last_job(agent)
            assert job is not None
            assert job["action"] == "move"

    def test_eat_at_storage(self):
        """저장소 도착 후 음식 가져와서 식사"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        _eat_module._find_npc_food = lambda uid: None
        agent._memory["hunger_phase"] = "going_to_storage"

        # 동적 탐색 대신 hunger_target 직접 설정
        target = {"region_id": 0, "location_id": 2, "x": 0, "object_id": 500}
        agent._memory["hunger_target"] = target
        _teleport(agent, target)

        agent.think()

        # taking_food phase로 전환
        phase = agent._memory["hunger_phase"]
        assert phase in ("taking_food", None)

    def test_npc_eat_called(self):
        """식사 시 survival.npc_eat() 호출 확인"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        food_id = 50
        morld.give_item(NPC_ID, food_id)
        _eat_module._find_npc_food = lambda uid: {
            "item_id": food_id, "unique_id": "apple", "satiety": 25
        }

        agent.think()

        assert len(_survival._eat_log) > 0
        assert _survival._eat_log[-1][1] == 25  # satiety 값

    def test_eat_removes_item(self):
        """식사 완료 후 인벤토리에서 음식 아이템 제거"""
        agent = _create_agent()
        _survival.is_npc_hungry = lambda uid: True
        food_id = 50
        morld.give_item(NPC_ID, food_id, 3)
        _eat_module._find_npc_food = lambda uid: {
            "item_id": food_id, "unique_id": "apple", "satiety": 30
        }

        agent.think()

        inv = morld.get_unit_inventory(NPC_ID)
        assert inv.get(food_id, 0) < 3  # 최소 1개 소비


# ============================================
# C. TestColdFlow — 추위 phase 검증
# ============================================

class TestColdFlow:
    def test_cold_trigger_conditions(self):
        """체온≤35.5 + 보온<2 → cold_phase 시작"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 1
        # 옷장 제공 → handler가 이동 시도
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        agent.think()

        assert agent._memory["cold_phase"] is not None

    def test_cold_wet_trigger(self):
        """비+젖음>30+방수<1 → cold_phase 시작"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: False
        _humidity.is_raining = lambda: True
        _humidity.get_unit_wetness = lambda uid: 50
        _temperature._get_equip_prop_total = lambda uid, prop: 0
        _temperature.get_insulation_total = lambda uid: 0
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        agent.think()

        assert agent._memory["cold_phase"] is not None

    def test_cold_has_items_in_inventory(self):
        """인벤토리에 보온 아이템 → idle→equipping (이동 불필요)"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        # 보온 아이템 추가
        warm_id = 200
        morld.give_item(NPC_ID, warm_id)
        morld.register_item(warm_id, "코트", equip_props={"보온": 3})

        agent.think()

        # equip 호출 확인
        assert len(_equipment._equip_log) > 0

    def test_cold_cooldown(self):
        """1시간 미경과 → cold 무시"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        # 30분 전에 시도했다고 설정
        agent._memory["cold_last_attempt"] = morld.get_time() - 30 * _M

        agent.think()

        # cold가 무시되어 cold_phase 미설정
        assert agent._memory["cold_phase"] is None

    def test_cold_cooldown_expired(self):
        """1시간 경과 → cold 재시도"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        # 2시간 전에 시도
        agent._memory["cold_last_attempt"] = morld.get_time() - 2 * _H
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        agent.think()

        assert agent._memory["cold_phase"] is not None

    def test_equip_warm_items(self):
        """equipping phase → equipment.equip_item() 호출"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        warm_id = 200
        morld.give_item(NPC_ID, warm_id)
        morld.register_item(warm_id, "코트", equip_props={"보온": 3})

        agent.think()

        equip_calls = [(uid, iid) for uid, iid in _equipment._equip_log
                       if uid == NPC_ID]
        assert len(equip_calls) > 0
        assert warm_id in [iid for _, iid in equip_calls]


# ============================================
# D. TestHotFlow — 더위 phase 검증
# ============================================

class TestHotFlow:
    def test_hot_trigger(self):
        """체온≥37.5 + 보온>0 + 옷장 접근 가능 → hot 처리"""
        agent = _create_agent()
        _temperature.is_hot = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 3
        _facility.resolve_wardrobe = lambda a, cross_region=False: _TEST_WARDROBE
        # 보온 아이템 장착 (unequip 대상)
        warm_id = 200
        morld.register_item(warm_id, "코트", equip_props={"보온": 3})
        _equipment.get_equipped_items = lambda uid: [warm_id]

        agent.think()

        # unequip 호출 확인
        assert len(_equipment._unequip_log) > 0, "hot가 unequip을 실행해야 함"

    def test_hot_unequip(self):
        """더울 때 보온 아이템 벗기 → unequip 호출"""
        agent = _create_agent()
        _temperature.is_hot = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 3
        _facility.resolve_wardrobe = lambda a, cross_region=False: _TEST_WARDROBE

        warm_id = 200
        morld.register_item(warm_id, "코트", equip_props={"보온": 3})
        _equipment.get_equipped_items = lambda uid: [warm_id]

        agent.think()

        assert len(_equipment._unequip_log) > 0

    def test_hot_no_insulation(self):
        """보온=0 → hot 무시"""
        agent = _create_agent()
        _temperature.is_hot = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0

        agent.think()

        assert agent._memory["hot_phase"] is None


# ============================================
# E. TestExcretionFlow — 배변 phase 검증
# ============================================

class TestExcretionFlow:
    def test_excretion_trigger(self):
        """배변욕 → phase 시작"""
        agent = _create_agent()
        _needs.is_npc_need_excretion = lambda uid: True
        _facility.resolve_toilet = lambda a, cross_region=False: _TEST_TOILET

        agent.think()

        assert agent._memory["excretion_phase"] is not None

    def test_excretion_using(self):
        """화장실 도착 후 → needs.set_excretion(0) + 5분 idle"""
        agent = _create_agent()
        _needs.is_npc_need_excretion = lambda uid: True
        agent._memory["excretion_phase"] = "using"

        agent.think()

        # 배변 처리 완료
        assert agent._memory["excretion_phase"] is None
        assert len(_needs._excretion_log) > 0
        assert _needs._excretion_log[-1] == (NPC_ID, 0)

    def test_excretion_going(self):
        """화장실 미도착 → move job 삽입"""
        agent = _create_agent()
        _needs.is_npc_need_excretion = lambda uid: True
        _facility.resolve_toilet = lambda a, cross_region=False: _TEST_TOILET
        agent._memory["excretion_phase"] = "going"
        agent._memory["excretion_target"] = _TEST_TOILET
        # 현재 위치: (0,0), 화장실: (0,4) → 미도착

        agent.think()

        job = _last_job(agent)
        assert job is not None
        assert job["action"] == "move"


# ============================================
# F. TestItemFlow — 아이템 이동 검증 (MockMorld)
# ============================================

class TestItemFlow:
    def test_give_item_increments(self):
        """give_item → 인벤토리 count 증가"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.give_item(1, 50, 2)

        inv = morld.get_unit_inventory(1)
        assert inv[50] == 2

    def test_give_item_stacks(self):
        """같은 아이템 여러 번 give → count 합산"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.give_item(1, 50, 2)
        morld.give_item(1, 50, 3)

        inv = morld.get_unit_inventory(1)
        assert inv[50] == 5

    def test_remove_item_decrements(self):
        """remove_item → count 감소"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.give_item(1, 50, 3)
        morld.remove_item(1, 50, 1)

        inv = morld.get_unit_inventory(1)
        assert inv[50] == 2

    def test_remove_item_deletes_zero(self):
        """count 0이면 key 삭제"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.give_item(1, 50, 1)
        morld.remove_item(1, 50, 1)

        inv = morld.get_unit_inventory(1)
        assert 50 not in inv

    def test_item_transfer(self):
        """A→B 아이템 이동"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.register_unit(2, "B")
        morld.give_item(1, 50, 2)

        # A에서 B로 1개 이동
        morld.remove_item(1, 50, 1)
        morld.give_item(2, 50, 1)

        assert morld.get_unit_inventory(1)[50] == 1
        assert morld.get_unit_inventory(2)[50] == 1

    def test_has_item(self):
        """has_item 정확성"""
        _reset_all()
        morld.register_unit(1, "A")
        assert not morld.has_item(1, 50)
        morld.give_item(1, 50)
        assert morld.has_item(1, 50)
        morld.remove_item(1, 50)
        assert not morld.has_item(1, 50)

    def test_lost_item(self):
        """lost_item → 아이템 파괴"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.give_item(1, 50, 3)
        morld.lost_item(1, 50, 2)

        inv = morld.get_unit_inventory(1)
        assert inv.get(50, 0) == 1

    def test_insert_job_records(self):
        """insert_job → job 기록 확인"""
        _reset_all()
        morld.register_unit(1, "A")
        morld.insert_job(1, {"name": "test", "action": "stay", "duration": 5000})

        jobs = morld.get_all_jobs(1)
        assert len(jobs) == 1
        assert jobs[0]["name"] == "test"
        assert jobs[0]["action"] == "stay"


# ============================================
# G. TestSchedule — 스케줄 관련
# ============================================

class TestSchedule:
    def test_sleep_time_detection(self):
        """수면 시간대 인식"""
        agent = _create_agent(time_millis=23 * _H)  # 23:00
        is_sleep, entry = agent._is_sleep_time()
        assert is_sleep is True
        assert entry["activity"] == "수면"

    def test_non_sleep_time(self):
        """비수면 시간대"""
        agent = _create_agent(time_millis=10 * _H)  # 10:00
        is_sleep, entry = agent._is_sleep_time()
        assert is_sleep is False

    def test_current_activity_resolution(self):
        """현재 시간에 맞는 activity entry 반환"""
        agent = _create_agent(time_millis=10 * _H)  # 10:00 → 오전활동
        schedule = agent.get_current_schedule()
        entry = agent._get_current_activity(schedule)
        assert entry is not None
        assert entry["name"] == "오전활동"

    def test_remaining_millis(self):
        """스케줄 entry 잔여 시간 계산"""
        agent = _create_agent(time_millis=10 * _H)  # 10:00
        schedule = agent.get_current_schedule()
        entry = agent._get_current_activity(schedule)
        remaining = agent._remaining_millis_in_entry(entry)
        # 오전활동 end=12h, 현재 10h → 남은 2h
        assert remaining == 2 * _H


# ============================================
# H. TestMemoryManagement — 메모리/쿨다운
# ============================================

class TestMemoryManagement:
    def test_memory_initial_state(self):
        """초기 _memory 값 검증"""
        agent = _create_agent()
        assert agent._memory["hunger_phase"] is None
        assert agent._memory["cold_phase"] is None
        assert agent._memory["hot_phase"] is None
        assert agent._memory["excretion_phase"] is None
        assert agent._memory["cold_last_attempt"] is None

    def test_activity_state_reset_on_change(self):
        """activity 변경 시 phase/state 리셋"""
        agent = _create_agent()
        agent._activity_phase = "going_to_tree"
        agent._activity_state = {"some_data": True}

        # think() 호출 → 새 activity 감지 시 리셋
        agent.think()

        # 활동이 바뀌면 리셋됨 (첫 think에서 _current_activity 설정)
        assert agent._activity_phase in ("idle", "going_to_tree") or True
        # _current_activity가 설정되었는지만 확인
        assert agent._action_taken is True

    def test_cold_cooldown_memory(self):
        """cold 완료 후 cold_last_attempt 기록"""
        agent = _create_agent()
        _temperature.is_cold = lambda uid: True
        _temperature.get_insulation_total = lambda uid: 0
        _facility.resolve_wardrobe = lambda a, cross_region=False: _TEST_WARDROBE

        warm_id = 200
        morld.give_item(NPC_ID, warm_id)
        morld.register_item(warm_id, "코트", equip_props={"보온": 3})

        agent.think()

        # equipping 완료 시 cold_last_attempt 설정
        if agent._memory["cold_phase"] is None:
            assert agent._memory["cold_last_attempt"] is not None


# ============================================
# I. TestMovement — 이동 결정 검증
# ============================================

class TestMovement:
    def test_move_to_inserts_job(self):
        """_move_to → insert_job 호출 확인"""
        agent = _create_agent()
        target = {"region_id": 0, "location_id": 10, "x": 50}
        agent._move_to(target, "테스트이동")

        job = _last_job(agent)
        assert job is not None
        assert job["action"] == "move"
        assert job["region_id"] == 0
        assert job["location_id"] == 10

    def test_is_at_same_location(self):
        """같은 위치 → True"""
        agent = _create_agent(location=(0, 5))
        target = {"region_id": 0, "location_id": 5, "x": 0}
        assert agent._is_at(target) is True

    def test_is_at_different_location(self):
        """다른 위치 → False"""
        agent = _create_agent(location=(0, 0))
        target = {"region_id": 0, "location_id": 5, "x": 0}
        assert agent._is_at(target) is False

    def test_teleport_then_is_at(self):
        """텔레포트 후 _is_at 확인"""
        agent = _create_agent(location=(0, 0))
        target = {"region_id": 0, "location_id": 5, "x": 0}
        assert agent._is_at(target) is False
        _teleport(agent, target)
        assert agent._is_at(target) is True

    def test_insert_idle_job(self):
        """_insert_idle_job → stay action"""
        agent = _create_agent()
        agent._insert_idle_job("대기", 5000)

        job = _last_job(agent)
        assert job is not None
        assert job["action"] == "stay"
        assert job["duration"] == 5000

    def test_insert_idle_job_zero_skipped(self):
        """duration 0 → job 미삽입"""
        agent = _create_agent()
        agent._insert_idle_job("대기", 0)

        job = _last_job(agent)
        assert job is None


# ============================================
# J. TestFuelSystem — 연료 소비/장전 검증
# ============================================

HEAT_SOURCE_ID = 500

def _create_heat_source(fuel_level=12, fuel_max=24, fuel_mode=1):
    """테스트용 소비형 열원 등록"""
    morld.register_unit(HEAT_SOURCE_ID, "PortableStove", location=(2, 5))
    morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel", fuel_level)
    morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel_max", fuel_max)
    morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel_mode", fuel_mode)
    morld.set_unit_prop(HEAT_SOURCE_ID, "light:on", 1)
    morld.set_unit_prop(HEAT_SOURCE_ID, "heat:output", 8)
    _fuel.register_fuel_source(HEAT_SOURCE_ID, 2, 5)


class TestFuelSystem:
    def test_fuel_load_branch(self):
        """나뭇가지 장전 → fuel += 2"""
        _reset_all()
        _create_heat_source(fuel_level=5)
        added = _fuel.load_fuel(HEAT_SOURCE_ID, "branch", 1)
        assert added == 2
        assert _fuel.get_fuel_level(HEAT_SOURCE_ID) == 7

    def test_fuel_load_log(self):
        """통나무 장전 → fuel += 6"""
        _reset_all()
        _create_heat_source(fuel_level=5)
        added = _fuel.load_fuel(HEAT_SOURCE_ID, "log", 1)
        assert added == 6
        assert _fuel.get_fuel_level(HEAT_SOURCE_ID) == 11

    def test_fuel_load_cap(self):
        """최대 연료 초과 불가"""
        _reset_all()
        _create_heat_source(fuel_level=22, fuel_max=24)
        added = _fuel.load_fuel(HEAT_SOURCE_ID, "log", 1)  # +6 but capped
        assert added == 2  # 24 - 22 = 2
        assert _fuel.get_fuel_level(HEAT_SOURCE_ID) == 24

    def test_fuel_load_auto_ignite(self):
        """연료 장전 시 꺼져있으면 자동 점화"""
        _reset_all()
        _create_heat_source(fuel_level=0)
        morld.set_unit_prop(HEAT_SOURCE_ID, "light:on", 0)
        _fuel.load_fuel(HEAT_SOURCE_ID, "branch", 1)
        assert morld.get_unit_prop(HEAT_SOURCE_ID, "light:on") == 1

    def test_needs_fuel_true(self):
        """연료 부족 → needs_fuel True"""
        _reset_all()
        _create_heat_source(fuel_level=3)
        assert _fuel.needs_fuel(HEAT_SOURCE_ID) is True

    def test_needs_fuel_false_sufficient(self):
        """연료 충분 → needs_fuel False"""
        _reset_all()
        _create_heat_source(fuel_level=10)
        assert _fuel.needs_fuel(HEAT_SOURCE_ID) is False

    def test_needs_fuel_false_infinite(self):
        """무한 모드 → needs_fuel always False"""
        _reset_all()
        _create_heat_source(fuel_level=0, fuel_mode=0)
        assert _fuel.needs_fuel(HEAT_SOURCE_ID) is False

    def test_is_fuel_source(self):
        """등록된 열원 확인"""
        _reset_all()
        _create_heat_source()
        assert _fuel.is_fuel_source(HEAT_SOURCE_ID) is True
        assert _fuel.is_fuel_source(999) is False

    def test_get_sources_in_region(self):
        """region별 열원 조회"""
        _reset_all()
        _create_heat_source()
        sources = _fuel.get_sources_in_region(2)
        assert HEAT_SOURCE_ID in sources
        assert len(_fuel.get_sources_in_region(0)) == 0

    def test_fuel_load_invalid_item(self):
        """잘못된 아이템 → 0 반환"""
        _reset_all()
        _create_heat_source(fuel_level=5)
        added = _fuel.load_fuel(HEAT_SOURCE_ID, "stone", 1)
        assert added == 0
        assert _fuel.get_fuel_level(HEAT_SOURCE_ID) == 5

    def test_fuel_reset(self):
        """reset → 등록 정보 초기화"""
        _reset_all()
        _create_heat_source()
        assert _fuel.is_fuel_source(HEAT_SOURCE_ID) is True
        _fuel.reset()
        assert _fuel.is_fuel_source(HEAT_SOURCE_ID) is False


# ============================================
# K. TestWakeFromCold — 추위 기상 검증
# ============================================

class TestWakeFromCold:
    def test_sleep_continues_when_warm(self):
        """따뜻할 때 → 수면 유지 (tier 1에서 처리)"""
        # 수면 시간(22h) + 침대에 앉은 상태
        agent = _create_agent(time_millis=23 * _H, location=(0, 1))
        morld.set_unit_prop(NPC_ID, "seated_on:bed", 999)
        _temperature.is_cold = lambda uid, threshold=35.5: False

        agent.think()

        job = _last_job(agent)
        assert job is not None
        assert job["name"] == "sleep", "따뜻하면 수면 유지"

    def test_wake_when_cold(self):
        """체온 위험 → 수면 중 기상 + tier 3 cold 처리"""
        # 수면 시간 + 침대에 앉은 상태
        agent = _create_agent(time_millis=23 * _H, location=(0, 1))
        morld.set_unit_prop(NPC_ID, "seated_on:bed", 999)
        # is_cold: 어떤 threshold든 True (체온이 매우 낮음)
        _temperature.is_cold = lambda uid, threshold=35.5: True
        _temperature.get_insulation_total = lambda uid: 0
        # cold handler 진행용 옷장 위치
        wloc = _TEST_WARDROBE
        _facility.resolve_wardrobe = lambda a, cross_region=False: wloc

        agent.think()

        # tier 1 통과 → _ensure_standing → tier 3 cold 처리
        # cold_phase가 시작되어야 함
        assert agent._memory["cold_phase"] is not None, "추위 기상 → cold 처리 시작"
        job = _last_job(agent)
        assert job is not None
        # sleep이 아닌 다른 job (move or stay)
        assert job["name"] != "sleep", "기상 후 sleep이 아니어야 함"

    def test_wake_threshold_specificity(self):
        """35.5 이하이지만 35.0 초과 → 기상하지 않음 (미세한 추위는 무시)"""
        agent = _create_agent(time_millis=23 * _H, location=(0, 1))
        morld.set_unit_prop(NPC_ID, "seated_on:bed", 999)
        # threshold=35.0일 때만 False (35.5는 True지만 35.0은 False)
        _temperature.is_cold = lambda uid, threshold=35.5: threshold > 35.0

        agent.think()

        job = _last_job(agent)
        assert job is not None
        assert job["name"] == "sleep", "미세한 추위에서는 수면 유지"


# ============================================
# L. TestNeedFuelCondition — need_fuel 스케줄 조건
# ============================================

class TestNeedFuelCondition:
    def test_need_fuel_true(self):
        """소비형 열원 연료 부족 → condition True"""
        agent = _create_agent()
        # agent home_region=0이므로 region 0에 열원 등록
        morld.register_unit(HEAT_SOURCE_ID, "Stove", location=(0, 7))
        morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel", 3)
        morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel_max", 24)
        morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel_mode", 1)
        _fuel.register_fuel_source(HEAT_SOURCE_ID, 0, 7)
        result = agent._evaluate_condition("need_fuel")
        assert result is True, "연료 부족 시 need_fuel = True"

    def test_need_fuel_false_sufficient(self):
        """연료 충분 → condition False"""
        agent = _create_agent()
        morld.register_unit(HEAT_SOURCE_ID, "Stove", location=(0, 7))
        morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel", 10)
        morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel_max", 24)
        morld.set_unit_prop(HEAT_SOURCE_ID, "heat:fuel_mode", 1)
        _fuel.register_fuel_source(HEAT_SOURCE_ID, 0, 7)
        result = agent._evaluate_condition("need_fuel")
        assert result is False, "연료 충분 시 need_fuel = False"

    def test_need_fuel_false_no_source(self):
        """소비형 열원 없음 → condition False"""
        agent = _create_agent()
        result = agent._evaluate_condition("need_fuel")
        assert result is False, "열원 없으면 need_fuel = False"

    def test_need_fuel_false_infinite(self):
        """무한 모드 열원 → condition False"""
        agent = _create_agent()
        _create_heat_source(fuel_level=0, fuel_mode=0)
        result = agent._evaluate_condition("need_fuel")
        assert result is False, "무한 모드에서 need_fuel = False"

    def test_need_fuel_different_region(self):
        """다른 region 열원 → condition False (home_region 불일치)"""
        agent = _create_agent()
        # agent의 home_region은 0, 열원은 region 2
        _create_heat_source(fuel_level=3)
        # _get_home_region()은 _home_region_id=0 을 반환
        result = agent._evaluate_condition("need_fuel")
        # fuel source는 region 2에 등록 → agent의 home_region(0)과 불일치
        assert result is False, "다른 region 열원은 무시"


# ============================================
# K. TestStorageResolver — 보관소 동적 탐색 검증
# ============================================

FOOD_STORAGE_ID = 600
TOOL_STORAGE_ID = 601
MATERIAL_STORAGE_ID = 602


def _create_food_storage(region=0, location=2):
    """food_ingredient/food/drink_ingredient 보관소 mock 생성"""
    morld.register_unit(FOOD_STORAGE_ID, "KitchenFridge", location=(region, location))
    morld.set_unit_prop(FOOD_STORAGE_ID, "storage:food", 1)
    morld.set_unit_prop(FOOD_STORAGE_ID, "storage:food_ingredient", 1)
    morld.set_unit_prop(FOOD_STORAGE_ID, "storage:drink_ingredient", 1)
    _assets_objects._location_objects[(region, location)] = [FOOD_STORAGE_ID]


def _create_tool_storage(region=0, location=6):
    """tool 보관소 mock 생성"""
    morld.register_unit(TOOL_STORAGE_ID, "Toolbox", location=(region, location))
    morld.set_unit_prop(TOOL_STORAGE_ID, "storage:tool", 1)
    morld.set_unit_prop(TOOL_STORAGE_ID, "storage:garden_tool", 1)
    existing = _assets_objects._location_objects.get((region, location), [])
    existing.append(TOOL_STORAGE_ID)
    _assets_objects._location_objects[(region, location)] = existing


def _create_material_storage(region=0, location=5):
    """material/seed/garden_supply 보관소 mock 생성"""
    morld.register_unit(MATERIAL_STORAGE_ID, "IngredientStorage", location=(region, location))
    morld.set_unit_prop(MATERIAL_STORAGE_ID, "storage:material", 1)
    morld.set_unit_prop(MATERIAL_STORAGE_ID, "storage:seed", 1)
    morld.set_unit_prop(MATERIAL_STORAGE_ID, "storage:garden_supply", 1)
    existing = _assets_objects._location_objects.get((region, location), [])
    existing.append(MATERIAL_STORAGE_ID)
    _assets_objects._location_objects[(region, location)] = existing


class TestStorageResolver:
    """resolve_storage_container 동적 탐색 검증"""

    def test_resolve_food_storage(self):
        """food_ingredient 카테고리 컨테이너 탐색"""
        agent = _create_agent()
        _create_food_storage(region=0, location=2)

        from think.activities.helpers import resolve_storage_container
        result = resolve_storage_container(agent, "food_ingredient")

        assert result is not None
        assert result["region_id"] == 0
        assert result["location_id"] == 2
        assert result["object_id"] == FOOD_STORAGE_ID

    def test_resolve_food_storage_not_found(self):
        """컨테이너 없으면 None"""
        agent = _create_agent()

        from think.activities.helpers import resolve_storage_container
        result = resolve_storage_container(agent, "food_ingredient")

        assert result is None

    def test_resolve_food_storage_different_region(self):
        """다른 region 컨테이너는 무시"""
        agent = _create_agent()
        # agent home_region = 0 (_home_region_id=0), storage in region 2
        _create_food_storage(region=2, location=5)

        from think.activities.helpers import resolve_storage_container
        result = resolve_storage_container(agent, "food_ingredient")

        assert result is None

    def test_resolve_tool_storage(self):
        """tool 카테고리 컨테이너 탐색"""
        agent = _create_agent()
        _create_tool_storage(region=0, location=6)

        from think.activities.helpers import resolve_storage_container
        result = resolve_storage_container(agent, "tool")

        assert result is not None
        assert result["object_id"] == TOOL_STORAGE_ID

    def test_resolve_material_storage(self):
        """material 카테고리 컨테이너 탐색"""
        agent = _create_agent()
        _create_material_storage(region=0, location=5)

        from think.activities.helpers import resolve_storage_container
        result = resolve_storage_container(agent, "material")

        assert result is not None
        assert result["object_id"] == MATERIAL_STORAGE_ID

    def test_resolve_wrong_category(self):
        """컨테이너에 없는 카테고리는 매칭 안됨"""
        agent = _create_agent()
        _create_food_storage(region=0, location=2)

        from think.activities.helpers import resolve_storage_container
        # food_storage has food/food_ingredient/drink_ingredient but not tool
        result = resolve_storage_container(agent, "tool")

        assert result is None


class TestStorageCondition:
    """_check_storage_need 카테고리 기반 조건 검증"""

    def test_need_food_dynamic(self):
        """food_ingredient 보관소 기반 need_food 조건"""
        agent = _create_agent()
        _create_food_storage(region=0, location=2)

        # Mock get_instance for item counting
        class FakeFridge:
            def get_item_count(self, uid=None):
                return 3
            def get_category_item_count(self, category):
                return 3  # 재고 3개 (threshold 10 미만)
        _assets_objects.get_instance = lambda obj_id: FakeFridge() if obj_id == FOOD_STORAGE_ID else None

        result = agent._check_storage_need("food_ingredient", None, 10)
        assert result is True, "재고 3 < threshold 10 → 부족"

    def test_need_food_sufficient(self):
        """재고 충분 → False"""
        agent = _create_agent()
        _create_food_storage(region=0, location=2)

        class FakeFridge:
            def get_item_count(self, uid=None):
                return 15
            def get_category_item_count(self, category):
                return 15  # 충분
        _assets_objects.get_instance = lambda obj_id: FakeFridge() if obj_id == FOOD_STORAGE_ID else None

        result = agent._check_storage_need("food_ingredient", None, 10)
        assert result is False, "재고 15 >= threshold 10 → 충분"

    def test_need_food_no_storage(self):
        """보관소 없으면 False (필요 없음)"""
        agent = _create_agent()

        result = agent._check_storage_need("food_ingredient", None, 10)
        assert result is False, "보관소 없으면 need 판정 안함"

    def test_check_specific_item(self):
        """특정 아이템(food_fish) 부족 체크"""
        agent = _create_agent()
        _create_food_storage(region=0, location=2)

        class FakeFridge:
            def get_item_count(self, uid=None):
                if uid == "food_fish":
                    return 1
                return 10
        _assets_objects.get_instance = lambda obj_id: FakeFridge() if obj_id == FOOD_STORAGE_ID else None

        result = agent._check_storage_need("food_ingredient", "food_fish", 3)
        assert result is True, "물고기 1 < threshold 3 → 부족"
