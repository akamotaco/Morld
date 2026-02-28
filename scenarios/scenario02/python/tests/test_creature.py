# test_creature.py — 세력 시스템 + CreatureAgent + 스포너 테스트
#
# - combat.py: is_faction_hostile / is_creature_unit
# - think/creature_agent.py: CreatureAgent think 4-tier
# - spawner.py: 스폰/수명/시체 정리
# - think._check_combat_threat: 세력 기반 적대 감지

import sys
import os
import types
import pytest

# ========================================
# 1. Mock morld 주입
# ========================================

sys.path.insert(0, os.path.dirname(__file__))
from mock_morld import MockMorld

mock = MockMorld()
sys.modules["morld"] = mock

# MockMorld에 없는 API 추가
if not hasattr(mock, 'get_actual_props'):
    def _get_actual_props(unit_id):
        u = mock._units.get(unit_id)
        if not u:
            return {}
        result = dict(u["props"])
        for item_id in u.get("equipped", []):
            item = mock._items.get(item_id)
            if item:
                for k, v in item.get("equip_props", {}).items():
                    result[k] = result.get(k, 0) + v
        return result
    mock.get_actual_props = _get_actual_props

if not hasattr(mock, 'get_current_time'):
    def _get_current_time():
        return mock._time
    mock.get_current_time = _get_current_time

if not hasattr(mock, 'set_unit'):
    def _set_unit(unit_id, key, value):
        u = mock._units.get(unit_id)
        if u:
            u["info"][key] = value
    mock.set_unit = _set_unit

if not hasattr(mock, 'get_inventory'):
    def _get_inventory(unit_id):
        u = mock._units.get(unit_id)
        return dict(u["inventory"]) if u else {}
    mock.get_inventory = _get_inventory

# ========================================
# 2. Stub 모듈 구성
# ========================================

# sound stub
sound_mod = types.ModuleType("sound")
sound_mod.emit_sound = lambda *a, **kw: None
sound_mod.register_hearing = lambda *a, **kw: None
sys.modules["sound"] = sound_mod

# survival stub
survival_mod = types.ModuleType("survival")
survival_mod._fainted_npcs = {}
survival_mod._faint_end = {}

def _get_health(uid):
    return mock.get_unit_prop(uid, "생존:체력") or 100

def _get_max_health(uid):
    return mock.get_unit_prop(uid, "생존:최대체력") or 100

def _add_health(uid, amount):
    cur = _get_health(uid)
    mx = _get_max_health(uid)
    new_hp = max(0, min(mx, cur + amount))
    mock.set_unit_prop(uid, "생존:체력", new_hp)

def _is_npc_fainted(uid):
    return uid in survival_mod._fainted_npcs

def _get_faint_remaining(uid):
    return survival_mod._faint_end.get(uid, 0)

def _is_npc_exhausted(uid):
    return False

def _is_npc_sleeping(uid):
    return False

survival_mod.get_health = _get_health
survival_mod.get_max_health = _get_max_health
survival_mod.add_health = _add_health
survival_mod.is_npc_fainted = _is_npc_fainted
survival_mod.get_faint_remaining_millis = _get_faint_remaining
survival_mod.is_npc_exhausted = _is_npc_exhausted
survival_mod.is_npc_sleeping = _is_npc_sleeping
sys.modules["survival"] = survival_mod

# events stub
events_mod = types.ModuleType("events")
events_mod.subscribe_time_elapsed = lambda *a, **kw: None
sys.modules["events"] = events_mod

# think stub (BaseAgent) — __path__ 설정으로 패키지처럼 동작
_scenario_path = os.path.join(os.path.dirname(__file__), "..")
think_mod = types.ModuleType("think")
think_mod.__path__ = [os.path.join(_scenario_path, "think")]  # 실제 패키지 경로
think_mod._agents = {}
think_mod.get_all_agents = lambda: think_mod._agents
think_mod.unregister_agent = lambda uid: think_mod._agents.pop(uid, None)
think_mod.register_agent = lambda uid, agent: think_mod._agents.__setitem__(uid, agent)

class _StubBaseAgent:
    """Minimal BaseAgent stub for character imports"""
    BATTLE_BEHAVIOR = None
    _action_duration_overrides = {}
    def __init__(self, unit_id=None):
        self.unit_id = unit_id
    def set_base_schedule(self, schedule):
        pass

