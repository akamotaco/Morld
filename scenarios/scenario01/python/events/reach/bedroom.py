# events/reach/bedroom.py - 침실 도착 이벤트
#
# 침실 첫 방문 시 알 수 없는 목소리

import morld
from events.registry import register
from events.base import ReachEvent


@register
class BedroomFirstVisit(ReachEvent):
    """침실 첫 방문 - 알 수 없는 목소리"""
    region_id = 0
    location_id = 6
    once = True
    priority = 10

    def handle(self, **ctx):
        yield morld.dialog("...어디선가 희미한 소리가 들린다.")
        yield morld.dialog("\"...나...가...\"")
        yield morld.dialog("목소리가 사라졌다.\n환청이었을까?")
