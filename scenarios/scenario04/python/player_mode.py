# player_mode.py — 플레이어 파티 모드 감지 유틸
#
# 플레이어는 세 가지 모드 중 하나:
#   - solo:   어떤 파티에도 속하지 않음 (또는 솔로 파티)
#   - leader: 파티 리더 (현재 구현에서 플레이어 솔로 파티도 여기 포함)
#   - member: 파티원 (리더는 NPC)
#
# 설계: docs/design.md "플레이어 모드 (리더 vs 파티원)"

import morld
from engine import party_group as _pg


MODE_SOLO = "solo"
MODE_LEADER = "leader"
MODE_MEMBER = "member"


def get_mode() -> str:
    """현재 플레이어 모드 반환."""
    player_id = morld.get_player_id()
    if player_id is None:
        return MODE_SOLO

    party = _pg.get_party_of(player_id)
    if party is None:
        return MODE_SOLO

    if party.get_leader() == player_id:
        # 솔로 파티도 리더로 취급 (멤버 1명)
        return MODE_LEADER

    return MODE_MEMBER


def is_solo() -> bool:
    return get_mode() == MODE_SOLO


def is_leader() -> bool:
    """플레이어가 파티 리더 (솔로 파티 포함)."""
    return get_mode() == MODE_LEADER


def is_member() -> bool:
    """플레이어가 파티원 (리더는 NPC)."""
    return get_mode() == MODE_MEMBER


def get_leader_id() -> int:
    """현재 플레이어가 속한 파티의 리더. 없으면 None."""
    player_id = morld.get_player_id()
    if player_id is None:
        return None
    party = _pg.get_party_of(player_id)
    if party is None:
        return None
    return party.get_leader()


def get_party_size() -> int:
    """플레이어가 속한 파티 크기 (솔로면 1)."""
    player_id = morld.get_player_id()
    if player_id is None:
        return 0
    party = _pg.get_party_of(player_id)
    if party is None:
        return 0
    return party.get_size()
