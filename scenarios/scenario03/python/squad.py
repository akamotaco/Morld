# squad.py — 분대 시스템 (시나리오03)
#
# party.py (시나리오02) 기반, S03 전용 확장:
# - Rank (대열 순번): 1열(전위), 2열(중위), 3열(후위)
# - Aggression Levels: retreat/defensive/hold/combat_normal/combat_aggressive
# - leader_traits 간소화 (build_leader_traits 없이 props 직접 사용)
# - FSM/follow 스케줄 없음 (데모: 데이터 관리만)

import morld


# ========================================
# 데이터 클래스
# ========================================

class Squad:
    """분대 객체"""

    MAX_MEMBERS = 3  # 리더 제외 최대 멤버 수

    def __init__(self, squad_id):
        self.squad_id = squad_id
        self.leader_id = None
        self.members = []
        self.aggression = "hold"        # 공세 레벨
        self.orders = {}                # {unit_id: Order}
        self.member_attrs = {}          # {unit_id: {"rank": int, ...}}

    def all_unit_ids(self):
        """리더 포함 전체 unit_id 목록"""
        ids = list(self.members)
        if self.leader_id is not None:
            ids.insert(0, self.leader_id)
        return ids

    def is_full(self):
        return len(self.members) >= self.MAX_MEMBERS


class Order:
    """오퍼레이터 → 분대원 지시"""

    def __init__(self, order_type, target=None,
                 priority=0.0, stealth=0.0):
        self.order_type = order_type
        self.target = target
        self.priority = priority
        self.stealth = stealth
        self.completed = False

    def main_type(self):
        return self.order_type.split(":")[0]


# ========================================
# 공세 레벨
# ========================================

AGGRESSION_LEVELS = {
    "retreat":           -2,
    "defensive":         -1,
    "hold":               0,
    "combat_normal":      1,
    "combat_aggressive":  2,
}


# ========================================
# 모듈 레지스트리
# ========================================

_squads = {}        # {squad_id: Squad}
_unit_squad = {}    # {unit_id: squad_id}
_next_id = 0


def reset():
    global _next_id
    _squads.clear()
    _unit_squad.clear()
    _next_id = 0


# ========================================
# 생명주기
# ========================================

def create_squad():
    """빈 분대 생성, squad_id 반환"""
    global _next_id
    squad_id = _next_id
    _next_id += 1
    _squads[squad_id] = Squad(squad_id)
    return squad_id


def disband_squad(squad_id):
    """분대 해산"""
    squad = _squads.get(squad_id)
    if not squad:
        return

    for unit_id in list(squad.members):
        remove_member(squad_id, unit_id)

    if squad.leader_id is not None:
        _unit_squad.pop(squad.leader_id, None)

    del _squads[squad_id]


# ========================================
# 리더 관리
# ========================================

def assign_leader(squad_id, leader_id):
    """리더 지정"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    if leader_id in _unit_squad:
        return False

    squad.leader_id = leader_id
    _unit_squad[leader_id] = squad_id
    _ensure_attrs(squad, leader_id)
    return True


def remove_leader(squad_id):
    """리더 해제"""
    squad = _squads.get(squad_id)
    if not squad or squad.leader_id is None:
        return
    _unit_squad.pop(squad.leader_id, None)
    squad.member_attrs.pop(squad.leader_id, None)
    squad.leader_id = None


def change_leader(squad_id, new_leader_id):
    """리더 교체 (이전 리더 → 멤버, 새 리더(멤버) → 리더)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    old_leader = squad.leader_id

    if new_leader_id in squad.members:
        squad.members.remove(new_leader_id)
        _unit_squad.pop(new_leader_id, None)
        squad.orders.pop(new_leader_id, None)

    if old_leader is not None:
        _unit_squad.pop(old_leader, None)
        squad.leader_id = None
        squad.members.append(old_leader)
        _unit_squad[old_leader] = squad_id

    squad.leader_id = new_leader_id
    _unit_squad[new_leader_id] = squad_id
    _ensure_attrs(squad, new_leader_id)
    return True


