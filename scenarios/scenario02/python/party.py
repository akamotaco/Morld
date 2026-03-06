# party.py — 파티(분대) 시스템
#
# Squad/Order 데이터 구조 + 레지스트리 + 생명주기/멤버/지시 API
# - S02: 플레이어 파티 1개 (플레이어 리더)
# - S03: NPC 분대 × N (NPC 리더)
# - 구조적으로 동일, 데이터 레이어에서 분대 수 제한 없음

import morld

# ========================================
# 데이터 클래스
# ========================================

class Squad:
    """분대 객체"""

    MAX_MEMBERS = 3  # 리더 제외 최대 멤버 수

    def __init__(self, squad_id):
        self.squad_id = squad_id
        self.leader_id = None               # 리더 unit_id (None = 미지정)
        self.members = []                   # [unit_id, ...] 리더 제외
        self.player_directive = "auto"      # 7종 지휘 자세
        self.orders = {}                    # {unit_id: Order}
        self.leader_traits = {}             # assign_leader() 시 생성
        self.leader_destination = None      # 리더 이동 목적지 (E3 gate 동기화)

    def all_unit_ids(self):
        """리더 포함 전체 unit_id 목록"""
        ids = list(self.members)
        if self.leader_id is not None:
            ids.insert(0, self.leader_id)
        return ids

    def is_full(self):
        """멤버 정원 초과 여부"""
        return len(self.members) >= self.MAX_MEMBERS


class Order:
    """분대장 → 분대원 지시"""

    def __init__(self, order_type, target=None,
                 priority=0.0, stealth=0.0):
        self.order_type = order_type    # "주타입" 또는 "주타입:부타입"
        self.target = target            # {region_id, location_id} 또는 None
        self.priority = priority        # -1.0 아이템 수집 ↔ +1.0 적 퇴치
        self.stealth = stealth          # 0.0 노출 ↔ 1.0 은밀

    def main_type(self):
        return self.order_type.split(":")[0]

    def sub_type(self):
        parts = self.order_type.split(":")
        return parts[1] if len(parts) > 1 else "*"

    def __repr__(self):
        return f"<Order({self.order_type}, priority={self.priority}, stealth={self.stealth})>"


# ========================================
# 모듈 레지스트리
# ========================================

_squads = {}            # {squad_id: Squad}
_unit_squad = {}        # {unit_id: squad_id} 역참조 (리더+멤버 모두)
_next_id = 0


def reset():
    """챕터 전환 시 호출"""
    global _next_id
    _squads.clear()
    _unit_squad.clear()
    _next_id = 0


# ========================================
# B1. 생명주기
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

    # 멤버 정리 (복사본으로 순회)
    for unit_id in list(squad.members):
        remove_member(squad_id, unit_id)

    # 리더 해제
    if squad.leader_id is not None:
        remove_leader(squad_id)

    del _squads[squad_id]
    on_squad_disbanded(squad_id)


# ========================================
# B2. 리더 관리
# ========================================

def assign_leader(squad_id, leader_id):
    """리더 지정"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    # 이미 다른 분대 소속이면 실패
    if leader_id in _unit_squad:
        return False

    old_leader = squad.leader_id
    squad.leader_id = leader_id
    _unit_squad[leader_id] = squad_id

    # leader_traits 생성
    from think.party_config import build_leader_traits
    unique_id = _get_unique_id(leader_id)
    squad.leader_traits = build_leader_traits(unique_id)

    on_leader_changed(squad_id, old_leader, leader_id)
    return True


def remove_leader(squad_id):
    """리더 해제"""
    squad = _squads.get(squad_id)
    if not squad or squad.leader_id is None:
        return

    old_leader = squad.leader_id
    _unit_squad.pop(old_leader, None)
    squad.leader_id = None
    squad.leader_traits = {}
    squad.leader_destination = None

    on_leader_changed(squad_id, old_leader, None)


def change_leader(squad_id, new_leader_id):
    """리더 교체 (이전 리더 → 멤버, 새 리더(멤버) → 리더)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    old_leader = squad.leader_id

    # 새 리더가 멤버였으면 멤버에서 제거
    if new_leader_id in squad.members:
        squad.members.remove(new_leader_id)
        _unit_squad.pop(new_leader_id, None)
        # orders 제거
        squad.orders.pop(new_leader_id, None)

    # 이전 리더를 멤버로 전환
    if old_leader is not None:
        _unit_squad.pop(old_leader, None)
        squad.leader_id = None
        # 이전 리더를 멤버로 추가
        squad.members.append(old_leader)
        _unit_squad[old_leader] = squad_id

    # 새 리더 지정
    squad.leader_id = new_leader_id
    _unit_squad[new_leader_id] = squad_id

    # leader_traits 전체 교체
    from think.party_config import build_leader_traits
    unique_id = _get_unique_id(new_leader_id)
    squad.leader_traits = build_leader_traits(unique_id)

    on_leader_changed(squad_id, old_leader, new_leader_id)
    return True


# ========================================
# B3. 멤버 관리
# ========================================

