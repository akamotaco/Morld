"""전투 시스템 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()

    def _setup_squad(self, vita=5, hp=100):
        """테스트용 분대 (리더1 + 멤버2)"""
        import squad
        squad.reset()
        sid = squad.create_squad()
        units = []
        for i, name in enumerate(["Echo-01", "Echo-02", "Echo-03"]):
            uid = morld.create_id("unit")
            morld.add_unit(uid, name, 0, 0, "male")
            morld.set_unit_prop(uid, "vita", vita)
            morld.set_unit_prop(uid, "생존:체력", hp)
            units.append(uid)
        squad.assign_leader(sid, units[0])
        squad.add_member(sid, units[1])
        squad.add_member(sid, units[2])
        # Set ranks: front/mid/rear
        squad.set_member_rank(sid, units[0], 1)
        squad.set_member_rank(sid, units[1], 2)
        squad.set_member_rank(sid, units[2], 3)
        return sid, units


class TestCombatNoThreat(_T):
    def test_no_threat_no_combat(self):
        from combat import resolve_room_combat
        sid, _ = self._setup_squad()
        room = {"id": 1, "type": "room"}
        result = resolve_room_combat(sid, room)
        assert result.occurred is False
        assert result.victory is False


class TestCombatResult(_T):
    def test_combat_occurs_with_threat(self):
        import random
        random.seed(42)
        from combat import resolve_room_combat
        sid, _ = self._setup_squad(vita=10)
        room = {"id": 1, "type": "room", "threat": "P"}
        result = resolve_room_combat(sid, room)
        assert result.occurred is True
        assert result.threat_code == "P"
        assert result.threat_name == "해충 떼"
        assert len(result.log) >= 2

    def test_high_vita_wins(self):
        import random
        random.seed(1)
        from combat import resolve_room_combat
        sid, _ = self._setup_squad(vita=20)
        room = {"id": 1, "type": "room", "threat": "P"}
        result = resolve_room_combat(sid, room)
        assert result.occurred is True
        # vita=20*3=60 vs threat=3, should almost certainly win
        assert result.victory is True

    def test_victory_removes_threat(self):
        import random
        random.seed(1)
        from combat import resolve_room_combat
        sid, _ = self._setup_squad(vita=20)
        room = {"id": 1, "type": "room", "threat": "B"}
        result = resolve_room_combat(sid, room)
        if result.victory:
            assert "threat" not in room


class TestCombatDamage(_T):
    def test_damage_applied(self):
        import random
        random.seed(42)
        from combat import resolve_room_combat
        sid, units = self._setup_squad(vita=5, hp=100)
        room = {"id": 1, "type": "room", "threat": "R"}
        result = resolve_room_combat(sid, room)
        assert result.occurred is True
        assert len(result.damage_taken) == 3
        for uid in units:
            assert result.damage_taken[uid] >= 1

    def test_front_rank_takes_more(self):
        import random
        random.seed(42)
        from combat import resolve_room_combat
        sid, units = self._setup_squad(vita=5, hp=100)
        room = {"id": 1, "type": "room", "threat": "W"}
        result = resolve_room_combat(sid, room)
        front_dmg = result.damage_taken[units[0]]  # rank 1
        rear_dmg = result.damage_taken[units[2]]   # rank 3
        assert front_dmg >= rear_dmg

    def test_death_at_zero_hp(self):
        """HP 0 도달 시 deaths에 기록 (결번 후보). HP는 음수로 내려가지 않음."""
        import random
        random.seed(42)
        from combat import resolve_room_combat
        sid, units = self._setup_squad(vita=1, hp=2)
        room = {"id": 1, "type": "room", "threat": "W"}
        result = resolve_room_combat(sid, room)
        assert len(result.deaths) >= 1
        for uid in result.deaths:
            assert morld.get_unit_prop(uid, "생존:체력") == 0
        for uid in units:
            assert morld.get_unit_prop(uid, "생존:체력") >= 0

    def test_absent_hp_initialized_from_vita(self):
        """prop 계약: 체력 prop 부재(=0)면 vita 기반 규격 체력으로 초기화 후 피해 적용.

        (구버전은 `is None` 판정으로 부재 유닛 HP가 1로 붕괴하는 버그가 있었다)
        """
        import random
        random.seed(1)
        import squad
        from combat import resolve_room_combat
        from assets.characters.squad_member import base_hp_for_vita

        squad.reset()
        sid = squad.create_squad()
        uid = morld.create_id("unit")
        morld.add_unit(uid, "Echo-99", 0, 0, "male")
        morld.set_unit_prop(uid, "vita", 6)  # 체력 prop 미설정
        squad.assign_leader(sid, uid)

        room = {"id": 1, "type": "room", "threat": "P"}
        result = resolve_room_combat(sid, room)
        hp = morld.get_unit_prop(uid, "생존:체력")
        expected = base_hp_for_vita(6) - result.damage_taken[uid]
        assert hp == max(0, expected)
        assert hp > 1  # 규격 체력(60)에서 소량 피해 — 1로 붕괴하지 않음


class TestGrowthAndHumanity(_T):
    def test_vita_growth_on_victory(self):
        """승리 시 생존자 vita +1 (상한 10)"""
        import random
        random.seed(1)
        from combat import resolve_room_combat
        sid, units = self._setup_squad(vita=8, hp=100)
        room = {"id": 1, "type": "room", "threat": "P"}
        result = resolve_room_combat(sid, room)
        assert result.victory is True
        for uid in units:
            assert morld.get_unit_prop(uid, "vita") == 9
            assert result.growth[uid] == 1

    def test_vita_capped_at_10(self):
        import random
        random.seed(1)
        from combat import resolve_room_combat
        sid, units = self._setup_squad(vita=10, hp=100)
        room = {"id": 1, "type": "room", "threat": "P"}
        result = resolve_room_combat(sid, room)
        assert result.victory is True
        for uid in units:
            assert morld.get_unit_prop(uid, "vita") == 10
        assert result.growth == {}

    def test_humanity_wear(self):
        """전투 후 인간성 마모 (-2), 미추적(0) 유닛은 건드리지 않음"""
        import random
        random.seed(1)
        from combat import resolve_room_combat
        sid, units = self._setup_squad(vita=8, hp=100)
        morld.set_unit_prop(units[0], "인간성", 100)  # units[1,2]는 미추적
        room = {"id": 1, "type": "room", "threat": "P"}
        resolve_room_combat(sid, room)
        assert morld.get_unit_prop(units[0], "인간성") == 98
        assert morld.get_unit_prop(units[1], "인간성") == 0  # 그대로 미추적


class TestAggressionEffect(_T):
    def test_aggressive_more_damage_taken(self):
        import random
        import squad
        from combat import resolve_room_combat

        # Aggressive
        random.seed(42)
        sid_a, units_a = self._setup_squad(vita=5, hp=100)
        squad.set_aggression(sid_a, "combat_aggressive")
        room_a = {"id": 1, "type": "room", "threat": "R"}
        result_a = resolve_room_combat(sid_a, room_a)

        morld.reset()

        # Defensive
        random.seed(42)
        sid_d, units_d = self._setup_squad(vita=5, hp=100)
        squad.set_aggression(sid_d, "defensive")
        room_d = {"id": 1, "type": "room", "threat": "R"}
        result_d = resolve_room_combat(sid_d, room_d)

        total_a = sum(result_a.damage_taken.values())
        total_d = sum(result_d.damage_taken.values())
        assert total_a >= total_d
