"""Hybrid 대화 어댑터(npc_dialogue.py) 테스트

핵심=고정/주변=dynamic 규약 중 '주변 대사' 경로:
분대원(아키타입 공용 풀) + 비서(cold + characters/비서.yaml override).
"""
import random

import morld


def _make_member(serial, role):
    from assets.characters.squad_member import SquadMember
    npc = SquadMember()
    npc.configure(f"echo_{serial:02d}", f"Echo-{serial:02d}", role)
    uid = morld.create_id("unit")
    npc.instantiate(uid, 0, 0)
    return uid


class _T:
    def __init__(self):
        morld.reset()
        import npc_dialogue
        npc_dialogue.clear_cache()


class TestArchetypeMapping(_T):
    def test_role_archetypes(self):
        import npc_dialogue
        expected = {
            "assault": "fierce",
            "support": "cheerful",
            "sniper": "stoic",
            "medic": "gentle",
        }
        for i, (role, arch) in enumerate(expected.items()):
            uid = _make_member(i + 1, role)
            assert npc_dialogue.member_archetype(uid) == arch

    def test_unknown_role_defaults(self):
        import npc_dialogue
        uid = morld.create_id("unit")
        morld.add_unit(uid, "무명", 0, 0, "male")  # 역할 prop 없음
        assert npc_dialogue.member_archetype(uid) == "stoic"


class TestStateMapping(_T):
    def test_state_from_props(self):
        import npc_dialogue
        uid = _make_member(1, "assault")  # vita 6, hp 60/60, 인간성 100
        morld.set_unit_prop(uid, "생존:체력", 30)  # 절반 부상
        st = npc_dialogue.member_state(uid)
        assert abs(st["fatigue"] - 0.5) < 1e-6
        assert abs(st["confidence"] - 0.2) < 1e-6  # (6-5)/5
        assert abs(st["affinity"] - 1.0) < 1e-6    # (100-50)/50

    def test_humanity_untracked_no_affinity(self):
        import npc_dialogue
        uid = morld.create_id("unit")
        morld.add_unit(uid, "무명", 0, 0, "male")  # 인간성 prop 없음(=0)
        st = npc_dialogue.member_state(uid)
        assert "affinity" not in st


class TestMemberLines(_T):
    def test_combat_lines_all_roles(self):
        """모든 역할 아키타입에서 전투 대사 생성 (빈 문자열 금지)"""
        import npc_dialogue
        for i, role in enumerate(["assault", "support", "sniper", "medic"]):
            uid = _make_member(i + 1, role)
            for intent in ("combat_engage", "combat_victory",
                           "combat_defeat", "combat_ally_down"):
                line = npc_dialogue.member_combat_line(
                    uid, intent, rng=random.Random(i * 10 + 1))
                assert line, f"{role}/{intent} 빈 대사"
                assert line.startswith(f"Echo-{i + 1:02d}: 「")

    def test_dungeon_and_party_lines(self):
        import npc_dialogue
        uid = _make_member(1, "sniper")
        amb = npc_dialogue.member_dungeon_line(
            uid, "dungeon_ambient", rng=random.Random(3))
        dep = npc_dialogue.member_dungeon_line(
            uid, "floor_descent", rng=random.Random(5))
        ret = npc_dialogue.member_party_line(
            uid, "vote_return", rng=random.Random(7))
        greet = npc_dialogue.member_daily_line(
            uid, "greet", rng=random.Random(9))
        for line in (amb, dep, ret, greet):
            assert line and "「" in line

    def test_unknown_intent_returns_empty(self):
        """미정의 인텐트는 빈 문자열 — 호출측이 조용히 생략 (폴백 계약)"""
        import npc_dialogue
        uid = _make_member(1, "assault")
        assert npc_dialogue.member_combat_line(
            uid, "no_such_intent_xyz", rng=random.Random(1)) == ""


class TestSecretaryLines(_T):
    def test_secretary_greet(self):
        import npc_dialogue
        line = npc_dialogue.secretary_line("greet", rng=random.Random(1))
        assert line  # cold 풀 + 비서.yaml override 중 하나

    def test_secretary_system_tone_reachable(self):
        """비서.yaml 시스템 톤 override가 병합되어 있는지 (여러 시드로 탐지)"""
        import npc_dialogue
        markers = ("접속", "인증", "연결", "작동", "시스템", "대기 상태",
                   "절전", "저전력", "확인", "인식")
        found = False
        for i in range(60):
            line = npc_dialogue.secretary_line(
                "greet", state={"confidence": 0.6, "fatigue": 0.7},
                rng=random.Random(i))
            if any(m in line for m in markers):
                found = True
                break
        assert found, "비서 시스템 톤 override 미병합 의심"
