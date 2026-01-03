# objects/__init__.py - 오브젝트 모듈 집합

import morld

from objects.containers import CONTAINERS
from objects.furniture import FURNITURE
from objects.grounds import get_ground_objects

# 모든 오브젝트 데이터
ALL_OBJECTS = CONTAINERS + FURNITURE


def initialize_objects():
    """morld API를 사용하여 모든 오브젝트 데이터 등록"""
    all_obj = ALL_OBJECTS + get_ground_objects()
    for obj_data in all_obj:
        _register_object(obj_data)
    print(f"[objects] {len(all_obj)} objects initialized via morld API")


def _register_object(data):
    """단일 오브젝트 데이터를 morld API로 등록"""
    unit_id = data["id"]
    name = data["name"]
    region_id = data.get("regionId", 0)
    location_id = data.get("locationId", 0)
    unit_type = data.get("type", "object")
    actions = data.get("actions")
    appearance = data.get("appearance")

    # 오브젝트 추가 (type은 항상 "object")
    morld.add_unit(unit_id, name, region_id, location_id, unit_type, actions, appearance, None)


def get_all_objects():
    """모든 오브젝트 데이터 반환 (Python 내부용)"""
    return ALL_OBJECTS + get_ground_objects()


def get_static_objects():
    """정적 오브젝트만 반환 (상자, 가구 등)"""
    return ALL_OBJECTS
