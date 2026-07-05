# scenario.py — scenario_mini 부트스트랩 (infra-unification U6 인수 검증)
#
# "신규 시나리오 = 콘텐츠 팩" 증명: 엔진 모듈만 사용, 시스템 코드 복사 없음.

# 대화 정책: 동적 생성 1차 레이어 (engine.dialogue_policy, §2-5)
from engine import dialogue_policy as _dialogue_policy
_dialogue_policy.set_policy(_dialogue_policy.POLICY_HYBRID)

import world


def initialize_scenario():
    """시나리오 초기화 — C# 진입점"""
    print("[scenario_mini] Initializing...")
    handles = world.build()
    print("[scenario_mini] Ready.")
    return handles
