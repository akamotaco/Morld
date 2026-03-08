"""분대 시스템 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()

    def _make_unit(self, name="Agent", region=0, location=0):
        uid = morld.create_id("unit")
        morld.add_unit(uid, name, region, location, "male")
        return uid


class TestSquadLifecycle(_T):
    def setUp(self):
        import squad
        squad.reset()

    def test_create_squad(self):
        import squad
        sid = squad.create_squad()
        assert sid == 0
        assert squad.get_squad(sid) is not None

    def test_create_multiple_squads(self):
        import squad
        s0 = squad.create_squad()
        s1 = squad.create_squad()
        assert s0 != s1
        assert squad.get_squad(s0) is not None
        assert squad.get_squad(s1) is not None

    def test_disband_squad(self):
        import squad
        sid = squad.create_squad()
        squad.disband_squad(sid)
        assert squad.get_squad(sid) is None

    def test_disband_with_members(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        u2 = self._make_unit("B")
        squad.assign_leader(sid, u1)
        squad.add_member(sid, u2)
        squad.disband_squad(sid)
        assert not squad.is_in_squad(u1)
        assert not squad.is_in_squad(u2)


class TestSquadLeader(_T):
    def setUp(self):
        import squad
        squad.reset()

    def test_assign_leader(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("Leader")
        assert squad.assign_leader(sid, u1) is True
        assert squad.is_squad_leader(u1)

    def test_assign_leader_already_in_squad(self):
        import squad
        s1 = squad.create_squad()
        s2 = squad.create_squad()
        u1 = self._make_unit("A")
        squad.assign_leader(s1, u1)
        assert squad.assign_leader(s2, u1) is False

    def test_remove_leader(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.assign_leader(sid, u1)
        squad.remove_leader(sid)
        assert not squad.is_in_squad(u1)
        sq = squad.get_squad(sid)
        assert sq.leader_id is None

    def test_change_leader(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        u2 = self._make_unit("B")
        squad.assign_leader(sid, u1)
        squad.add_member(sid, u2)
        assert squad.change_leader(sid, u2) is True
        sq = squad.get_squad(sid)
        assert sq.leader_id == u2
        assert u1 in sq.members
        assert u2 not in sq.members


class TestSquadMembers(_T):
    def setUp(self):
        import squad
        squad.reset()

    def test_add_member(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        assert squad.add_member(sid, u1) is True
        assert squad.is_in_squad(u1)

    def test_add_member_full(self):
        import squad
        sid = squad.create_squad()
        members = [self._make_unit(f"M{i}") for i in range(3)]
        for m in members:
            squad.add_member(sid, m)
        extra = self._make_unit("Extra")
        assert squad.add_member(sid, extra) is False

    def test_add_member_already_same_squad(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        assert squad.add_member(sid, u1) is False

    def test_add_member_transfers_from_other(self):
        import squad
        s1 = squad.create_squad()
        s2 = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(s1, u1)
        assert squad.add_member(s2, u1) is True
        assert u1 not in squad.get_squad(s1).members
        assert u1 in squad.get_squad(s2).members

    def test_remove_member(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        assert squad.remove_member(sid, u1) is True
        assert not squad.is_in_squad(u1)

    def test_all_unit_ids(self):
        import squad
        sid = squad.create_squad()
        leader = self._make_unit("L")
        m1 = self._make_unit("M1")
        m2 = self._make_unit("M2")
        squad.assign_leader(sid, leader)
        squad.add_member(sid, m1)
        squad.add_member(sid, m2)
        ids = squad.get_all_unit_ids(sid)
        assert len(ids) == 3
        assert ids[0] == leader


class TestSquadAggression(_T):
    def setUp(self):
        import squad
        squad.reset()

    def test_default_aggression(self):
        import squad
        sid = squad.create_squad()
        assert squad.get_aggression(sid) == "hold"

    def test_set_aggression(self):
        import squad
        sid = squad.create_squad()
        assert squad.set_aggression(sid, "combat_aggressive") is True
        assert squad.get_aggression(sid) == "combat_aggressive"

    def test_set_invalid_aggression(self):
        import squad
        sid = squad.create_squad()
        assert squad.set_aggression(sid, "invalid") is False
        assert squad.get_aggression(sid) == "hold"

    def test_aggression_value(self):
        import squad
        sid = squad.create_squad()
        squad.set_aggression(sid, "retreat")
        assert squad.get_aggression_value(sid) == -2
        squad.set_aggression(sid, "combat_aggressive")
        assert squad.get_aggression_value(sid) == 2


class TestSquadRank(_T):
    def setUp(self):
        import squad
        squad.reset()

    def test_default_rank(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        assert squad.get_member_rank(sid, u1) == 2

    def test_set_rank(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        assert squad.set_member_rank(sid, u1, 1) is True
        assert squad.get_member_rank(sid, u1) == 1

    def test_set_rank_invalid(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        assert squad.set_member_rank(sid, u1, 4) is False
        assert squad.get_member_rank(sid, u1) == 2

    def test_leader_rank(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.assign_leader(sid, u1)
        assert squad.set_member_rank(sid, u1, 1) is True
        assert squad.get_member_rank(sid, u1) == 1


class TestSquadOrder(_T):
    def setUp(self):
        import squad
        squad.reset()

    def test_set_order(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        order = squad.Order("search", priority=0.5)
        assert squad.set_order(sid, u1, order) is True
        assert squad.get_order(sid, u1) is order

    def test_set_order_non_member(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        order = squad.Order("search")
        assert squad.set_order(sid, u1, order) is False

    def test_clear_order(self):
        import squad
        sid = squad.create_squad()
        u1 = self._make_unit("A")
        squad.add_member(sid, u1)
        squad.set_order(sid, u1, squad.Order("guard"))
        squad.clear_order(sid, u1)
        assert squad.get_order(sid, u1) is None

    def test_order_main_type(self):
        import squad
        order = squad.Order("follow:close")
        assert order.main_type() == "follow"
