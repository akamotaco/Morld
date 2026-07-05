# party_squad.py — 분대(Squad) 시스템 (U3c: engine.party 코어 위로 재배선)
#
# U3c (infra-unification §2-1): 멤버십 저장소를 party_group(engine.party 코어)로
# 이전 — S02 분대와 S04 파티가 단일 멤버십 레지스트리를 공유한다.
# 분대 고유 레이어는 유지:
#   - player_directive 7종 (stance/mode로 엔진 미러링)
#   - Order + follow 스케줄 전환 + FSM Standby/Command phase
#   - leader_traits / leader_destination (E3 gate 동기화)
#   - 플레이어 can: props 갱신
# 리더 없는 분대/빈 분대는 편성 중 상태 → 분대 메타데이터로 표현
# (엔진 Party는 항상 리더 보유 — 분대 leader_id는 메타데이터가 정본).
#
# - S02: 플레이어 파티 1개 (플레이어 리더)
# - S03: NPC 분대 × N (NPC 리더) — S03는 scenario03/squad.py shim 사용
#
# rank/Order 저장소는 engine.party의 유닛 귀속 저장소를 사용.

import morld

from engine import party as _party

MILLIS_PER_DAY = 86_400_000

# 분대원 follow 스케줄 (24시간, CommandPhase가 행동 결정)
PARTY_FOLLOW_SCHEDULE = [
    {"name": "따라가기", "action": "follow", "start": 0,
     "end": MILLIS_PER_DAY, "activity": "분대행동"}
]

# Order는 engine.party 정본 재수출 (party_squad.Order 기존 import 경로 호환)
Order = _party.Order


# ========================================
# 데이터 클래스 (engine Party 위의 뷰 + 분대 메타데이터)
# ========================================

class Squad:
    """분대 객체 — 멤버십은 engine Party, 분대 고유 상태는 메타데이터"""

    MAX_MEMBERS = 3  # 리더 제외 최대 멤버 수

    def __init__(self, squad_id):
        self.squad_id = squad_id
        self.party_id = None                # engine Party (유닛 1명 이상일 때 생성)
        self.leader_id = None               # 리더 unit_id (None = 미지정)
        self.player_directive = "auto"      # 7종 지휘 자세
        self.leader_traits = {}             # assign_leader() 시 생성
        self.leader_destination = None      # 리더 이동 목적지 (E3 gate 동기화)

    def _party_units(self):
        if self.party_id is None:
            return []
        p = _party.get_party(self.party_id)
        return p.get_members() if p else []

    @property
    def members(self):
        """리더 제외 멤버 목록"""
        return [u for u in self._party_units() if u != self.leader_id]

    @property
    def orders(self):
        """{unit_id: Order} — engine 유닛 귀속 저장소의 분대 단면 (읽기용)"""
        result = {}
        for uid in self.all_unit_ids():
            order = _party.get_order(uid)
            if order is not None:
                result[uid] = order
        return result

    def all_unit_ids(self):
        """리더 포함 전체 unit_id 목록 (리더가 [0])"""
        ids = self.members
        if self.leader_id is not None:
            ids.insert(0, self.leader_id)
        return ids

    def is_full(self):
        """멤버 정원 초과 여부"""
        return len(self.members) >= self.MAX_MEMBERS


# ========================================
# 모듈 레지스트리 (분대 메타데이터)
# ========================================

_squads = {}            # {squad_id: Squad}
_next_id = 0


def reset():
    """챕터 전환 시 호출 (engine.party 코어 포함)"""
    global _next_id
    _squads.clear()
    _next_id = 0
    _party.reset()


# ========================================
# 내부: engine Party 멤버십 조작
# ========================================

def _units_of(squad_id):
    squad = _squads.get(squad_id)
    return squad._party_units() if squad else []


def _find_squad_of_unit(unit_id):
    for sid, squad in _squads.items():
        if unit_id in squad._party_units():
            return sid
    return None


