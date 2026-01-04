# events/scripts/__init__.py - 스크립트 함수 패키지
#
# @morld.register_script 데코레이터로 등록된 콜백 함수들

from . import player_creation
from . import npc_talk
from . import location_callbacks

__all__ = ['player_creation', 'npc_talk', 'location_callbacks']
