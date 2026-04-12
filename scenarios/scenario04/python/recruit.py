# recruit.py — 플레이어가 NPC를 파티원으로 모집
#
# 방향: 플레이어 파티에 NPC 추가 (플레이어가 리더일 때).
# 반대 방향(플레이어가 NPC 파티에 합류)은 party_join.py.
#
# 설계: docs/design.md — 파티 시스템, NPC 모집

import morld
import trust as trust_module
from engine import party_group as _pg


# 결과 코드
RESULT_RECRUITED = "recruited"
RESULT_NO_PLAYER = "no_player"
RESULT_NO_PARTY = "no_party"
RESULT_NOT_LEADER = "not_leader"         # 플레이어가 리더가 아님
RESULT_PARTY_FULL = "party_full"
RESULT_ALREADY = "already_member"
RESULT_SELF = "self"
RESULT_DECLINED = "declined"             # NPC가 거부


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

    # NPC 수락 판정
    if not _judge_accept(npc_id, player_id):
        return {"success": False, "result": RESULT_DECLINED, "npc_id": npc_id}

    # 엔진 compat API: 플레이어 파티에 멤버 추가
    ok = _pg.add_member(npc_id)
    if not ok:
        return {"success": False, "result": RESULT_PARTY_FULL, "npc_id": npc_id}

    return {"success": True, "result": RESULT_RECRUITED, "npc_id": npc_id}


def _judge_accept(npc_id: int, player_id: int) -> bool:
    """NPC가 플레이어 모집 제안을 수락하는지 판정.

    현재: 신뢰도 ≥ 30이면 수락 (기본값이 50이므로 대부분 수락).
    향후 확장: 성향 충돌, 도덕성 차이, 명성 임계.
    """
    return trust_module.get_trust(npc_id) >= 30
