# test_acceptance.py — scenario_mini 인수 테스트 (infra-unification U6)
#
# "신규 시나리오 = 콘텐츠 팩" 심 구동 검증. 요구 4항 대응:
#   (a) 통합 인프라만 사용 (팩에 시스템 코드 없음 — import 경로가 증거)
#   (b) 대화 정책 선택제 (이 팩 hybrid / S02 fixed)
#   (c) 캐릭터 = 별도 파일 (데이터 ① + AI ③ 분리)
#   (d) 파티 공용 + 무플레이어 구동
#
# 실행: python scenarios/scenario_mini/python/tests/test_acceptance.py

import io
import os
import sys
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
sys.path.append(os.path.join(_common_dir, "testing"))

from mock_morld import MockMorld  # noqa: E402

_mock = MockMorld()
sys.modules["morld"] = _mock


def _fresh_world():
    """월드 초기화 — 시나리오 부트스트랩 실행"""
    _mock.reset()
    import think
    think.clear_agents()
    from engine import party
    party.reset()
    import scenario
    return scenario.initialize_scenario()


class TestContentPackBootstrap:
    def test_policy_declared_hybrid(self):
        """(b) 부트스트랩이 대화 정책 hybrid 를 선언한다"""
        import scenario  # noqa: F401 — 선언은 import 시점
        from engine import dialogue_policy
        assert dialogue_policy.get_policy() == dialogue_policy.POLICY_HYBRID

    def test_player_contract(self):
        """(d/U0) unique_id='player' 등록만으로 PlayerId 성립 (truthy 계약)"""
        import morld
        handles = _fresh_world()
        assert morld.get_player_id() == handles["player"]
        assert morld.get_player_id()  # truthy — 0(부재) 아님


class TestCharacterStandard:
    def test_describe_from_archetype_pool(self):
        """(a/c) engine.archetype_describe 빌더만으로 묘사 rule 이 동작한다"""
        handles = _fresh_world()
        mia = handles["guide_asset"]
        text = mia.get_describe_text()
        assert text and "미아" in text, text
        focus = mia.get_focus_text()
        assert focus, focus

    def test_agent_registered_and_thinks(self):
        """(c) 캐릭터 표준 ③: think/agents 레지스트리 경유 에이전트가 job 을 삽입"""
        import think
        import morld
        handles = _fresh_world()
        assert "mini_guide" in think.get_registered_agent_ids()
        think.think_all()
        jobs = morld.get_all_jobs(handles["guide"])
        assert jobs, "think_all 후 guide job 이 없음"

    def test_hybrid_line_without_character_yaml(self):
        """(b) 캐릭터 yaml 없이 아키타입 공용 풀만으로 대사 생성"""
        import npc_dialogue
        handles = _fresh_world()
        line = npc_dialogue.daily_line(handles["guide"], "greet")
        assert line.startswith("미아: 「") and line.endswith("」"), line
        # stoic 아키타입도 동일 경로로 생성
        line2 = npc_dialogue.daily_line(handles["ranger"], "greet")
        assert line2.startswith("레인: 「"), line2


class TestPartyUnified:
    def test_recruit_into_player_party(self):
        """(d) engine.party 표준 진입점으로 모집 — 플레이어 파티 합류"""
        from engine import party
        handles = _fresh_world()
        assert party.request_recruit(handles["ranger"])
        p = party.get_party_of(handles["player"])
        assert p is not None
        assert p.is_member(handles["ranger"])
        assert p.get_leader() == handles["player"]
        assert p.get_size() == 2

    def test_stance_and_rank(self):
        """(d) 지휘 자세/대열 순번 — S02/S03 개념이 엔진 공용으로 동작"""
        from engine import party
        handles = _fresh_world()
        party.request_recruit(handles["ranger"])
        pid = party.get_party_of(handles["player"]).party_id
        assert party.set_stance(pid, "combat_normal")
        assert party.get_stance_value(pid) == 1
        assert party.set_member_rank(handles["ranger"], 1)
        assert party.get_member_rank(handles["ranger"]) == 1

    def test_playerless_operation(self):
        """(d) 플레이어 없이도 파티/AI 가 동작 (S03 오퍼레이터형 시나리오 계약)"""
        import morld
        import think
        from engine import party
        from assets.characters import Mia

        _mock.reset()
        think.clear_agents()
        party.reset()

        morld.add_region(0, "무인 마을")
        morld.add_location(0, 0, "광장")
        mia = Mia()
        mia_id = morld.create_id("unit")
        mia.instantiate(mia_id, 0, 0)

        assert not morld.get_player_id()  # 부재 = 0 (None 아님)

        solo = party.create_solo_party(mia_id)
        assert solo is not None and solo.get_leader() == mia_id

        agent = think.create_agent_for("mini_guide", mia_id)
        think.register_agent(mia_id, agent)
        think.think_all()
        assert morld.get_all_jobs(mia_id), "무플레이어 think_all 실패"


def _run():
    classes = [TestContentPackBootstrap, TestCharacterStandard, TestPartyUnified]
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
