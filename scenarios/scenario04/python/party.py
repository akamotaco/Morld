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

import random
import sys
import morld
from engine import party_group as _m
sys.modules[__name__] = _m


# 사망 직전 통행인 구출 이벤트 확률 (0.0 ~ 1.0)
RESCUE_CHANCE = 0.10


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

    # 임시 follow: 신규 멤버를 리더 위치로 즉시 이동 (정식 follow 로직은 추후)
    leader_id = party.get_leader()
    if leader_id != unit_id:
        loc = morld.get_unit_location(leader_id)
        if loc is not None:
            try:
                # get_unit_location 반환 형식 확인: tuple(region, location, x) 가정
                if isinstance(loc, (tuple, list)) and len(loc) >= 2:
                    region, location = loc[0], loc[1]
                    x = loc[2] if len(loc) > 2 else 0
                    morld.set_unit_location(unit_id, region, location, x=x)
            except Exception as e:
                print(f"[party] follow teleport failed for {unit_id}: {e}")

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
    """멤버 이탈 시 prop 정리 + 순서 재정렬 + 리더 자격 검증."""
    # 이탈 당사자 prop 초기화 (파티 소속 여부와 무관하게)
    morld.set_unit_prop(unit_id, "파티:소속", 0)
    morld.set_unit_prop(unit_id, "파티:순서", -1)
    morld.set_unit_prop(unit_id, "파티:리더", 0)

    if party is None or party.get_size() == 0:
        return

    # 순서 재정렬 + 리더 동기화
    for i, mid in enumerate(party.get_members()):
        morld.set_unit_prop(mid, "파티:순서", i)
    _sync_leader_prop(party)

    # 리더 자격 검증 (자격 없는 리더 → 승계, 자격자 없음 → 해산, 초과 → 분리)
    _m.ensure_valid_leadership(party.party_id)


def _leadership_fn(unit_id):
    """리더십 prop 조회 — 미설정 시 0."""
    val = morld.get_unit_prop(unit_id, "리더십")
    return int(val) if val is not None else 0


def _leadership_priority_fn(unit_id):
    """승계 우선순위: 신뢰도 (높을수록 선순위)."""
    try:
        import trust as trust_module
        return trust_module.get_trust(unit_id)
    except ImportError:
        return 0


def _on_dissolved(party_id, reason):
    """파티 해산 콜백 — 로그만 출력 (대사/UI는 차후)."""
    print(f"[party] Party {party_id} dissolved — reason={reason}")


def _on_faint(unit_id, party):
    """실신 처리 — 파티 이탈(split) + 구출 시도 + 타이머 등록.

    모든 캐릭터(플레이어 포함) 실신 → 파티에서 분리.
    플레이어 실신 시: 파티 NPC가 관계성 기반 구출 시도 → 성공 시 구호소.
    구출 실패 또는 NPC 실신 → faint_timer로 타임아웃 → 사망 전환.

    Returns: True (플레이어 파티) / False (몬스터 파티는 기본 처리)
    """
    if not _is_player_party(party):
        return False

    morld.set_unit_prop(unit_id, "상태:실신", 1)

    # 플레이어 실신 → 파티 NPC가 즉시 구출 시도 (성공 시 구호소 이동)
    player_id = morld.get_player_id()
    if unit_id == player_id:
        _try_party_rescue(unit_id, party)

    # 타이머 등록 — 구호소에 있으면 timer가 타임아웃 정지 + 의사 치료 가능
    try:
        import faint_timer
        faint_timer.register(unit_id)
    except ImportError:
        pass

    # 리더 실신 → 솔로 파티로 분리 (엔진 기본 split은 리더 대상 아님)
    if unit_id == party.get_leader():
        _m.split(party.party_id, [unit_id])
        print(f"[party] Leader fainted — split to solo party: {unit_id}")
        return True

    # 일반 파티원 → 엔진 기본 split 경로 사용
    return False


def _try_party_rescue(fainted_id, party):
    """파티 NPC가 실신한 플레이어를 구출. 성공 시 구호소 이동.

    구호소가 없으면 구출 로직 전체 비활성 (마을 발전 전 상태).
    각 생존 NPC가 MAX(신뢰, 복종) 기반 roll. 첫 성공자로 구출.
    """
    import facility
    if not facility.has_infirmary():
        return False

    import trust as trust_module
    import obedience as obedience_module

    for npc_id in party.get_members():
        if npc_id == fainted_id:
            continue
        if morld.get_unit_prop(npc_id, "상태:실신"):
            continue
        affinity = max(
            trust_module.get_trust(npc_id),
            obedience_module.get_obedience(npc_id),
        )
        if random.random() * 100 < affinity:
            morld.set_unit_location(fainted_id, 0, 5, x=50)  # 구호소
            print(f"[party] NPC {npc_id} rescued player {fainted_id} → 구호소")
            return True
    return False


def _on_death(unit_id, party, cause="unknown"):
    """사망 처리 — cause별 분기.

    cause:
      - "neglect": 실신 방치로 타임아웃 → 통행인 구출 roll 발동
      - 그 외 (combat/attack_while_fainted/unknown): 즉시 사망 (구출 불가)

    플레이어 파티 소속이면 재편성 + 광장 이동, 그 외(잔류 NPC)는 MIA 처리.
    """
    is_player_party = _is_player_party(party)
    player_id = morld.get_player_id()
    is_player = (unit_id == player_id)

    # 방치 사망만 통행인 구출 roll (전투/피격 사망은 즉시 사망)
    # 구호소가 없으면 구출 불가능 — 바로 사망 경로.
    import facility
    if cause == "neglect" and facility.has_infirmary() and random.random() < RESCUE_CHANCE:
        morld.set_unit_location(unit_id, 0, 5, x=50)  # 구호소
        # 타이머 재등록 (구호소에 있으니 timeout 없고, 의사 치료 가능)
        try:
            import faint_timer
            faint_timer.register(unit_id)
        except ImportError:
            pass
        print(f"[party] Rescue event! {unit_id} saved by a passerby → 구호소")
        return True

    # 사망 확정 → 타이머 정리
    try:
        import faint_timer
        faint_timer.unregister(unit_id)
    except ImportError:
        pass

    # 사망 확정
    morld.set_unit_prop(unit_id, "상태:사망", 1)
    morld.set_unit_prop(unit_id, "상태:실신", 0)

    # 플레이어 파티 케이스: 재편성 + 생존자 광장 이동
    if is_player_party:
        _m.remove_member(unit_id, reason="사망")
        try:
            import dungeon
            dungeon.reorganize()
        except ImportError:
            pass
        player_party = _m.get_party_of(player_id) if player_id is not None else None
        if player_party is not None:
            for mid in player_party.get_members():
                morld.set_unit_location(mid, 0, 0, x=150)
        return True

    # 그 외(솔로 파티 잔류 NPC 등): MIA 처리 — 파티 해체, 유닛은 그대로 방치
    # (향후: 시체 처리, 아이템 드롭 등)
    if party is not None:
        _m.dissolve_party(party.party_id)
    print(f"[party] NPC {unit_id} died (MIA, cause={cause})")
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
    on_death=_on_death,
    on_leader_changed=_on_leader_changed,
    on_dissolved=_on_dissolved,
    leadership_fn=_leadership_fn,
    leadership_priority_fn=_leadership_priority_fn,
)
