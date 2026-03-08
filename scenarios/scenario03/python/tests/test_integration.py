"""통합 테스트 — 원정 전체 흐름"""
import morld


class _T:
    def __init__(self):
        morld.reset()


class TestFullExpeditionFlow(_T):
    def setUp(self):
        import squad
        import expedition
        import mapgen
        squad.reset()
        expedition.reset()
        mapgen.reset()

    def _setup_squad_with_hp(self):
        """분대 생성 + HP/vita 설정"""
        import squad
        sid = squad.create_squad()
        units = []
        for i, (name, role) in enumerate([
            ("Echo-01", "assault"),
            ("Echo-02", "support"),
            ("Echo-03", "sniper"),
        ]):
            uid = morld.create_id("unit")
            morld.add_unit(uid, name, 0, 0, "male")
            morld.set_unit_prop(uid, "vita", 6)
            morld.set_unit_prop(uid, "생존:체력", 100)
            units.append(uid)
        squad.assign_leader(sid, units[0])
        squad.add_member(sid, units[1])
        squad.add_member(sid, units[2])
        squad.set_member_rank(sid, units[0], 1)
        squad.set_member_rank(sid, units[1], 2)
        squad.set_member_rank(sid, units[2], 3)
        return sid, units

    def test_prepare_start_explore_retreat(self):
        """준비 → 출발 → 이동 → 귀환 전체 흐름"""
        import expedition

        sid, units = self._setup_squad_with_hp()

        # 준비
        state = expedition.prepare_expedition(sid, "easy")
        assert state is not None
        assert state.status == "preparing"

        # 출발
        success, msg = expedition.start_expedition(state.expedition_id)
        assert success
        assert state.status == "active"
        assert len(state.rooms) >= 3

        # 입구에서 연결된 방으로 이동
        explorable = expedition.get_explorable_rooms(state.expedition_id)
        assert len(explorable) >= 1
        target = explorable[0]["id"]
        success, room, msg = expedition.move_to_room(
            state.expedition_id, target)
        assert success
        assert state.current_room == target

        # 귀환
        success, msg = expedition.retreat_expedition(state.expedition_id)
        assert success
        assert state.status == "completed"

        # 플랫폼 복귀 확인
        for uid in units:
            loc = morld.get_unit_location(uid)
            assert loc == (0, 0)

        # 완료
        summary = expedition.complete_expedition(state.expedition_id)
        assert summary is not None
        assert summary["rooms_explored"] >= 2  # entrance + 1

    def test_combat_during_exploration(self):
        """탐사 중 전투 발생 시 전체 흐름"""
        import expedition
        from combat import resolve_room_combat
        import random

        random.seed(42)
        sid, units = self._setup_squad_with_hp()

        state = expedition.prepare_expedition(sid, "easy")
        expedition.start_expedition(state.expedition_id)

        # 위협이 있는 방 찾기
        threat_rooms = [r for r in state.rooms if r.get("threat")]

        if threat_rooms:
            # 위협 방으로 이동 가능한지 확인
            target_room = threat_rooms[0]
            # 경로 찾기 (BFS)
            path = _find_path(state, 0, target_room["id"])
            if path:
                for step in path[1:]:  # skip entrance
                    expedition.move_to_room(state.expedition_id, step)
                # 전투 실행
                result = resolve_room_combat(sid, target_room)
                assert result.occurred is True
                state.combat_log.extend(result.log)

        # 귀환
        expedition.retreat_expedition(state.expedition_id)
        summary = expedition.complete_expedition(state.expedition_id)
        assert summary is not None

    def test_first_mission_start_expedition(self):
        """first_mission.start_expedition 통합 테스트"""
        from events.first_mission import start_expedition

        sid, units = self._setup_squad_with_hp()
        gen = start_expedition(sid)

        # generator 반환 (대화 시퀀스)
        if gen is not None:
            # generator 소비
            for _ in gen:
                pass

        # 원정이 활성 상태인지 확인
        import expedition
        state = expedition.get_expedition_by_squad(sid)
        assert state is not None
        assert state.status == "active"

    def test_first_mission_retreat(self):
        """first_mission.retreat_expedition 통합 테스트"""
        from events.first_mission import start_expedition, retreat_expedition
        import expedition

        sid, units = self._setup_squad_with_hp()
        gen = start_expedition(sid)
        if gen:
            for _ in gen:
                pass

        gen = retreat_expedition(sid)
        if gen:
            for _ in gen:
                pass

        state = expedition.get_expedition_by_squad(sid)
        assert state is not None
        assert state.status == "completed"

    def test_progression_step_10(self):
        """progression step 10 핸들러 통합"""
        import squad
        import expedition
        from events.progression import _handle_step_10

        sid, units = self._setup_squad_with_hp()

        gen = _handle_step_10()
        if gen:
            for _ in gen:
                pass

        # 원정이 시작되었는지 확인
        active = expedition.get_active_expeditions()
        assert len(active) == 1


class TestChapterInit(_T):
    def test_demo_init_resets_systems(self):
        """챕터 초기화 시 squad/expedition/mapgen reset 호출"""
        import squad
        import expedition
        import mapgen

        # 상태 오염
        squad.create_squad()
        mapgen._expeditions[999] = "dummy"

        # 챕터 초기화
        from chapters.demo import initialize
        initialize()

        # 리셋 확인
        assert len(squad.get_all_squads()) == 0
        assert len(expedition._expeditions) == 0
        assert len(mapgen._expeditions) == 0


def _find_path(state, start, end):
    """BFS 경로 탐색"""
    from collections import deque
    adj = {}
    for r in state.rooms:
        adj[r["id"]] = []
    for c in state.connections:
        adj[c["from"]].append(c["to"])
        adj[c["to"]].append(c["from"])

    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node == end:
            return path
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None
