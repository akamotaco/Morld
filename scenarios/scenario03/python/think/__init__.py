# think/__init__.py - NPC AI 시스템 (시나리오03) — engine 코어 채택 (U1)
#
# 레지스트리/디스패처: engine.think (C# 계약: `import think; think.think_all()`)
# BaseAgent: engine.think_base 상속 (스케줄 스택/FSM/activity 슬롯/job 헬퍼 상속)
#
# 과거 이 패키지는 자체 registry + 자체 BaseAgent 최소 구현을 갖고 있었다
# (엔진 이관에서 누락된 세대). infra-unification-plan §2-3에 따라 정본 채택.

from engine.think import (  # noqa: F401
    _agents, _agent_classes,
    register_agent, unregister_agent, get_agent, get_all_agents,
    think_all, clear_all, clear_agents,
    register_agent_class, create_agent_for, get_registered_agent_ids,
    reset,
)

from engine.think_base import BaseAgent as _EngineBaseAgent


class BaseAgent(_EngineBaseAgent):
    """S03 Agent 기반 클래스 — engine.think_base 확장.

    S03 전용 확장:
    - _move_to_target: 텔레포트식 이동 (원격 지휘 시나리오의 데모 시맨틱 —
      engine의 경로 이동 _move_to(region, location)와 별개)
    - _get_action_duration: 미등록 키 기본 60초 (기존 데모 시맨틱 유지)
    """

    _action_duration_overrides = {}  # 인스턴스별 오버라이드 (레거시 호환)

    ACTION_DURATION = {"brief": 3_000}

    def _get_action_duration(self, key):
        if key in self._action_duration_overrides:
            return self._action_duration_overrides[key]
        if key in self.ACTION_DURATION:
            return self.ACTION_DURATION[key]
        if key == "safety_net":
            return self.SAFETY_NET_DURATION
        return 60_000

    def _move_to_target(self, target, job_name="이동"):
        """target dict({"region_id","location_id"})로 즉시 배치 + 이동 시간 job"""
        import morld
        morld.set_unit_location(
            self.unit_id, target["region_id"], target["location_id"])
        self._insert_idle_job(job_name, 60_000)


# 시나리오03 Agent 임포트 (자동 등록)
from . import agents  # noqa: E402,F401
