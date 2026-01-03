# scenario04 Python 패키지

import world
import items
import events
from characters import (
    initialize_characters,
    initialize_player,
    initialize_npcs,
    get_character_event_handler,
    get_all_presence_texts
)
from objects import initialize_objects


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출 (챕터 0 시작)"""
    print("[scenario04] Initializing scenario data via morld API...")
    world.initialize_world()
    world.initialize_time()
    items.initialize_items()
    initialize_player()  # 챕터 0: 플레이어만 등록 (NPC는 챕터 1에서 로드)
    initialize_objects()
    print("[scenario04] Scenario data initialization complete!")
