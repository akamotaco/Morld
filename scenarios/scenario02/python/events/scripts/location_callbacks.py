# events/scripts/location_callbacks.py - 위치 이벤트 콜백 함수
#
# NOTE: after_collapse 콜백은 front_yard.py의 FrontYardCollapse 이벤트에 통합됨
# 이 파일은 호환성을 위해 유지하지만 새 코드에서는 사용하지 않음

import morld


def _load_chapter_1_npcs():
    """챕터 1에서 NPC들을 인스턴스화"""
    from world import instantiate_npcs
    instantiate_npcs()
