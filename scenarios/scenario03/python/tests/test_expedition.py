"""원정 라이프사이클 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()

    def _setup_squad(self):
        """테스트용 분대 생성 (리더1 + 멤버2)"""
        import squad
        squad.reset()
        sid = squad.create_squad()
        leader = morld.create_id("unit")
        morld.add_unit(leader, "Echo-01", 0, 0, "male")
        m1 = morld.create_id("unit")
        morld.add_unit(m1, "Echo-02", 0, 0, "male")
        m2 = morld.create_id("unit")
        morld.add_unit(m2, "Echo-03", 0, 0, "male")
        squad.assign_leader(sid, leader)
        squad.add_member(sid, m1)
        squad.add_member(sid, m2)
        return sid, leader, m1, m2


class TestPrepareExpedition(_T):
    def setUp(self):
        import expedition
        expedition.reset()
        import mapgen
        mapgen.reset()

    def test_prepare_success(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid, "easy")
        assert state is not None
        assert state.status == "preparing"
        assert state.squad_id == sid

    def test_prepare_no_leader(self):
        import squad
        import expedition
        squad.reset()
        sid = squad.create_squad()
        m1 = morld.create_id("unit")
        morld.add_unit(m1, "A", 0, 0, "male")
        squad.add_member(sid, m1)
        state = expedition.prepare_expedition(sid)
        assert state is None

    def test_prepare_no_members(self):
        import squad
        import expedition
        squad.reset()
        sid = squad.create_squad()
        leader = morld.create_id("unit")
        morld.add_unit(leader, "L", 0, 0, "male")
        squad.assign_leader(sid, leader)
        state = expedition.prepare_expedition(sid)
        assert state is None

    def test_prepare_already_on_expedition(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        expedition.prepare_expedition(sid)
        state2 = expedition.prepare_expedition(sid)
        assert state2 is None


class TestStartExpedition(_T):
    def setUp(self):
        import expedition
        expedition.reset()
        import mapgen
        mapgen.reset()

    def test_start_generates_map(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid, "easy")
        success, msg = expedition.start_expedition(state.expedition_id)
        assert success is True
        assert state.status == "active"
        assert len(state.rooms) >= 3

    def test_start_places_squad_at_entrance(self):
        import expedition
        import squad
        sid, leader, m1, m2 = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        expedition.start_expedition(state.expedition_id)

        for uid in [leader, m1, m2]:
            loc = morld.get_unit_location(uid)
            assert loc[0] == state.region_id
            assert loc[1] == 0  # entrance

    def test_start_marks_entrance_explored(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        expedition.start_expedition(state.expedition_id)
        assert 0 in state.explored_rooms

    def test_start_wrong_status(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        expedition.start_expedition(state.expedition_id)
        success, msg = expedition.start_expedition(state.expedition_id)
        assert success is False


class TestMoveToRoom(_T):
    def setUp(self):
        import expedition
        expedition.reset()
        import mapgen
        mapgen.reset()

    def _start_expedition(self):
        import expedition
        sid, leader, m1, m2 = self._setup_squad()
        state = expedition.prepare_expedition(sid, "easy")
        expedition.start_expedition(state.expedition_id)
        return state, sid, leader, m1, m2

    def test_move_to_connected(self):
        import expedition
        state, sid, leader, m1, m2 = self._start_expedition()
        # Find a connected room from entrance
        explorable = expedition.get_explorable_rooms(state.expedition_id)
        assert len(explorable) >= 1
        target = explorable[0]["id"]
        success, room, msg = expedition.move_to_room(
            state.expedition_id, target)
        assert success is True
        assert state.current_room == target

    def test_move_updates_location(self):
        import expedition
        state, sid, leader, m1, m2 = self._start_expedition()
        explorable = expedition.get_explorable_rooms(state.expedition_id)
        target = explorable[0]["id"]
        expedition.move_to_room(state.expedition_id, target)

        for uid in [leader, m1, m2]:
            loc = morld.get_unit_location(uid)
            assert loc[1] == target

    def test_move_to_disconnected_fails(self):
        import expedition
        state, _, _, _, _ = self._start_expedition()
        # Room 999 doesn't exist
        success, _, msg = expedition.move_to_room(
            state.expedition_id, 999)
        assert success is False

    def test_move_marks_explored(self):
        import expedition
        state, _, _, _, _ = self._start_expedition()
        explorable = expedition.get_explorable_rooms(state.expedition_id)
        target = explorable[0]["id"]
        expedition.move_to_room(state.expedition_id, target)
        assert target in state.explored_rooms


class TestRetreatExpedition(_T):
    def setUp(self):
        import expedition
        expedition.reset()
        import mapgen
        mapgen.reset()

    def test_retreat_returns_to_platform(self):
        import expedition
        sid, leader, m1, m2 = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        expedition.start_expedition(state.expedition_id)
        success, msg = expedition.retreat_expedition(state.expedition_id)
        assert success is True
        assert state.status == "completed"

        for uid in [leader, m1, m2]:
            loc = morld.get_unit_location(uid)
            assert loc == (0, 0)

    def test_retreat_from_non_active_fails(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        success, msg = expedition.retreat_expedition(state.expedition_id)
        assert success is False


class TestCompleteExpedition(_T):
    def setUp(self):
        import expedition
        expedition.reset()
        import mapgen
        mapgen.reset()

    def test_complete_returns_summary(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        expedition.start_expedition(state.expedition_id)
        expedition.retreat_expedition(state.expedition_id)
        summary = expedition.complete_expedition(state.expedition_id)
        assert summary is not None
        assert summary["rooms_explored"] >= 1

    def test_complete_cleans_registry(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        eid = state.expedition_id
        expedition.start_expedition(eid)
        expedition.retreat_expedition(eid)
        expedition.complete_expedition(eid)
        assert expedition.get_expedition(eid) is None
        assert expedition.get_expedition_by_squad(sid) is None


class TestExpeditionQuery(_T):
    def setUp(self):
        import expedition
        expedition.reset()
        import mapgen
        mapgen.reset()

    def test_get_by_squad(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        found = expedition.get_expedition_by_squad(sid)
        assert found is state

    def test_get_active_expeditions(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        assert len(expedition.get_active_expeditions()) == 0
        expedition.start_expedition(state.expedition_id)
        assert len(expedition.get_active_expeditions()) == 1

    def test_get_explorable_rooms(self):
        import expedition
        sid, _, _, _ = self._setup_squad()
        state = expedition.prepare_expedition(sid)
        expedition.start_expedition(state.expedition_id)
        rooms = expedition.get_explorable_rooms(state.expedition_id)
        assert isinstance(rooms, list)
        for r in rooms:
            assert "id" in r
            assert "explored" in r
