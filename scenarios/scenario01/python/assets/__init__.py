# assets/__init__.py - Asset 모듈 진입점
#
# 클래스 기반 Asset 시스템
# - 각 Asset은 클래스로 정의
# - instantiate()로 morld에 등록

from assets.base import Asset, Unit, Character, Object, Item, Location

# 레지스트리 함수 export (ID 조회용)
from assets.registry import (
    get_instance_id,
    get_unique_id,
    require_instance_id,
    clear,
    register_instance as register_id_mapping,
)


# ========================================
# 인스턴스 레지스트리 (instance_id → Asset 인스턴스)
# ========================================

_instances = {}


def register_instance(instance_id: int, instance: Asset):
    """인스턴스 등록 (get_focus_text 조회용)"""
    _instances[instance_id] = instance
    # unique_id → instance_id 매핑도 등록
    if hasattr(instance, 'unique_id') and instance.unique_id:
        register_id_mapping(instance.unique_id, instance_id)


def get_instance(instance_id: int) -> Asset:
    """인스턴스 조회"""
    return _instances.get(instance_id)


# ========================================
# Asset 로드 함수 (하위 호환용)
# ========================================

def load_all_assets():
    """
    모든 Asset 클래스 로드

    클래스 기반 시스템에서는 import만으로 클래스가 정의됨.
    이 함수는 하위 호환성을 위해 유지.
    """
    # 각 모듈 import하여 클래스 정의 로드
    from assets import items
    from assets import objects
    from assets import characters
    from assets import locations

    print("[assets] All asset classes loaded")
