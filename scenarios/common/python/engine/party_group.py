# party_group.py — 파티(Group) 시스템
#
# JRPG 스타일 단일 파티: 플레이어 고정 리더 + N명 동료
# - 멤버 관리 (추가/제거/조회)
# - 공유 소비 (식량)
# - 실신 처리
#
# 시나리오별 확장은 콜백(set_callbacks)으로 주입.
# 같은 시나리오에서 party_squad와 독립 공존 가능.

import morld

# === 설정 ===
MAX_PARTY_SIZE = 4  # 플레이어 포함

# === 상태 ===
_party_members = []  # [unit_id, ...] 순서 = 편성 순서. [0]은 항상 플레이어

# === 콜백 ===
# 시나리오별 확장 포인트. set_callbacks()로 등록.
_callbacks = {
    "on_initialized": None,      # (player_id) -> None
    "on_member_added": None,     # (unit_id, order_index) -> None
    "on_member_removed": None,   # (unit_id, reason) -> None
    "on_faint": None,            # (unit_id) -> bool (True = 시나리오가 처리함)
}


def reset():
    """챕터 전환 시 리셋 (콜백은 유지)"""
    _party_members.clear()


def set_callbacks(**kwargs):
    """시나리오별 콜백 등록

    사용 가능 키:
        on_initialized(player_id)
        on_member_added(unit_id, order_index)
        on_member_removed(unit_id, reason)
        on_faint(unit_id) -> bool
    """
    for k, v in kwargs.items():
        if k in _callbacks:
            _callbacks[k] = v


# ========================================
# 초기화
# ========================================

def initialize_party(player_id):
    """파티 초기화 (플레이어만)"""
    _party_members.clear()
    _party_members.append(player_id)
    cb = _callbacks["on_initialized"]
    if cb:
        cb(player_id)


# ========================================
# 멤버 관리
# ========================================

def add_member(unit_id):
    """파티원 추가.

    Returns: True 합류 성공, False 정원 초과 or 이미 소속
    """
    if len(_party_members) >= MAX_PARTY_SIZE:
        return False
    if unit_id in _party_members:
        return False

    _party_members.append(unit_id)
    order = len(_party_members) - 1

    cb = _callbacks["on_member_added"]
    if cb:
        cb(unit_id, order)

    name = ""
    info = morld.get_unit_info(unit_id)
    if info:
        name = info.get("name", "")
    print(f"[party_group] Joined: {name} (id={unit_id}, slot={order})")
    return True


def remove_member(unit_id, reason="해제"):
    """파티원 제거.

    Args:
        unit_id: 제거할 멤버
        reason: "해제", "실신", "반란", "도주"
    """
    if unit_id not in _party_members:
        return False

    # 리더(항상 [0])는 제거 불가
    if _party_members and unit_id == _party_members[0]:
        return False

    _party_members.remove(unit_id)

    cb = _callbacks["on_member_removed"]
    if cb:
        cb(unit_id, reason)

    name = ""
    info = morld.get_unit_info(unit_id)
    if info:
        name = info.get("name", "")
    print(f"[party_group] Left: {name} (id={unit_id}, reason={reason})")
    return True


# ========================================
# 조회
# ========================================

def get_members():
    """파티원 목록 (순서대로)"""
    return _party_members.copy()


def get_leader():
    """파티 리더 (항상 [0] = 플레이어)"""
    return _party_members[0] if _party_members else None


def get_size():
    return len(_party_members)


def is_full():
    return len(_party_members) >= MAX_PARTY_SIZE


def is_member(unit_id):
    return unit_id in _party_members


def get_non_leader_members():
    """리더 제외 파티원"""
    return _party_members[1:] if len(_party_members) > 1 else []


# ========================================
# 실신 처리
# ========================================

def handle_faint(unit_id):
    """파티원 실신 처리.

    on_faint 콜백이 True 반환 시 시나리오가 직접 처리.
    아니면 기본 동작: 리더 아닌 멤버 제거.
    """
    if not is_member(unit_id):
        return

    cb = _callbacks["on_faint"]
    if cb and cb(unit_id):
        return  # 시나리오가 처리함

    # 기본: 리더가 아니면 제거
    if unit_id != get_leader():
        remove_member(unit_id, reason="실신")


# ========================================
# 공유 소비
# ========================================

def consume_party_food(food_amount):
    """파티 식량 소비 (공유 식량).

    포만감 80 미만인 멤버에게 1회 30씩 회복.

    Args:
        food_amount: 사용 가능한 식량 수

    Returns:
        실제 소비한 식량 수
    """
    import survival

    consumed = 0
    for mid in _party_members:
        satiety = survival.get_satiety(mid)
        if satiety < 80:
            needed = min(food_amount - consumed, 30)
            if needed > 0:
                survival.set_satiety(mid, min(100, satiety + needed))
                consumed += 1
    return consumed