def add_member(squad_id, unit_id):
    """멤버 등록 (FSM push 하지 않음 — 지시 부여 시 push)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    if squad.is_full():
        return False

    if unit_id in _unit_squad:
        return False  # 이미 다른 분대 소속

    squad.members.append(unit_id)
    _unit_squad[unit_id] = squad_id

    on_member_added(squad_id, unit_id)
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

    on_member_removed(squad_id, unit_id)
    return True


# ========================================
# B4. 조회
# ========================================

def get_squad(squad_id):
    """분대 조회"""
    return _squads.get(squad_id)


def get_squad_by_unit(unit_id):
    """unit_id로 소속 분대 조회 (리더/멤버 모두)"""
    squad_id = _unit_squad.get(unit_id)
    if squad_id is not None:
        return _squads.get(squad_id)
    return None


def is_in_squad(unit_id):
    """분대 소속 여부"""
    return unit_id in _unit_squad


def is_squad_leader(unit_id):
    """리더 여부"""
    squad = get_squad_by_unit(unit_id)
    return squad is not None and squad.leader_id == unit_id


def get_squad_members(squad_id):
    """멤버 목록 (리더 제외)"""
    squad = _squads.get(squad_id)
    return list(squad.members) if squad else []


def get_all_unit_ids(squad_id):
    """리더 포함 전체 unit_id 목록"""
    squad = _squads.get(squad_id)
    return squad.all_unit_ids() if squad else []


def get_all_squads():
    """전체 분대 목록"""
    return list(_squads.values())


# ========================================
# B5. 지휘/지시
# ========================================

VALID_DIRECTIVES = {
    "auto", "search", "combat_stealth", "combat_normal",
    "combat_aggressive", "retreat", "wait",
}


def set_directive(squad_id, directive):
    """플레이어 지휘 설정 (7종)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if directive not in VALID_DIRECTIVES:
        return False

    old = squad.player_directive
    squad.player_directive = directive
    on_directive_changed(squad_id, old, directive)
    return True


def get_directive(squad_id):
    """현재 지휘 자세 조회"""
    squad = _squads.get(squad_id)
    return squad.player_directive if squad else None


def set_order(squad_id, unit_id, order):
    """분대원 지시 설정

    FSM에 StandbyPhase/CommandPhase가 없으면 push.
    이미 있으면 데이터만 갱신 (다음 think()에서 반영).
    """
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if unit_id not in squad.members and unit_id != squad.leader_id:
        return False

    squad.orders[unit_id] = order
    _ensure_party_phases(unit_id)
    return True


def clear_order(squad_id, unit_id):
    """지시 해제"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    squad.orders.pop(unit_id, None)
    return True


def get_order(squad_id, unit_id):
    """분대원 지시 조회"""
    squad = _squads.get(squad_id)
    if not squad:
        return None
    return squad.orders.get(unit_id)


def get_order_for_unit(unit_id):
    """unit_id로 직접 지시 조회 (CommandPhase에서 사용)"""
    squad = get_squad_by_unit(unit_id)
    if not squad:
        return None
    return squad.orders.get(unit_id)


# ========================================
# B6. 이벤트 훅 (향후 확장)
# ========================================

def on_member_added(squad_id, unit_id):
    pass


def on_member_removed(squad_id, unit_id):
    """멤버 제거 후 FSM 정리"""
    _remove_party_phases(unit_id)


def on_leader_changed(squad_id, old_leader_id, new_leader_id):
    pass


def on_squad_disbanded(squad_id):
    pass


def on_directive_changed(squad_id, old_directive, new_directive):
    pass


# ========================================
# 내부 유틸
# ========================================

def _get_unique_id(unit_id):
    """unit_id → unique_id 변환"""
    info = morld.get_unit_info(unit_id)
    if info:
        uid = info.get("unique_id")
        if uid:
            return uid
        return info.get("name", "")
    # fallback: props에서 조회
    props = morld.get_unit_props(unit_id)
    if props:
        return props.get("unique_id", "")
    return ""


def _get_agent(unit_id):
    """think 레지스트리에서 agent 조회 (없으면 None)"""
    try:
        from think.registry import get_agent
        return get_agent(unit_id)
    except ImportError:
        return None


def _ensure_party_phases(unit_id):
    """FSM에 StandbyPhase/CommandPhase가 없으면 push"""
    agent = _get_agent(unit_id)
    if not agent:
        return

    has_standby = any(s.state_type == "standby" for s in agent._fsm_stack)
    has_command = any(s.state_type == "command" for s in agent._fsm_stack)

    if not has_standby:
        from think.fsm import StandbyPhase
        agent._fsm_push(StandbyPhase())

    if not has_command:
        from think.fsm import CommandPhase
        agent._fsm_push(CommandPhase())


def _remove_party_phases(unit_id):
    """FSM에서 Command/Standby phase 제거"""
    agent = _get_agent(unit_id)
    if not agent:
        return

    agent._fsm_pop_by_type("command")
    agent._fsm_pop_by_type("standby")
