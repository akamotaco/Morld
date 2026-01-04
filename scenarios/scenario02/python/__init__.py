# scenario02 Python 패키지 - 인스턴스 기반 Asset 구조
#
# 폴더 구조:
# - assets/: Asset 클래스 정의 (locations, objects, characters, items)
# - world/: 지형 + 인스턴스화
# - events/: 이벤트 핸들러
# - think/: NPC Agent 시스템

import world
import events

from assets.characters import get_character_event_handler, get_all_presence_texts


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출 (챕터 0 시작)"""
    print("[scenario02] Initializing scenario data via morld API...")

    # 1. 월드 초기화 (지형 + 시간 + Location 인스턴스화)
    world.initialize_world()

    # 2. 플레이어 인스턴스화 (NPC는 챕터 1에서)
    world.instantiate_player()

    print("[scenario02] Scenario data initialization complete!")


def initialize_chapter1():
    """챕터 1 전환 시 호출 - NPC 인스턴스화"""
    world.instantiate_npcs()
    print("[scenario02] Chapter 1: NPCs instantiated")
