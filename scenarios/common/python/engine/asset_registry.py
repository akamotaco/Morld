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
    """아이템 클래스 등록 데코레이터"""
    if cls.unique_id:
        _item_classes[cls.unique_id] = cls
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


def get_or_create_item_id(unique_id: str) -> Optional[int]:
    """
    아이템 싱글톤 ID 조회 또는 생성

    같은 unique_id의 아이템은 항상 같은 instance_id를 반환하여
    인벤토리에서 하나의 슬롯에 쌓이도록 보장합니다.

    Args:
        unique_id: 아이템 unique_id (예: "log", "plank")

    Returns:
        instance_id (int) 또는 None (클래스가 없는 경우)
    """
    import morld

    # 1. registry에서 기존 인스턴스 확인
    existing_id = _instance_map.get(unique_id)
    if existing_id is not None:
        return existing_id

    # 2. 없으면 새로 생성
    cls = get_item_class(unique_id)
    if not cls:
        print(f"[registry] Item class not found: {unique_id}")
        return None

    # 새 ID 생성 및 인스턴스화
    new_id = morld.create_id("item")
    item = cls()
    item.instantiate(new_id)

    # registry에 등록 (instantiate에서 안 했을 경우 대비)
    _instance_map[unique_id] = new_id
    _reverse_map[new_id] = unique_id

    print(f"[registry] Created item singleton: {unique_id} (id={new_id})")
    return new_id


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


def reset():
    """챕터 전환 시 리셋 (clear와 동일 — 엔진 공통 인터페이스)"""
    clear()


def get_stats() -> dict:
    """등록 통계 반환"""
    return {
        "items": len(_item_classes),
        "objects": len(_object_classes),
        "characters": len(_character_classes),
        "locations": len(_location_classes),
        "instances": len(_instance_map),
    }
