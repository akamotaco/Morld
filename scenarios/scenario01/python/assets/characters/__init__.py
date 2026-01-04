# assets/characters/__init__.py - 캐릭터 Asset 모듈

from assets import registry

# 개별 캐릭터 모듈
from . import player


def register_all():
    """모든 캐릭터 Asset 등록"""
    player.register()
    print("[assets.characters] All character assets registered")


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
