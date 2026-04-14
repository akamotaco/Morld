# recruit.py — 플레이어가 NPC를 파티원으로 모집
#
# 방향: 플레이어 파티에 NPC 추가 (플레이어가 리더일 때).
# 반대 방향(플레이어가 NPC 파티에 합류)은 party_join.py.
#
# 설계: docs/design.md — 파티 시스템, NPC 모집

import random

import morld
import trust as trust_module
from engine import party_group as _pg


# 결과 코드
RESULT_RECRUITED = "recruited"
RESULT_SWITCHED = "switched"             # 타 파티에서 이적
RESULT_NO_PLAYER = "no_player"
RESULT_NO_PARTY = "no_party"
RESULT_NOT_LEADER = "not_leader"         # 플레이어가 리더가 아님
RESULT_PARTY_FULL = "party_full"
RESULT_ALREADY = "already_member"
RESULT_SELF = "self"
RESULT_DECLINED = "declined"             # NPC가 거부 (솔로/여관 NPC)
RESULT_LOYALTY_DECLINED = "loyalty_declined"  # 타 파티 리더에 대한 충성으로 거부


def recruit(npc_id: int) -> dict:
    """NPC에게 파티 합류 제안. 수락되면 플레이어 파티에 추가.

    Args:
        npc_id: 대상 NPC unit_id

    Returns:
        {"success": bool, "result": str, "npc_id": int}
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return {"success": False, "result": RESULT_NO_PLAYER, "npc_id": npc_id}
    if npc_id == player_id:
        return {"success": False, "result": RESULT_SELF, "npc_id": npc_id}

    party = _pg.get_party_of(player_id)
    if party is None:
        return {"success": False, "result": RESULT_NO_PARTY, "npc_id": npc_id}

    if party.get_leader() != player_id:
        return {"success": False, "result": RESULT_NOT_LEADER, "npc_id": npc_id}

    if party.is_full():
        return {"success": False, "result": RESULT_PARTY_FULL, "npc_id": npc_id}

    if npc_id in party.get_members():
        return {"success": False, "result": RESULT_ALREADY, "npc_id": npc_id}

    # 타 파티(솔로 아님) 소속 여부 판단
    npc_party = _pg.get_party_of(npc_id)
    if (npc_party is not None
            and npc_party.get_size() > 1
            and npc_party.get_leader() != player_id):
        return _try_switch(npc_id, player_id)

    # 솔로/무소속: 일반 모집
    if not _judge_accept(npc_id, player_id):
        return {"success": False, "result": RESULT_DECLINED, "npc_id": npc_id}

    ok = _pg.add_member(npc_id)
    if not ok:
        return {"success": False, "result": RESULT_PARTY_FULL, "npc_id": npc_id}

    return {"success": True, "result": RESULT_RECRUITED, "npc_id": npc_id}


def _try_switch(npc_id: int, player_id: int) -> dict:
    """타 파티 소속 NPC에게 이적 제안.

    판정: 플레이어 신뢰도 vs 현 리더 신뢰도 (둘 다 0~100 roll).
      - 플레이어 호응 성공 + 리더 충성 실패 → 이적
      - 그 외 → 충성 거부 (현 파티 유지)

    '리더:신뢰' prop 미설정 시 기본 50 사용 (차후 파티 활동으로 증감).
    """
    trust_to_player = trust_module.get_trust(npc_id)
    leader_trust_raw = morld.get_unit_prop(npc_id, "리더:신뢰")
    trust_to_leader = int(leader_trust_raw) if leader_trust_raw is not None else 50

    player_favor = random.random() * 100 < trust_to_player
    leader_loyalty = random.random() * 100 < trust_to_leader

    if player_favor and not leader_loyalty:
        ok = _pg.add_member(npc_id)  # engine이 split+merge 처리
        if not ok:
            return {"success": False, "result": RESULT_PARTY_FULL, "npc_id": npc_id}
        return {"success": True, "result": RESULT_SWITCHED, "npc_id": npc_id}

    return {"success": False, "result": RESULT_LOYALTY_DECLINED, "npc_id": npc_id}


def _judge_accept(npc_id: int, player_id: int) -> bool:
    """NPC가 플레이어 모집 제안을 수락하는지 판정.

    신뢰도 기반 확률 roll: random(0~100) < 신뢰도 → 수락.
    향후 확장: 성향 충돌, 도덕성 차이, 명성 임계.
    """
    return random.random() * 100 < trust_module.get_trust(npc_id)
