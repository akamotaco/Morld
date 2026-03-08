# expedition.py — 원정 라이프사이클 (시나리오03)
#
# 준비 → 출발 → 탐사 → 귀환 → 완료
# squad.py + mapgen.py 위에서 동작.

import morld

EXPEDITION_REGION_BASE = 100  # 원정 Region ID 시작


# ========================================
# 상태
# ========================================

class ExpeditionState:
    """원정 상태 객체"""

    __slots__ = ("expedition_id", "squad_id", "region_id", "difficulty",
                 "rooms", "connections", "status",
                 "explored_rooms", "current_room", "combat_log")

    def __init__(self, expedition_id, squad_id, region_id, difficulty):
        self.expedition_id = expedition_id
        self.squad_id = squad_id
        self.region_id = region_id
        self.difficulty = difficulty
        self.rooms = []
        self.connections = []
        self.status = "preparing"  # preparing → active → returning → completed
        self.explored_rooms = set()
        self.current_room = None
        self.combat_log = []


# ========================================
# 모듈 레지스트리
# ========================================

_expeditions = {}   # {expedition_id: ExpeditionState}
_squad_expedition = {}  # {squad_id: expedition_id}
_next_id = 0


def reset():
    global _next_id
    _expeditions.clear()
    _squad_expedition.clear()
    _next_id = 0


# ========================================
# 라이프사이클
# ========================================

def prepare_expedition(squad_id, difficulty="easy"):
    """원정 준비. ExpeditionState 생성.

    Returns:
        ExpeditionState or None (분대 검증 실패 시)
    """
    import squad as squad_module

    sq = squad_module.get_squad(squad_id)
    if not sq:
        return None
    if sq.leader_id is None:
        return None
    if len(sq.members) == 0:
        return None

    # 이미 원정 중이면 실패
    if squad_id in _squad_expedition:
        return None

    global _next_id
    eid = _next_id
    _next_id += 1

    region_id = EXPEDITION_REGION_BASE + eid

    state = ExpeditionState(eid, squad_id, region_id, difficulty)
    _expeditions[eid] = state
    _squad_expedition[squad_id] = eid

    print(f"[expedition] Prepared expedition {eid} "
          f"(squad={squad_id}, region={region_id}, difficulty={difficulty})")
    return state


def start_expedition(expedition_id):
    """원정 출발. 맵 생성 + 분대원 입구 배치.

    Returns:
        (success, message)
    """
    import squad as squad_module
    import mapgen

    state = _expeditions.get(expedition_id)
    if not state:
        return False, "원정을 찾을 수 없습니다"
    if state.status != "preparing":
        return False, f"현재 상태({state.status})에서 출발할 수 없습니다"

    # 맵 생성
    rooms, connections = mapgen.generate_expedition(
        state.region_id, state.difficulty,
    )
    state.rooms = rooms
    state.connections = connections

    # 분대원 입구(room 0)로 배치
    unit_ids = squad_module.get_all_unit_ids(state.squad_id)
    for uid in unit_ids:
        morld.set_unit_location(uid, state.region_id, 0)

    state.status = "active"
    state.current_room = 0
    state.explored_rooms.add(0)

    print(f"[expedition] Started expedition {expedition_id}: "
          f"{len(rooms)} rooms generated")
    return True, "탐사를 시작합니다"


def move_to_room(expedition_id, target_room_id):
    """분대를 다른 방으로 이동.

    Returns:
        (success, room_info, message)
    """
    import squad as squad_module

    state = _expeditions.get(expedition_id)
    if not state:
        return False, None, "원정을 찾을 수 없습니다"
    if state.status != "active":
        return False, None, "탐사 중이 아닙니다"

    # 현재 방에서 이동 가능한지 확인
    connected = _get_connected_rooms(state, state.current_room)
    if target_room_id not in connected:
        return False, None, "연결되지 않은 방입니다"

    # 방 정보
    room = _find_room(state, target_room_id)
    if not room:
        return False, None, "방을 찾을 수 없습니다"

    # 분대원 이동
    unit_ids = squad_module.get_all_unit_ids(state.squad_id)
    for uid in unit_ids:
        morld.set_unit_location(uid, state.region_id, target_room_id)

    state.current_room = target_room_id
    first_visit = target_room_id not in state.explored_rooms
    state.explored_rooms.add(target_room_id)

    print(f"[expedition] Moved to room {target_room_id} "
          f"({'new' if first_visit else 'revisit'})")
    return True, room, "이동 완료"


def retreat_expedition(expedition_id):
    """원정 귀환. 분대원을 플랫폼으로 복귀.

    Returns:
        (success, message)
    """
    import squad as squad_module
    import mapgen

    state = _expeditions.get(expedition_id)
    if not state:
        return False, "원정을 찾을 수 없습니다"
    if state.status not in ("active",):
        return False, f"현재 상태({state.status})에서 귀환할 수 없습니다"

    state.status = "returning"

    # 분대원을 플랫폼(R0, L0)으로 복귀
    unit_ids = squad_module.get_all_unit_ids(state.squad_id)
    for uid in unit_ids:
        morld.set_unit_location(uid, 0, 0)

    # 맵 정리
    mapgen.cleanup_expedition(state.region_id)

    state.status = "completed"

    print(f"[expedition] Retreat complete for expedition {expedition_id}")
    return True, "귀환 완료"


def complete_expedition(expedition_id):
    """원정 완료 처리 + 레지스트리 정리.

    Returns:
        summary dict
    """
    state = _expeditions.get(expedition_id)
    if not state:
        return None

    summary = {
        "expedition_id": expedition_id,
        "rooms_explored": len(state.explored_rooms),
        "rooms_total": len(state.rooms),
        "combat_log": list(state.combat_log),
    }

    _squad_expedition.pop(state.squad_id, None)
    _expeditions.pop(expedition_id, None)

    return summary


# ========================================
# 조회
# ========================================

def get_expedition(expedition_id):
    return _expeditions.get(expedition_id)


def get_expedition_by_squad(squad_id):
    eid = _squad_expedition.get(squad_id)
    if eid is not None:
        return _expeditions.get(eid)
    return None


def get_active_expeditions():
    return [e for e in _expeditions.values() if e.status == "active"]


def get_explorable_rooms(expedition_id):
    """현재 방에서 이동 가능한 방 목록"""
    state = _expeditions.get(expedition_id)
    if not state or state.status != "active":
        return []
    connected = _get_connected_rooms(state, state.current_room)
    result = []
    for rid in connected:
        room = _find_room(state, rid)
        if room:
            result.append({
                "id": rid,
                "type": room["type"],
                "explored": rid in state.explored_rooms,
                "threat": room.get("threat"),
                "has_loot": room.get("has_loot", False),
            })
    return result


# ========================================
# 내부 유틸
# ========================================

def _get_connected_rooms(state, room_id):
    """연결된 방 ID 목록"""
    result = []
    for conn in state.connections:
        if conn["from"] == room_id:
            result.append(conn["to"])
        elif conn["to"] == room_id:
            result.append(conn["from"])
    return result


def _find_room(state, room_id):
    """rooms 리스트에서 방 찾기"""
    for room in state.rooms:
        if room["id"] == room_id:
            return room
    return None
