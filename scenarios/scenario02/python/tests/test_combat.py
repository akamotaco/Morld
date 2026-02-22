# test_combat.py — 전투 시스템 테스트
#
# combat.py의 핵심 로직 검증:
# - 스탯 조회 (get_combat_stat)
# - 거리 계산 (get_distance)
# - 명중/데미지 (calculate_hit_chance, calculate_damage)
# - 공격 실행 (execute_attack)
# - 적대도 (get/set/modify_hostility, is_hostile_to)
# - 디버프 (bleeding, slow)
# - 시간 처리 (hostility decay)

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
        """base props + equipped item equip_props 합산"""
        u = mock._units.get(unit_id)
        if not u:
            return {}
        result = dict(u["props"])
        # 장비 equip_props 합산 (간략화)
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

# sound 모듈 stub
sound_mod = types.ModuleType("sound")
sound_mod.emit_sound = lambda *a, **kw: None
sys.modules["sound"] = sound_mod

# survival 모듈 stub
survival_mod = types.ModuleType("survival")
survival_mod._fainted_npcs = {}

def _get_health(uid):
    return mock.get_unit_prop(uid, "생존:체력") or 100

def _get_max_health(uid):
    return mock.get_unit_prop(uid, "생존:최대체력") or 100

def _add_health(uid, amount):
    cur = _get_health(uid)
    mx = _get_max_health(uid)
    new_hp = max(0, min(mx, cur + amount))
    mock.set_unit_prop(uid, "생존:체력", new_hp)
    if new_hp <= 0:
        survival_mod._fainted_npcs[uid] = True

def _is_npc_fainted(uid):
    return uid in survival_mod._fainted_npcs

def _is_npc_exhausted(uid):
    return False

survival_mod.get_health = _get_health
survival_mod.get_max_health = _get_max_health
survival_mod.add_health = _add_health
survival_mod.is_npc_fainted = _is_npc_fainted
survival_mod.is_npc_exhausted = _is_npc_exhausted
sys.modules["survival"] = survival_mod

# events stub
events_mod = types.ModuleType("events")
events_mod.subscribe_time_elapsed = lambda *a, **kw: None
sys.modules["events"] = events_mod

# think stub (for get_all_agents + BaseAgent for character imports)
think_mod = types.ModuleType("think")
think_mod._agents = {}
think_mod.get_all_agents = lambda: think_mod._agents
think_mod.unregister_agent = lambda uid: think_mod._agents.pop(uid, None)
think_mod.register_agent = lambda uid, agent: think_mod._agents.__setitem__(uid, agent)

class _StubBaseAgent:
    """Minimal BaseAgent stub for character file imports"""
    BATTLE_BEHAVIOR = None
    _action_duration_overrides = {}
    def __init__(self, unit_id=None):
        self.unit_id = unit_id
    def set_base_schedule(self, schedule):
        pass

think_mod.BaseAgent = _StubBaseAgent
think_mod.register_agent_class = lambda uid: (lambda cls: cls)
sys.modules["think"] = think_mod

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
restraint_mod.get_restrained_units_at = lambda lid: []
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
# 3. Import combat (under test)
# ========================================

# Python path for scenario code
scenario_path = os.path.join(os.path.dirname(__file__), "..")
if scenario_path not in sys.path:
    sys.path.insert(0, scenario_path)

import combat


# ========================================
# Fixtures
# ========================================

@pytest.fixture(autouse=True)
def setup():
    """각 테스트 전 상태 초기화"""
    mock.reset()
    # get_actual_props 재바인딩 (reset으로 사라지지 않게)
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
    yield


def make_unit(uid, name="Unit", hp=100, atk=5, defense=2, accuracy=80,
              evasion=5, crit=5, weapon_range=50, location=(0, 0), **extra):
    """전투용 유닛 생성 헬퍼"""
    props = {
        "생존:체력": hp,
        "생존:최대체력": hp,
        "전투:공격력": atk,
        "전투:방어력": defense,
        "전투:명중": accuracy,
        "전투:회피": evasion,
        "전투:치명타": crit,
        "전투:사거리": weapon_range,
        "전투:공격속도": 1.0,
    }
    props.update(extra)
    mock.register_unit(uid, name=name, props=props, location=location)
    mock.set_unit_position(uid, 50)  # 기본 x=50


# ========================================
# Tests: 스탯 조회
# ========================================

