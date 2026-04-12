# party.py - S04 파티 시스템 (engine.party_group wrapper)
#
# 엔진 party_group에 S04 전용 콜백 등록.
# 콜백은 플레이어 파티에만 적용 (몬스터 파티에는 영향 없음).
#
# - 파티:소속/순서/리더 prop 관리
#   · 파티:리더 = 해당 파티의 리더 unit_id
#     (본인 id와 같으면 리더, 다르면 파티원, 없으면 미소속)
# - 마을 NPC 목록 제거
# - survival/erosion/morale/trust 시스템 연동
# - 던전 재편성 트리거

import sys
import morld
from engine import party_group as _m
sys.modules[__name__] = _m


def _is_player_party(party):
    """해당 파티가 플레이어 파티인지 확인"""
    if party is None:
        return False
    player_id = morld.get_player_id()
    return player_id is not None and party.is_member(player_id)


# ========================================
# S04 콜백 정의
# ========================================

def _sync_leader_prop(party):
    """파티 전원에게 '파티:리더' = 리더 unit_id 갱신."""
    leader_id = party.get_leader()
    for mid in party.get_members():
        morld.set_unit_prop(mid, "파티:리더", leader_id)


def _on_initialized(player_id, party):
    """파티 초기화 시 prop 설정"""
    morld.set_unit_prop(player_id, "파티:소속", 1)
    morld.set_unit_prop(player_id, "파티:순서", 0)
    morld.set_unit_prop(player_id, "파티:리더", player_id)


def _on_member_added(unit_id, party):
    """멤버 합류 시 S04 시스템 등록 (플레이어 파티만)"""
    if not _is_player_party(party):
        return

    # 순서 = 파티 내 index
    members = party.get_members()
    order = members.index(unit_id) if unit_id in members else 0
    morld.set_unit_prop(unit_id, "파티:소속", 1)
    morld.set_unit_prop(unit_id, "파티:순서", order)

    # 리더 prop은 파티 전체 갱신 (리더가 바뀌지 않더라도 신규 멤버에게 주입 필요)
    _sync_leader_prop(party)

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


def _on_member_removed(unit_id, party, reason):
    """멤버 이탈 시 prop 정리 + 순서 재정렬 (플레이어 파티만)"""
    if not _is_player_party(party):
        return

    morld.set_unit_prop(unit_id, "파티:소속", 0)
    morld.set_unit_prop(unit_id, "파티:순서", -1)
    morld.set_unit_prop(unit_id, "파티:리더", 0)  # 미소속

    # 순서 재정렬 + 리더 동기화 (리더 승계된 경우 반영)
    for i, mid in enumerate(party.get_members()):
        morld.set_unit_prop(mid, "파티:순서", i)
    _sync_leader_prop(party)


def _on_faint(unit_id, party):
    """실신 처리 — S04 던전 재편성 포함 (플레이어 파티만)

    설계(design.md): 플레이어는 리더/파티원 무관 실신 시 재편성 발동.
    플레이어 외 특수 존재(D 등)도 동일.

    Returns: True (플레이어 파티) / False (몬스터 파티는 기본 처리)
    """
    if not _is_player_party(party):
        return False  # 기본 처리 (remove)

    player_id = morld.get_player_id()

    # 플레이어 실신 → 모드 무관 재편성
    if unit_id == player_id:
        print("[party] Player fainted! Triggering reorganization...")
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

    # 리더(NPC) 실신 — Party.remove()가 자동 리더 승계 (members[0]이 새 리더)
    if unit_id == party.get_leader():
        party.remove(unit_id)
        morld.set_unit_prop(unit_id, "상태:실신", 1)
        new_leader = party.get_leader()
        print(f"[party] Leader NPC fainted — succession: new leader = {new_leader}")
        # 플레이어가 새 리더가 되면 → 경로 4 "리더 승계" 분기
        if new_leader == player_id:
            print("[party] Player has taken leadership (경로 4)")
        return True

    # 일반 파티원 실신
    _m.remove_member(unit_id, reason="실신")
    morld.set_unit_prop(unit_id, "상태:실신", 1)
    return True


# ========================================
# 콜백 등록
# ========================================

def _on_leader_changed(old_leader, new_leader, party):
    """리더 교체 시 파티 전원의 '파티:리더' prop 갱신."""
    if not _is_player_party(party):
        return
    _sync_leader_prop(party)


_m.set_callbacks(
    on_initialized=_on_initialized,
    on_member_added=_on_member_added,
    on_member_removed=_on_member_removed,
    on_faint=_on_faint,
    on_leader_changed=_on_leader_changed,
)
