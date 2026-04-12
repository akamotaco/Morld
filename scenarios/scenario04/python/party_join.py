# party_join.py — 플레이어의 파티 가입 요청
#
# 플레이어가 NPC 파티(리더가 NPC인)에 합류하려 할 때 사용.
# 기존 party_group.add_member()는 "플레이어 파티에 NPC 추가"이므로
# 이 모듈은 반대 방향(NPC 파티에 플레이어 합류)을 담당.
#
# 설계: docs/design.md "플레이어 모드 전환 조건"

import morld
import trust as trust_module
from engine import party_group as _pg


# 결과 코드
RESULT_ACCEPTED = "accepted"
RESULT_NOT_LEADER = "not_leader"       # 대상이 리더가 아님
RESULT_ALREADY_MEMBER = "already_member"
RESULT_FULL = "full"                   # 파티 정원 초과
RESULT_LOW_TRUST = "low_trust"         # 신뢰 부족
RESULT_NO_PLAYER = "no_player"


def request_join(leader_id: int) -> dict:
    """플레이어가 leader_id의 파티에 가입 요청.

    Args:
        leader_id: 대상 파티의 리더 NPC

    Returns:
        {"success": bool, "result": str, "leader_id": int|None}
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return {"success": False, "result": RESULT_NO_PLAYER, "leader_id": None}

    # 대상 파티 확인 (리더가 솔로라면 생성)
    target_party = _pg.get_party_of(leader_id)
    if target_party is None:
        target_party = _pg.create_solo_party(leader_id)

    # 리더 검증
    if target_party.get_leader() != leader_id:
        return {"success": False, "result": RESULT_NOT_LEADER, "leader_id": leader_id}

    # 이미 멤버
    if player_id in target_party.get_members():
        return {"success": False, "result": RESULT_ALREADY_MEMBER, "leader_id": leader_id}

    # 정원 체크 (플레이어가 추가되므로 +1 필요)
    if target_party.is_full():
        return {"success": False, "result": RESULT_FULL, "leader_id": leader_id}

    # 수락 판정 (단순: 리더의 플레이어에 대한 신뢰가 일정 이상)
    accept_result = _judge_acceptance(leader_id, player_id)
    if not accept_result["success"]:
        return {**accept_result, "leader_id": leader_id}

    # 실행: 플레이어 솔로 파티를 리더 파티에 merge
    player_party = _pg.get_party_of(player_id)
    if player_party is None:
        player_party = _pg.create_solo_party(player_id)

    # 자기 자신이 이미 그 파티면 성공 처리
    if player_party.party_id == target_party.party_id:
        return {"success": True, "result": RESULT_ACCEPTED, "leader_id": leader_id}

    ok = _pg.merge(target_party.party_id, player_party.party_id)
    if not ok:
        return {"success": False, "result": RESULT_FULL, "leader_id": leader_id}

    # 플레이어 파티 ID 재정의 — 이제 리더의 파티가 "플레이어 파티"
    _pg._set_player_party_id(target_party.party_id)

    return {"success": True, "result": RESULT_ACCEPTED, "leader_id": leader_id}


def _judge_acceptance(leader_id: int, player_id: int) -> dict:
    """리더가 플레이어를 받아들일지 단순 판정.

    현재: 리더의 플레이어 신뢰도가 30 이상이면 수락.
    향후 확장: 도덕성 차이, 명성, 성향 등.
    """
    leader_trust_to_player = trust_module.get_trust(leader_id)
    if leader_trust_to_player < 30:
        return {"success": False, "result": RESULT_LOW_TRUST}

    return {"success": True, "result": RESULT_ACCEPTED}


def leave_party(reason: str = "자진 이탈") -> bool:
    """플레이어가 현재 파티에서 이탈 (리더가 아닐 때만).

    리더가 플레이어인 경우는 파티 해산(dissolve) 쪽으로 처리해야 함.
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return False

    party = _pg.get_party_of(player_id)
    if party is None:
        return False

    if party.get_leader() == player_id:
        return False  # 리더는 이탈 대신 해산해야 함

    # 플레이어만 떼어내서 솔로 파티로
    new_party = _pg.split(party.party_id, [player_id])
    if new_party is None:
        return False

    _pg._set_player_party_id(new_party.party_id)
    return True
