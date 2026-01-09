# assets/objects/__init__.py - 오브젝트 Asset 모듈

from assets.base import Object

# 오브젝트 클래스 import (장소별 분류)
from .basement import OldBox, PowerPanel
from .storage import Shelf, OldCabinet
from .living_room import Fireplace, SofaCushion
from .kitchen import Refrigerator, Cupboard
from .bedroom import BedUnder, VanityDrawer
from .study import Safe, DeskDrawer
from .corridor import PictureFrame, GrandfatherClock, UmbrellaStand, StudyDoor
from .stairs import BrokenStep, StairWindow
from .entrance import FrontDoor

# 모든 오브젝트 클래스 export
__all__ = [
    'OldBox', 'PowerPanel',
    'Shelf', 'OldCabinet',
    'Fireplace', 'SofaCushion',
    'Refrigerator', 'Cupboard',
    'BedUnder', 'VanityDrawer',
    'Safe', 'DeskDrawer',
    'PictureFrame', 'GrandfatherClock', 'UmbrellaStand', 'StudyDoor',
    'BrokenStep', 'StairWindow',
    'FrontDoor',
]


# ========================================
# 인스턴스 레지스트리 (unique_id → Object 인스턴스)
# ========================================

_instances = {}


def register_instance(unique_id: str, instance: Object):
    """오브젝트 인스턴스 등록"""
    _instances[unique_id] = instance


def get_instance(unique_id: str) -> Object:
    """오브젝트 인스턴스 조회"""
    return _instances.get(unique_id)


# ========================================
# 스크립트 함수 export (script: 액션에서 호출됨)
# Note: 대부분의 오브젝트 스크립트는 call: 액션으로 전환되어
#       인스턴스 메서드로 구현됨. 아래는 script: 액션 유지 항목만.
# ========================================

# entrance.py - 탈출/엔딩 (script: 액션 유지)
from .entrance import escape, show_ending, show_ending_credits
