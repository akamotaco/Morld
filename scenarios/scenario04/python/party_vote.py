# party_vote.py — 파티 내 다수결 투표
#
# 던전 분기점, 마을 귀환, 파티 결정 등에서 사용.
#
# 규칙:
#   1) 각 파티원이 옵션에 1표 (플레이어 추종 조건 만족 NPC는 플레이어 투표 복사).
#   2) 다수결 → 최다 득표 옵션.
#   3) 동점 → 리더가 최종 결정 (리더 투표 옵션 중 상위).
#
# 설계: docs/design.md — 플레이어 모드 / 던전 분기
#
# 플레이어 추종은 신뢰도(trust) 기반. 호감/연애는 향후 romance 시스템 연결 시 확장.

import random

import morld
import trust as trust_module
from engine import party_group as _pg


# 플레이어 추종 임계
FOLLOW_TRUST_THRESHOLD = 70


def cast_vote(
    voters: list,
    options: list,
    *,
    player_id: int = None,
    player_choice: str = None,
    npc_choice_fn=None,
) -> dict:
    """파티 투표 집계.

    Args:
        voters: 투표자 unit_id 리스트 (첫 요소가 리더 가정).
        options: 옵션 id 문자열 리스트.
        player_id: 플레이어 unit_id. 없으면 플레이어 추종 로직 비활성.
        player_choice: 플레이어가 택한 옵션. None이면 플레이어는 npc_choice_fn 규칙 따름.
        npc_choice_fn: (voter_id, options) -> 옵션 id. None이면 랜덤.

    Returns:
        {"winner": str, "tallies": {option: count}, "tiebreaker": bool, "votes": {voter_id: option}}
    """
    if not options:
        raise ValueError("options empty")
    if not voters:
        raise ValueError("voters empty")

    npc_choice = npc_choice_fn or _default_npc_choice
    tallies = {opt: 0 for opt in options}
    votes = {}

    for voter_id in voters:
        if voter_id == player_id:
            pick = player_choice if player_choice in options else options[0]
        elif (
            player_id is not None
            and player_choice in options
            and _should_follow_player(voter_id, player_id)
        ):
            pick = player_choice
        else:
            pick = npc_choice(voter_id, options)
            if pick not in options:
                pick = options[0]

        votes[voter_id] = pick
        tallies[pick] += 1

    # 다수결
    max_votes = max(tallies.values())
    winners = [opt for opt, cnt in tallies.items() if cnt == max_votes]

    tiebreaker = False
    if len(winners) == 1:
        winner = winners[0]
    else:
        tiebreaker = True
        # 동점 → 리더 선택 기준
        leader_id = voters[0]
        leader_pick = votes.get(leader_id, winners[0])
        winner = leader_pick if leader_pick in winners else winners[0]

    return {
        "winner": winner,
        "tallies": tallies,
        "tiebreaker": tiebreaker,
        "votes": votes,
    }


def should_follow_player_public(voter_id: int, player_id: int) -> bool:
    """외부 노출용 (테스트/UI에서 "이 NPC는 나를 따를 것" 표시 등)."""
    return _should_follow_player(voter_id, player_id)


def _should_follow_player(voter_id: int, player_id: int) -> bool:
    """NPC가 플레이어의 선택을 따르는지 판정 (신뢰 기반).

    리더는 결정 주체이므로 플레이어를 추종하지 않는다 (플레이어가 멤버인 경우).
    """
    if voter_id == player_id:
        return False

    # 리더는 본인 판단 유지
    voter_party = _pg.get_party_of(voter_id)
    if voter_party is not None and voter_party.get_leader() == voter_id:
        return False

    t = trust_module.get_trust(voter_id)
    return t >= FOLLOW_TRUST_THRESHOLD


def _default_npc_choice(voter_id: int, options: list) -> str:
    """기본 NPC 투표: 랜덤. 실제 게임에서는 성향/맥락 기반 로직으로 교체."""
    return random.choice(options)


# ========================================
# 편의 함수: 파티 투표 실행
# ========================================

def vote_in_player_party(options: list, player_choice: str = None, npc_choice_fn=None) -> dict:
    """현재 플레이어 파티의 구성원으로 투표 실행."""
    player_id = morld.get_player_id()
    if player_id is None:
        raise RuntimeError("no player")
    party = _pg.get_party_of(player_id)
    if party is None:
        raise RuntimeError("player has no party")

    members = party.get_members()
    # 리더가 첫 요소가 되도록 정렬
    leader = party.get_leader()
    ordered = [leader] + [m for m in members if m != leader]

    return cast_vote(
        ordered,
        options,
        player_id=player_id,
        player_choice=player_choice,
        npc_choice_fn=npc_choice_fn,
    )
