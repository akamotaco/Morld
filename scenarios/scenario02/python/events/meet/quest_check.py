# events/meet/quest_check.py - 퀘스트 meet 조건 체크
#
# 플레이어가 NPC를 만날 때마다 진행 중인 퀘스트의 meet 조건을 체크합니다.
# 우선순위를 낮게 설정하여 다른 이벤트 후에 실행됩니다.

from events.base import MeetEvent
from events import registry


@registry.register
class QuestMeetCheck(MeetEvent):
    """NPC 만남 시 퀘스트 조건 체크"""
    target_unique_id = None  # 모든 NPC
    priority = -100  # 낮은 우선순위 (다른 이벤트 후에 실행)

    def handle(self, player_id, unit_ids=None, **ctx):
        from quest import quest_manager

        # unit_ids에서 플레이어가 아닌 유닛 찾기
        if unit_ids:
            for uid in unit_ids:
                if uid != player_id:
                    quest_manager.check_meet_conditions(player_id, uid)
        # Generator가 아니므로 아무것도 yield하지 않음
        return
        yield  # Generator로 만들기 위한 더미 (실행되지 않음)
