# think/resource_agent.py - 자원 생성 시스템
#
# OnTimeElapsed 이벤트 기반 자원 생성
# survival.py와 동일한 패턴으로 시간 누적 후 생성
#
# 규칙:
# - spawn_interval 시간마다 1개 생성
# - max_resources 이상이면 시간 누적 없음 (꽉 찬 상태에서 0 유지)
# - 하나 가져가자마자 바로 생성되지 않음
#
# 자원 타입:
# - RESOURCE_CONFIG: 인벤토리 기반 음식 자원 (사과, 산딸기 등)
# - TREE_RESOURCE_CONFIG: props 기반 나무 자원 (통나무, 나뭇가지)

import morld
from assets.objects import get_instance

# 순환 참조 방지: subscribe_time_elapsed는 모듈 하단에서 지연 import


# === 자원 생성 설정 (인벤토리 기반 음식) ===
# unique_id: (spawn_interval, max_resources)
# 포만감 감소: 1시간당 1 (하루 24), 최대 포만감 100 → 약 4일 버팀
RESOURCE_CONFIG = {
    "apple_tree": (720, 3),      # 12시간마다, 최대 3개 (포만감 25)
    "berry_bush": (480, 5),      # 8시간마다, 최대 5개 (포만감 10)
    "mushroom_patch": (600, 4),  # 10시간마다, 최대 4개 (포만감 15)
}

# === 나무 자원 설정 (props 기반) ===
# unique_id: {"log": (interval, max), "branch": (interval, max)}
TREE_RESOURCE_CONFIG = {
    "pine_tree": {"log": (1440, 4), "branch": (480, 6)},      # 통나무 24시간, 가지 8시간
    "oak_tree": {"log": (1440, 5), "branch": (480, 4)},       # 통나무 24시간, 가지 8시간
    "apple_tree": {"log": (1440, 2), "branch": (480, 3)},     # 과일나무 - 자원 적음
}

# 오브젝트별 누적 시간 (인벤토리 기반): instance_id -> accumulated_minutes
_accumulated_time = {}

# 등록된 자원 오브젝트: instance_id -> unique_id
_registered_objects = {}

# 나무 자원용 누적 시간: instance_id -> {"log": minutes, "branch": minutes}
_tree_accumulated_time = {}

# 등록된 나무 오브젝트: instance_id -> unique_id
_registered_trees = {}


def register_resource_object(instance_id: int, unique_id: str):
    """
    자원 오브젝트 등록 (instantiate 시 호출)

    Args:
        instance_id: 오브젝트 인스턴스 ID
        unique_id: 오브젝트 타입 (apple_tree, berry_bush 등)
    """
    if unique_id not in RESOURCE_CONFIG:
        return

    # 첫 등록 시 이벤트 구독
    _ensure_subscribed()

    _registered_objects[instance_id] = unique_id
    _accumulated_time[instance_id] = 0
    print(f"[resource_agent] Registered: {unique_id} (id={instance_id})")


def unregister_resource_object(instance_id: int):
    """자원 오브젝트 등록 해제"""
    if instance_id in _registered_objects:
        del _registered_objects[instance_id]
    if instance_id in _accumulated_time:
        del _accumulated_time[instance_id]


def register_tree_object(instance_id: int, unique_id: str):
    """
    나무 오브젝트 등록 (instantiate 시 호출)

    Args:
        instance_id: 오브젝트 인스턴스 ID
        unique_id: 나무 타입 (pine_tree, oak_tree, apple_tree 등)
    """
    if unique_id not in TREE_RESOURCE_CONFIG:
        return

    # 첫 등록 시 이벤트 구독
    _ensure_subscribed()

    _registered_trees[instance_id] = unique_id
    _tree_accumulated_time[instance_id] = {"log": 0, "branch": 0}
    print(f"[resource_agent] Registered tree: {unique_id} (id={instance_id})")


def unregister_tree_object(instance_id: int):
    """나무 오브젝트 등록 해제"""
    if instance_id in _registered_trees:
        del _registered_trees[instance_id]
    if instance_id in _tree_accumulated_time:
        del _tree_accumulated_time[instance_id]


def clear_all():
    """모든 등록 정보 초기화 (챕터 전환용)"""
    _registered_objects.clear()
    _accumulated_time.clear()
    _registered_trees.clear()
    _tree_accumulated_time.clear()
    print("[resource_agent] All registrations cleared.")


