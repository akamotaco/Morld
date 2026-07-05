# test_dialogue_policy.py — 대화 정책 스위치 계약 (U5, infra-unification §2-5)

from engine import dialogue_policy


class TestDialoguePolicy:
    def setUp(self):
        dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_default_policy_allows_dynamic(self):
        """기본 정책(fixed+fallback)은 동적 생성 허용 — 기존 동작 보존"""
        assert dialogue_policy.get_policy() == dialogue_policy.POLICY_FIXED_FALLBACK
        assert dialogue_policy.allows_dynamic()

    def test_fixed_blocks_dynamic(self):
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        assert not dialogue_policy.allows_dynamic()
        dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_hybrid_allows_dynamic(self):
        dialogue_policy.set_policy(dialogue_policy.POLICY_HYBRID)
        assert dialogue_policy.allows_dynamic()
        dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)

    def test_invalid_policy_raises(self):
        try:
            dialogue_policy.set_policy("dynamic")
        except ValueError:
            pass
        else:
            assert False, "잘못된 정책이 통과됨"
        # 실패한 선언은 기존 정책을 바꾸지 않는다
        assert dialogue_policy.get_policy() == dialogue_policy.DEFAULT_POLICY

    def test_reset_preserves_policy(self):
        """정책은 시나리오 속성 — 챕터 리셋에도 유지 (party 콜백과 동일 정책)"""
        dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
        dialogue_policy.reset()
        assert dialogue_policy.get_policy() == dialogue_policy.POLICY_FIXED
        dialogue_policy.set_policy(dialogue_policy.DEFAULT_POLICY)