think_mod.BaseAgent = _StubBaseAgent
think_mod.register_agent_class = lambda uid: (lambda cls: cls)
sys.modules["think"] = think_mod

# carry stub
carry_mod = types.ModuleType("carry")
carry_mod.is_being_carried = lambda uid: False
carry_mod.get_carrier = lambda uid: None
carry_mod.is_carrying = lambda uid: False
sys.modules["carry"] = carry_mod

# ui stub
ui_mod = types.ModuleType("ui")
ui_mod.dialog = lambda *a, **kw: None
sys.modules["ui"] = ui_mod

# stealth stub
stealth_mod = types.ModuleType("stealth")
stealth_mod.is_unit_stealthed = lambda uid: False
sys.modules["stealth"] = stealth_mod

# restraint stub
restraint_mod = types.ModuleType("restraint")
restraint_mod.is_restrained = lambda uid: False
restraint_mod.get_restrained_units_at = lambda rid, lid: []
sys.modules["restraint"] = restraint_mod

# equipment stub
equip_mod = types.ModuleType("equipment")
equip_mod.get_equipped_items = lambda uid: []
sys.modules["equipment"] = equip_mod

# romance stub
romance_mod = types.ModuleType("romance")
romance_mod.get_interrupted_context = lambda: None
sys.modules["romance"] = romance_mod

# inventory stub
inv_mod = types.ModuleType("inventory")
inv_mod.safe_give_item = lambda uid, iid, count=1: mock.give_item(uid, iid, count)
sys.modules["inventory"] = inv_mod

# reputation stub
rep_mod = types.ModuleType("reputation")
rep_mod.get_trust = lambda: 0
sys.modules["reputation"] = rep_mod

# ========================================
# 3. Import modules under test
# ========================================

scenario_path = os.path.join(os.path.dirname(__file__), "..")
if scenario_path not in sys.path:
    sys.path.insert(0, scenario_path)

import combat
import spawner

# ========================================
# 4. CreatureAgent — BaseAgent를 직접 상속할 수 없으므로
#    creature_agent.py의 로직을 _StubBaseAgent 기반으로 재구현
# ========================================

# creature_agent.py는 think.BaseAgent를 import하므로
# think 모듈의 BaseAgent를 실제 동작하는 stub으로 교체

class _TestableBaseAgent:
    """테스트용 BaseAgent — creature_agent.py가 의존하는 메서드 제공"""
    BATTLE_BEHAVIOR = None
    _action_duration_overrides = {}

    def __init__(self, unit_id=None):
        self.unit_id = unit_id
        self.schedule_stack = [None]
        self._action_taken = False
        self._memory = {}
        self._arrived = False
        self._fsm_stack = []

    def set_base_schedule(self, schedule):
        self.schedule_stack[0] = schedule

    def get_current_schedule(self):
        for i in range(len(self.schedule_stack) - 1, -1, -1):
            if self.schedule_stack[i] is not None:
                return self.schedule_stack[i]
        return None

    def get_time(self):
        return mock.get_game_time()

    def get_location(self):
        return mock.get_unit_location(self.unit_id)

    def _remaining_millis_in_entry(self, entry):
        millis = self.get_time()
        end = entry["end"]
        start = entry["start"]
        if end < start:
            if millis >= start:
                return (86_400_000 - millis) + end
            else:
                return end - millis
        else:
            return max(0, end - millis)

    def _insert_idle_job(self, name, duration_millis):
        if duration_millis > 0:
            mock.insert_job(self.unit_id, {
                "name": name,
                "action": "stay",
                "duration": duration_millis,
            })

    def _is_at(self, target):
        loc = self.get_location()
        return (loc and loc[0] == target["region_id"]
                and loc[1] == target["location_id"])

    def _move_to(self, target, name="이동"):
        mock.insert_job(self.unit_id, {
            "name": name,
            "action": "move",
            "region_id": target["region_id"],
            "location_id": target["location_id"],
            "target_x": 0,
            "duration": 0,
        })
        self._action_taken = True

    def _fsm_push(self, state):
        """FSM 스택 push (간략화 — 동일 레벨 auto-pop)"""
        self._fsm_stack = [s for s in self._fsm_stack
                           if s.level < state.level]
        self._fsm_stack.append(state)

    def _fsm_pop(self):
        """FSM 스택 pop"""
        if self._fsm_stack:
            self._fsm_stack.pop()

    def _fsm_top(self):
        """FSM 스택 top"""
        return self._fsm_stack[-1] if self._fsm_stack else None

    def _check_combat_threat(self):
        """세력 기반 전투 위협 감지 (간략화)"""
        behavior = getattr(self, 'BATTLE_BEHAVIOR', None)
        if not behavior:
            return False

        # 이미 전투 FSM 상태이면 True
        if any(s.state_type == "combat" for s in self._fsm_stack):
            self._insert_idle_job("전투", 6_000)
            self._action_taken = True
            return True

        my_loc = mock.get_unit_location(self.unit_id)
        if not my_loc:
            return False

        units = mock.get_units_at_location(my_loc[0], my_loc[1])
        my_faction = mock.get_unit_prop(self.unit_id, "전투:세력")

        for uid in units:
            if uid == self.unit_id:
                continue
            if mock.get_unit_prop(uid, "상태:사망"):
                continue
            their_faction = mock.get_unit_prop(uid, "전투:세력")
            if combat.is_faction_hostile(my_faction, their_faction):
                from think.fsm import CombatState
                self._fsm_push(CombatState(uid))
                self._insert_idle_job("전투", 6_000)
                self._action_taken = True
                return True
        return False

    def _do_wander(self, entry=None):
        if entry is None:
            entry = {"name": "배회", "start": 0, "end": 86_400_000, "activity": "순찰"}
        remaining = self._remaining_millis_in_entry(entry)
        if remaining < 5 * 60_000:
            self._insert_idle_job(entry["name"], max(remaining, 1_000))
        else:
            # 랜덤 이동 대신 간단히 idle (테스트용)
            idle_ms = min(remaining, 20 * 60_000)
            self._insert_idle_job(entry["name"], idle_ms)
        self._action_taken = True


