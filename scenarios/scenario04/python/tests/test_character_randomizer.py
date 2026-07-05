# test_character_randomizer.py — S04 랜덤 생성 (engine.character_gen 이관 회귀)
#
# 검증: roll_* 가 엔진 프리미티브 위에서 동작하고, rng 주입 시 결정적 재현.
# 실행: python scenarios/scenario04/python/tests/test_character_randomizer.py

import io
import os
import sys
import types
import traceback

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
_common_dir = os.path.abspath(os.path.join(
    _tests_dir, "..", "..", "..", "common", "python"))
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _common_dir not in sys.path:
    sys.path.append(_common_dir)


# ── mock morld + tags stub (randomizer import 전에 주입) ──
class _MockMorld:
    def __init__(self):
        self.props = {}

    def set_unit_prop(self, uid, key, val):
        self.props.setdefault(uid, {})[key] = val

    def get_unit_prop(self, uid, key):
        return self.props.setdefault(uid, {}).get(key, 0)


_mock = _MockMorld()
sys.modules["morld"] = _mock

_tags_stub = types.ModuleType("tags")
_tags_stub._calls = []
_tags_stub.add_self_tags = lambda uid, *tags: _tags_stub._calls.append((uid, tags))
sys.modules["tags"] = _tags_stub

import character_randomizer as randomizer
from engine import character_gen as cg


class TestRollFunctions:
    def test_stats_within_range(self):
        rng = cg.make_rng(1)
        for _ in range(50):
            s = randomizer.roll_stats(8, 15, rng=rng)
            for k in ("str", "agi", "vit", "mnd"):
                assert 8 <= s[k] <= 15, s

    def test_leadership_in_domain(self):
        rng = cg.make_rng(2)
        for _ in range(50):
            assert randomizer.roll_leadership(rng) in (0, 1, 2)

    def test_personality_from_pool(self):
        rng = cg.make_rng(3)
        for _ in range(30):
            assert randomizer.roll_personality(rng) in randomizer.PERSONALITY_POOL

    def test_class_from_pool(self):
        rng = cg.make_rng(4)
        allowed = set(randomizer.CLASS_POOL) | set(randomizer.CLASS_RARE)
        for _ in range(30):
            assert randomizer.roll_class(rng=rng) in allowed

    def test_name_avoids_duplicates(self):
        rng = cg.make_rng(5)
        avoid = set(randomizer.NAME_POOL_MALE[:-1])  # 하나만 남김
        name = randomizer.roll_name(True, avoid=avoid, rng=rng)
        assert name == randomizer.NAME_POOL_MALE[-1]

    def test_name_pool_exhausted_fallback(self):
        rng = cg.make_rng(6)
        avoid = set(randomizer.NAME_POOL_FEMALE)  # 전부 회피 → 폴백
        name = randomizer.roll_name(False, avoid=avoid, rng=rng)
        assert name in randomizer.NAME_POOL_FEMALE  # 폴백은 전체 풀에서

    def test_quirks_distinct(self):
        rng = cg.make_rng(7)
        for _ in range(30):
            q = randomizer.roll_quirks(rng=rng)
            assert len(q) == len(set(q)), q
            assert len(q) <= 2


class TestReproducibility:
    def test_same_seed_same_character(self):
        _mock.props.clear()
        randomizer.apply_random_character(1, rng=cg.make_rng(42))
        first = dict(_mock.props[1])
        _mock.props.clear()
        randomizer.apply_random_character(1, rng=cg.make_rng(42))
        assert _mock.props[1] == first

    def test_different_seed_differs(self):
        _mock.props.clear()
        randomizer.apply_random_character(1, rng=cg.make_rng(1))
        a = dict(_mock.props[1])
        _mock.props.clear()
        randomizer.apply_random_character(1, rng=cg.make_rng(2))
        assert _mock.props[1] != a


class TestApplyProps:
    def test_props_set(self):
        _mock.props.clear()
        _tags_stub._calls.clear()
        applied = randomizer.apply_random_character(
            7, is_male=True, assign_class=True, rng=cg.make_rng(3))
        p = _mock.props[7]
        assert p["성별"] == "남"
        assert p["성격"] in randomizer.PERSONALITY_POOL
        assert 1 <= p["동정심"] <= 10
        assert "클래스" in p
        assert applied["name"]
        # 태그 동기화 호출됨
        assert _tags_stub._calls and _tags_stub._calls[-1][0] == 7

    def test_player_no_class(self):
        _mock.props.clear()
        randomizer.apply_random_character(
            9, assign_class=False, assign_quirks=False, rng=cg.make_rng(3))
        assert "클래스" not in _mock.props[9]


def _run():
    classes = [TestRollFunctions, TestReproducibility, TestApplyProps]
    passed = failed = 0
    for cls in classes:
        for name in sorted(dir(cls)):
            if not name.startswith("test_"):
                continue
            try:
                getattr(cls(), name)()
                passed += 1
                print(f"  PASS  {cls.__name__}.{name}")
            except Exception:
                failed += 1
                print(f"  FAIL  {cls.__name__}.{name}")
                traceback.print_exc()
    total = passed + failed
    print(f"\nTOTAL: {passed}/{total} passed ({failed} failed, 0 errors)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run())
