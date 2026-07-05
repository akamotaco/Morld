# assets/registry.py — engine.asset_registry 재수출 shim (S03)
#
# U2: 자체 unique_id↔instance_id 사본 → engine 정본으로 단일화.
# engine 쪽은 클래스 레지스트리(@register_item 등) + 인스턴스 맵 + 싱글톤 생성
# (get_or_create_item_id)까지 제공 — S03 자재 아이템은 materials.py에서
# @register_item으로 등록되어 싱글톤 생성이 실제로 동작하게 된다
# (기존 자체 구현은 조회만 가능해 항상 None → 자재 투입 불가였음).
from engine.asset_registry import (  # noqa: F401
    register_item, register_object, register_character, register_location,
    get_item_class, get_object_class, get_character_class, get_location_class,
    get_instance_id, get_unique_id, require_instance_id,
    get_or_create_item_id, clear, reset, get_stats,
    _instance_map, _reverse_map,
)


def register_instance(unique_id, instance_id):
    """unique_id ↔ instance_id 수동 등록 (레거시 호환)"""
    _instance_map[unique_id] = instance_id
    _reverse_map[instance_id] = unique_id
