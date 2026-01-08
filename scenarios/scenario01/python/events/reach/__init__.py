# events/reach/__init__.py - 위치 도착 이벤트
#
# 방 탈출 시나리오: 각 방 첫 방문 시 이벤트

from . import bedroom
from . import game_start

__all__ = ['bedroom', 'game_start']
