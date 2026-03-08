# think/agents/secretary_agent.py - 비서 Agent
#
# 플랫폼 상주, 보고/안내 역할.
# 전투/탐사에 참여하지 않는 비전투 NPC.
# 통신실에서 대기하며 플레이어(오퍼레이터)를 보좌한다.

import morld
from think import BaseAgent

MILLIS_PER_DAY = 86_400_000


class SecretaryAgent(BaseAgent):
    """비서 AI — 플랫폼 상주, 보고/안내 역할

    스케줄: 통신실(R0, L2)에서 24시간 대기.
    전투/탐사 불참.
    """

    # 비서 전용 스케줄: 통신실 상주
    _schedule = [
        {
            "name": "대기",
            "start": 0,
            "end": MILLIS_PER_DAY,
            "activity": "대기",
            "region_id": 0,
            "location_id": 2,
            "x": 30,
        },
    ]

    owner_unique_id = "secretary"

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self._schedule)

    def think(self):
        """비서 AI — 통신실 대기만 수행

        비전투 NPC이므로 5-tier 로직 대부분 생략.
        통신실에 있으면 대기, 없으면 이동.
        """
        self._action_taken = False

        loc = self.get_location()
        target_region = 0
        target_location = 2  # 통신실

        if loc and loc[0] == target_region and loc[1] == target_location:
            # 통신실에 있음 → 대기
            self._insert_idle_job("대기", MILLIS_PER_DAY)
            self._action_taken = True
        else:
            # 통신실로 이동
            morld.insert_job(self.unit_id, {
                "name": "통신실 복귀",
                "action": "move",
                "region_id": target_region,
                "location_id": target_location,
                "target_x": 30,
                "duration": 0,
            })
            self._action_taken = True

        # safety net
        if not self._action_taken:
            self._insert_idle_job("할 일 없음", 600_000)

        return None
