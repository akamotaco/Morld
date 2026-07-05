# test_dialogue_policy_s02.py — S02 fixed 정책 게이트 검증 (U5, §2-5)
#
# S02 프로덕션 부트스트랩은 POLICY_FIXED 를 선언한다. 이 테스트는 fixed 에서
# Character 의 3개 hybrid 폴백 경로(톤 접두사 위임 / _generate_dialogue
# catch-all / initiative during_ 폴백)가 전부 차단되는지 검증한다.
# 테스트 스위트 자체는 기본 정책(fixed+fallback)으로 돈다 — 각 테스트가
# 정책을 바꾼 뒤 반드시 DEFAULT 로 복원한다.

from engine import dialogue_policy
import assets.base as base


class _GateProbe:
    """Character 게이트 검증용 최소 fake — 실제 base 메서드를 차용"""
    name = "프로브"
    instance_id = 1
    REACTION_PROFILE = {"name": "프로브", "archetype": "stoic"}
    ROMANCE_REACTIONS = {}
    INITIATIVE_REACTIONS = None

    get_romance_reaction = base.Character.get_romance_reaction
    get_initiative_reaction = base.Character.get_initiative_reaction
    _resolve_reaction_rules = base.Character._resolve_reaction_rules
    _resolve_texts = base.Character._resolve_texts
    _nearest_2d = base.Character._nearest_2d
    _nearest_2d_raw = base.Character._nearest_2d_raw
    _check_reaction_condition = base.Character._check_reaction_condition

    def __init__(self):
        self.gen_calls = 0

    def _build_reaction_state(self, stim_state=None):
        return {"호감": 50, "성욕": 50}

    def _generate_dialogue(self, action_id, timing, stim_state=None):
        self.gen_calls += 1
        return f"[GEN:{action_id}:{timing}]"


class _RealDelegateProbe(_GateProbe):
    """base 의 실제 _generate_dialogue(정책 게이트 내장)를 사용하는 프로브"""
    _generate_dialogue = base.Character._generate_dialogue
    ROMANCE_REACTIONS = {
        "hug:start": [({}, "_generate_dialogue")],  # hybrid catch-all
    }


class TestFixedPolicyGates:
    def test_prefix_fallback_delegates_by_default(self):
        """기본 정책: 톤 접두사 키는 hybrid 위임 (기존 동작 보존)"""
        probe = _GateProbe()
        result = probe.get_romance_reaction("forced_hug", "during")
        assert result == "[GEN:forced_hug:during]"
        assert probe.gen_calls == 1

    def test_fixed_blocks_prefix_fallback(self):
        """fixed: 톤 접두사 위임 차단 — 조용히 None (호출측이 기본 키로 폴백)"""
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        try:
            probe = _GateProbe()
            result = probe.get_romance_reaction("forced_hug", "during")
            assert result is None
            assert probe.gen_calls == 0, "fixed 에서 hybrid 가 호출됨"
        finally:
            dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_fixed_blocks_generate_dialogue_catchall(self):
        """fixed: ({}, '_generate_dialogue') catch-all 차단 → None"""
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        try:
            probe = _RealDelegateProbe()
            result = probe.get_romance_reaction("hug", "start")
            assert result is None
        finally:
            dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_fixed_keeps_explicit_fixed_rules(self):
        """fixed: 고정 rule 은 그대로 동작 — 차단 대상은 hybrid 위임뿐"""
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        try:
            probe = _GateProbe()
            probe.ROMANCE_REACTIONS = {"hug:start": [({}, ["고정 대사"])]}
            result = probe.get_romance_reaction("hug", "start")
            assert result == "고정 대사"
        finally:
            dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_fixed_blocks_initiative_fallback(self):
        """fixed: get_initiative_reaction 의 during_ hybrid 폴백 차단"""
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        try:
            probe = _GateProbe()
            assert probe.get_initiative_reaction("during_hug") is None
            assert probe.get_initiative_reaction("forced_during_hug") is None
        finally:
            dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_fixed_initiative_fixed_rules_still_work(self):
        """fixed: INITIATIVE_REACTIONS 고정 rule 은 유지"""
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        try:
            probe = _GateProbe()
            probe.INITIATIVE_REACTIONS = {
                "during_hug": [({}, ["고정 주도 대사"])],
            }
            assert probe.get_initiative_reaction("during_hug") == "고정 주도 대사"
        finally:
            dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)