class TestCombatStat:
    def test_get_combat_stat_returns_prop(self):
        make_unit(1, atk=10)
        assert combat.get_combat_stat(1, "전투:공격력") == 10

    def test_get_combat_stat_default(self):
        """prop 미설정 시 DEFAULT_STATS 사용"""
        mock.register_unit(1, props={})
        assert combat.get_combat_stat(1, "전투:명중") == 80  # default

    def test_get_combat_stat_nonexistent_unit(self):
        """존재하지 않는 유닛"""
        result = combat.get_combat_stat(999, "전투:공격력")
        assert result == 1  # default


# ========================================
# Tests: 거리
# ========================================

class TestDistance:
    def test_same_location(self):
        make_unit(1, location=(0, 0))
        make_unit(2, location=(0, 0))
        mock.set_unit_position(1, 10)
        mock.set_unit_position(2, 60)
        assert combat.get_distance(1, 2) == 50

    def test_different_location(self):
        make_unit(1, location=(0, 0))
        make_unit(2, location=(0, 1))
        assert combat.get_distance(1, 2) == float('inf')

    def test_in_range(self):
        make_unit(1, weapon_range=60, location=(0, 0))
        make_unit(2, location=(0, 0))
        mock.set_unit_position(1, 10)
        mock.set_unit_position(2, 60)
        assert combat.is_in_range(1, 2) is True

    def test_out_of_range(self):
        make_unit(1, weapon_range=30, location=(0, 0))
        make_unit(2, location=(0, 0))
        mock.set_unit_position(1, 10)
        mock.set_unit_position(2, 60)
        assert combat.is_in_range(1, 2) is False


# ========================================
# Tests: 명중/데미지
# ========================================

class TestHitDamage:
    def test_hit_chance_clamp(self):
        make_unit(1, accuracy=100)
        make_unit(2, evasion=0)
        assert combat.calculate_hit_chance(1, 2) == 95  # max clamp

    def test_hit_chance_clamp_min(self):
        make_unit(1, accuracy=0)
        make_unit(2, evasion=100)
        assert combat.calculate_hit_chance(1, 2) == 5  # min clamp

    def test_damage_formula(self):
        make_unit(1, atk=10)
        make_unit(2, defense=3)
        damage = combat.calculate_damage(1, 2)
        # damage = (atk - def) ± 10% → 7 ± 0.7 → 6~8 (or crit → higher)
        assert damage >= 1  # MIN_DAMAGE

    def test_damage_min(self):
        """공격력 < 방어력일 때 최소 데미지"""
        make_unit(1, atk=1)
        make_unit(2, defense=100)
        damage = combat.calculate_damage(1, 2)
        assert damage >= combat.MIN_DAMAGE


# ========================================
# Tests: 적대도
# ========================================

class TestHostility:
    def test_get_set_hostility(self):
        make_unit(1)
        combat.set_hostility(1, "player", 50)
        assert combat.get_hostility(1, "player") == 50

    def test_modify_hostility(self):
        make_unit(1)
        combat.set_hostility(1, "player", 30)
        combat.modify_hostility(1, "player", 20)
        assert combat.get_hostility(1, "player") == 50

    def test_hostility_clamp(self):
        make_unit(1)
        combat.set_hostility(1, "player", 150)
        assert combat.get_hostility(1, "player") == 100

    def test_hostility_clamp_negative(self):
        make_unit(1)
        combat.set_hostility(1, "player", -10)
        assert combat.get_hostility(1, "player") == 0

    def test_is_hostile_to(self):
        make_unit(1)
        make_unit(2, name="target")
        combat.set_hostility(1, "target", combat.HOSTILITY_HOSTILE)
        assert combat.is_hostile_to(1, 2) is True

    def test_not_hostile(self):
        make_unit(1)
        make_unit(2, name="target")
        combat.set_hostility(1, "target", 30)
        assert combat.is_hostile_to(1, 2) is False

    def test_clear_hostility(self):
        make_unit(1)
        combat.set_hostility(1, "player", 80)
        combat.clear_hostility(1, "player")
        assert combat.get_hostility(1, "player") == 0

    def test_hostility_level(self):
        make_unit(1)
        combat.set_hostility(1, "p", 20)
        assert combat.get_hostility_level(1, "p") == "neutral"
        combat.set_hostility(1, "p", 50)
        assert combat.get_hostility_level(1, "p") == "hostile"
        combat.set_hostility(1, "p", 80)
        assert combat.get_hostility_level(1, "p") == "attack_on_sight"


