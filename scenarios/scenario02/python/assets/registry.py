# assets/registry.py - Asset 클래스 레지스트리
#
# 클래스 기반 Asset 등록 및 조회

from typing import Type, Optional, Dict

# Asset 클래스 저장소: unique_id → Asset 클래스
_item_classes: Dict[str, Type] = {}
_object_classes: Dict[str, Type] = {}
_character_classes: Dict[str, Type] = {}
_location_classes: Dict[str, Type] = {}

# Instance 매핑: unique_id → instance_id
_instance_map: Dict[str, int] = {}

# 역방향 매핑: instance_id → unique_id
_reverse_map: Dict[int, str] = {}


# ========================================
# 클래스 등록 데코레이터
# ========================================

def register_item(cls):
    """
    아이템 클래스 등록 데코레이터

    equip_slot이 정의되어 있으면 equip_props에 "장착:{slot}:{unique_id}": 1 자동 추가
    """
    if cls.unique_id:
        _item_classes[cls.unique_id] = cls

        # equip_slot → equip_props 자동 추가
        equip_slot = getattr(cls, 'equip_slot', None)
        if equip_slot:
            if cls.equip_props is None:
                cls.equip_props = {}
            slot_key = f"장착:{equip_slot}:{cls.unique_id}"
            cls.equip_props[slot_key] = 1

    return cls


def register_object(cls):
    """오브젝트 클래스 등록 데코레이터"""
    if cls.unique_id:
        _object_classes[cls.unique_id] = cls
    return cls


def register_character(cls):
    """캐릭터 클래스 등록 데코레이터"""
    if cls.unique_id:
        _character_classes[cls.unique_id] = cls
    return cls


def register_location(cls):
    """Location 클래스 등록 데코레이터"""
    if cls.unique_id:
        _location_classes[cls.unique_id] = cls
    return cls


# ========================================
# 클래스 조회
# ========================================

def get_item_class(unique_id: str) -> Optional[Type]:
    """아이템 클래스 조회"""
    return _item_classes.get(unique_id)


def get_object_class(unique_id: str) -> Optional[Type]:
    """오브젝트 클래스 조회"""
    return _object_classes.get(unique_id)


def get_character_class(unique_id: str) -> Optional[Type]:
    """캐릭터 클래스 조회"""
    return _character_classes.get(unique_id)


def get_location_class(unique_id: str) -> Optional[Type]:
    """Location 클래스 조회"""
    return _location_classes.get(unique_id)


def get_all_character_classes() -> Dict[str, Type]:
    """모든 캐릭터 클래스 반환"""
    return _character_classes.copy()


def get_all_location_classes() -> Dict[str, Type]:
    """모든 Location 클래스 반환"""
    return _location_classes.copy()


# ========================================
# 인스턴스 생성 헬퍼
# ========================================

def instantiate_item(unique_id: str, instance_id: int, modify: dict = None) -> int:
    """아이템 인스턴스 생성"""
    cls = get_item_class(unique_id)
    if not cls:
        raise KeyError(f"[registry] Item class not found: {unique_id}")

    _instance_map[unique_id] = instance_id
    _reverse_map[instance_id] = unique_id

    return cls.instantiate(instance_id, modify)


def instantiate_object(unique_id: str, instance_id: int, region_id: int, location_id: int, modify: dict = None) -> int:
    """오브젝트 인스턴스 생성"""
    cls = get_object_class(unique_id)
    if not cls:
        raise KeyError(f"[registry] Object class not found: {unique_id}")

    _instance_map[unique_id] = instance_id
    _reverse_map[instance_id] = unique_id

    return cls.instantiate(instance_id, region_id, location_id, modify)


def instantiate_character(unique_id: str, instance_id: int, region_id: int, location_id: int, modify: dict = None) -> int:
    """캐릭터 인스턴스 생성"""
    cls = get_character_class(unique_id)
    if not cls:
        raise KeyError(f"[registry] Character class not found: {unique_id}")

    _instance_map[unique_id] = instance_id
    _reverse_map[instance_id] = unique_id

    return cls.instantiate(instance_id, region_id, location_id, modify)


def instantiate_location(unique_id: str, location_id: int, region_id: int, ground_instance_id: int = None) -> int:
    """Location 인스턴스 생성"""
    cls = get_location_class(unique_id)
    if not cls:
        raise KeyError(f"[registry] Location class not found: {unique_id}")

    _instance_map[unique_id] = location_id
    _reverse_map[location_id] = unique_id

    return cls.instantiate(location_id, region_id, ground_instance_id)


# ========================================
# ID 조회
# ========================================

def get_instance_id(unique_id: str) -> Optional[int]:
    """unique_id → instance_id (없으면 None)"""
    return _instance_map.get(unique_id)


def get_unique_id(instance_id: int) -> Optional[str]:
    """instance_id → unique_id (없으면 None)"""
    return _reverse_map.get(instance_id)


def require_instance_id(unique_id: str) -> int:
    """unique_id → instance_id (없으면 에러)"""
    iid = _instance_map.get(unique_id)
    if iid is None:
        raise KeyError(f"[registry] No instance for: {unique_id}")
    return iid


# ========================================
# 초기화
# ========================================

def clear():
    """모든 등록 정보 초기화"""
    _item_classes.clear()
    _object_classes.clear()
    _character_classes.clear()
    _location_classes.clear()
    _instance_map.clear()
    _reverse_map.clear()


def get_stats() -> dict:
    """등록 통계 반환"""
    return {
        "items": len(_item_classes),
        "objects": len(_object_classes),
        "characters": len(_character_classes),
        "locations": len(_location_classes),
        "instances": len(_instance_map),
    }