# think.BaseAgent 교체
think_mod.BaseAgent = _TestableBaseAgent

# 이제 creature_agent를 import
from think.creature_agent import CreatureAgent


# ========================================
# Fixtures
# ========================================

@pytest.fixture(autouse=True)
def setup():
    """각 테스트 전 상태 초기화"""
    mock.reset()
    if not hasattr(mock, 'get_actual_props'):
        mock.get_actual_props = _get_actual_props
    if not hasattr(mock, 'get_current_time'):
        mock.get_current_time = _get_current_time
    if not hasattr(mock, 'set_unit'):
        mock.set_unit = _set_unit
    if not hasattr(mock, 'get_inventory'):
        mock.get_inventory = _get_inventory
    combat.reset()
    survival_mod._fainted_npcs = {}
    survival_mod._faint_end = {}
    think_mod._agents.clear()
    spawner.reset()
    yield


# ========================================
# Helpers
# ========================================

WOLF_SCHEDULE = [
    {"name": "수면",  "start": 0,          "end": 18_000_000,  "activity": "수면"},
    {"name": "순찰",  "start": 18_000_000,  "end": 43_200_000,  "activity": "순찰"},
    {"name": "휴식",  "start": 43_200_000,  "end": 54_000_000,  "activity": "휴식"},
    {"name": "순찰",  "start": 54_000_000,  "end": 75_600_000,  "activity": "순찰"},
    {"name": "복귀",  "start": 75_600_000,  "end": 82_800_000,  "activity": "복귀"},
    {"name": "수면",  "start": 82_800_000,  "end": 86_400_000,  "activity": "수면"},
]


def make_creature(uid, name="늑대", faction="늑대", hp=40,
                  location=(3, 4), schedule=None, detect_range=120):
    """테스트용 생물 유닛 생성"""
    props = {
        "전투:세력": faction,
        "생존:체력": hp,
        "생존:최대체력": hp,
        "전투:공격력": 8,
        "전투:방어력": 3,
        "전투:명중": 75,
        "전투:회피": 15,
        "전투:사거리": 70,
        "전투:감지거리": detect_range,
        "전투:공격속도": 1.0,
    }
    mock.register_unit(uid, name=name, props=props, location=location)
    mock.set_unit_position(uid, 50)
    agent = CreatureAgent(uid, schedule=schedule)
    agent.BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 70,
        "retreat_threshold": 0.2,
    }
    return agent


