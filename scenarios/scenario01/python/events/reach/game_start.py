# events/reach/game_start.py - 게임 시작 이벤트
#
# 게임 시작 시 표시되는 모놀로그

import morld
from events.registry import register
from events.base import GameStartEvent


@register
class GameStart(GameStartEvent):
    """게임 시작 시 - 정신을 차림"""
    once = True
    priority = 100

    def handle(self, **ctx):
        yield morld.dialog("...어디지, 여기는?")
        yield morld.dialog("머리가 지끈거린다.\n기억이... 잘 나지 않는다.")
        yield morld.dialog("일단 이 저택에서 나가야 할 것 같다.")
