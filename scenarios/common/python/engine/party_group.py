# party_group.py — 파티(Group) 시스템
#
# 핵심 원칙:
# - 모든 캐릭터는 항상 하나의 파티에 속함 (솔로도 파티로 취급)
# - 파티 조작은 merge / split / transfer_leader로 통일
# - 플레이어/몬스터 구분 없이 동등한 Party 인스턴스
#
# 시나리오별 확장은 콜백(set_callbacks)으로 주입.
# 같은 시나리오에서 party_squad와 독립 공존 가능.

import morld

# === 설정 ===
MAX_PARTY_SIZE = 4


# ========================================
# Party 클래스
# ========================================

class Party:
    """단일 파티 인스턴스

    속성:
        party_id: 파티 고유 ID
        leader_id: 리더 유닛 ID
        members: [unit_id, ...] 순서 = 편성 순서, [0]은 항상 리더
        max_size: 최대 크기
    """

    def __init__(self, party_id, leader_id, max_size=MAX_PARTY_SIZE):
        self.party_id = party_id
        self.leader_id = leader_id
        self.members = [leader_id]
        self.max_size = max_size

    def add(self, unit_id):
        """멤버 추가. 용량 초과 시 False"""
        if len(self.members) >= self.max_size:
            return False
        if unit_id in self.members:
            return False
        self.members.append(unit_id)
        return True

    def remove(self, unit_id):
        """멤버 제거 (리더 포함 가능). 성공 시 True"""
        if unit_id not in self.members:
            return False
        self.members.remove(unit_id)
        # 리더 제거 시 남은 멤버 중 첫 번째가 새 리더
        if unit_id == self.leader_id and self.members:
            self.leader_id = self.members[0]
        return True

    def get_members(self):
        return self.members.copy()

    def get_leader(self):
        return self.leader_id

    def get_non_leader_members(self):
        return [m for m in self.members if m != self.leader_id]

    def get_size(self):
        return len(self.members)

    def is_full(self):
        return len(self.members) >= self.max_size

    def is_member(self, unit_id):
        return unit_id in self.members

    def transfer_leader(self, new_leader_id):
        """리더 변경. 새 리더가 멤버가 아니면 False"""
        if new_leader_id not in self.members:
            return False
        self.leader_id = new_leader_id
        # 리더를 [0]으로 재정렬
        self.members.remove(new_leader_id)
        self.members.insert(0, new_leader_id)
        return True


# ========================================
# 전역 레지스트리
# ========================================

_parties = {}          # party_id → Party
_unit_to_party = {}    # unit_id → party_id
_next_party_id = 1

# === 콜백 ===
# 시나리오별 확장 포인트. set_callbacks()로 등록.
_callbacks = {
    "on_initialized": None,      # (leader_id, party) -> None
    "on_member_added": None,     # (unit_id, party) -> None
    "on_member_removed": None,   # (unit_id, party, reason) -> None
    "on_faint": None,            # (unit_id, party) -> bool (True = 시나리오가 처리함)
    "on_leader_changed": None,   # (old_leader, new_leader, party) -> None
}


def reset():
    """챕터 전환 시 리셋 (콜백은 유지)"""
    global _next_party_id
    _parties.clear()
    _unit_to_party.clear()
    _next_party_id = 1


def set_callbacks(**kwargs):
    """시나리오별 콜백 등록"""
    for k, v in kwargs.items():
        if k in _callbacks:
            _callbacks[k] = v


def _fire(cb_name, *args):
    cb = _callbacks.get(cb_name)
    if cb:
        return cb(*args)
    return None


def _new_party_id():
    global _next_party_id
    pid = _next_party_id
    _next_party_id += 1
    return pid


# ========================================
# 파티 생성
# ========================================

def create_solo_party(unit_id):
    """유닛의 솔로 파티 생성. 이미 속한 파티가 있으면 기존 파티 반환"""
    existing = get_party_of(unit_id)
    if existing is not None:
        return existing

    pid = _new_party_id()
    party = Party(pid, unit_id)
    _parties[pid] = party
    _unit_to_party[unit_id] = pid
    return party