def _process_resource_spawn(instance_id: int, minutes: int):
    """
    개별 오브젝트의 자원 생성 처리

    Args:
        instance_id: 오브젝트 인스턴스 ID
        minutes: 경과 시간 (분)
    """
    unique_id = _registered_objects.get(instance_id)
    if not unique_id:
        return

    config = RESOURCE_CONFIG.get(unique_id)
    if not config:
        return

    spawn_interval, max_resources = config

    # 오브젝트 인스턴스 가져오기
    obj = get_instance(instance_id)
    if obj is None:
        return

    # 현재 자원 개수 확인
    current_count = obj.get_resource_count() if hasattr(obj, 'get_resource_count') else 0

    # 최대 개수에 도달했으면 시간 누적 없음 (0 유지)
    if current_count >= max_resources:
        _accumulated_time[instance_id] = 0
        return

    # 시간 누적
    _accumulated_time[instance_id] += minutes

    # spawn_interval 이상이면 생성
    while _accumulated_time[instance_id] >= spawn_interval:
        _accumulated_time[instance_id] -= spawn_interval

        # 생성 전 다시 개수 체크 (연속 생성 방지)
        current_count = obj.get_resource_count() if hasattr(obj, 'get_resource_count') else 0
        if current_count >= max_resources:
            _accumulated_time[instance_id] = 0
            break

        # 자원 생성
        if hasattr(obj, 'spawn_resource') and obj.spawn_resource():
            print(f"[resource_agent] Spawned resource: {unique_id} (id={instance_id})")


def _process_tree_resource_spawn(instance_id: int, minutes: int):
    """
    나무 오브젝트의 자원(통나무/나뭇가지) 보충 처리

    Args:
        instance_id: 나무 인스턴스 ID
        minutes: 경과 시간 (분)
    """
    unique_id = _registered_trees.get(instance_id)
    if not unique_id:
        return

    config = TREE_RESOURCE_CONFIG.get(unique_id)
    if not config:
        return

    # 오브젝트 인스턴스 가져오기
    obj = get_instance(instance_id)
    if obj is None:
        return

    # 통나무 처리
    if "log" in config:
        spawn_interval, max_count = config["log"]
        current = obj.get_log_count() if hasattr(obj, 'get_log_count') else 0

        if current >= max_count:
            _tree_accumulated_time[instance_id]["log"] = 0
        else:
            _tree_accumulated_time[instance_id]["log"] += minutes

            while _tree_accumulated_time[instance_id]["log"] >= spawn_interval:
                _tree_accumulated_time[instance_id]["log"] -= spawn_interval

                current = obj.get_log_count() if hasattr(obj, 'get_log_count') else 0
                if current >= max_count:
                    _tree_accumulated_time[instance_id]["log"] = 0
                    break

                # 통나무 1개 추가
                if hasattr(obj, 'set_log_count'):
                    obj.set_log_count(current + 1)
                    print(f"[resource_agent] Tree log spawned: {unique_id} (id={instance_id})")

    # 나뭇가지 처리
    if "branch" in config:
        spawn_interval, max_count = config["branch"]
        current = obj.get_branch_count() if hasattr(obj, 'get_branch_count') else 0

        if current >= max_count:
            _tree_accumulated_time[instance_id]["branch"] = 0
        else:
            _tree_accumulated_time[instance_id]["branch"] += minutes

            while _tree_accumulated_time[instance_id]["branch"] >= spawn_interval:
                _tree_accumulated_time[instance_id]["branch"] -= spawn_interval

                current = obj.get_branch_count() if hasattr(obj, 'get_branch_count') else 0
                if current >= max_count:
                    _tree_accumulated_time[instance_id]["branch"] = 0
                    break

                # 나뭇가지 1개 추가
                if hasattr(obj, 'set_branch_count'):
                    obj.set_branch_count(current + 1)
                    print(f"[resource_agent] Tree branch spawned: {unique_id} (id={instance_id})")


def _on_time_elapsed(minutes: int):
    """
    OnTimeElapsed 이벤트 핸들러

    모든 등록된 자원 오브젝트에 대해 시간 처리
    """
    # 인벤토리 기반 자원 (음식)
    for instance_id in list(_registered_objects.keys()):
        _process_resource_spawn(instance_id, minutes)

    # props 기반 나무 자원 (통나무/나뭇가지)
    for instance_id in list(_registered_trees.keys()):
        _process_tree_resource_spawn(instance_id, minutes)


# ========================================
# 이벤트 구독 - 지연 등록 함수
# ========================================
_subscribed = False

def _ensure_subscribed():
    """이벤트 구독 (최초 1회만 실행)"""
    global _subscribed
    if _subscribed:
        return
    _subscribed = True

    from events import subscribe_time_elapsed
    subscribe_time_elapsed(_on_time_elapsed)
    print("[resource_agent] Subscribed to time_elapsed events")


# Note: 이벤트 기반으로 변경되어 Agent 클래스는 더 이상 필요하지 않음
# 자원 오브젝트는 register_resource_object()로 등록하고
# OnTimeElapsed 이벤트로 자동 생성됨