def make_npc(uid, name="NPC", faction=None, hp=100, location=(3, 4)):
    """테스트용 NPC(주민) 유닛 생성"""
    props = {
        "생존:체력": hp,
        "생존:최대체력": hp,
        "전투:공격력": 5,
        "전투:방어력": 2,
        "전투:명중": 80,
        "전투:회피": 5,
        "전투:사거리": 50,
        "전투:감지거리": 100,
        "전투:공격속도": 1.0,
    }
    if faction:
        props["전투:세력"] = faction
    mock.register_unit(uid, name=name, props=props, location=location)
    mock.set_unit_position(uid, 100)


# ========================================
# Tests: 세력 시스템 (combat.py)
# ========================================

class TestFactionHostility:
    """is_faction_hostile() 양방향 적대 판정"""

    def test_same_faction_not_hostile(self):
        """같은 세력끼리는 적대 아님"""
        assert combat.is_faction_hostile("늑대", "늑대") is False
        assert combat.is_faction_hostile("주민", "주민") is False
        assert combat.is_faction_hostile("거미", "거미") is False

    def test_wolf_vs_citizen(self):
        """늑대 vs 주민 — 적대"""
        assert combat.is_faction_hostile("늑대", "주민") is True
        assert combat.is_faction_hostile("주민", "늑대") is True

    def test_wolf_vs_spider(self):
        """늑대 vs 거미 — 적대"""
        assert combat.is_faction_hostile("늑대", "거미") is True
        assert combat.is_faction_hostile("거미", "늑대") is True

    def test_bat_vs_citizen(self):
        """박쥐 vs 주민 — 적대"""
        assert combat.is_faction_hostile("박쥐", "주민") is True

    def test_bat_vs_wolf_not_hostile(self):
        """박쥐 vs 늑대 — 비적대 (테이블에 없음)"""
        assert combat.is_faction_hostile("박쥐", "늑대") is False

    def test_bat_vs_spider_not_hostile(self):
        """박쥐 vs 거미 — 비적대"""
        assert combat.is_faction_hostile("박쥐", "거미") is False

    def test_none_faction_defaults_to_citizen(self):
        """세력 미설정(None) → '주민'으로 취급"""
        assert combat.is_faction_hostile(None, "늑대") is True
        assert combat.is_faction_hostile("늑대", None) is True
        assert combat.is_faction_hostile(None, None) is False

    def test_unknown_faction(self):
        """테이블에 없는 세력 — 같은 세력=우호, 정의 안 된 이종=중립"""
        assert combat.is_faction_hostile("야생", "야생") is False
        # "야생" vs "주민" — FACTION_RELATIONS에 적대 정의됨
        assert combat.is_faction_hostile("야생", "주민") is True

    def test_citizen_friendly_with_citizen(self):
        """주민 vs 주민 — 우호 (같은 세력)"""
        assert combat.get_faction_relation("주민", "주민") == 1

    def test_faction_relation_friendly(self):
        """같은 세력은 항상 우호"""
        assert combat.is_faction_friendly("주민", "주민") is True
        assert combat.is_faction_friendly("늑대", "늑대") is True

    def test_faction_relation_neutral(self):
        """정의 안 된 이종 세력은 중립"""
        assert combat.get_faction_relation("박쥐", "늑대") == 0
        assert combat.is_faction_hostile("박쥐", "늑대") is False
        assert combat.is_faction_friendly("박쥐", "늑대") is False


class TestIsCreatureUnit:
    """is_creature_unit() — 세력 기반 생물 판별"""

    def test_wolf_is_creature(self):
        make_creature(10, faction="늑대")
        assert combat.is_creature_unit(10) is True

    def test_citizen_not_creature(self):
        make_npc(20, faction="주민")
        assert combat.is_creature_unit(20) is False

    def test_no_faction_not_creature(self):
        """세력 미설정 → 생물 아님"""
        make_npc(30)
        assert combat.is_creature_unit(30) is False

    def test_nonexistent_unit(self):
        """존재하지 않는 유닛"""
        assert combat.is_creature_unit(999) is False


# ========================================
# Tests: CreatureAgent think() 4-tier
# ========================================