def initialize_party(player_id):
    """플레이어 파티 초기화 (기존 API 호환).

    기존 파티 전부 정리 후 플레이어 솔로 파티 생성.
    """
    reset()
    party = create_solo_party(player_id)
    _fire("on_initialized", player_id, party)
    return party


# ========================================
# 조회
# ========================================

def get_party(party_id):
    """party_id로 파티 조회"""
    return _parties.get(party_id)


def get_party_of(unit_id):
    """유닛이 속한 파티 반환 (없으면 None)"""
    pid = _unit_to_party.get(unit_id)
    if pid is None:
        return None
    return _parties.get(pid)


def get_all_parties():
    """모든 파티 목록"""
    return list(_parties.values())


# ========================================
# 파티 조작
# ========================================

def merge(primary_id, secondary_id):
    """secondary 파티를 primary에 합침. primary 리더 유지.

    Args:
        primary_id: 흡수하는 파티 (리더/ID 유지)
        secondary_id: 흡수되는 파티 (해체됨)

    Returns:
        성공 여부. 용량 초과 시 False (부분 병합 없음)
    """
    primary = _parties.get(primary_id)
    secondary = _parties.get(secondary_id)
    if primary is None or secondary is None:
        return False
    if primary.party_id == secondary.party_id:
        return False

    # 용량 체크
    if primary.get_size() + secondary.get_size() > primary.max_size:
        return False

    for uid in secondary.get_members():
        primary.add(uid)
        _unit_to_party[uid] = primary.party_id
        _fire("on_member_added", uid, primary)

    del _parties[secondary.party_id]
    return True


def split(party_id, unit_ids):
    """unit_ids를 떼어 새 파티 생성.

    리더가 포함되면 리더도 이동 (기존 파티는 남은 멤버 중 첫 번째가 리더).

    Returns:
        새 파티 (실패 시 None)
    """
    party = _parties.get(party_id)
    if party is None:
        return None

    # 유효성 검사
    unit_ids = [u for u in unit_ids if u in party.members]
    if not unit_ids:
        return None
    if len(unit_ids) == party.get_size():
        # 전부 떼면 원래 파티가 빈 파티가 됨 → 의미 없음
        return None

    # 첫 번째 유닛이 새 파티 리더
    new_leader = unit_ids[0]
    new_pid = _new_party_id()
    new_party = Party(new_pid, new_leader)
    _parties[new_pid] = new_party
    _unit_to_party[new_leader] = new_pid

    # 나머지 유닛 추가
    for uid in unit_ids[1:]:
        new_party.add(uid)
        _unit_to_party[uid] = new_pid

    # 원본 파티에서 제거
    for uid in unit_ids:
        party.remove(uid)
        _fire("on_member_removed", uid, party, "split")

    # 원본 리더가 옮겨갔으면 on_leader_changed 발생
    if new_leader in unit_ids and party.get_size() > 0:
        _fire("on_leader_changed", new_leader, party.leader_id, party)

    return new_party


def transfer_leader(party_id, new_leader_id):
    """파티 리더 변경"""
    party = _parties.get(party_id)
    if party is None:
        return False
    old_leader = party.leader_id
    if not party.transfer_leader(new_leader_id):
        return False
    _fire("on_leader_changed", old_leader, new_leader_id, party)
    return True


def dissolve_party(party_id):
    """파티 해체 — 각 멤버는 솔로 파티로 돌아감"""
    party = _parties.get(party_id)
    if party is None:
        return
    members = party.get_members()
    del _parties[party_id]
    for uid in members:
        del _unit_to_party[uid]
        create_solo_party(uid)


# ========================================
# 기존 API 호환 (플레이어 파티 조작)
# ========================================
# 플레이어 파티를 지정 파티로 가정하는 기존 코드 호환용 래퍼.
# 플레이어 파티는 initialize_party()로 생성된 파티.

_player_party_id = None  # initialize_party 호출 시 설정


def _get_player_party():
    """플레이어 파티 조회 (기존 API용)"""
    global _player_party_id
    if _player_party_id is not None:
        party = _parties.get(_player_party_id)
        if party is not None:
            return party
    # 플레이어 ID 기반 조회
    pid = morld.get_player_id()
    if pid is None:
        return None
    party = get_party_of(pid)
    if party is not None:
        _player_party_id = party.party_id
    return party