def _join(target_pid, unit_id):
    """유닛을 대상 파티로 이동 (솔로/타 파티 모두 처리)"""
    up = _party.get_party_of(unit_id)
    if up is None:
        _party.create_solo_party(unit_id)
        up = _party.get_party_of(unit_id)
    if up.party_id == target_pid:
        return False
    if up.get_size() == 1:
        return _party.merge(target_pid, up.party_id)
    new_p = _party.split(up.party_id, [unit_id])
    if new_p is None:
        return _party.merge(target_pid, up.party_id)
    return _party.merge(target_pid, new_p.party_id)


def _leave(squad_id, unit_id):
    """유닛을 분대 파티에서 분리 (솔로 파티로)"""
    squad = _squads.get(squad_id)
    if not squad or squad.party_id is None:
        return False
    p = _party.get_party(squad.party_id)
    if not p or unit_id not in p.get_members():
        return False
    if p.get_size() == 1:
        # 마지막 유닛 — 파티는 유닛의 솔로 파티로 남기고 분대에서 분리
        squad.party_id = None
        return True
    return _party.split(p.party_id, [unit_id]) is not None


def _attach_unit(squad, unit_id):
    """분대에 파티가 없으면 유닛의 (솔로) 파티를 분대 파티로 채택, 있으면 join"""
    if squad.party_id is None:
        p = _party.create_solo_party(unit_id)
        squad.party_id = p.party_id
        _sync_directive_to_engine(squad)
        return True
    return _join(squad.party_id, unit_id)


# ========================================
# B1. 생명주기
# ========================================

def create_squad():
    """빈 분대 생성, squad_id 반환"""
    global _next_id
    squad_id = _next_id
    _next_id += 1
    _squads[squad_id] = Squad(squad_id)
    update_party_props()
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
    if _find_squad_of_unit(leader_id) is not None:
        return False

    old_leader = squad.leader_id
    if not _attach_unit(squad, leader_id):
        return False
    squad.leader_id = leader_id
    _party.transfer_leader(squad.party_id, leader_id)

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
    squad.leader_id = None
    squad.leader_traits = {}
    squad.leader_destination = None
    _leave(squad_id, old_leader)

    on_leader_changed(squad_id, old_leader, None)