class TestCreatureAgentThink:
    """CreatureAgent.think() 계층 우선순위"""

    def test_tier0_carried(self):
        """Tier 0: 운반 중 → 운반 중 job"""
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        carry_mod.is_being_carried = lambda uid: uid == 10
        try:
            agent.think()
            job = mock.get_current_job(10)
            assert job is not None
            assert job["name"] == "운반 중"
            assert job["action"] == "stay"
        finally:
            carry_mod.is_being_carried = lambda uid: False

    def test_tier1_dead(self):
        """Tier 1: 사망 → 사망 대기 job (1시간)"""
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock.set_unit_prop(10, "상태:사망", True)
        agent.think()
        job = mock.get_current_job(10)
        assert job["name"] == "사망"
        assert job["duration"] == 3_600_000

    def test_tier2_fainted(self):
        """Tier 2: 기절 → 기절 대기 job"""
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        survival_mod._fainted_npcs[10] = True
        survival_mod._faint_end[10] = 30_000
        agent.think()
        job = mock.get_current_job(10)
        assert job["name"] == "기절"
        assert job["duration"] >= 1_000

    def test_tier3_combat_detects_enemy(self):
        """Tier 3: 같은 location에 적대 세력 → 전투 개시"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 4))  # 주민 (늑대와 적대)
        mock._time = 20_000_000  # 순찰 시간대
        agent.think()
        assert any(s.state_type == "combat" for s in agent._fsm_stack)

    def test_tier3_no_enemy_different_location(self):
        """다른 location의 유닛은 감지 안 함"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 5))  # 다른 location
        mock._time = 20_000_000
        agent.think()
        assert not any(s.state_type == "combat" for s in agent._fsm_stack)

    def test_tier3_skips_dead_enemies(self):
        """사망한 유닛은 적으로 감지 안 함"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 4))
        mock.set_unit_prop(20, "상태:사망", True)
        mock._time = 20_000_000
        agent.think()
        assert not any(s.state_type == "combat" for s in agent._fsm_stack)

    def test_tier3_same_faction_no_fight(self):
        """같은 세력끼리는 전투 안 함"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_creature(20, faction="늑대", location=(3, 4),
                      schedule=WOLF_SCHEDULE)
        mock._time = 20_000_000
        agent.think()
        assert not any(s.state_type == "combat" for s in agent._fsm_stack)

    def test_tier4_schedule_sleep(self):
        """Tier 4: 수면 시간 → 수면 idle job"""
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 10_000_000  # 00:00~05:00 수면 시간
        agent.think()
        job = mock.get_current_job(10)
        assert job is not None
        assert job["name"] == "수면"
        assert job["action"] == "stay"

    def test_tier4_schedule_patrol(self):
        """Tier 4: 순찰 시간 → wander job"""
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 20_000_000  # 05:00~12:00 순찰 시간
        agent.think()
        job = mock.get_current_job(10)
        assert job is not None
        assert job["action"] == "stay"  # wander = idle (테스트 간략화)

    def test_tier4_schedule_rest(self):
        """Tier 4: 휴식 시간 → 휴식 idle job"""
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 45_000_000  # 12:00~15:00 휴식 시간
        agent.think()
        job = mock.get_current_job(10)
        assert job["name"] == "휴식"

    def test_safety_net(self):
        """스케줄 없으면 safety net job"""
        agent = make_creature(10, schedule=None)
        agent.think()
        job = mock.get_current_job(10)
        assert job is not None
        assert job["name"] == "할 일 없음"

    def test_always_inserts_job(self):
        """모든 think() 경로가 job을 삽입 (DES 필수)"""
        # 수면
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 5_000_000
        agent.think()
        assert mock.get_current_job(10) is not None

        mock.clear_jobs(10)

        # 순찰
        mock._time = 20_000_000
        agent._memory.clear()
        agent.think()
        assert mock.get_current_job(10) is not None

        mock.clear_jobs(10)

        # 사망
        mock.set_unit_prop(10, "상태:사망", True)
        agent.think()
        assert mock.get_current_job(10) is not None


# ========================================
# Tests: CreatureAgent 복귀 행동
# ========================================