def add_member(unit_id):
    """플레이어 파티에 멤버 추가 (기존 API)"""
    player_party = _get_player_party()
    if player_party is None:
        return False

    # 유닛이 다른 파티에 있으면 그 파티를 merge
    unit_party = get_party_of(unit_id)
    if unit_party is not None and unit_party.party_id != player_party.party_id:
        # 솔로 파티면 merge, 아니면 split 후 merge
        if unit_party.get_size() == 1:
            return merge(player_party.party_id, unit_party.party_id)
        else:
            new_party = split(unit_party.party_id, [unit_id])
            if new_party is None:
                return False
            return merge(player_party.party_id, new_party.party_id)

    if unit_party is None:
        create_solo_party(unit_id)
        return merge(player_party.party_id, get_party_of(unit_id).party_id)

    return False  # 이미 플레이어 파티원


def remove_member(unit_id, reason="해제"):
    """플레이어 파티에서 멤버 제거 (기존 API). 리더는 제거 불가"""
    player_party = _get_player_party()
    if player_party is None:
        return False
    if unit_id == player_party.leader_id:
        return False
    if not player_party.is_member(unit_id):
        return False

    # 개별 유닛을 떼어 솔로 파티로
    new_party = split(player_party.party_id, [unit_id])
    if new_party is None:
        return False
    _fire("on_member_removed", unit_id, player_party, reason)
    return True


def get_members():
    """플레이어 파티원 목록 (기존 API)"""
    party = _get_player_party()
    return party.get_members() if party else []


def get_leader():
    """플레이어 파티 리더 (기존 API)"""
    party = _get_player_party()
    return party.get_leader() if party else None


def get_size():
    """플레이어 파티 크기 (기존 API)"""
    party = _get_player_party()
    return party.get_size() if party else 0


def is_full():
    """플레이어 파티 만원 여부 (기존 API)"""
    party = _get_player_party()
    return party.is_full() if party else False


def is_member(unit_id):
    """플레이어 파티 소속 여부 (기존 API)"""
    party = _get_player_party()
    return party.is_member(unit_id) if party else False


def get_non_leader_members():
    """리더 제외 플레이어 파티원 (기존 API)"""
    party = _get_player_party()
    return party.get_non_leader_members() if party else []


# ========================================
# 실신 처리
# ========================================

def handle_faint(unit_id):
    """파티원 실신 처리 (어느 파티든)."""
    party = get_party_of(unit_id)
    if party is None:
        return

    cb_result = _fire("on_faint", unit_id, party)
    if cb_result:
        return  # 시나리오가 처리함

    # 기본: 리더가 아니면 제거 (솔로 파티로 분리)
    if unit_id != party.leader_id:
        split(party.party_id, [unit_id])


# ========================================
# 공유 소비 (플레이어 파티 전용)
# ========================================

def consume_party_food(food_amount):
    """플레이어 파티 식량 소비 (공유 식량).

    포만감 80 미만인 멤버에게 1회 30씩 회복.
    """
    import survival

    party = _get_player_party()
    if party is None:
        return 0

    consumed = 0
    for mid in party.get_members():
        satiety = survival.get_satiety(mid)
        if satiety < 80:
            needed = min(food_amount - consumed, 30)
            if needed > 0:
                survival.set_satiety(mid, min(100, satiety + needed))
                consumed += 1
    return consumed


# ========================================
# 초기화 시 _player_party_id 설정
# ========================================

def _set_player_party_id(pid):
    """내부: 플레이어 파티 ID 설정"""
    global _player_party_id
    _player_party_id = pid


# initialize_party 호출 시 자동으로 설정되도록 래핑
_original_initialize_party = initialize_party


def initialize_party(player_id):  # noqa: F811
    """플레이어 파티 초기화 (플레이어 파티 ID 자동 설정)"""
    reset()
    party = create_solo_party(player_id)
    _set_player_party_id(party.party_id)
    _fire("on_initialized", player_id, party)
    return party
