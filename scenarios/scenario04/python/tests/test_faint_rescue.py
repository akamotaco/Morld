# test_faint_rescue.py — 실신 사이클 단위 테스트
#
# 검증:
#   - 자력 탈출 확률 (저층 전용)
#   - 지나가는 NPC 확률 (평판 + 시간)
#   - 침식 가속 (층수별)
#   - 사망 판정 (침식 200)

import io
import os
import random
import sys
import traceback


if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
_common_dir = os.path.abspath(os.path.join(_tests_dir, "..", "..", "..", "common", "python"))
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _common_dir not in sys.path:
    sys.path.append(_common_dir)


# ============================================
# Mocks
# ============================================

class _MockMorld:
    def __init__(self):
        self.props = {}
        self.player_id = 1
        self.time = 0
        self.time_advances = []

    def get_player_id(self): return self.player_id
    def get_unit_prop(self, uid, key):  # 실 계약: 부재 시 0
        return self.props.setdefault(uid, {}).get(key, 0)
    def set_unit_prop(self, uid, key, val):
        self.props.setdefault(uid, {})[key] = val
    def get_unit_location(self, uid):
        return self.props.setdefault(uid, {}).get("_loc")
    def get_unit_name(self, uid):
        return self.props.setdefault(uid, {}).get("_name", f"U{uid}")
    def advance_time_des(self, millis):
        self.time_advances.append(millis)
        self.time += millis


mock = _MockMorld()
sys.modules["morld"] = mock

# ui stub
_ui_stub = type(sys)("ui")
_ui_stub.dialog = lambda s: ("dialog", s)
sys.modules["ui"] = _ui_stub

# linear_dungeon stub — is_active=False로 floor_idx=0
_ld_stub = type(sys)("linear_dungeon")
_ld_stub.is_active = lambda: False
_ld_stub.get_floor_info = lambda: (1, 1)
_ld_stub.exit_to_village = lambda reason: mock.time_advances.append(("exit", reason))
sys.modules["linear_dungeon"] = _ld_stub

# reputation stub
_rep_stub = type(sys)("reputation")
_rep_stub._vals = {"모험가길드": 0, "마을주민": 0}
_rep_stub.get_reputation = lambda k: _rep_stub._vals.get(k, 0)
sys.modules["reputation"] = _rep_stub

# survival stub
_sv_stub = type(sys)("survival")
_sv_stub._hp = {}
_sv_stub.set_health = lambda uid, hp: _sv_stub._hp.__setitem__(uid, hp)
_sv_stub.get_health = lambda uid: _sv_stub._hp.get(uid, 0)
_sv_stub.get_max_health = lambda uid: 100
sys.modules["survival"] = _sv_stub

# erosion stub
_er_stub = type(sys)("erosion")
_er_stub._vals = {}
_er_stub.EROSION_MAX = 200
_er_stub.get_erosion = lambda uid: _er_stub._vals.get(uid, 0)
_er_stub.set_erosion = lambda uid, v: _er_stub._vals.__setitem__(uid, max(0, min(200, v)))
_er_stub.add_erosion = lambda uid, amt: _er_stub._vals.__setitem__(
    uid, max(0, min(200, _er_stub._vals.get(uid, 0) + int(amt))))
sys.modules["erosion"] = _er_stub

# engine.korean stub
_kr_stub = type(sys)("engine.korean")
_kr_stub.이_가 = lambda name: "이"
sys.modules["engine.korean"] = _kr_stub

# engine.party_group stub (빈 파티)
_pg_stub = type(sys)("engine.party_group")
_pg_stub.get_party_of = lambda uid: None
sys.modules["engine.party_group"] = _pg_stub

# engine.fsm_dungeon stub — _should_rescue True로 통제
_fd_stub = type(sys)("engine.fsm_dungeon")
_fd_stub._should_rescue = lambda uid: True
sys.modules["engine.fsm_dungeon"] = _fd_stub

# facility stub — 기본 구호소 없음
_fc_stub = type(sys)("facility")
_fc_stub._has_infirmary = False
_fc_stub.has_infirmary = lambda: _fc_stub._has_infirmary
sys.modules["facility"] = _fc_stub

import faint_rescue


# ============================================
# Tests
# ============================================

def _reset():
    mock.props.clear()
    mock.time = 0
    mock.time_advances.clear()
    _sv_stub._hp.clear()
    _er_stub._vals.clear()
    _rep_stub._vals = {"모험가길드": 0, "마을주민": 0}


class TestSelfRescueProb:

    def test_floor_0_has_chance(self):
        _reset()
        # 기본 5% — 100회 중 몇 번은 성공해야 함
        random.seed(0)
        successes = sum(faint_rescue._try_self_rescue(0) for _ in range(1000))
        # 기대치 50회, 편차 고려 20~80 범위
        assert 20 < successes < 100, f"floor0 self-rescue: {successes}"

    def test_floor_3_zero(self):
        """3층: 5 - 3*2 = -1 → 0%"""
        _reset()
        random.seed(0)
        successes = sum(faint_rescue._try_self_rescue(3) for _ in range(500))
        assert successes == 0

    def test_floor_4_zero(self):
        _reset()
        random.seed(0)
        successes = sum(faint_rescue._try_self_rescue(4) for _ in range(500))
        assert successes == 0


