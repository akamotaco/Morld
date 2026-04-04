# assets/registry.py - Asset 클래스 레지스트리 (S04)
#
# S02 registry.py 기반. 동일한 패턴 유지.

import morld
from typing import Type, Optional, Dict

# Asset 클래스 저장소: unique_id → Asset 클래스
_item_classes: Dict[str, Type] = {}
_object_classes: Dict[str, Type] = {}
_character_classes: Dict[str, Type] = {}

# Instance 매핑: unique_id → instance_id
_instance_map: Dict[str, int] = {}

# 역방향 매핑: instance_id → unique_id
_reverse_map: Dict[int, str] = {}


# ========================================
# 클래스 등록 데코레이터
# ========================================

def register_item(cls):
    if cls.unique_id:
        _item_classes[cls.unique_id] = cls
    return cls


def register_object(cls):
    if cls.unique_id:
        _object_classes[cls.unique_id] = cls
    return cls


def register_character(cls):
    if cls.unique_id:
        _character_classes[cls.unique_id] = cls
    return cls


# ========================================
# 인스턴스 생성
# ========================================

def instantiate_character(unique_id: str, region_id: int, location_id: int, x: int = 0) -> int:
    """캐릭터 인스턴스 생성 → unit_id 반환"""
    cls = _character_classes.get(unique_id)
    if not cls:
        raise KeyError(f"[registry] Character class not found: {unique_id}")

    unit_id = morld.create_id("character")
    _instance_map[unique_id] = unit_id
    _reverse_map[unit_id] = unique_id

    # C# 측 유닛 생성
    morld.add_character(unit_id, cls.name, region_id, location_id, x)

    # props 적용
    if hasattr(cls, 'props') and cls.props:
        for key, value in cls.props.items():
            morld.set_unit_prop(unit_id, key, value)

    print(f"[registry] Instantiated character: {unique_id} (id={unit_id})")
    return unit_id


def instantiate_object(unique_id: str, region_id: int, location_id: int, x: int = 0) -> int:
    """오브젝트 인스턴스 생성 → unit_id 반환"""
    cls = _object_classes.get(unique_id)
    if not cls:
        raise KeyError(f"[registry] Object class not found: {unique_id}")

    unit_id = morld.create_id("object")
    _instance_map[unique_id] = unit_id
    _reverse_map[unit_id] = unique_id

    morld.add_object(unit_id, cls.name, region_id, location_id, x)

    if hasattr(cls, 'props') and cls.props:
        for key, value in cls.props.items():
            morld.set_unit_prop(unit_id, key, value)

    print(f"[registry] Instantiated object: {unique_id} (id={unit_id})")
    return unit_id


# ========================================
# ID 조회
# ========================================

def get_instance_id(unique_id: str) -> Optional[int]:
    return _instance_map.get(unique_id)


def get_unique_id(instance_id: int) -> Optional[str]:
    return _reverse_map.get(instance_id)


def get_or_create_item_id(unique_id: str) -> Optional[int]:
    existing_id = _instance_map.get(unique_id)
    if existing_id is not None:
        return existing_id

    cls = _item_classes.get(unique_id)
    if not cls:
        print(f"[registry] Item class not found: {unique_id}")
        return None

    new_id = morld.create_id("item")
    _instance_map[unique_id] = new_id
    _reverse_map[new_id] = unique_id

    if hasattr(cls, 'props') and cls.props:
        for key, value in cls.props.items():
            morld.set_item_prop(new_id, key, value)

    print(f"[registry] Created item: {unique_id} (id={new_id})")
    return new_id


# ========================================
# 리셋
# ========================================

def clear():
    _instance_map.clear()
    _reverse_map.clear()
