# dialogue_policy.py - 시나리오 대화 레이어 정책 (U5, infra-unification §2-5)
#
# 시나리오 부트스트랩에서 선언한다:
#   from engine import dialogue_policy
#   dialogue_policy.set_policy(dialogue_policy.POLICY_FIXED)
#
# 정책 3종:
#   - fixed:          고정 대사 전용. hybrid(동적 생성) 폴백을 전면 차단 (S02)
#   - fixed+fallback: 고정 대사 우선, 미커버 지점만 hybrid 폴백 (기본값 = 기존 동작)
#   - hybrid:         동적 생성이 1차 레이어인 시나리오 (S03/S04) — 선언적 표시
#
# 게이트는 allows_dynamic() 하나: fixed 에서만 False.
# fixed 차단 시 노출되는 커버리지 갭은
# scenarios/scenario02/docs/dialogue-fallback-coverage.md 참조.

POLICY_FIXED = "fixed"
POLICY_FIXED_FALLBACK = "fixed+fallback"
POLICY_HYBRID = "hybrid"
VALID_POLICIES = (POLICY_FIXED, POLICY_FIXED_FALLBACK, POLICY_HYBRID)

DEFAULT_POLICY = POLICY_FIXED_FALLBACK

_policy = DEFAULT_POLICY


def set_policy(policy):
    """대화 정책 선언 (시나리오 부트스트랩에서 1회)"""
    global _policy
    if policy not in VALID_POLICIES:
        raise ValueError(
            f"invalid dialogue policy: {policy!r} (valid: {VALID_POLICIES})")
    _policy = policy
    print(f"[dialogue_policy] policy = {policy}")
    return _policy


def get_policy():
    return _policy


def allows_dynamic():
    """동적(hybrid) 생성 허용 여부 — fixed 에서만 False"""
    return _policy != POLICY_FIXED


def reset():
    """pi-world reset 계약 — 정책은 챕터 상태가 아니라 시나리오 속성이므로 유지.

    (party_group 의 콜백/핸들러 유지와 같은 정책. 테스트에서 정책을 바꿨다면
    set_policy(DEFAULT_POLICY) 로 직접 복원할 것.)
    """
    pass
