# think/agents/mia_agent.py — 안내인 미아 AI (캐릭터 표준 ③)
#
# engine.think_base.BaseAgent 를 그대로 사용하는 최소 에이전트.
# _on_think 만 구현하면 FSM/perceive/evaluate/safety-net 은 엔진이 처리한다.

import morld

from think import BaseAgent, register_agent_class


@register_agent_class("mini_guide")
class MiaAgent(BaseAgent):
    """광장 안내인 — 30분 단위로 안내 활동 유지"""

    def _on_think(self):
        morld.insert_job(self.unit_id, {
            "name": "안내",
            "action": "stay",
            "duration": 30 * 60_000,
        })
        self._action_taken = True
