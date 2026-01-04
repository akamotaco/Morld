# assets/items/__init__.py - 아이템 Asset 모듈

from assets import registry

# 개별 아이템 모듈
from . import keys
from . import golden_key
from . import notes
from . import documents


def register_all():
    """모든 아이템 Asset 등록"""
    keys.register()
    golden_key.register()
    notes.register()
    documents.register()
    print("[assets.items] All item assets registered")
