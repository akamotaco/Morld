# think/agents/squad_agent.py - 분대원 Agent
#
# BaseAgent 확장. 5-tier think() 그대로 사용.
# Tier 2: 전투 반응 (MicroTurnCombatState, 미래)
# Tier 5: 분대 행동 대기 (CommandPhase, 미래)
#
# 현재 데모에서는 간소화된 대기/이동만 구현.
# party.py FSM과 호환되는 구조.

import morld
from think import BaseAgent

MILLIS_PER_DAY = 86_400_000


class SquadMemberAgent(BaseAgent):
    """분대원 Agent — BaseAgent 확장

    5-tier think() 그대로 사용.
    기본 스케줄: 분대 행동 대기 (24시간).
    """

    # 기본 스케줄: 분대 행동 대기
    _schedule = [
        {
            "name": "대기",
            "start": 0,
            "end": MILLIS_PER_DAY,
            "activity": "분대행동",
        },
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self._schedule)

    def think(self):
        """분대원 AI

        현재 데모에서는 간소화:
        - FSM 스택에 분대 명령이 있으면 수행
        - 없으면 현재 위치에서 대기

        TODO: 5-tier think() 전체 활성화
        TODO: CommandPhase FSM 연동
        TODO: 건설 Activity 핸들러 연동
        """
        self._action_taken = False

        # FSM 스택 처리 (분대 명령이 push되어 있으면 수행)
        for _state in reversed(list(self._fsm_stack)):
            if _state.update(self):
                return None  # FSM이 처리함

        # FSM에서 처리되지 않으면 대기
        self._insert_idle_job("분대 대기", self._get_action_duration("safety_net"))
        self._action_taken = True

        # safety net
        if not self._action_taken:
            info = self.get_info()
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            print(f"[squad_agent] WARNING: {name} 행동 미결정")
            self._insert_idle_job("할 일 없음", 600_000)

        return None
