# assets/items/__init__.py - 아이템 Asset 모듈

from . import resources
from . import equipment
from . import tools


def register_all():
    """모든 아이템 Asset 등록"""
    resources.register()
    equipment.register()
    tools.register()
    print("[assets.items] All item assets registered")