class TestPasserbyProb:

    def test_zero_rep_zero_time(self):
        """rep=0 → bonus=15%, time=0, floor=0 → 15%"""
        _reset()
        random.seed(0)
        successes = sum(faint_rescue._try_passerby_rescue(0, 0) for _ in range(1000))
        # 기대치 150, 범위 넓게
        assert 100 < successes < 200, successes

    def test_high_rep_boosts(self):
        _reset()
        _rep_stub._vals = {"모험가길드": 100, "마을주민": 100}
        random.seed(0)
        successes = sum(faint_rescue._try_passerby_rescue(0, 0) for _ in range(1000))
        # rep_avg=100 → (100+100)*0.15 = 30%
        assert 200 < successes < 400, successes

    def test_deep_floor_penalty(self):
        """rep=0, time=0, floor=5 → 15 - 15 = 0%"""
        _reset()
        random.seed(0)
        successes = sum(faint_rescue._try_passerby_rescue(0, 5) for _ in range(500))
        assert successes == 0

    def test_time_bonus_accumulates(self):
        """rep=0, floor=0, time=10h → 15 + 20 = 35%"""
        _reset()
        random.seed(0)
        successes = sum(faint_rescue._try_passerby_rescue(10, 0) for _ in range(1000))
        assert 250 < successes < 450, successes


class TestErosionTick:

    def test_floor_0_tick(self):
        _reset()
        faint_rescue._add_erosion_tick(1, 0)
        assert _er_stub._vals[1] == 5  # base

    def test_floor_3_tick(self):
        _reset()
        faint_rescue._add_erosion_tick(1, 3)
        assert _er_stub._vals[1] == 5 + 3 * 2  # 11

    def test_death_threshold(self):
        _reset()
        _er_stub._vals[1] = 195
        faint_rescue._add_erosion_tick(1, 0)  # +5 = 200
        assert faint_rescue._is_eroded_to_death(1)

    def test_not_yet_death(self):
        _reset()
        _er_stub._vals[1] = 190
        faint_rescue._add_erosion_tick(1, 0)  # +5 = 195
        assert not faint_rescue._is_eroded_to_death(1)


class TestReputationAvg:

    def test_default_zero(self):
        _reset()
        assert faint_rescue._get_public_reputation_avg() == 0

    def test_average(self):
        _reset()
        _rep_stub._vals = {"모험가길드": 80, "마을주민": 20}
        assert faint_rescue._get_public_reputation_avg() == 50


class TestRecoveryAndDeath:

    def test_recover_minimal_sets_hp_and_clears_faint(self):
        _reset()
        mock.props[1] = {"상태:실신": 1}
        faint_rescue._recover_minimal()
        assert _sv_stub._hp[1] == 10
        assert mock.props[1].get("상태:실신") == 0

    def test_reorganization_resets_erosion(self):
        _reset()
        _er_stub._vals[1] = 200
        mock.props[1] = {"상태:실신": 1}
        faint_rescue._trigger_reorganization()
        assert _er_stub._vals[1] == 0
        assert _sv_stub._hp[1] == 10
        assert mock.props[1].get("상태:실신") == 0


class TestDeathEvent:
    """재편성 이벤트 — 다이얼로그 흐름 + 상태 전환"""

    def _consume_gen(self, gen):
        dialogs = []
        for item in gen:
            if isinstance(item, tuple) and item and item[0] == "dialog":
                dialogs.append(item[1])
        return dialogs

    def test_death_event_no_infirmary_variant(self):
        _reset()
        _er_stub._vals[1] = 200
        mock.props[1] = {"상태:실신": 1}
        _fc_stub._has_infirmary = False

        dialogs = self._consume_gen(faint_rescue._handle_death())

        # 최소 4개 다이얼로그 (침식/암전/기상/재출발)
        assert len(dialogs) >= 4, f"expected >=4 dialogs, got {len(dialogs)}"
        # 구호소 없는 분기 확인
        wake_dialogs = [d for d in dialogs if "던전 입구의 차가운 바람" in d]
        assert len(wake_dialogs) == 1
        # 상태 리셋 완료
        assert _er_stub._vals[1] == 0
        assert _sv_stub._hp[1] == 10
        assert mock.props[1].get("상태:실신") == 0

    def test_death_event_with_infirmary_variant(self):
        _reset()
        _er_stub._vals[1] = 200
        mock.props[1] = {"상태:실신": 1}
        _fc_stub._has_infirmary = True

        dialogs = self._consume_gen(faint_rescue._handle_death())

        wake_dialogs = [d for d in dialogs if "구호소의 천장" in d]
        assert len(wake_dialogs) == 1


# ============================================
# 러너
# ============================================

def _run():
    test_classes = [TestSelfRescueProb, TestPasserbyProb,
                    TestErosionTick, TestReputationAvg, TestRecoveryAndDeath,
                    TestDeathEvent]
    passed = failed = errors = 0
    for cls in test_classes:
        for name in sorted(dir(cls)):
            if not name.startswith("test_"):
                continue
            instance = cls()
            method = getattr(instance, name)
            full = f"{cls.__name__}.{name}"
            try:
                method()
                print(f"  PASS  {full}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {full}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ERROR {full}: {e}")
                traceback.print_exc()
                errors += 1
    total = passed + failed + errors
    print("=" * 50)
    print(f"TOTAL: {passed}/{total} passed ({failed} failed, {errors} errors)")
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    sys.exit(_run())