class TestCreatureReturn:
    """_do_return_to_lair — spawn location 복귀"""

    def test_return_moves_when_away(self):
        """다른 location에 있을 때 → 이동 job"""
        agent = make_creature(10, location=(3, 2), schedule=WOLF_SCHEDULE)
        mock.set_unit_prop(10, "전투:홈리전", 3)
        mock.set_unit_prop(10, "생물:스폰위치", 4)
        mock._time = 76_000_000  # 21:00~23:00 복귀 시간

        agent.think()
        job = mock.get_current_job(10)
        assert job is not None
        assert job["action"] == "move"
        assert job["region_id"] == 3
        assert job["location_id"] == 4

    def test_return_idles_when_home(self):
        """이미 spawn location에 있을 때 → idle job"""
        agent = make_creature(10, location=(3, 4), schedule=WOLF_SCHEDULE)
        mock.set_unit_prop(10, "전투:홈리전", 3)
        mock.set_unit_prop(10, "생물:스폰위치", 4)
        mock._time = 76_000_000

        agent.think()
        job = mock.get_current_job(10)
        assert job is not None
        assert job["action"] == "stay"
        assert job["name"] == "복귀"


# ========================================
# Tests: CreatureAgent 스케줄 탐색
# ========================================

class TestCreatureScheduleEntry:
    """_get_creature_entry — 현재 시간에 맞는 스케줄 entry"""

    def test_finds_correct_entry(self):
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 10_000_000  # 수면 시간대 (0~18_000_000)
        entry = agent._get_creature_entry()
        assert entry is not None
        assert entry["activity"] == "수면"

    def test_patrol_time(self):
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 30_000_000  # 순찰 시간대 (18M~43.2M)
        entry = agent._get_creature_entry()
        assert entry["activity"] == "순찰"

    def test_rest_time(self):
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 50_000_000  # 휴식 시간대 (43.2M~54M)
        entry = agent._get_creature_entry()
        assert entry["activity"] == "휴식"

    def test_return_time(self):
        agent = make_creature(10, schedule=WOLF_SCHEDULE)
        mock._time = 78_000_000  # 복귀 시간대 (75.6M~82.8M)
        entry = agent._get_creature_entry()
        assert entry["activity"] == "복귀"

    def test_no_schedule_returns_none(self):
        agent = make_creature(10, schedule=None)
        mock._time = 10_000_000
        entry = agent._get_creature_entry()
        assert entry is None

    def test_midnight_wrap(self):
        """자정 넘기기 스케줄 (end < start)"""
        midnight_schedule = [
            {"name": "순찰", "start": 72_000_000, "end": 7_200_000, "activity": "순찰"},
        ]
        agent = make_creature(10, schedule=midnight_schedule)

        # 자정 이전 (23시 = 82.8M → 72M~7.2M 범위)
        mock._time = 80_000_000
        entry = agent._get_creature_entry()
        assert entry is not None
        assert entry["activity"] == "순찰"

        # 자정 이후 (01시 = 3.6M → 72M~7.2M 범위)
        mock._time = 3_600_000
        entry = agent._get_creature_entry()
        assert entry is not None
        assert entry["activity"] == "순찰"


# ========================================
# Tests: Spawner 스폰
# ========================================

class _MockMonsterClass:
    """spawner 테스트용 가짜 Monster 클래스"""
    unique_id = "test_wolf"
    name = "테스트 늑대"
    type = "creature"
    owner = None
    props = {
        "전투:세력": "늑대",
        "생존:체력": 40,
        "생존:최대체력": 40,
    }
    actions = ["call:attack:공격#"]
    SCHEDULE = WOLF_SCHEDULE

    def __init__(self):
        self.instance_id = None

    def instantiate(self, unit_id, region_id, location_id):
        self.instance_id = unit_id
        mock.add_unit(unit_id, self.name, region_id, location_id, self.type)
        mock.set_unit_props(unit_id, dict(self.props))

    def _populate_inventory(self):
        pass


