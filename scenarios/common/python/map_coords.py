# map_coords.py - Location 2D 좌표 자동 배치
#
# Gate 그래프 기반으로 Location의 2D 지도 좌표를 자동 계산.
# - register(): Location 등록 (좌표 자동 결정)
# - rebuild(): Gate 연결 기반 전체 재배치 + 정규화
# - 건축/파괴 시 rebuild()로 자동 조정
#
# 좌표계: float (내부), 렌더러가 정수 그리드로 변환.
# 정규화: 중심 = (0,0), 최대 범위 = location 수 비례.

import morld


# (region_id, location_id) -> (x: float, y: float)
_coords = {}

# 수동 오버라이드 좌표 (있으면 rebuild 시 이 값을 힌트로 사용)
_pinned = {}


def reset():
    """챕터 전환 시 리셋"""
    _coords.clear()
    _pinned.clear()


# ========================================
# 등록 / 조회 / 삭제
# ========================================

def register(region_id, location_id, x=None, y=None):
    """Location 등록.

    x, y 생략 시: rebuild()에서 자동 계산.
    x, y 지정 시: 핀 고정 (rebuild 시에도 이 위치 유지).
    """
    if x is not None and y is not None:
        _pinned[(region_id, location_id)] = (float(x), float(y))
        _coords[(region_id, location_id)] = (float(x), float(y))
    else:
        # 임시 좌표 — rebuild()에서 재계산됨
        if (region_id, location_id) not in _coords:
            _coords[(region_id, location_id)] = (0.0, 0.0)


def remove(region_id, location_id):
    """좌표 삭제 (방 파괴 시)"""
    _coords.pop((region_id, location_id), None)
    _pinned.pop((region_id, location_id), None)


def get_coords(region_id, location_id):
    """좌표 조회. 없으면 None."""
    return _coords.get((region_id, location_id))


def get_all(region_id):
    """해당 region의 모든 좌표 반환.
    Returns: {location_id: (x, y), ...}  (정수 변환된 좌표)
    """
    result = {}
    for (rid, lid), (x, y) in _coords.items():
        if rid == region_id:
            result[lid] = (round(x), round(y))
    return result


def has_coords(region_id, location_id):
    """좌표 등록 여부"""
    return (region_id, location_id) in _coords


# ========================================
# 그래프 기반 자동 배치
# ========================================

def rebuild(region_id):
    """Gate 그래프 기반으로 해당 region의 전체 좌표 재계산.

    1. 등록된 Location 목록 수집
    2. Gate 인접 관계(adjacency) 구축
    3. BFS로 연결 순서대로 배치
    4. 정규화 (중심 = 0, 스케일 균등)
    """
    # 이 region에 등록된 location 목록
    loc_ids = [lid for (rid, lid) in _coords if rid == region_id]
    if not loc_ids:
        return

    # Gate 인접 관계 구축
    adjacency = {}
    for lid in loc_ids:
        adjacency[lid] = []
        gates = morld.get_location_gates(region_id, lid)
        if gates:
            for gate in gates:
                conn_region = gate.get("connected_region")
                conn_loc = gate.get("connected_location") or gate.get("connected_local")
                if conn_region == region_id and conn_loc in adjacency or conn_loc in loc_ids:
                    adjacency[lid].append(conn_loc)

    # 핀 고정된 좌표 반영
    placed = {}
    for lid in loc_ids:
        key = (region_id, lid)
        if key in _pinned:
            placed[lid] = _pinned[key]

    # BFS 배치 (핀 없는 것만)
    if not placed:
        # 시작점: 첫 번째 location → (0, 0)
        start = loc_ids[0]
        placed[start] = (0.0, 0.0)

    _bfs_place(loc_ids, adjacency, placed)

    # 정규화
    _normalize(placed)

    # 결과 저장
    for lid, (x, y) in placed.items():
        _coords[(region_id, lid)] = (x, y)


# 8방향 오프셋 (BFS 배치용)
_DIRECTIONS = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]


def _bfs_place(loc_ids, adjacency, placed):
    """BFS로 미배치 노드를 이웃 기반으로 배치."""
    # BFS 큐: 이미 배치된 노드부터 시작 (list로 구현 — SharpPy 호환)
    queue = list(placed.keys())
    visited = set(placed.keys())

    while queue:
        current = queue.pop(0)
        cx, cy = placed[current]

        for neighbor in adjacency.get(current, []):
            if neighbor in visited:
                continue
            if neighbor not in [lid for lid in loc_ids]:
                continue

            # 이웃의 위치 결정: 현재 위치 주변 빈 자리
            occupied = set()
            for _, (px, py) in placed.items():
                occupied.add((round(px), round(py)))

            nx, ny = cx, cy
            found = False
            for dist in range(1, 50):
                for dx, dy in _DIRECTIONS:
                    tx, ty = round(cx + dx * dist), round(cy + dy * dist)
                    if (tx, ty) not in occupied:
                        nx, ny = float(tx), float(ty)
                        found = True
                        break
                if found:
                    break

            placed[neighbor] = (nx, ny)
            visited.add(neighbor)
            queue.append(neighbor)

    # 연결 안 된 고립 노드도 배치
    for lid in loc_ids:
        if lid not in placed:
            occupied = set()
            for _, (px, py) in placed.items():
                occupied.add((round(px), round(py)))

            x, y = 0.0, 0.0
            for dist in range(0, 50):
                found = False
                for dx, dy in _DIRECTIONS:
                    tx, ty = round(dx * dist), round(dy * dist)
                    if (tx, ty) not in occupied:
                        x, y = float(tx), float(ty)
                        found = True
                        break
                if found:
                    break
            placed[lid] = (x, y)


def _normalize(placed):
    """좌표 정규화: 중심을 (0,0)으로, 스케일을 location 수 비례로 조정."""
    if not placed:
        return

    xs = [x for x, y in placed.values()]
    ys = [y for x, y in placed.values()]

    # 중심 이동
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    for lid in placed:
        x, y = placed[lid]
        placed[lid] = (x - cx, y - cy)

    # 현재 범위
    if len(placed) <= 1:
        return

    xs = [x for x, y in placed.values()]
    ys = [y for x, y in placed.values()]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    span = max(span_x, span_y, 1.0)

    # 목표 범위: sqrt(n) 비례 (자연스러운 확장)
    import math
    target = max(math.sqrt(len(placed)) * 2, 3.0)

    scale = target / span

    for lid in placed:
        x, y = placed[lid]
        placed[lid] = (x * scale, y * scale)
