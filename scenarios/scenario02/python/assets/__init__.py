# assets/__init__.py - Asset 시스템 (scenario02)
#
# 클래스 기반 Asset 구조:
#   Asset (base)
#   ├── Unit
#   │   ├── Character
#   │   └── Object
#   ├── Item
#   └── Location
#
# 사용법:
#   1. Asset 클래스 정의 시 @register_* 데코레이터 사용
#   2. 모듈 import 시 자동으로 registry에 등록됨
#   3. registry.instantiate_*() 로 인스턴스 생성

# 베이스 클래스 export
from assets.base import Asset, Unit, Character, Object, Item, Location

# 레지스트리 함수 export
from assets.registry import (
    # 클래스 등록 데코레이터
    register_item,
    register_object,
    register_character,
    register_location,
    # 클래스 조회
    get_item_class,
    get_object_class,
    get_character_class,
    get_location_class,
    get_all_character_classes,
    get_all_location_classes,
    # 인스턴스 생성
    instantiate_item,
    instantiate_object,
    instantiate_character,
    instantiate_location,
    # ID 조회
    get_instance_id,
    get_unique_id,
    require_instance_id,
    # 유틸리티
    clear,
    get_stats,
)


def load_all_assets():
    """
    모든 Asset 로드 (import로 데코레이터 실행)

    import 순서가 중요:
    1. objects (grounds 포함) - Location에서 참조
    2. items
    3. characters
    4. locations
    """
    from assets import objects      # noqa: F401
    from assets import items        # noqa: F401
    from assets import characters   # noqa: F401
    from assets import locations    # noqa: F401

    stats = get_stats()
    print(f"[assets] Loaded: {stats['items']} items, {stats['objects']} objects, "
          f"{stats['characters']} characters, {stats['locations']} locations")
