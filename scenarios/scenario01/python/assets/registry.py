# assets/registry.py - Asset 클래스 레지스트리 (scenario01)
#
# 간단한 구현: unique_id ↔ instance_id 매핑만 제공

from typing import Optional, Dict

# Instance 매핑: unique_id → instance_id
_instance_map: Dict[str, int] = {}

# 역방향 매핑: instance_id → unique_id
_reverse_map: Dict[int, str] = {}


# ========================================
# 인스턴스 등록
# ========================================

def register_instance(unique_id: str, instance_id: int):
    """인스턴스 등록"""
    _instance_map[unique_id] = instance_id
    _reverse_map[instance_id] = unique_id


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
    _instance_map.clear()
    _reverse_map.clear()
