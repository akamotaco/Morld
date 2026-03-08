# think/__init__.py - NPC AI 시스템 (시나리오03)

# 레지스트리 함수 export
from .registry import (
    _agents, _agent_classes,
    register_agent, unregister_agent, get_agent, get_all_agents,
    think_all, clear_all, clear_agents,
    register_agent_class, create_agent_for, get_registered_agent_ids,
)


# BaseAgent 최소 구현
class BaseAgent:
    STAY_SCHEDULE = [{"name": "대기", "start": 0, "end": 86_400_000, "activity": "대기"}]
    _action_duration_overrides = {}

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self._current_activity = None
        self._activity_phase = "idle"
        self._activity_state = {}
        self._action_taken = False
        self._fsm_stack = []
        self._memory = {}
        self._schedule = None

    def set_base_schedule(self, schedule):
        self._schedule = schedule

    def think(self):
        self._action_taken = False
        self._insert_idle_job("대기", 600_000)
        self._action_taken = True

    def get_info(self):
        import morld
        return morld.get_unit_info(self.unit_id)

    def get_location(self):
        import morld
        return morld.get_unit_location(self.unit_id)

    def _insert_idle_job(self, name, duration_millis):
        if duration_millis <= 0:
            return
        import morld
        morld.insert_job(self.unit_id, {
            "name": name,
            "action": "stay",
            "duration": duration_millis,
        })

    def _get_action_duration(self, key):
        if key in self._action_duration_overrides:
            return self._action_duration_overrides[key]
        # Default durations
        defaults = {"safety_net": 600_000, "brief": 3_000}
        return defaults.get(key, 60_000)

    def _do_instant_action(self, job_name, duration_key):
        duration = self._get_action_duration(duration_key)
        self._insert_idle_job(job_name, duration)
        self._action_taken = True


# 시나리오03 Agent 임포트 (자동 등록)
from . import agents
