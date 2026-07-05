"""반복 운영 루프(cycle.py) 테스트 — 결번/재보급/보고서"""
import morld


def _make_member(serial, role="assault", humanity=100):
    """SquadMember 인스턴스 생성 (승강장 배치)"""
    from assets.characters.squad_member import SquadMember
    npc = SquadMember()
    npc.configure(f"echo_{serial:02d}", f"Echo-{serial:02d}", role,
                  humanity=humanity)
    uid = morld.create_id("unit")
    npc.instantiate(uid, 0, 0)
    return uid


def _make_squad(roles=("assault", "support", "sniper")):
    import squad
    sid = squad.create_squad()
    units = []
    for i, role in enumerate(roles):
        uid = _make_member(i + 1, role)
        units.append(uid)
    squad.assign_leader(sid, units[0])
    for uid in units[1:]:
        squad.add_member(sid, uid)
    return sid, units


class _T:
    def __init__(self):
        morld.reset()
        import squad, expedition, mapgen, cycle
        squad.reset()
        expedition.reset()
        mapgen.reset()
        cycle.reset()
        from think import clear_all
        clear_all()


class TestOperationsLifecycle(_T):
    def test_start_operations(self):
        import cycle
        assert cycle.is_active() is False
        cycle.start_operations()
        assert cycle.is_active() is True
        assert cycle.get_cycle_number() == 1
        assert cycle.get_phase() == "ready"

    def test_difficulty_ramp(self):
        import cycle
        assert cycle.difficulty_for_cycle(1) == "easy"
        assert cycle.difficulty_for_cycle(2) == "easy"
        assert cycle.difficulty_for_cycle(3) == "normal"
        assert cycle.difficulty_for_cycle(4) == "normal"
        assert cycle.difficulty_for_cycle(5) == "hard"
        assert cycle.difficulty_for_cycle(9) == "hard"

    def test_phase_transitions(self):
        import cycle
        cycle.start_operations()
        cycle.mark_expedition_started()
        assert cycle.get_phase() == "expedition"
        report = cycle.complete_cycle({"collected_loot": {}, "casualties": []})
        assert cycle.get_phase() == "debrief"
        assert report["cycle"] == 1
        supply = cycle.run_supply_phase()
        assert cycle.get_phase() == "ready"
        assert cycle.get_cycle_number() == 2
        assert supply["cycle"] == 2


class TestCasualties(_T):
    def test_member_death_removed(self):
        import cycle
        import squad
        sid, units = _make_squad()
        dead = units[1]
        records = cycle.process_casualties(sid, [dead])
        assert records[0]["name"] == "Echo-02"
        assert records[0]["role_key"] == "support"
        assert dead not in squad.get_all_unit_ids(sid)
        assert morld.get_unit_info(dead) is None  # 유닛 제거됨

    def test_leader_death_promotes_member(self):
        import cycle
        import squad
        sid, units = _make_squad()
        cycle.process_casualties(sid, [units[0]])
        sq = squad.get_squad(sid)
        assert sq is not None
        assert sq.leader_id == units[1]  # 첫 잔존 대원 승계
        assert units[0] not in sq.all_unit_ids()

    def test_full_wipe_disbands_squad(self):
        import cycle
        import squad
        sid, units = _make_squad(("assault",))  # 리더 1명뿐
        cycle.process_casualties(sid, [units[0]])
        assert squad.get_squad(sid) is None

    def test_casualty_queues_supply(self):
        import cycle
        sid, units = _make_squad()
        cycle.start_operations()
        cycle.process_casualties(sid, [units[2]])
        supply = cycle.run_supply_phase()
        assert len(supply["replacements"]) == 1
        assert supply["replacements"][0]["role_key"] == "sniper"


