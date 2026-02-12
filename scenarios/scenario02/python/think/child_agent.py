# think/child_agent.py - 아이 NPC AI
#
# 출산 시 동적 생성되는 아이 NPC의 에이전트.
# 최소 욕구 행동만 수행 (먹고/자고/배변).

import morld
from think import BaseAgent

# 분 → 밀리초 변환
_M = 60_000


class ChildAgent(BaseAgent):
    """아이 NPC — 최소 욕구 행동만"""

    DEFAULT_SCHEDULE = [
        {"name": "수면", "start": 0, "end": 360 * _M, "activity": "수면"},
        {"name": "기상", "start": 360 * _M, "end": 420 * _M, "activity": "대기"},
        {"name": "아침", "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
        {"name": "오전", "start": 480 * _M, "end": 720 * _M, "activity": "대기"},
        {"name": "점심", "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
        {"name": "오후", "start": 780 * _M, "end": 1080 * _M, "activity": "대기"},
        {"name": "저녁", "start": 1080 * _M, "end": 1140 * _M, "activity": "식사"},
        {"name": "야간", "start": 1140 * _M, "end": 1200 * _M, "activity": "대기"},
        {"name": "수면", "start": 1200 * _M, "end": 86_400_000, "activity": "수면"},
    ]

    owner_unique_id = "child"

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.DEFAULT_SCHEDULE)

        import survival
        survival.register_npc(unit_id)
        import temperature
        temperature.register_character(unit_id)
