# scenario01 Python 패키지 - 방 탈출 시나리오

import world
import items
import events
from objects import initialize_objects, initialize_player


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출"""
    print("[scenario01] Initializing escape room scenario via morld API...")
    world.initialize_world()
    world.initialize_time()
    items.initialize_items()
    initialize_player()
    initialize_objects()
    print("[scenario01] Scenario data initialization complete!")
