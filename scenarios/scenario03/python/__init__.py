# scenario03 Python 패키지
# morld 모듈을 사용하여 직접 게임 시스템에 데이터 등록

from . import world
from . import items
from . import events
from .characters import initialize_characters, get_character_event_handler, get_all_presence_texts
from .objects import initialize_objects


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출"""
    print("[scenario03] Initializing scenario data via morld API...")
    world.initialize_world()
    world.initialize_time()
    items.initialize_items()
    initialize_characters()
    initialize_objects()
    print("[scenario03] Scenario data initialization complete!")
