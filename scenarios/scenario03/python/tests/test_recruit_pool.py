"""recruit_pool 테스트 — 티어 로트/제조 편차/재현성/대화 연동"""
import morld


class _T:
    def __init__(self):
        morld.reset()
        import squad, cycle
        squad.reset()
        cycle.reset()
        from think import clear_all
        clear_all()


class TestTierLot:
    def test_tier_for_cycle(self):
        import recruit_pool as rp
        assert rp.tier_for_cycle(0) == rp.TIER_STANDARD
        assert rp.tier_for_cycle(2) == rp.TIER_STANDARD
        assert rp.tier_for_cycle(3) == rp.TIER_IMPROVED
        assert rp.tier_for_cycle(4) == rp.TIER_IMPROVED
        assert rp.tier_for_cycle(5) == rp.TIER_PROTOTYPE
        assert rp.tier_for_cycle(9) == rp.TIER_PROTOTYPE

    def test_prototype_humanity_penalty(self):
        import recruit_pool as rp
        spec = rp.generate_member("assault", serial=9, cycle=6)
        assert spec["tier"] == rp.TIER_PROTOTYPE
        assert spec["humanity_mod"] == -20
        # standard 로트는 페널티 없음
        spec0 = rp.generate_member("assault", serial=9, cycle=1)
        assert spec0["humanity_mod"] == 0


class TestManufactureVariance:
    def test_stats_within_bounds(self):
        import recruit_pool as rp
        from engine import character_gen as cg
        rng = cg.make_rng(7)
        for _ in range(50):
            spec = rp.generate_member("sniper", serial=5, cycle=1, rng=rng)
            # sniper 기준 vita 4 ± 1 (standard variance), 클램프 1~10
            assert 3 <= spec["stat_overrides"]["vita"] <= 5
            assert 4 <= spec["stat_overrides"]["sapientia"] <= 6

    def test_archetype_from_role_pool(self):
        import recruit_pool as rp
        from engine import character_gen as cg
        rng = cg.make_rng(11)
        allowed = {"gentle", "timid", "devoted"}
        for _ in range(30):
            spec = rp.generate_member("medic", serial=4, cycle=1, rng=rng)
            assert spec["archetype"] in allowed, spec["archetype"]

    def test_reproducible_seed(self):
        """같은 (cycle, serial) → 항상 같은 개체 (세이브/재실행 재현성)"""
        import recruit_pool as rp
        a = rp.generate_member("assault", serial=7, cycle=3)
        b = rp.generate_member("assault", serial=7, cycle=3)
        assert a == b
        c = rp.generate_member("assault", serial=8, cycle=3)
        assert a != c  # 다른 시리얼은 다른 개체 (같을 확률 극히 낮은 조합)


class TestConfigureIntegration(_T):
    def test_configure_sets_archetype_prop(self):
        from assets.characters.squad_member import SquadMember, base_hp_for_vita
        npc = SquadMember()
        npc.configure("echo_10", "Echo-10", "assault",
                      archetype="proud", stat_overrides={"vita": 8})
        assert npc.props["아키타입"] == "proud"
        assert npc.props["vita"] == 8
        # 체력은 오버라이드된 vita 기준으로 재계산
        assert npc.props["생존:체력max"] == base_hp_for_vita(8)

    def test_configure_without_archetype_backcompat(self):
        """기존 호출 (archetype 미지정) — prop 없음, 역할 매핑 폴백 대상"""
        from assets.characters.squad_member import SquadMember
        npc = SquadMember()
        npc.configure("echo_11", "Echo-11", "sniper")
        assert "아키타입" not in npc.props

    def test_member_archetype_prop_first(self):
        import npc_dialogue
        from assets.characters.squad_member import SquadMember
        npc = SquadMember()
        npc.configure("echo_12", "Echo-12", "sniper", archetype="proud")
        uid = morld.create_id("unit")
        npc.instantiate(uid, 0, 0)
        assert npc_dialogue.member_archetype(uid) == "proud"

    def test_member_archetype_role_fallback(self):
        import npc_dialogue
        from assets.characters.squad_member import SquadMember
        npc = SquadMember()
        npc.configure("echo_13", "Echo-13", "sniper")  # 아키타입 미지정
        uid = morld.create_id("unit")
        npc.instantiate(uid, 0, 0)
        assert npc_dialogue.member_archetype(uid) == "stoic"  # 저격 고정 매핑


class TestSpawnReplacementLot(_T):
    def test_replacement_carries_lot_identity(self):
        import cycle
        cycle.start_operations()
        rec = cycle._spawn_replacement("assault")
        assert rec["tier"] == "standard"  # cycle 1 → 규격품
        assert rec["archetype"]
        assert morld.get_unit_prop(rec["unit_id"], "아키타입") == rec["archetype"]
        assert morld.get_unit_prop(rec["unit_id"], "인간성") >= 10

    def test_prototype_lot_at_late_cycle(self):
        import cycle
        cycle.start_operations()
        cycle._ops["cycle"] = 6
        cycle._ops["role_deaths"]["medic"] = 3  # 결번 3회 → 기본 70
        rec = cycle._spawn_replacement("medic")
        assert rec["tier"] == "prototype"
        # 70 - 20(시제품) = 50
        assert rec["humanity"] == 50
        assert morld.get_unit_prop(rec["unit_id"], "인간성") == 50
