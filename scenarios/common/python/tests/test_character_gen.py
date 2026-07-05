# test_character_gen.py — 랜덤 캐릭터 생성 프레임워크 계약

from engine import character_gen as cg


_SPEC = {
    "roles": {
        "assault": {
            "base_props": {"vita": 6, "sapientia": 3},
            "archetypes": [("fierce", 80), ("proud", 20)],
        },
        "plain": {
            "base_props": {"vita": 5},
            "archetypes": ["stoic"],
        },
    },
    "tiers": {
        "standard": {"variance": {"vita": (-1, 1)}},
        "prototype": {
            "prop_bonus": {"vita": 2},
            "variance": {"vita": (-2, 2)},
            "archetype_extra": [("cold", 100000)],  # 사실상 cold 확정
        },
    },
}


class TestWeightedChoice:
    def test_uniform_pool(self):
        rng = cg.make_rng(1)
        for _ in range(20):
            assert cg.weighted_choice(["a", "b"], rng) in ("a", "b")

    def test_weighted_pool(self):
        rng = cg.make_rng(2)
        picks = {cg.weighted_choice([("x", 1), ("y", 0)], rng) for _ in range(20)}
        assert picks == {"x"}

    def test_empty_pool(self):
        assert cg.weighted_choice([], cg.make_rng(0)) is None


class TestSampleDistinct:
    def test_distinct_count(self):
        rng = cg.make_rng(5)
        picks = cg.sample_distinct(["a", "b", "c", "d"], 2, rng)
        assert len(picks) == 2
        assert len(set(picks)) == 2

    def test_avoid_excluded(self):
        rng = cg.make_rng(5)
        for _ in range(20):
            picks = cg.sample_distinct(["a", "b", "c"], 1, rng, avoid={"a", "b"})
            assert picks == ["c"]

    def test_pool_exhaustion_returns_available(self):
        rng = cg.make_rng(5)
        picks = cg.sample_distinct(["a", "b"], 5, rng)
        assert sorted(picks) == ["a", "b"]  # count 초과 → 있는 만큼

    def test_all_avoided_returns_empty(self):
        picks = cg.sample_distinct(["a", "b"], 1, cg.make_rng(0), avoid={"a", "b"})
        assert picks == []

    def test_reproducible(self):
        a = cg.sample_distinct(list("abcdef"), 3, cg.make_rng(9))
        b = cg.sample_distinct(list("abcdef"), 3, cg.make_rng(9))
        assert a == b


class TestRollIdentity:
    def test_props_within_bounds(self):
        rng = cg.make_rng(3)
        for _ in range(50):
            identity = cg.roll_identity(_SPEC, "assault", "standard", rng)
            assert 5 <= identity["props"]["vita"] <= 7  # 6 ± 1
            assert identity["props"]["sapientia"] == 3   # variance 없는 prop 유지
            assert identity["archetype"] in ("fierce", "proud")

    def test_tier_bonus_and_extra_pool(self):
        rng = cg.make_rng(4)
        identity = cg.roll_identity(_SPEC, "plain", "prototype", rng)
        # 5 + variance(-2..2) + bonus(2) = 5..9
        assert 5 <= identity["props"]["vita"] <= 9
        assert identity["archetype"] == "cold"  # 압도적 가중치의 티어 추가 후보

    def test_reproducible_with_seed(self):
        a = cg.roll_identity(_SPEC, "assault", "standard", cg.make_rng(42))
        b = cg.roll_identity(_SPEC, "assault", "standard", cg.make_rng(42))
        assert a == b

    def test_unknown_role_tier_graceful(self):
        identity = cg.roll_identity(_SPEC, "ghost", "none", cg.make_rng(0))
        assert identity["props"] == {}
        assert identity["archetype"] is None

    def test_make_rng_isolated(self):
        """전역 random 상태와 독립 — 같은 시드는 항상 같은 열"""
        import random
        random.seed(999)
        first = cg.make_rng(7).randint(0, 10 ** 9)
        random.seed(123)
        second = cg.make_rng(7).randint(0, 10 ** 9)
        assert first == second
