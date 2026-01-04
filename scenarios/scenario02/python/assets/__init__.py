# assets/__init__.py - Asset 시스템 (scenario02)
#
# 인스턴스 기반 Asset 구조:
#   Asset (base)
#   ├── Unit
#   │   ├── Character
#   │   └── Object
#   ├── Item
#   └── Location
#
# 사용법:
#   loc = BackYard()
#   loc.instantiate(12, REGION_ID)
#   loc.add_item_to_ground(herb)

# 베이스 클래스 export
from assets.base import Asset, Unit, Character, Object, Item, Location

# 레지스트리 함수 export (ID 조회용)
from assets.registry import (
    get_instance_id,
    get_unique_id,
    require_instance_id,
    clear,
)
