# generator.py — BSP 기반 2D 던전 맵 생성
"""
순수 Python. morld 의존 없음.
BSP(Binary Space Partition)로 사각형 공간을 재귀 분할 → 방 + 복도 생성.

사용법:
    rooms, corridors = generate_dungeon(width=400, height=400, min_size=60, max_depth=4)
"""

import random


class Room:
    """생성된 방"""
    __slots__ = ("id", "x", "y", "w", "h", "room_type")

    def __init__(self, room_id, x, y, w, h, room_type="normal"):
        self.id = room_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.room_type = room_type

    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    def __repr__(self):
        return f"Room({self.id}, {self.x},{self.y} {self.w}x{self.h} [{self.room_type}])"


class Corridor:
    """두 방을 연결하는 복도"""
    __slots__ = ("room_a", "room_b")

    def __init__(self, room_a_id, room_b_id):
        self.room_a = room_a_id
        self.room_b = room_b_id

    def __repr__(self):
        return f"Corridor({self.room_a} <-> {self.room_b})"


class _BSPNode:
    """BSP 트리 노드"""
    __slots__ = ("x", "y", "w", "h", "left", "right", "room")

    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.left = None
        self.right = None
        self.room = None


def generate_dungeon(width=400, height=400, min_size=60, max_depth=4,
                     room_padding=8, seed=None):
    """
    BSP 던전 생성.

    Args:
        width, height: 전체 공간 크기
        min_size: 최소 방 크기 (이 미만이면 분할 중단)
        max_depth: 최대 분할 깊이
        room_padding: 방과 셀 경계 사이 여백
        seed: 랜덤 시드 (None이면 랜덤)

    Returns:
        (rooms: list[Room], corridors: list[Corridor])
    """
    if seed is not None:
        random.seed(seed)

    root = _BSPNode(0, 0, width, height)
    _split(root, min_size, max_depth, 0)

    rooms = []
    _room_counter = [0]

    def _create_rooms(node):
        if node.left is None and node.right is None:
            # 리프 노드 → 방 생성 (패딩 적용)
            pad = room_padding
            rw = node.w - pad * 2
            rh = node.h - pad * 2
            if rw < 20:
                rw = node.w - 4
                pad = 2
            if rh < 20:
                rh = node.h - 4
                pad = 2

            rx = node.x + pad + random.randint(0, max(0, rw // 4))
            ry = node.y + pad + random.randint(0, max(0, rh // 4))
            rw = max(20, rw - random.randint(0, max(0, rw // 4)))
            rh = max(20, rh - random.randint(0, max(0, rh // 4)))

            room = Room(_room_counter[0], rx, ry, rw, rh)
            node.room = room
            rooms.append(room)
            _room_counter[0] += 1
        else:
            if node.left:
                _create_rooms(node.left)
            if node.right:
                _create_rooms(node.right)

    _create_rooms(root)

    # 복도 연결: 형제 노드의 방을 연결
    corridors = []
    _connect_siblings(root, corridors)

    # 방 타입 할당
    if rooms:
        rooms[0].room_type = "start"
        rooms[-1].room_type = "boss"
        # 보물방: 중간쯤 1개
        if len(rooms) > 3:
            treasure_idx = len(rooms) // 2
            rooms[treasure_idx].room_type = "treasure"

    return rooms, corridors


def generate_multi_floor(floors=3, width=400, height=400, min_size=60,
                         max_depth=4, room_padding=8, seed=None):
    """
    다층 던전 생성.

    층별로 독립 BSP → 계단(stairs_up/stairs_down)으로 연결.
    1층 입구(start), 최하층 보스(boss).

    Args:
        floors: 층 수
        나머지: generate_dungeon과 동일

    Returns:
        list[dict]: 층별 {"floor": int, "rooms": list[Room], "corridors": list[Corridor]}
    """
    if seed is not None:
        random.seed(seed)

    result = []
    for floor in range(floors):
        floor_seed = (seed * 100 + floor + 1) if seed else None
        rooms, corridors = generate_dungeon(
            width=width, height=height,
            min_size=min_size, max_depth=max_depth,
            room_padding=room_padding, seed=floor_seed
        )

        # 타입 재할당 (다층용)
        for room in rooms:
            room.room_type = "normal"

        if rooms:
            if floor == 0:
                rooms[0].room_type = "start"        # 1층 입구
            if floor == floors - 1:
                rooms[-1].room_type = "boss"         # 최하층 보스

            # 보물방: 각 층 중간 1개
            if len(rooms) > 3:
                rooms[len(rooms) // 2].room_type = "treasure"

            # 계단: 마지막 방 = stairs_down (최하층 제외)
            if floor < floors - 1:
                stairs_down_room = rooms[-1] if rooms[-1].room_type == "normal" else rooms[-2]
                stairs_down_room.room_type = "stairs_down"

            # 계단: 첫 번째 방 = stairs_up (1층 제외)
            if floor > 0:
                stairs_up_room = rooms[0] if rooms[0].room_type == "normal" else rooms[1]
                stairs_up_room.room_type = "stairs_up"

        result.append({
            "floor": floor,
            "rooms": rooms,
            "corridors": corridors,
        })

    return result


def _split(node, min_size, max_depth, depth):
    """재귀 BSP 분할"""
    if depth >= max_depth:
        return
    if node.w < min_size * 2 and node.h < min_size * 2:
        return

    # 분할 방향 결정
    if node.w > node.h * 1.3:
        horizontal = False  # 세로로 자름
    elif node.h > node.w * 1.3:
        horizontal = True   # 가로로 자름
    else:
        horizontal = random.random() < 0.5

    if horizontal:
        if node.h < min_size * 2:
            return
        split = random.randint(min_size, node.h - min_size)
        node.left = _BSPNode(node.x, node.y, node.w, split)
        node.right = _BSPNode(node.x, node.y + split, node.w, node.h - split)
    else:
        if node.w < min_size * 2:
            return
        split = random.randint(min_size, node.w - min_size)
        node.left = _BSPNode(node.x, node.y, split, node.h)
        node.right = _BSPNode(node.x + split, node.y, node.w - split, node.h)

    _split(node.left, min_size, max_depth, depth + 1)
    _split(node.right, min_size, max_depth, depth + 1)


def _get_room(node):
    """노드의 대표 방 (리프면 자신, 아니면 재귀)"""
    if node.room:
        return node.room
    if node.left:
        r = _get_room(node.left)
        if r:
            return r
    if node.right:
        return _get_room(node.right)
    return None


def _connect_siblings(node, corridors):
    """형제 노드의 방을 복도로 연결"""
    if node.left and node.right:
        room_a = _get_room(node.left)
        room_b = _get_room(node.right)
        if room_a and room_b:
            corridors.append(Corridor(room_a.id, room_b.id))
        _connect_siblings(node.left, corridors)
        _connect_siblings(node.right, corridors)


class Bridge:
    """BSP tree 위의 추가 간선 (루프 생성)"""
    __slots__ = ("room_a", "room_b")

    def __init__(self, room_a_id, room_b_id):
        self.room_a = room_a_id
        self.room_b = room_b_id

    def __repr__(self):
        return f"Bridge({self.room_a} <-> {self.room_b})"


def generate_bridges(rooms, corridors, max_bridges=2, max_distance=200, seed=None):
    """
    BSP tree 위에 추가 간선(bridge)을 생성하여 루프를 만듦.

    Args:
        rooms: 방 목록
        corridors: 기존 corridor 목록
        max_bridges: 최대 bridge 수
        max_distance: 후보 최대 유클리디안 거리
        seed: 랜덤 시드

    Returns:
        list[Bridge]
    """
    if max_bridges <= 0 or len(rooms) < 3:
        return []

    if seed is not None:
        random.seed(seed)

    # 기존 연결 집합
    connected = set()
    for c in corridors:
        connected.add((min(c.room_a, c.room_b), max(c.room_a, c.room_b)))

    # 방 중심 좌표
    centers = {r.id: r.center() for r in rooms}

    # 기존 간선 선분 목록 (교차 검사용)
    existing_segments = []
    for c in corridors:
        existing_segments.append((centers[c.room_a], centers[c.room_b]))

    # 후보: 비연결 + 거리 내
    candidates = []
    room_ids = [r.id for r in rooms]
    for i in range(len(room_ids)):
        for j in range(i + 1, len(room_ids)):
            a, b = room_ids[i], room_ids[j]
            key = (min(a, b), max(a, b))
            if key in connected:
                continue
            ca, cb = centers[a], centers[b]
            dist = ((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2) ** 0.5
            if dist <= max_distance:
                candidates.append((dist, a, b))

    candidates.sort()

    bridges = []
    bridge_segments = []

    for dist, a, b in candidates:
        if len(bridges) >= max_bridges:
            break

        seg = (centers[a], centers[b])

        # 교차 검사: 기존 corridor + 이미 추가된 bridge
        crosses = False
        for existing in existing_segments + bridge_segments:
            if _segments_intersect(seg[0], seg[1], existing[0], existing[1]):
                crosses = True
                break

        if not crosses:
            bridges.append(Bridge(a, b))
            bridge_segments.append(seg)
            connected.add((min(a, b), max(a, b)))

    return bridges


def _segments_intersect(p1, p2, p3, p4):
    """두 선분의 교차 여부 (유클리디안, 끝점 공유 제외)"""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # 끝점 공유 시 교차 아님
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False

    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False


def generate_floor(spec_base, floor_num, seed, max_floors=None,
                   stairs_per_floor=1):
    """
    단일 층 BSP 생성 (Lazy Generation용).

    Args:
        spec_base: {"width", "height", "min_size", "max_depth"} + floor_scaling
        floor_num: 현재 층 번호 (0-indexed)
        seed: base_seed (floor_num 기반 파생)
        max_floors: 최대 층수 (None=무한)
        stairs_per_floor: 계단 수

    Returns:
        (rooms, corridors, bridges)
    """
    floor_seed = seed + floor_num * 100

    # floor_scaling 적용
    width = spec_base["width"]
    height = spec_base["height"]
    min_size = spec_base["min_size"]
    max_depth = spec_base["max_depth"]

    scaling = spec_base.get("floor_scaling", {})
    width += int(scaling.get("width_per_floor", 0) * floor_num)
    height += int(scaling.get("height_per_floor", 0) * floor_num)
    max_depth += int(scaling.get("max_depth_per_floor", 0) * floor_num)

    rooms, corridors = generate_dungeon(
        width=width, height=height,
        min_size=min_size, max_depth=max_depth,
        seed=floor_seed
    )

    # 타입 재할당
    for room in rooms:
        room.room_type = "normal"

    if rooms:
        # 입구 (1층만)
        if floor_num == 0:
            rooms[0].room_type = "start"

        # stairs_up (1층 이외)
        if floor_num > 0:
            rooms[0].room_type = "stairs_up"

        # 보물방
        if len(rooms) > 3:
            rooms[len(rooms) // 2].room_type = "treasure"

        # 보스 (마지막 층)
        is_last_floor = max_floors is not None and floor_num >= max_floors - 1
        if is_last_floor:
            rooms[-1].room_type = "boss"
        else:
            # stairs_down
            for count in range(stairs_per_floor):
                # 마지막 방부터 역순으로 stairs_down 배치
                idx = -(1 + count)
                if abs(idx) <= len(rooms) and rooms[idx].room_type == "normal":
                    rooms[idx].room_type = "stairs_down"

    # Bridge 생성
    bridge_seed = seed + floor_num * 100 + 99
    bridge_cfg = spec_base.get("connections", {})
    bridges = generate_bridges(
        rooms, corridors,
        max_bridges=bridge_cfg.get("bridges_per_floor", 0),
        max_distance=bridge_cfg.get("bridge_max_distance", 200),
        seed=bridge_seed,
    )

    return rooms, corridors, bridges


def render_ascii(rooms, corridors, width, height, scale=1):
    """
    디버그용 ASCII 맵 렌더링.

    Args:
        rooms: 방 목록
        corridors: 복도 목록
        width, height: 전체 크기
        scale: 축소 비율 (2면 2배 축소)

    Returns:
        str: ASCII 맵 문자열
    """
    sw = width // scale
    sh = height // scale
    grid = [['.' for _ in range(sw)] for _ in range(sh)]

    # 방 그리기
    type_chars = {"start": "S", "boss": "B", "treasure": "T", "normal": "#"}
    for room in rooms:
        rx = room.x // scale
        ry = room.y // scale
        rw = max(1, room.w // scale)
        rh = max(1, room.h // scale)
        ch = type_chars.get(room.room_type, "#")
        for dy in range(rh):
            for dx in range(rw):
                y = ry + dy
                x = rx + dx
                if 0 <= y < sh and 0 <= x < sw:
                    grid[y][x] = ch

    # 복도 그리기 (방 중심 간 L자 연결)
    room_map = {r.id: r for r in rooms}
    for corr in corridors:
        ra = room_map[corr.room_a]
        rb = room_map[corr.room_b]
        ax, ay = ra.center()[0] // scale, ra.center()[1] // scale
        bx, by = rb.center()[0] // scale, rb.center()[1] // scale

        # 가로 먼저
        x = ax
        while x != bx:
            if 0 <= ay < sh and 0 <= x < sw and grid[ay][x] == '.':
                grid[ay][x] = '+'
            x += 1 if bx > ax else -1
        # 세로
        y = ay
        while y != by:
            if 0 <= y < sh and 0 <= bx < sw and grid[y][bx] == '.':
                grid[y][bx] = '+'
            y += 1 if by > ay else -1

    return '\n'.join(''.join(row) for row in grid)