class TestSpawnerRegister:
    """register_spawn_source + _try_spawn"""

    def test_register_creates_source(self):
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=6,
            region_id=3,
            location_id=4,
            lifespan_hours=72,
        )
        assert "test_wolves" in spawner._spawn_sources
        src = spawner._spawn_sources["test_wolves"]
        assert src["max"] == 2
        assert src["interval_h"] == 6
        assert src["lifespan_h"] == 72

    def test_spawn_creates_unit(self):
        """스폰 조건 충족 시 유닛 생성"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=1,
            region_id=3,
            location_id=4,
        )
        mock._time = 3_600_000  # 1시간 경과
        spawner._on_time_elapsed(3_600_000)

        src = spawner._spawn_sources["test_wolves"]
        assert len(src["spawned"]) >= 1
        spawned_id = src["spawned"][0]

        # 유닛 prop 확인
        assert mock.get_unit_prop(spawned_id, "전투:홈리전") == 3
        assert mock.get_unit_prop(spawned_id, "생물:스폰위치") == 4
        assert mock.get_unit_prop(spawned_id, "생물:탄생시각") is not None

    def test_max_count_limit(self):
        """최대 수 초과 시 스폰 안 함"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=1,
            interval_hours=1,
            region_id=3,
            location_id=4,
        )
        # 첫 번째 스폰
        mock._time = 3_600_000
        spawner._on_time_elapsed(3_600_000)
        # 두 번째 스폰 시도 (이미 1마리)
        mock._time = 7_200_000
        spawner._on_time_elapsed(3_600_000)

        src = spawner._spawn_sources["test_wolves"]
        assert len(src["spawned"]) == 1

    def test_interval_respected(self):
        """스폰 간격 미충족 시 스폰 안 함"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=5,
            interval_hours=6,
            region_id=3,
            location_id=4,
        )
        # 1시간 → 스폰
        mock._time = 3_600_000
        spawner._on_time_elapsed(3_600_000)
        count_after_1h = len(spawner._spawn_sources["test_wolves"]["spawned"])

        # 2시간 → 간격 미충족 (6시간 간격), 추가 스폰 없어야
        mock._time = 7_200_000
        spawner._on_time_elapsed(3_600_000)
        count_after_2h = len(spawner._spawn_sources["test_wolves"]["spawned"])

        assert count_after_1h == count_after_2h


# ========================================
# Tests: Spawner 수명 + 시체 정리
# ========================================

class TestSpawnerLifecycle:
    """수명 만료 자연 소멸 + 시체 정리"""

    def test_natural_despawn_at_spawn_location(self):
        """수명 초과 + spawn location → 자연 소멸"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=1,
            region_id=3,
            location_id=4,
            lifespan_hours=2,  # 짧은 수명
        )
        # 스폰
        mock._time = 3_600_000
        spawner._on_time_elapsed(3_600_000)
        src = spawner._spawn_sources["test_wolves"]
        assert len(src["spawned"]) == 1
        spawned_id = src["spawned"][0]

        # 수명 초과 (탄생시각+2h 이상) + spawn location에 위치
        mock.set_unit_location(spawned_id, 3, 4)
        mock._time = 3_600_000 + 3 * 3_600_000  # 3시간 경과 (수명 2시간 초과)
        spawner._on_time_elapsed(3_600_000)

        # spawned 목록에서 제거됨
        assert spawned_id not in src["spawned"]
        # 맵 밖으로 이동
        loc = mock.get_unit_location(spawned_id)
        assert loc == (-1, -1)

    def test_no_despawn_away_from_lair(self):
        """수명 초과 but spawn location이 아닌 곳 → 소멸 안 함"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=1,
            region_id=3,
            location_id=4,
            lifespan_hours=2,
        )
        mock._time = 3_600_000
        spawner._on_time_elapsed(3_600_000)
        src = spawner._spawn_sources["test_wolves"]
        spawned_id = src["spawned"][0]

        # 다른 location으로 이동
        mock.set_unit_location(spawned_id, 3, 2)  # 참나무 숲
        mock._time = 3_600_000 + 3 * 3_600_000  # 수명 초과
        spawner._on_time_elapsed(3_600_000)

        # 아직 spawned 목록에 있음 (복귀 후 다음 사이클에 소멸)
        assert spawned_id in src["spawned"]

    def test_dead_unit_removed_from_spawned(self):
        """사망 유닛은 spawned 목록에서 제거"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=1,
            region_id=3,
            location_id=4,
        )
        mock._time = 3_600_000
        spawner._on_time_elapsed(3_600_000)
        src = spawner._spawn_sources["test_wolves"]
        spawned_id = src["spawned"][0]

        # 사망 처리
        mock.set_unit_prop(spawned_id, "상태:사망", True)
        mock._time = 7_200_000
        spawner._on_time_elapsed(3_600_000)

        # spawned 목록에서 제거됨 (시체 정리와 별개)
        assert spawned_id not in src["spawned"]

    def test_corpse_cleanup(self):
        """시체 정리: 사망 후 4시간 + 플레이어 부재"""
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=1,
            region_id=3,
            location_id=4,
        )
        mock._time = 3_600_000
        spawner._on_time_elapsed(3_600_000)
        src = spawner._spawn_sources["test_wolves"]
        spawned_id = src["spawned"][0]

        # 사망 처리
        mock.set_unit_prop(spawned_id, "상태:사망", True)
        mock.set_unit_prop(spawned_id, "상태:사망시각", mock._time)

        # 플레이어를 다른 위치에
        mock.register_unit(1, "Player", location=(0, 0))
        mock._player_id = 1

        # 4시간 이상 경과
        mock._time = 3_600_000 + 5 * 3_600_000
        spawner._on_time_elapsed(3_600_000)

        # 시체 디스폰 (맵 밖)
        loc = mock.get_unit_location(spawned_id)
        assert loc == (-1, -1)


