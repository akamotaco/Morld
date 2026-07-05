# squad.py — engine.party 기반 shim (시나리오03, U3)
#
# 과거: party.py(S02)에서 FSM을 걷어낸 독립 축소 사본 (엔진 미편입).
# U3 (infra-unification §2-1): 분대 = engine.party의 Party 인스턴스로 단일화.
#   - rank/Order는 엔진 유닛 귀속 저장소 사용
#   - aggression = 엔진 stance 축 (파티 존재 시 미러링)
#   - 리더 없는 분대/빈 분대는 S03 편성 UX 전용 개념 → shim 메타데이터로 유지
#     (엔진 Party는 항상 리더 보유 — 분대 leader_id는 메타데이터가 정본)
# 기존 공개 API/시맨틱은 유지 (squad_id 기반 시그니처).

import morld  # noqa: F401 (기존 import 경로 호환)

from engine import party as _party

# 하위호환 별칭
AGGRESSION_LEVELS = _party.AGGRESSION_LEVELS
Order = _party.Order


# ========================================
# 모듈 상태 (squad 메타데이터)
# ========================================

# squad_id → {"party_id": int|None, "leader_id": int|None,
#             "stance": str, "view": Squad}
_squads = {}
_next_id = 0


def reset():
    global _next_id
    _squads.clear()
    _next_id = 0
    _party.reset()


# ========================================
# Squad 뷰 (기존 코드가 접근하는 속성 인터페이스)
# ========================================

class Squad:
    """분대 뷰 — engine Party 위의 읽기 인터페이스"""

    MAX_MEMBERS = 3  # 리더 제외 최대 멤버 수

    def __init__(self, squad_id):
        self.squad_id = squad_id

    @property
    def leader_id(self):
        meta = _squads.get(self.squad_id)
        return meta["leader_id"] if meta else None

    @property
    def members(self):
        """리더 제외 멤버 목록"""
        meta = _squads.get(self.squad_id)
        if not meta:
            return []
        units = _units_of(self.squad_id)
        leader = meta["leader_id"]
        return [u for u in units if u != leader]

    @property
    def aggression(self):
        meta = _squads.get(self.squad_id)
        return meta["stance"] if meta else None

    def all_unit_ids(self):
        """리더 포함 전체 unit_id 목록 (리더가 [0])"""
        meta = _squads.get(self.squad_id)
        if not meta:
            return []
        leader = meta["leader_id"]
        ids = self.members
        if leader is not None:
            ids.insert(0, leader)
        return ids

    def is_full(self):
        return len(self.members) >= self.MAX_MEMBERS


# ========================================
# 내부 유틸
# ========================================

def _units_of(squad_id):
    """분대의 실제 파티 멤버 (엔진 조회)"""
    meta = _squads.get(squad_id)
    if not meta or meta["party_id"] is None:
        return []
    p = _party.get_party(meta["party_id"])
    return p.get_members() if p else []


def _find_squad_of_unit(unit_id):
    for sid in _squads:
        if unit_id in _units_of(sid):
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
    meta = _squads.get(squad_id)
    if not meta or meta["party_id"] is None:
        return False
    p = _party.get_party(meta["party_id"])
    if not p or unit_id not in p.get_members():
        return False
    if p.get_size() == 1:
        # 마지막 유닛 — 파티는 유닛의 솔로 파티로 남기고 분대에서 분리
        meta["party_id"] = None
        return True
    return _party.split(p.party_id, [unit_id]) is not None


def _attach_unit(meta, unit_id):
    """분대에 파티가 없으면 유닛의 (솔로) 파티를 분대 파티로 채택, 있으면 join"""
    if meta["party_id"] is None:
        p = _party.create_solo_party(unit_id)
        meta["party_id"] = p.party_id
        # stance 미러링
        _party.set_stance(p.party_id, meta["stance"])
        return True
    return _join(meta["party_id"], unit_id)


# ========================================
# 생명주기
# ========================================

def create_squad():
    """빈 분대 생성, squad_id 반환"""
    global _next_id
    squad_id = _next_id
    _next_id += 1
    _squads[squad_id] = {
        "party_id": None,
        "leader_id": None,
        "stance": "hold",
        "view": Squad(squad_id),
    }
    return squad_id


def disband_squad(squad_id):
    """분대 해산 — 전원 솔로 파티로"""
    meta = _squads.pop(squad_id, None)
    if not meta:
        return
    if meta["party_id"] is not None:
        _party.dissolve_party(meta["party_id"])


# ========================================
# 리더 관리
# ========================================

