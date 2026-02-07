# think/trap_agent.py - 덫 시스템
#
# OnTimeElapsed 이벤트 기반 덫 체크
# resource_agent.py와 동일한 패턴
#
# 규칙:
# - check_interval 시간마다 덫 체크
# - 토끼 굴에 rabbit_trap이 있으면 확률 판정
# - 성공 시 rabbit_trap → trapped_rabbit으로 교체
# - 한 번에 하나의 덫만 체크

import random
import morld
MILLIS_PER_MINUTE = 60_000
MILLIS_PER_HOUR = 60 * MILLIS_PER_MINUTE
from assets.objects import get_instance
from assets.registry import get_or_create_item_id

# 순환 참조 방지: subscribe_time_elapsed는 모듈 하단에서 지연 import


# === 토끼 굴 설정 ===
# unique_id: (check_interval, catch_chance)
RABBIT_BURROW_CONFIG = {
    "rabbit_burrow": (360 * MILLIS_PER_MINUTE, 0.4),  # 6시간마다 체크, 40% 확률
}

# 오브젝트별 누적 시간: instance_id -> accumulated_millis
_accumulated_time = {}

# 등록된 토끼 굴: instance_id -> unique_id
_registered_burrows = {}


def register_rabbit_burrow(instance_id: int, unique_id: str):
    """
    토끼 굴 등록 (instantiate 시 호출)

    Args:
        instance_id: 오브젝트 인스턴스 ID
        unique_id: 오브젝트 타입 (rabbit_burrow)
    """
    if unique_id not in RABBIT_BURROW_CONFIG:
        return

    # 첫 등록 시 이벤트 구독
    _ensure_subscribed()

    _registered_burrows[instance_id] = unique_id
    _accumulated_time[instance_id] = 0
    print(f"[trap_agent] Registered: {unique_id} (id={instance_id})")


def unregister_rabbit_burrow(instance_id: int):
    """토끼 굴 등록 해제"""
    if instance_id in _registered_burrows:
        del _registered_burrows[instance_id]
    if instance_id in _accumulated_time:
        del _accumulated_time[instance_id]


def clear_all():
    """모든 등록 정보 초기화 (챕터 전환용)"""
    _registered_burrows.clear()
    _accumulated_time.clear()
    print("[trap_agent] All registrations cleared.")


def _process_trap_check(instance_id: int, millis: int):
    """
    개별 토끼 굴의 덫 체크 처리

    Args:
        instance_id: 오브젝트 인스턴스 ID
        millis: 경과 시간 (밀리초)
    """
    unique_id = _registered_burrows.get(instance_id)
    if not unique_id:
        return

    config = RABBIT_BURROW_CONFIG.get(unique_id)
    if not config:
        return

    check_interval, catch_chance = config

    # 시간 누적
    _accumulated_time[instance_id] += millis

    # check_interval 이상이면 체크
    while _accumulated_time[instance_id] >= check_interval:
        _accumulated_time[instance_id] -= check_interval

        # 덫 체크 실행
        _check_and_convert_trap(instance_id, catch_chance)


def _check_and_convert_trap(instance_id: int, catch_chance: float):
    """
    토끼 굴의 덫을 체크하고, 성공 시 교체

    한 번에 하나의 덫만 체크 (여러 덫이 있어도)
    """
    # 인벤토리 조회
    inventory = morld.get_unit_inventory(instance_id)
    if not inventory:
        return

    # rabbit_trap 찾기
    trap_item_id = None
    for item_id, count in inventory.items():
        item_info = morld.get_item_info(item_id)
        if item_info and item_info.get("unique_id") == "rabbit_trap":
            trap_item_id = int(item_id)
            break

    if trap_item_id is None:
        return  # 덫이 없음

    # 확률 체크
    if random.random() >= catch_chance:
        print(f"[trap_agent] Trap check failed (id={instance_id})")
        return  # 실패

    # 성공! rabbit_trap 제거, trapped_rabbit 추가
    morld.lost_item(instance_id, trap_item_id, 1)

    trapped_id = get_or_create_item_id("trapped_rabbit")
    if trapped_id:
        morld.give_item(instance_id, trapped_id, 1)
        print(f"[trap_agent] Rabbit caught! (burrow={instance_id})")
    else:
        print(f"[trap_agent] Failed to create trapped_rabbit item")


def _on_time_elapsed(millis: int):
    """
    OnTimeElapsed 이벤트 핸들러

    모든 등록된 토끼 굴에 대해 시간 처리
    """
    for instance_id in list(_registered_burrows.keys()):
        _process_trap_check(instance_id, millis)


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
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
    print("[trap_agent] Subscribed to time_elapsed events (hourly)")
