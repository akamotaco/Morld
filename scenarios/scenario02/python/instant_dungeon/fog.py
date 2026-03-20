# fog.py — 인스턴트 던전 Fog of War
"""
던전별 방 가시성 관리.

모드:
    volatile   — 현재 위치 + 인접만 밝게, 이전 방문 이력은 흐리게 유지
    permanent  — 한 번 방문하면 영구 밝게 표시 (신규 지역 탐험)
    none       — 완전 정보 (디버그/일반 지도)

가시성 상태:
    HIDDEN   (0) — 미발견, 맵에 · 으로 표시 (위치는 고정)
    REVEALED (1) — 발견됨 (방문 이력), 흐리게 표시
    VISIBLE  (2) — 현재 보임 (현재 위치 + 인접), 밝게 표시

사용:
    fog.init_fog(dungeon_id, rooms, corridors, mode="volatile")
    fog.update_fog(dungeon_id, current_room_id)
    fog.get_room_visibility(dungeon_id, room_id)  → HIDDEN/REVEALED/VISIBLE
"""

# 가시성 상태 (숫자 순서 = 밝기 순서)
HIDDEN = 0      # 미발견
REVEALED = 1    # 발견됨 (흐리게)
VISIBLE = 2     # 현재 보임 (밝게)

# 던전별 FoW 데이터
_fog_data = {}


def _build_adjacency(corridors):
    """Corridor 목록에서 인접 맵 생성"""
    adj = {}
    for c in corridors:
        adj.setdefault(c.room_a, set()).add(c.room_b)
        adj.setdefault(c.room_b, set()).add(c.room_a)
    return adj


def init_fog(dungeon_id, rooms, corridors, mode="volatile"):
    """
    던전 FoW 초기화.

    Args:
        dungeon_id: 던전 식별자
        rooms: list[Room]
        corridors: list[Corridor]
        mode: "volatile" | "permanent" | "none"
    """
    visibility = {}
    for room in rooms:
        visibility[room.id] = HIDDEN if mode != "none" else VISIBLE

    _fog_data[dungeon_id] = {
        "mode": mode,
        "visibility": visibility,
        "adjacency": _build_adjacency(corridors),
        # 복도 방문 기록: (room_a, room_b) frozenset → True
        "revealed_corridors": set(),
    }


def update_fog(dungeon_id, current_room_id):
    """
    플레이어 이동 시 FoW 갱신.

    volatile: 모든 방 → REVEALED (방문 이력 유지), 현재+인접 → VISIBLE
    permanent: VISIBLE → REVEALED 강등, 현재+인접 → VISIBLE
    none: 전부 VISIBLE
    """
    data = _fog_data.get(dungeon_id)
    if data is None:
        return

    mode = data["mode"]
    vis = data["visibility"]
    adj = data["adjacency"]
    revealed_corrs = data["revealed_corridors"]

    if mode == "none":
        for rid in vis:
            vis[rid] = VISIBLE
        return

    # volatile/permanent 공통: 기존 VISIBLE → REVEALED 강등
    for rid in vis:
        if vis[rid] == VISIBLE:
            vis[rid] = REVEALED

    # 현재 방 + 인접 방 VISIBLE
    vis[current_room_id] = VISIBLE
    for neighbor_id in adj.get(current_room_id, set()):
        if neighbor_id in vis:
            vis[neighbor_id] = VISIBLE
            # 복도 방문 기록
            corr_key = frozenset((current_room_id, neighbor_id))
            revealed_corrs.add(corr_key)


def get_room_visibility(dungeon_id, room_id):
    """방 가시성 조회 (HIDDEN/REVEALED/VISIBLE)"""
    data = _fog_data.get(dungeon_id)
    if data is None:
        return HIDDEN
    return data["visibility"].get(room_id, HIDDEN)


def get_fog_state(dungeon_id):
    """던전 전체 FoW 상태 반환 (렌더러용)"""
    data = _fog_data.get(dungeon_id)
    if data is None:
        return {}
    return dict(data["visibility"])


def get_fog_mode(dungeon_id):
    """던전 FoW 모드 반환"""
    data = _fog_data.get(dungeon_id)
    if data is None:
        return "none"
    return data["mode"]


def get_adjacency(dungeon_id):
    """던전 인접 맵 반환 (렌더러용)"""
    data = _fog_data.get(dungeon_id)
    if data is None:
        return {}
    return data["adjacency"]


def is_corridor_revealed(dungeon_id, room_a, room_b):
    """복도가 발견되었는지 (한 번이라도 인접했으면 True)"""
    data = _fog_data.get(dungeon_id)
    if data is None:
        return False
    return frozenset((room_a, room_b)) in data["revealed_corridors"]


def destroy_fog(dungeon_id):
    """던전 FoW 데이터 삭제"""
    _fog_data.pop(dungeon_id, None)


def reset():
    """챕터 전환 시 전체 리셋"""
    _fog_data.clear()
