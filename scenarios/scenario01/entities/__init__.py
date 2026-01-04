# entities/__init__.py - 통합 엔티티 로더
"""
Python Entity System의 통합 진입점

C# 시스템에서 다음과 같이 호출:
- proc_all("BaseCharacter", "think", game_time) → ThinkSystem
- proc_all("BaseRegion", "update_weather", game_time) → WeatherSystem
"""

import os
import importlib
from typing import Type, Callable

# 등록된 엔티티 인스턴스 (Base 클래스별로 분류)
_instances: dict[Type, dict[int, object]] = {}


def register_instance(instance):
    """
    엔티티 인스턴스 등록 (Base 클래스별 분류)

    각 인스턴스는 가장 가까운 Base* 클래스 아래에 등록됨
    """
    for base in type(instance).__mro__:
        if base.__name__.startswith("Base") and base.__name__ != "BaseEntity":
            if base not in _instances:
                _instances[base] = {}
            _instances[base][instance.ID] = instance
            return

    # BaseEntity만 상속한 경우
    from entities.base import BaseEntity
    if BaseEntity not in _instances:
        _instances[BaseEntity] = {}
    _instances[BaseEntity][instance.ID] = instance


def unregister_instance(instance):
    """엔티티 인스턴스 등록 해제"""
    for base, instances in _instances.items():
        if instance.ID in instances:
            del instances[instance.ID]
            return


def get_all_by_base(base_class_name: str) -> list:
    """특정 Base 클래스의 모든 인스턴스 반환"""
    for base, instances in _instances.items():
        if base.__name__ == base_class_name:
            return list(instances.values())
    return []


def get_by_id(base_class_name: str, entity_id: int):
    """특정 Base 클래스에서 ID로 인스턴스 조회"""
    for base, instances in _instances.items():
        if base.__name__ == base_class_name:
            return instances.get(entity_id)
    return None


def proc_all(base_class_name: str, method_name: str, *args) -> dict:
    """
    특정 Base 클래스의 모든 인스턴스에 대해 메서드 호출

    Args:
        base_class_name: 대상 Base 클래스 이름 (예: "BaseCharacter")
        method_name: 호출할 메서드 이름 (예: "think")
        *args: 메서드에 전달할 인자

    Returns:
        { entity_id: result, ... } - None이 아닌 결과만 포함
    """
    results = {}
    instances = get_all_by_base(base_class_name)

    for instance in instances:
        method = getattr(instance, method_name, None)
        if method and callable(method):
            try:
                result = method(*args)
                if result is not None:
                    results[instance.ID] = result
            except Exception as e:
                print(f"[entities] Error calling {method_name} on {type(instance).__name__}: {e}")

    return results


def clear_all():
    """모든 등록된 인스턴스 제거"""
    _instances.clear()


# === 로딩 시스템 ===

def discover_all_entities() -> list[tuple[str, str, str]]:
    """
    모든 엔티티 파일 목록 반환 (로드 전)

    Returns:
        [(phase, module_path, display_name), ...]
    """
    entities = []
    base_dir = os.path.dirname(__file__)

    # Phase 순서: world → items → characters → objects
    phases = [
        ("world", "world"),
        ("items", "items"),
        ("characters", "characters"),
        ("objects", "objects"),
    ]

    for phase_name, subdir in phases:
        subdir_path = os.path.join(base_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue

        for filename in os.listdir(subdir_path):
            if filename.endswith('.py') and filename not in ('__init__.py', 'base.py'):
                module_name = filename[:-3]  # .py 제거
                module_path = f"entities.{subdir}.{module_name}"
                display_name = module_name
                entities.append((phase_name, module_path, display_name))

    return entities


def load_entity(module_path: str):
    """
    단일 엔티티 모듈 로드 및 등록

    모듈 내 BaseEntity 서브클래스를 찾아 인스턴스화하고 등록
    """
    from entities.base import BaseEntity

    module = importlib.import_module(module_path)

    # BaseEntity 서브클래스 찾기
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (isinstance(attr, type) and
            issubclass(attr, BaseEntity) and
            attr is not BaseEntity and
            not attr.__name__.startswith("Base")):  # Base* 클래스는 스킵
            # 인스턴스 생성 및 등록
            try:
                instance = attr()
                instance.register()
                register_instance(instance)
            except Exception as e:
                print(f"[entities] Error loading {attr.__name__}: {e}")


def load_all_entities(on_progress: Callable[[int, int, str], None] = None):
    """
    모든 엔티티 로드

    Args:
        on_progress: 진행률 콜백 (current, total, display_name)
    """
    entities = discover_all_entities()
    total = len(entities)

    last_phase = None

    for i, (phase, module_path, display_name) in enumerate(entities):
        # 진행률 콜백
        if on_progress:
            on_progress(i, total, f"{phase}/{display_name}")

        # World 로딩 완료 후 특수 처리
        if last_phase == "world" and phase != "world":
            _post_world_loading()

        # 모듈 로드
        load_entity(module_path)
        last_phase = phase

    # 마지막 phase가 world였다면 처리
    if last_phase == "world":
        _post_world_loading()

    # 완료 콜백
    if on_progress:
        on_progress(total, total, "완료")

    print(f"[entities] Loaded {total} entities")


def _post_world_loading():
    """World 로딩 완료 후 처리 (바닥 오브젝트 생성 등)"""
    # C# 측에서 처리하도록 설계됨
    pass


# === 편의 함수 ===

def get_character(unit_id: int):
    """캐릭터 인스턴스 반환"""
    return get_by_id("BaseCharacter", unit_id)


def get_all_characters() -> list:
    """모든 캐릭터 반환"""
    return get_all_by_base("BaseCharacter")


def get_region(region_id: int):
    """Region 인스턴스 반환"""
    return get_by_id("BaseRegion", region_id)


def get_all_regions() -> list:
    """모든 Region 반환"""
    return get_all_by_base("BaseRegion")


def think_all(game_time: int) -> dict:
    """
    모든 캐릭터의 think() 호출

    Returns:
        { unit_id: command_dict, ... }
    """
    return proc_all("BaseCharacter", "think", game_time)


def get_presence_text(unit_id: int, region_id: int, location_id: int) -> str:
    """특정 캐릭터의 presence text 반환"""
    char = get_character(unit_id)
    if char and hasattr(char, 'get_presence_text'):
        return char.get_presence_text(region_id, location_id)
    return None
