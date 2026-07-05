# party.py — 통합 파티/스쿼드 시스템 (U3, infra-unification §2-1)
#
# 코어: engine/party_group (merge/split/리더 승계/콜백, "솔로도 파티" 원칙,
#       leader-agnostic — 플레이어 없는 시나리오에서도 동작)
# 확장: 이 모듈이 squad 계열(S02 party_squad / S03 squad)의 개념을 흡수:
#   - stance (지휘 자세): retreat/defensive/hold/combat_normal/combat_aggressive
#     (S03 aggression 5단계 = 코어 축. S02 directive의 search/stealth는 모드 플래그)
#   - rank (대열 순번): 1=전위, 2=중위(기본), 3=후위 — 유닛 귀속 (파티 이동에도 유지)
#   - Order (지시): party_squad 풀버전 계승 — 유닛 귀속
#   - request_recruit / request_dismiss: C# MetaActionHandler 단일 진입점
#     (시나리오가 판정 로직을 콜백으로 주입 — 기존 add_member 직결로 인한
#      모집 판정 우회 문제 해소)
#
# follow/FSM 연동(party_squad)은 S02 전용 opt-in으로 유지 — U3c에서 재배선.

import morld

from engine.party_group import (  # noqa: F401 — 코어 재수출
    MAX_PARTY_SIZE, Party,
    create_solo_party, initialize_party,
    get_party, get_party_of, get_all_parties,
    merge, split, transfer_leader, dissolve_party,
    add_member, remove_member, get_members, get_leader, get_size,
    is_full, is_member, get_non_leader_members,
    is_party_leader, is_in_same_party,
    handle_faint, handle_death, ensure_valid_leadership,
    consume_party_food, set_callbacks,
)
from engine import party_group as _pg


# ========================================
# 지휘 자세 (stance) — 파티 단위
# ========================================

STANCE_LEVELS = {
    "retreat":           -2,
    "defensive":         -1,
    "hold":               0,
    "combat_normal":      1,
    "combat_aggressive":  2,
}
# S03 squad 하위호환 별칭
AGGRESSION_LEVELS = STANCE_LEVELS

DEFAULT_STANCE = "hold"

# 모드 플래그 (S02 directive의 비-자세 축: search / stealth 등)
VALID_MODES = {"search", "stealth"}

_party_stance = {}   # party_id → stance str
_party_modes = {}    # party_id → set(modes)


def set_stance(party_id, stance):
    """파티 지휘 자세 설정"""
    if stance not in STANCE_LEVELS:
        return False
    if _pg.get_party(party_id) is None:
        return False
    _party_stance[party_id] = stance
    return True


def get_stance(party_id):
    return _party_stance.get(party_id, DEFAULT_STANCE)


def get_stance_value(party_id):
    """지휘 자세 수치 (-2 ~ +2)"""
    return STANCE_LEVELS.get(get_stance(party_id), 0)


def set_mode(party_id, mode, enabled=True):
    """모드 플래그 설정 (search/stealth)"""
    if mode not in VALID_MODES:
        return False
    modes = _party_modes.setdefault(party_id, set())
    if enabled:
        modes.add(mode)
    else:
        modes.discard(mode)
    return True


def has_mode(party_id, mode):
    return mode in _party_modes.get(party_id, ())


# ========================================
# 대열 순번 (rank) — 유닛 귀속
# ========================================

DEFAULT_RANK = 2  # 중위

_unit_rank = {}   # unit_id → 1~3


def set_member_rank(unit_id, rank):
    """대열 순번 설정 (1=전위, 2=중위, 3=후위)"""
    if rank not in (1, 2, 3):
        return False
    _unit_rank[unit_id] = rank
    return True


def get_member_rank(unit_id):
    """대열 순번 (기본 2=중위)"""
    return _unit_rank.get(unit_id, DEFAULT_RANK)


def clear_member_rank(unit_id):
    _unit_rank.pop(unit_id, None)


# ========================================
# 지시 (Order) — 유닛 귀속 (party_squad 풀버전 계승)
# ========================================

class Order:
    """지휘자 → 파티원 지시

    order_type: "주:부" 형식 (예: "follow:close", "search")
    priority: -1.0 ~ +1.0 / stealth: 0.0 ~ 1.0
    duration_ms: 지속 시간 (None = 무기한)
    """

    def __init__(self, order_type, target=None,
                 priority=0.0, stealth=0.0, duration_ms=None):
        self.order_type = order_type
        self.target = target
        self.priority = priority
        self.stealth = stealth
        self.duration_ms = duration_ms
        self.started_at = None
        self.completed = False

    def main_type(self):
        return self.order_type.split(":")[0]

    def sub_type(self):
        """부타입 (없으면 "*" — 와일드카드, party_squad 원본 시맨틱)"""
        parts = self.order_type.split(":")
        return parts[1] if len(parts) > 1 else "*"

    def is_expired(self, now_ms):
        if self.duration_ms is None or self.started_at is None:
            return False
        return now_ms - self.started_at >= self.duration_ms


_unit_order = {}  # unit_id → Order


def set_order(unit_id, order):
    """유닛 지시 설정"""
    if order.started_at is None:
        try:
            order.started_at = morld.get_game_time()
        except Exception:
            order.started_at = 0
    _unit_order[unit_id] = order
    return True


def get_order(unit_id):
    return _unit_order.get(unit_id)


def clear_order(unit_id):
    _unit_order.pop(unit_id, None)
    return True


# ========================================
# C# 단일 진입점 (MetaActionHandler recruit:/dismiss:)
# ========================================
# 시나리오가 판정 로직(모집 수락/이적/충성 거절 등)을 콜백으로 주입.
# 미주입 시 코어 기본 동작 (플레이어 파티 add/remove).

_recruit_fn = None   # (unit_id) -> bool | dict
_dismiss_fn = None   # (unit_id) -> bool | dict


def set_request_handlers(recruit_fn=None, dismiss_fn=None):
    """시나리오별 모집/해제 판정 핸들러 등록"""
    global _recruit_fn, _dismiss_fn
    if recruit_fn is not None:
        _recruit_fn = recruit_fn
    if dismiss_fn is not None:
        _dismiss_fn = dismiss_fn


def request_recruit(unit_id):
    """모집 요청 — 시나리오 판정 핸들러 경유 (C# 진입점)"""
    if _recruit_fn is not None:
        return _recruit_fn(unit_id)
    return _pg.add_member(unit_id)


def request_dismiss(unit_id):
    """해제 요청 — 시나리오 판정 핸들러 경유 (C# 진입점)"""
    if _dismiss_fn is not None:
        return _dismiss_fn(unit_id)
    return _pg.remove_member(unit_id)


# ========================================
# 리셋 (pi-world reset 계약)
# ========================================

def reset():
    """챕터 전환 시 리셋 (콜백/핸들러는 유지 — party_group과 동일 정책)"""
    _pg.reset()
    _party_stance.clear()
    _party_modes.clear()
    _unit_rank.clear()
    _unit_order.clear()
