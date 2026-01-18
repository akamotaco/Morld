# events/reach/quest_check.py - 퀘스트 reach 조건 체크
#
# 플레이어가 위치에 도착할 때마다 진행 중인 퀘스트의 reach 조건을 체크합니다.
# 우선순위를 낮게 설정하여 다른 이벤트 후에 실행됩니다.

from events.base import ReachEvent
from events import registry


@registry.register
class QuestReachCheck(ReachEvent):
    """위치 도착 시 퀘스트 조건 체크"""
    region_id = None  # 모든 region
    location_id = None  # 모든 location
    priority = -100  # 낮은 우선순위 (다른 이벤트 후에 실행)

    def handle(self, region_id, location_id, **ctx):
        from quest import quest_manager
        quest_manager.check_reach_conditions(region_id, location_id)
        # Generator가 아니므로 아무것도 yield하지 않음
        return
        yield  # Generator로 만들기 위한 더미 (실행되지 않음)