def assign_leader(squad_id, leader_id):
    """리더 지정 (이미 분대 소속인 유닛은 거부 — 기존 시맨틱)"""
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if _find_squad_of_unit(leader_id) is not None:
        return False
    if not _attach_unit(meta, leader_id):
        return False
    meta["leader_id"] = leader_id
    _party.transfer_leader(meta["party_id"], leader_id)
    return True


def remove_leader(squad_id):
    """리더 해제 (분대에서 이탈)"""
    meta = _squads.get(squad_id)
    if not meta or meta["leader_id"] is None:
        return
    uid = meta["leader_id"]
    meta["leader_id"] = None
    _leave(squad_id, uid)
    _party.clear_member_rank(uid)


def change_leader(squad_id, new_leader_id):
    """리더 교체 (이전 리더 → 멤버, 새 리더는 멤버/외부인 모두 허용)"""
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if new_leader_id not in _units_of(squad_id):
        if not _attach_unit(meta, new_leader_id):
            return False
    meta["leader_id"] = new_leader_id
    _party.transfer_leader(meta["party_id"], new_leader_id)
    return True


# ========================================
# 멤버 관리
# ========================================

def add_member(squad_id, unit_id):
    """멤버 등록 (타 분대 소속이면 자동 이적)"""
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if meta["view"].is_full():
        return False

    current = _find_squad_of_unit(unit_id)
    if current == squad_id:
        return False
    if current is not None:
        old_meta = _squads[current]
        if old_meta["leader_id"] == unit_id:
            remove_leader(current)
        else:
            remove_member(current, unit_id)

    return _attach_unit(meta, unit_id)


def remove_member(squad_id, unit_id):
    """멤버 제거"""
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if unit_id == meta["leader_id"] or unit_id not in _units_of(squad_id):
        return False
    if not _leave(squad_id, unit_id):
        return False
    _party.clear_member_rank(unit_id)
    _party.clear_order(unit_id)
    return True


# ========================================
# 조회
# ========================================

def get_squad(squad_id):
    meta = _squads.get(squad_id)
    return meta["view"] if meta else None


def get_squad_by_unit(unit_id):
    sid = _find_squad_of_unit(unit_id)
    return _squads[sid]["view"] if sid is not None else None


def is_in_squad(unit_id):
    return _find_squad_of_unit(unit_id) is not None


def is_squad_leader(unit_id):
    sid = _find_squad_of_unit(unit_id)
    return sid is not None and _squads[sid]["leader_id"] == unit_id


def get_squad_members(squad_id):
    view = get_squad(squad_id)
    return view.members if view else []


def get_all_unit_ids(squad_id):
    view = get_squad(squad_id)
    return view.all_unit_ids() if view else []


def get_all_squads():
    return [meta["view"] for _, meta in sorted(_squads.items())]


# ========================================
# 공세 레벨 (= engine stance)
# ========================================

def set_aggression(squad_id, level):
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if level not in AGGRESSION_LEVELS:
        return False
    meta["stance"] = level
    if meta["party_id"] is not None:
        _party.set_stance(meta["party_id"], level)
    return True


def get_aggression(squad_id):
    meta = _squads.get(squad_id)
    return meta["stance"] if meta else None


def get_aggression_value(squad_id):
    """공세 레벨 수치 (-2 ~ +2)"""
    level = get_aggression(squad_id)
    return AGGRESSION_LEVELS.get(level, 0)


# ========================================
# 대열 순번 (= engine rank, 유닛 귀속)
# ========================================

def set_member_rank(squad_id, unit_id, rank):
    """대열 순번 설정 (1=전위, 2=중위, 3=후위)"""
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if unit_id not in _units_of(squad_id):
        return False
    return _party.set_member_rank(unit_id, rank)


def get_member_rank(squad_id, unit_id):
    """대열 순번 조회 (기본값: 2=중위)"""
    if squad_id not in _squads:
        return _party.DEFAULT_RANK
    return _party.get_member_rank(unit_id)


# ========================================
# 지시 (= engine Order, 유닛 귀속)
# ========================================

def set_order(squad_id, unit_id, order):
    meta = _squads.get(squad_id)
    if not meta:
        return False
    if unit_id not in _units_of(squad_id):
        return False
    return _party.set_order(unit_id, order)


def clear_order(squad_id, unit_id):
    if squad_id not in _squads:
        return False
    _party.clear_order(unit_id)
    return True


def get_order(squad_id, unit_id):
    if squad_id not in _squads:
        return None
    return _party.get_order(unit_id)
