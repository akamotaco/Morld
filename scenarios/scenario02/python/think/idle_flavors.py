# think/idle_flavors.py - NPC idle flavor 시스템
#
# NPC가 쉬는 시간에 다양한 행동 묘사를 제공.
# flavor는 activity와 별도 키로 관리되어 이름 충돌 없음.
#
# 3-tier 우선순위:
#   Tier 1: 오브젝트 근접 (벽난로 → 불멍)
#   Tier 2: 실내/실외 (창밖구경 vs 하늘구경)
#   Tier 3: 공통 + 아키타입 전용
#
# 사용:
#   _insert_flavored_idle() → pick_idle_flavor() → set_flavor()
#   _build_context() → get_flavor() → context["flavor"]

import random
import morld

# ========================================
# 상태 관리
# ========================================

_current_flavor = {}  # unit_id → flavor_name


def set_flavor(unit_id, flavor):
    """현재 idle flavor 설정"""
    _current_flavor[unit_id] = flavor


def get_flavor(unit_id):
    """현재 idle flavor 조회 (없으면 빈 문자열)"""
    return _current_flavor.get(unit_id, "")


def clear_flavor(unit_id):
    """flavor 클리어 (think 시작 시 호출)"""
    _current_flavor.pop(unit_id, None)


def reset():
    """챕터 전환 시 초기화"""
    _current_flavor.clear()


# ========================================
# Tier 3: 공통 + 아키타입 전용 flavor 풀
# ========================================

_COMMON_IDLE = ["기지개", "앉아쉬기", "스트레칭", "두리번"]

_ARCHETYPE_IDLE = {
    "stoic": ["경계", "명상", "장비점검", "벽기대"],
    "gentle": ["콧노래", "정리", "미소", "차마시기"],
    "timid": ["가만히앉기", "읽기", "기다림"],
    "cold": ["벽기대", "무표정", "시선", "경계"],
    "cheerful": ["콧노래", "장난", "산책구경"],
    "proud": ["자세정리", "시선", "경계"],
}

# ========================================
# Tier 2: 실내/실외 풀
# ========================================

_INDOOR_IDLE = ["창밖구경", "정리"]
_OUTDOOR_IDLE = ["하늘구경", "바람쐬기"]

# ========================================
# Tier 1: 오브젝트 prop 기반
# ========================================

_OBJECT_FLAVORS = {
    "heat:output": ["불멍", "온기"],
    "can:sit": ["앉아쉬기"],
}


# ========================================
# 선택 로직
# ========================================

def pick_idle_flavor(unit_id, base_activity, *,
                     region_id=None, location_id=None,
                     archetype="stoic"):
    """idle flavor를 3-tier 우선순위로 선택하고 set_flavor() 호출.

    Args:
        unit_id: NPC unit ID
        base_activity: 원래 스케줄 활동명 (사용하지 않지만 확장 가능)
        region_id: 현재 region
        location_id: 현재 location
        archetype: NPC 아키타입

    Returns:
        str: 선택된 flavor name
    """
    candidates = []

    # Tier 1: 오브젝트 근접
    if region_id is not None and location_id is not None:
        from assets.objects import get_location_objects
        obj_ids = get_location_objects(region_id, location_id)
        for obj_id in obj_ids:
            for prop_key, flavors in _OBJECT_FLAVORS.items():
                val = morld.get_unit_prop(obj_id, prop_key)
                if val and val > 0:
                    candidates.extend(flavors)

    # Tier 2: 실내/실외
    if region_id is not None and location_id is not None:
        loc_info = morld.get_location_info(region_id, location_id)
        if loc_info:
            if loc_info.get("is_indoor", True):
                candidates.extend(_INDOOR_IDLE)
            else:
                candidates.extend(_OUTDOOR_IDLE)

    # Tier 3: 공통 + 아키타입 전용
    candidates.extend(_COMMON_IDLE)
    candidates.extend(_ARCHETYPE_IDLE.get(archetype, []))

    flavor = random.choice(candidates) if candidates else ""
    if flavor:
        set_flavor(unit_id, flavor)
    return flavor
