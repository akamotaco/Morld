# assets/characters/__init__.py - 캐릭터 Asset 모듈

from assets.base import Character

# 캐릭터 클래스 import
from .player import Player

# 모든 캐릭터 클래스 export
__all__ = ['Player']


# === 시나리오02 호환 인터페이스 ===

def get_character_event_handler(unit_id: int):
    """
    캐릭터 이벤트 핸들러 반환
    시나리오01에는 NPC가 없으므로 항상 None 반환
    """
    return None


def get_all_presence_texts(region_id: int, location_id: int) -> list:
    """
    현재 위치의 모든 캐릭터 presence text 반환
    시나리오01에는 NPC가 없으므로 빈 리스트 반환
    """
    return []