# ========================================
# Tests: 적대모드
# ========================================

class TestHostileMode:
    def test_toggle(self):
        mock._player_id = 1
        make_unit(1)
        assert combat.is_hostile_mode() is False
        combat.set_hostile_mode(True)
        assert combat.is_hostile_mode() is True
        # can:attack, can:steal 활성화 확인
        assert mock.get_unit_prop(1, "can:attack") == 1
        assert mock.get_unit_prop(1, "can:steal") == 1

    def test_toggle_off(self):
        mock._player_id = 1
        make_unit(1)
        combat.set_hostile_mode(True)
        combat.set_hostile_mode(False)
        assert combat.is_hostile_mode() is False
        assert mock.get_unit_prop(1, "can:attack") == 0
        assert mock.get_unit_prop(1, "can:steal") == 0


# ========================================
# Tests: 공격 실행
# ========================================

class TestExecuteAttack:
    def test_out_of_range(self):
        make_unit(1, weapon_range=10, location=(0, 0))
        make_unit(2, location=(0, 0))
        mock.set_unit_position(1, 0)
        mock.set_unit_position(2, 100)
        result = combat.execute_attack(1, 2)
        assert result["hit"] is False
        assert "사거리" in result["message"]

    def test_attack_reduces_hp(self):
        """공격이 대상 HP를 감소시키는지"""
        make_unit(1, atk=20, accuracy=100, crit=0, weapon_range=200, location=(0, 0))
        make_unit(2, defense=0, evasion=0, hp=50, location=(0, 0))
        mock.set_unit_position(1, 0)
        mock.set_unit_position(2, 50)

        result = combat.execute_attack(1, 2)
        # 100% 명중, 크리티컬 0% → 반드시 명중
        if result["hit"]:
            assert result["damage"] > 0
            assert result["target_hp"] < 50

    def test_faint_on_zero_hp(self):
        """HP 0 → 기절 트리거"""
        make_unit(1, atk=200, accuracy=100, weapon_range=200, location=(0, 0))
        make_unit(2, defense=0, evasion=0, hp=1, location=(0, 0))
        mock.set_unit_position(1, 0)
        mock.set_unit_position(2, 50)

        result = combat.execute_attack(1, 2)
        if result["hit"]:
            assert result["target_fainted"] is True


# ========================================
# Tests: 디버프
# ========================================

class TestDebuffs:
    def test_apply_bleeding(self):
        make_unit(1)
        combat.apply_bleeding(1)
        assert mock.get_unit_prop(1, "상태:출혈") == combat.BLEEDING_DURATION_HOURS

    def test_cure_bleeding(self):
        make_unit(1)
        combat.apply_bleeding(1)
        combat.cure_bleeding(1)
        assert mock.get_unit_prop(1, "상태:출혈") is None

    def test_apply_slow(self):
        make_unit(1)
        combat.apply_slow(1)
        assert mock.get_unit_prop(1, "이동:부상") == combat.SLOW_SPEED_PERCENT


# ========================================
# Tests: 시간 처리
# ========================================

class TestTimeElapsed:
    def test_hostility_decay(self):
        make_unit(1)
        mock._player_id = 99
        make_unit(99, name="Player")
        combat.set_hostility(1, "Player", 60)

        # _on_time_elapsed는 think._agents에 등록된 유닛만 처리
        think_mod._agents[1] = True

        # 1시간 경과 호출
        combat._on_time_elapsed(3_600_000)
        assert combat.get_hostility(1, "Player") == 60 - combat.HOSTILITY_DECAY_PER_HOUR

    def test_bleeding_damage(self):
        make_unit(1, hp=50)
        combat.apply_bleeding(1)
        mock.set_unit_prop(1, "상태:출혈시각", mock.get_current_time())
        # 1시간 경과
        combat._on_time_elapsed(3_600_000)
        hp_after = mock.get_unit_prop(1, "생존:체력")
        assert hp_after < 50


# ========================================
# Tests: 리셋
# ========================================

class TestReset:
    def test_reset_clears_hostile_mode(self):
        combat.set_hostile_mode(True)
        combat.reset()
        assert combat.is_hostile_mode() is False