class TestSupplyReplacement(_T):
    def test_next_serial_and_trauma(self):
        """차기 시리얼 번호 + 트라우마 계승 (역할 누적 결번 x10 감소)"""
        import cycle
        import squad
        sid, units = _make_squad()
        cycle.start_operations()

        cycle.process_casualties(sid, [units[1]])  # support 결번 1회
        supply = cycle.run_supply_phase()
        rep = supply["replacements"][0]
        assert rep["name"] == "Echo-05"
        assert rep["humanity"] == 90
        # 자동 편입
        assert rep["unit_id"] in squad.get_all_unit_ids(sid)
        # 인간성 prop 반영 (하한 1 계약)
        assert morld.get_unit_prop(rep["unit_id"], "인간성") == 90

        # 같은 역할 2번째 결번 → 트라우마 누적
        cycle.process_casualties(sid, [rep["unit_id"]])
        supply2 = cycle.run_supply_phase()
        rep2 = supply2["replacements"][0]
        assert rep2["name"] == "Echo-06"
        assert rep2["humanity"] == 80

    def test_supply_stockpile(self):
        import cycle
        cycle.start_operations()
        cycle.run_supply_phase()
        stock = cycle.get_stockpile()
        assert stock["plank"] == 5
        assert stock["concrete_block"] == 3

    def test_replacement_hp_initialized(self):
        import cycle
        from assets.characters.squad_member import base_hp_for_vita, ROLE_PROPS
        sid, units = _make_squad()
        cycle.start_operations()
        cycle.process_casualties(sid, [units[0]])
        supply = cycle.run_supply_phase()
        rep = supply["replacements"][0]
        expected = base_hp_for_vita(ROLE_PROPS["assault"]["vita"])
        assert morld.get_unit_prop(rep["unit_id"], "생존:체력") == expected
        assert morld.get_unit_prop(rep["unit_id"], "생존:체력max") == expected


class TestReport(_T):
    def test_complete_cycle_report(self):
        import cycle
        sid, units = _make_squad()
        cycle.start_operations()
        summary = {
            "difficulty": "easy",
            "rooms_explored": 4, "rooms_total": 6,
            "combat_count": 2, "victory_count": 2,
            "collected_loot": {"plank": 3},
            "casualties": [{"name": "Echo-02", "role_key": "support"}],
        }
        report = cycle.complete_cycle(summary)
        assert report["rooms_explored"] == 4
        assert report["stockpile"]["plank"] == 3
        assert len(report["members"]) == 3
        assert cycle.get_last_report() is report

    def test_report_text(self):
        import cycle
        sid, units = _make_squad()
        cycle.start_operations()
        cycle.complete_cycle({
            "difficulty": "easy",
            "rooms_explored": 4, "rooms_total": 6,
            "combat_count": 1, "victory_count": 1,
            "collected_loot": {"plank": 3},
            "casualties": [{"name": "Echo-09"}],
        })
        text = cycle.build_report_text()
        assert "운행 주기 1" in text
        assert "Echo-01" in text          # 대원별 상태
        assert "Echo-09" in text          # 결번
        assert "plank x3" in text         # 수집
        assert "H.I" in text

    def test_report_text_without_report(self):
        import cycle
        assert "없습니다" in cycle.build_report_text()


class TestOperationsCycleFlow(_T):
    def test_full_cycle_loop(self):
        """운영 개시 → 출발 → 전 구역 탐사(전투/결번 포함) → 귀환 → 보고 → 보급"""
        import random as _r
        _r.seed(42)
        import cycle
        import expedition
        import squad
        from events.first_mission import handle_room_entered, retreat_expedition

        sid, units = _make_squad()
        cycle.start_operations()

        state = expedition.prepare_expedition(sid, cycle.current_difficulty())
        ok, _ = expedition.start_expedition(state.expedition_id)
        assert ok
        cycle.mark_expedition_started()
        assert cycle.get_phase() == "expedition"

        # 미탐색 구역 순회 (전멸 시 중단)
        for _ in range(30):
            rooms = expedition.get_explorable_rooms(state.expedition_id)
            unexplored = [r for r in rooms if not r["explored"]]
            if not unexplored:
                break
            target = unexplored[0]
            ok, room, _msg = expedition.move_to_room(
                state.expedition_id, target["id"])
            assert ok
            gen = handle_room_entered(state.expedition_id, target["id"])
            if gen:
                for _ in gen:
                    pass
            if not squad.get_all_unit_ids(sid):
                break  # 전멸

        # 귀환 + 주기 마감
        gen = retreat_expedition(state.squad_id)
        if gen:
            for _ in gen:
                pass
        summary = expedition.complete_expedition(state.expedition_id)
        assert summary is not None

        report = cycle.complete_cycle(summary)
        assert report["cycle"] == 1
        text = cycle.build_report_text(report)
        assert "운행 주기 1" in text

        supply = cycle.run_supply_phase()
        assert cycle.get_cycle_number() == 2
        assert cycle.get_phase() == "ready"
        # 결번이 있었다면 대체 개체가 도착했어야 함
        assert len(supply["replacements"]) == len(summary["casualties"])