class TestSpawnerReset:
    """spawner.reset() 챕터 전환"""

    def test_reset_clears_all(self):
        spawner.register_spawn_source(
            source_id="test_wolves",
            monster_class=_MockMonsterClass,
            max_count=2,
            interval_hours=6,
            region_id=3,
            location_id=4,
        )
        assert len(spawner._spawn_sources) > 0
        spawner.reset()
        assert len(spawner._spawn_sources) == 0


# ========================================
# Tests: 세력 + 전투 감지 통합
# ========================================

class TestFactionCombatIntegration:
    """_check_combat_threat가 세력 시스템을 올바르게 사용하는지"""

    def test_wolf_detects_citizen(self):
        """늑대가 주민을 적으로 감지"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 4))
        result = agent._check_combat_threat()
        assert result is True
        combat_state = next(s for s in agent._fsm_stack
                             if s.state_type == "combat")
        assert combat_state.target_id == 20

    def test_wolf_ignores_wolf(self):
        """늑대가 늑대를 무시"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_creature(20, faction="늑대", location=(3, 4),
                      schedule=WOLF_SCHEDULE)
        result = agent._check_combat_threat()
        assert result is False

    def test_wolf_detects_spider(self):
        """늑대가 거미를 적으로 감지"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_creature(20, faction="거미", location=(3, 4),
                      schedule=WOLF_SCHEDULE)
        result = agent._check_combat_threat()
        assert result is True

    def test_bat_ignores_wolf(self):
        """박쥐가 늑대를 무시 (적대 관계 아님)"""
        agent = make_creature(10, faction="박쥐", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_creature(20, faction="늑대", location=(3, 4),
                      schedule=WOLF_SCHEDULE)
        result = agent._check_combat_threat()
        assert result is False

    def test_no_battle_behavior_returns_false(self):
        """BATTLE_BEHAVIOR 없으면 전투 감지 안 함"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        agent.BATTLE_BEHAVIOR = None
        make_npc(20, location=(3, 4))
        result = agent._check_combat_threat()
        assert result is False


# ========================================
# Tests: 우선순위 (tier 순서)
# ========================================

class TestTierPriority:
    """상위 tier가 하위 tier보다 우선"""

    def test_dead_overrides_combat(self):
        """사망 > 전투: 사망 상태면 적이 있어도 전투 안 함"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 4))
        mock.set_unit_prop(10, "상태:사망", True)
        mock._time = 20_000_000
        agent.think()
        job = mock.get_current_job(10)
        assert job["name"] == "사망"
        assert not any(s.state_type == "combat" for s in agent._fsm_stack)

    def test_faint_overrides_combat(self):
        """기절 > 전투"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 4))
        survival_mod._fainted_npcs[10] = True
        survival_mod._faint_end[10] = 30_000
        mock._time = 20_000_000
        agent.think()
        job = mock.get_current_job(10)
        assert job["name"] == "기절"

    def test_combat_overrides_schedule(self):
        """전투 > 스케줄: 적이 있으면 수면 안 하고 전투"""
        agent = make_creature(10, faction="늑대", location=(3, 4),
                              schedule=WOLF_SCHEDULE)
        make_npc(20, location=(3, 4))
        mock._time = 5_000_000  # 수면 시간대
        agent.think()
        # 전투가 우선 → FSM 스택에 CombatState
        assert any(s.state_type == "combat" for s in agent._fsm_stack)
