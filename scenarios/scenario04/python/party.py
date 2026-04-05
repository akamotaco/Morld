# party.py - S04 파티 시스템 (engine.party_group wrapper)
#
# 엔진 party_group에 S04 전용 콜백 등록:
# - 파티:소속/순서 prop 관리
# - 마을 NPC 목록 제거
# - survival/erosion/morale/trust 시스템 연동
# - 던전 재편성 트리거

import sys
import morld
from engine import party_group as _m
sys.modules[__name__] = _m


# ========================================
# S04 콜백 정의
# ========================================

def _on_initialized(player_id):
    """파티 초기화 시 prop 설정"""
    morld.set_unit_prop(player_id, "파티:소속", 1)
    morld.set_unit_prop(player_id, "파티:순서", 0)


def _on_member_added(unit_id, order):
    """멤버 합류 시 S04 시스템 등록"""
    morld.set_unit_prop(unit_id, "파티:소속", 1)
    morld.set_unit_prop(unit_id, "파티:순서", order)

    # 마을 NPC 목록에서 제거
    try:
        import npc_generator
        npc_generator.remove_from_village(unit_id)
    except ImportError:
        pass

    # 시스템 등록
    try:
        import survival
        survival.register_character(unit_id)
    except ImportError:
        pass

    try:
        import erosion
        erosion.register(unit_id)
    except ImportError:
        pass

    try:
        import morale
        if morale.get_morale(unit_id) == morale.MORALE_DEFAULT:
            morale.set_morale(unit_id, morale.MORALE_DEFAULT)
    except ImportError:
        pass

    try:
        import trust
        if trust.get_trust(unit_id) == trust.TRUST_DEFAULT:
            trust.set_trust(unit_id, trust.TRUST_DEFAULT)
    except ImportError:
        pass


def _on_member_removed(unit_id, reason):
    """멤버 이탈 시 prop 정리 + 순서 재정렬"""
    morld.set_unit_prop(unit_id, "파티:소속", 0)
    morld.set_unit_prop(unit_id, "파티:순서", -1)

    # 순서 재정렬
    members = _m.get_members()
    for i, mid in enumerate(members):
        morld.set_unit_prop(mid, "파티:순서", i)


def _on_faint(unit_id):
    """실신 처리 — S04 던전 재편성 포함

    Returns: True (항상 S04가 처리)
    """
    leader = _m.get_leader()

    if unit_id == leader:
        # 플레이어 실신 = 재편성 트리거
        print("[party] Leader fainted! Triggering reorganization...")
        try:
            import dungeon
            dungeon.reorganize()
        except ImportError:
            pass
        # 플레이어는 마을 구호소에서 깨어남
        morld.set_unit_location(unit_id, 0, 5, x=50)
        return True

    # 특수 존재 실신 = 재편성 트리거
    if morld.get_unit_prop(unit_id, "특수:존재"):
        print(f"[party] Special entity fainted! Triggering reorganization...")
        _m.remove_member(unit_id, reason="실신")
        morld.set_unit_prop(unit_id, "상태:실신", 1)
        try:
            import dungeon
            dungeon.reorganize()
        except ImportError:
            pass
        return True

    # 일반 멤버 실신
    _m.remove_member(unit_id, reason="실신")
    morld.set_unit_prop(unit_id, "상태:실신", 1)
    return True


# ========================================
# 콜백 등록
# ========================================

_m.set_callbacks(
    on_initialized=_on_initialized,
    on_member_added=_on_member_added,
    on_member_removed=_on_member_removed,
    on_faint=_on_faint,
)