# ========================================
# 멤버 관리
# ========================================

def add_member(squad_id, unit_id):
    """멤버 등록"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if squad.is_full():
        return False

    existing = _unit_squad.get(unit_id)
    if existing == squad_id:
        return False

    if existing is not None:
        old_squad = _squads.get(existing)
        if old_squad:
            if old_squad.leader_id == unit_id:
                remove_leader(existing)
            else:
                remove_member(existing, unit_id)

    squad.members.append(unit_id)
    _unit_squad[unit_id] = squad_id
    _ensure_attrs(squad, unit_id)
    return True


def remove_member(squad_id, unit_id):
    """멤버 제거"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if unit_id not in squad.members:
        return False

    squad.members.remove(unit_id)
    _unit_squad.pop(unit_id, None)
    squad.orders.pop(unit_id, None)
    squad.member_attrs.pop(unit_id, None)
    return True


# ========================================
# 조회
# ========================================

def get_squad(squad_id):
    return _squads.get(squad_id)


def get_squad_by_unit(unit_id):
    squad_id = _unit_squad.get(unit_id)
    if squad_id is not None:
        return _squads.get(squad_id)
    return None


def is_in_squad(unit_id):
    return unit_id in _unit_squad


def is_squad_leader(unit_id):
    squad = get_squad_by_unit(unit_id)
    return squad is not None and squad.leader_id == unit_id


def get_squad_members(squad_id):
    squad = _squads.get(squad_id)
    return list(squad.members) if squad else []


def get_all_unit_ids(squad_id):
    squad = _squads.get(squad_id)
    return squad.all_unit_ids() if squad else []


def get_all_squads():
    return list(_squads.values())


# ========================================
# 공세 레벨 (Aggression)
# ========================================

def set_aggression(squad_id, level):
    """공세 레벨 설정"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if level not in AGGRESSION_LEVELS:
        return False
    squad.aggression = level
    return True


def get_aggression(squad_id):
    squad = _squads.get(squad_id)
    return squad.aggression if squad else None


def get_aggression_value(squad_id):
    """공세 레벨 수치 반환 (-2 ~ +2)"""
    level = get_aggression(squad_id)
    return AGGRESSION_LEVELS.get(level, 0)


# ========================================
# 대열 순번 (Rank)
# ========================================

def set_member_rank(squad_id, unit_id, rank):
    """대열 순번 설정 (1=전위, 2=중위, 3=후위)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if unit_id not in squad.members and unit_id != squad.leader_id:
        return False
    if rank not in (1, 2, 3):
        return False
    _ensure_attrs(squad, unit_id)
    squad.member_attrs[unit_id]["rank"] = rank
    return True


def get_member_rank(squad_id, unit_id):
    """대열 순번 조회 (기본값: 2=중위)"""
    squad = _squads.get(squad_id)
    if not squad:
        return 2
    attrs = squad.member_attrs.get(unit_id, {})
    return attrs.get("rank", 2)


# ========================================
# 지시 (Order)
# ========================================

def set_order(squad_id, unit_id, order):
    """분대원 지시 설정"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if unit_id not in squad.members and unit_id != squad.leader_id:
        return False
    squad.orders[unit_id] = order
    return True


def clear_order(squad_id, unit_id):
    """지시 해제"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    squad.orders.pop(unit_id, None)
    return True


def get_order(squad_id, unit_id):
    squad = _squads.get(squad_id)
    if not squad:
        return None
    return squad.orders.get(unit_id)


# ========================================
# 내부 유틸
# ========================================

def _ensure_attrs(squad, unit_id):
    """member_attrs 초기화"""
    if unit_id not in squad.member_attrs:
        squad.member_attrs[unit_id] = {"rank": 2}
