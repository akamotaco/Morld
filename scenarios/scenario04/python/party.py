# party.py - S04 파티 시스템
#
# JRPG 파티: 최대 4인 (플레이어 포함 = 플레이어 + 3명)
# 파티 상태에서는 일심동체 (이동/행동 공유)
# 이탈/반란 시 파티 강제 해제 후 독립 행동
#
# 욕구 통합: 배고픔/피로 → 파티 단위로 식량 소비
# 인벤토리: 개별 (S02 동일), 지시/교환으로 분배

import morld

# === 상수 ===
MAX_PARTY_SIZE = 4  # 플레이어 포함

# === 상태 ===
_party_members = []  # [unit_id, ...] 순서 = 편성 순서. [0]은 항상 플레이어


def reset():
    """챕터 전환 시 리셋"""
    _party_members.clear()


def initialize_party(player_id: int):
    """파티 초기화 (플레이어만)"""
    _party_members.clear()
    _party_members.append(player_id)
    morld.set_unit_prop(player_id, "파티:소속", 1)
    morld.set_unit_prop(player_id, "파티:순서", 0)


def add_member(unit_id: int) -> bool:
    """
    파티원 추가.

    Returns:
        True: 합류 성공
        False: 정원 초과 or 이미 소속
    """
    if len(_party_members) >= MAX_PARTY_SIZE:
        print(f"[party] Full ({MAX_PARTY_SIZE})")
        return False

    if unit_id in _party_members:
        print(f"[party] Already in party: {unit_id}")
        return False

    _party_members.append(unit_id)
    order = len(_party_members) - 1
    morld.set_unit_prop(unit_id, "파티:소속", 1)
    morld.set_unit_prop(unit_id, "파티:순서", order)

    # 마을 NPC 목록에서 제거
    import npc_generator
    npc_generator.remove_from_village(unit_id)

    # 시스템 등록
    import survival, erosion, morale, trust
    survival.register_character(unit_id)
    erosion.register(unit_id)
    if morale.get_morale(unit_id) == morale.MORALE_DEFAULT:
        morale.set_morale(unit_id, morale.MORALE_DEFAULT)
    if trust.get_trust(unit_id) == trust.TRUST_DEFAULT:
        trust.set_trust(unit_id, trust.TRUST_DEFAULT)

    name = morld.get_unit_info(unit_id).get("name", "???") if morld.get_unit_info(unit_id) else "???"
    print(f"[party] Joined: {name} (id={unit_id}, slot={order})")
    return True


def remove_member(unit_id: int, reason: str = "해제") -> bool:
    """
    파티원 제거.

    Args:
        unit_id: 제거할 멤버
        reason: "해제", "실신", "반란", "도주"
    """
    if unit_id not in _party_members:
        return False

    if unit_id == get_leader():
        print("[party] Cannot remove leader")
        return False

    _party_members.remove(unit_id)
    morld.set_unit_prop(unit_id, "파티:소속", 0)
    morld.set_unit_prop(unit_id, "파티:순서", -1)

    # 순서 재정렬
    for i, mid in enumerate(_party_members):
        morld.set_unit_prop(mid, "파티:순서", i)

    name = morld.get_unit_info(unit_id).get("name", "???") if morld.get_unit_info(unit_id) else "???"
    print(f"[party] Left: {name} (id={unit_id}, reason={reason})")
    return True


def get_members() -> list:
    """파티원 목록 (순서대로)"""
    return _party_members.copy()


def get_leader() -> int:
    """파티 리더 (항상 [0] = 플레이어)"""
    return _party_members[0] if _party_members else None


def get_size() -> int:
    return len(_party_members)


def is_full() -> bool:
    return len(_party_members) >= MAX_PARTY_SIZE


def is_member(unit_id: int) -> bool:
    return unit_id in _party_members


def get_non_leader_members() -> list:
    """리더 제외 파티원"""
    return _party_members[1:] if len(_party_members) > 1 else []


# === 실신 처리 ===

def handle_faint(unit_id: int):
    """
    파티원 실신 처리.
    자동 이탈 + 해당 Location에 잔류.
    플레이어 실신 = 재편성 트리거.
    """
    if not is_member(unit_id):
        return

    if unit_id == get_leader():
        # 플레이어 실신 = 재편성 트리거
        print("[party] Leader fainted! Triggering reorganization...")
        import dungeon
        dungeon.reorganize()
        # 플레이어는 마을 구호소에서 깨어남
        morld.set_unit_location(unit_id, 0, 5, x=50)  # 구호소
        return

    # D 실신 체크 (특수 존재 = 재편성 트리거)
    if morld.get_unit_prop(unit_id, "특수:존재"):
        print(f"[party] Special entity fainted! Triggering reorganization...")
        remove_member(unit_id, reason="실신")
        morld.set_unit_prop(unit_id, "상태:실신", 1)
        import dungeon
        dungeon.reorganize()
        # D는 던전 내 랜덤 재배치 (dungeon.reorganize에서 처리)
        return

    remove_member(unit_id, reason="실신")
    morld.set_unit_prop(unit_id, "상태:실신", 1)


# === 파티 통합 관리 ===

def consume_party_food(food_amount: int) -> int:
    """
    파티 식량 소비 (공유 식량).

    Args:
        food_amount: 사용 가능한 식량

    Returns:
        실제 소비량
    """
    import survival

    consumed = 0
    for mid in _party_members:
        satiety = survival.get_satiety(mid)
        if satiety < 80:  # 80 미만이면 식사
            needed = min(food_amount - consumed, 30)  # 1회 30 회복
            if needed > 0:
                survival.set_satiety(mid, min(100, satiety + needed))
                consumed += 1  # 식량 1개 소비

    return consumed
