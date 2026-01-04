# assets/objects/__init__.py - 오브젝트 Asset 모듈

from . import furniture
from . import outdoor


def register_all():
    """모든 오브젝트 Asset 등록"""
    furniture.register()
    outdoor.register()
    print("[assets.objects] All object assets registered")
