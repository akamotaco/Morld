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
        # 멀티페이지 다이얼로그: 여러 페이지를 순차 표시
        yield morld.dialog([
            "...어디지, 여기는?",
            "머리가 지끈거린다.\n기억이... 잘 나지 않는다.",
            "일단 이 저택에서 나가야 할 것 같다."
        ])