def change_leader(squad_id, new_leader_id):
    """리더 교체 (이전 리더 → 멤버, 새 리더(멤버) → 리더)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    old_leader = squad.leader_id

    # 새 리더가 멤버였으면 order 제거, 외부인이면 파티 편입
    if new_leader_id in squad._party_units():
        _party.clear_order(new_leader_id)
    else:
        if not _attach_unit(squad, new_leader_id):
            return False

    # 새 리더 지정 (이전 리더는 파티에 남아 멤버로 전환됨)
    squad.leader_id = new_leader_id
    _party.transfer_leader(squad.party_id, new_leader_id)

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
    """멤버 등록 (FSM push 하지 않음 — 지시 부여 시 push)

    이미 다른 분대 소속이면 기존 분대에서 자동 제거 후 편입.
    같은 분대에 이미 소속이면 False.
    """
    squad = _squads.get(squad_id)
    if not squad:
        return False

    if squad.is_full():
        return False

    # G2: 데이트 중 모집 불가 (상태 변경 전에 체크)
    try:
        from date import is_on_date, get_date_partner
        player_id = morld.get_player_id()
        if player_id and is_on_date(player_id) and get_date_partner(player_id) == unit_id:
            return False
    except ImportError:
        pass

    # 이미 같은 분대 소속 (리더 포함)
    existing_squad_id = _find_squad_of_unit(unit_id)
    if existing_squad_id == squad_id:
        return False

    # 다른 분대 소속 → 자동 제거 후 전환
    if existing_squad_id is not None:
        old_squad = _squads.get(existing_squad_id)
        if old_squad:
            if old_squad.leader_id == unit_id:
                remove_leader(existing_squad_id)
            else:
                remove_member(existing_squad_id, unit_id)

    if not _attach_unit(squad, unit_id):
        return False

    on_member_added(squad_id, unit_id)
    return True


def remove_member(squad_id, unit_id):
    """멤버 제거"""
    squad = _squads.get(squad_id)
    if not squad:
        return False

    if unit_id not in squad.members:
        return False

    if not _leave(squad_id, unit_id):
        return False
    _party.clear_order(unit_id)

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
    squad_id = _find_squad_of_unit(unit_id)
    if squad_id is not None:
        return _squads.get(squad_id)
    return None


def is_in_squad(unit_id):
    """분대 소속 여부"""
    return _find_squad_of_unit(unit_id) is not None


def is_squad_leader(unit_id):
    """리더 여부"""
    squad = get_squad_by_unit(unit_id)
    return squad is not None and squad.leader_id == unit_id


def get_squad_members(squad_id):
    """멤버 목록 (리더 제외)"""
    squad = _squads.get(squad_id)
    return squad.members if squad else []


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

# directive → engine stance/mode 매핑 (infra-unification §2-1)
_DIRECTIVE_TO_STANCE = {
    "auto":              ("hold", set()),
    "wait":              ("hold", set()),
    "search":            ("hold", {"search"}),
    "combat_stealth":    ("combat_normal", {"stealth"}),
    "combat_normal":     ("combat_normal", set()),
    "combat_aggressive": ("combat_aggressive", set()),
    "retreat":           ("retreat", set()),
}


def _sync_directive_to_engine(squad):
    """directive를 engine stance/mode로 미러링 (파티 존재 시)"""
    if squad.party_id is None:
        return
    stance, modes = _DIRECTIVE_TO_STANCE.get(
        squad.player_directive, ("hold", set()))
    _party.set_stance(squad.party_id, stance)
    for m in _party.VALID_MODES:
        _party.set_mode(squad.party_id, m, m in modes)


def set_directive(squad_id, directive):
    """플레이어 지휘 설정 (7종)"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if directive not in VALID_DIRECTIVES:
        return False

    old = squad.player_directive
    squad.player_directive = directive
    _sync_directive_to_engine(squad)
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
    이전 order → 새 order 전환 시 follow 스케줄 정리/설정.
    """
    squad = _squads.get(squad_id)
    if not squad:
        return False
    if unit_id not in squad.members and unit_id != squad.leader_id:
        return False

    old_order = _party.get_order(unit_id)
    old_type = old_order.main_type() if old_order else None
    new_type = order.main_type()

    # follow 스케줄 전환
    if old_type == "follow" and new_type != "follow":
        _stop_follow(unit_id)
    elif old_type != "follow" and new_type == "follow":
        _start_follow(unit_id)

    # started_at 자동 기록 (기존 시맨틱: time_info 없으면 None 유지)
    if order.started_at is None:
        time_info = morld.get_time_info()
        if time_info:
            order.started_at = time_info.get("total_millis", 0)

    _party._unit_order[unit_id] = order  # engine 저장소 직접 기록 (타임스탬프 보존)
    _ensure_party_phases(unit_id)
    return True


def clear_order(squad_id, unit_id):
    """지시 해제"""
    squad = _squads.get(squad_id)
    if not squad:
        return False
    old_order = _party.get_order(unit_id)
    _party.clear_order(unit_id)
    if old_order and old_order.main_type() == "follow":
        _stop_follow(unit_id)
    return True


def get_order(squad_id, unit_id):
    """분대원 지시 조회"""
    squad = _squads.get(squad_id)
    if not squad:
        return None
    if unit_id not in squad._party_units():
        return None
    return _party.get_order(unit_id)


def get_order_for_unit(unit_id):
    """unit_id로 직접 지시 조회 (CommandPhase에서 사용)"""
    squad = get_squad_by_unit(unit_id)
    if not squad:
        return None
    return _party.get_order(unit_id)


# ========================================
# B6. 이벤트 훅
# ========================================

def on_member_added(squad_id, unit_id):
    update_party_props()


def on_member_removed(squad_id, unit_id):
    """멤버 제거 후 일상 복귀 (E4)"""
    _return_to_life(unit_id)
    update_party_props()


def on_leader_changed(squad_id, old_leader_id, new_leader_id):
    update_party_props()


def on_squad_disbanded(squad_id):
    update_party_props()


def on_directive_changed(squad_id, old_directive, new_directive):
    pass


# ========================================
# B7. 플레이어 can: props 갱신
# ========================================

def update_party_props():
    """파티 상태에 따라 플레이어 can: props 갱신

    분대 생성/해산/멤버 추가·제거/리더 변경 시 호출.
    """
    player_id = morld.get_player_id()
    if not player_id:
        return

    squads = get_all_squads()

    # 분대 존재 여부
    has_squad = len(squads) > 0

    # 플레이어 리더 분대 (직접 지시 가능)
    player_leader_squad = None
    # NPC 리더 분대 (지휘 가능)
    npc_leader_squad = None
    # 리더 없는 분대
    leaderless_squad = None
    # 빈자리 있는 분대
    has_vacancy = False

    for sq in squads:
        if sq.leader_id == player_id:
            player_leader_squad = sq
        elif sq.leader_id is not None:
            npc_leader_squad = sq
        else:
            leaderless_squad = sq

        if not sq.is_full():
            has_vacancy = True

    # can: props 갱신
    morld.set_unit_prop(player_id, "can:disband_squad",
                        1 if has_squad else 0)
    morld.set_unit_prop(player_id, "can:assign_leader",
                        1 if leaderless_squad else 0)
    morld.set_unit_prop(player_id, "can:set_directive",
                        1 if npc_leader_squad else 0)
    morld.set_unit_prop(player_id, "can:set_order",
                        1 if player_leader_squad else 0)
    morld.set_unit_prop(player_id, "can:recruit",
                        1 if has_vacancy else 0)


# ========================================
# 내부 유틸
# ========================================

def _start_follow(unit_id):
    """멤버에게 follow 스케줄 push (E1)"""
    agent = _get_agent(unit_id)
    if agent:
        agent.push_schedule(PARTY_FOLLOW_SCHEDULE)


def _stop_follow(unit_id):
    """follow 스케줄 pop (E1)"""
    agent = _get_agent(unit_id)
    if not agent:
        return
    # 스택 최상단이 follow 스케줄인 경우에만 pop
    if len(agent.schedule_stack) > 1:
        top = agent.schedule_stack[-1]
        if top is PARTY_FOLLOW_SCHEDULE:
            agent.pop_schedule()


def _return_to_life(unit_id):
    """분대 이탈 → 일상 복귀 (E4)

    FSM 파티 phase 제거 + follow 스케줄 pop.
    이후 기존 스케줄의 think()가 자연 재개.
    """
    _remove_party_phases(unit_id)
    _stop_follow(unit_id)


# ========================================
# E3. Gate 동기화
# ========================================

def on_leader_move(leader_id, target):
    """리더 cross-location 이동 시 분대에 목적지 기록 (E3)

    movement_mixin._move_to()에서 호출.
    멤버는 다음 think()에서 leader_destination을 감지하여 따라감.
    """
    squad = get_squad_by_unit(leader_id)
    if not squad or squad.leader_id != leader_id:
        return
    squad.leader_destination = {
        "region_id": target["region_id"],
        "location_id": target["location_id"],
    }
    # 멤버들에게 파티 phase 보장 (destination 감지 가능하도록)
    for member_id in squad.members:
        _ensure_party_phases(member_id)


def on_leader_arrived(leader_id):
    """리더 도착 시 목적지 클리어 (E3)

    GateTransitState 최종 도착 시 호출.
    """
    squad = get_squad_by_unit(leader_id)
    if not squad or squad.leader_id != leader_id:
        return
    squad.leader_destination = None


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


# ========================================
# C# 단일 진입점 (engine.party와 동일 인터페이스)
# ========================================
# MetaActionHandler recruit:/dismiss: 액션이 `party.request_recruit(id)` 형식으로
# 호출한다. S02의 party 모듈은 이 모듈의 alias이므로 여기서 제공.

def request_recruit(unit_id):
    """플레이어 리더 분대에 영입 (분대 없으면 생성)"""
    player_id = morld.get_player_id()
    if not player_id:  # player_id 계약: 부재 시 0
        return False
    sq = get_squad_by_unit(player_id)
    if sq is None:
        sid = create_squad()
        if not assign_leader(sid, player_id):
            return False
        sq = get_squad(sid)
    if sq.leader_id != player_id:
        return False
    return add_member(sq.squad_id, unit_id)


def request_dismiss(unit_id):
    """유닛이 속한 분대에서 제거"""
    sq = get_squad_by_unit(unit_id)
    if sq is None:
        return False
    return remove_member(sq.squad_id, unit_id)
