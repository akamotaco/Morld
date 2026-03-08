# mapgen.py — 동적 맵 생성 (시나리오03)
#
# BSP 기반 탐사 지역 생성기.
# 2D 레이아웃 생성 → Location/Gate 변환 → 콘텐츠 배치.
# C# 변경 없음 — 순수 Python.

import random
import morld


# ========================================
# 난이도 설정
# ========================================

class DifficultyConfig:
    __slots__ = ("room_count_min", "room_count_max",
                 "enemy_chance", "loot_chance",
                 "min_room_size", "map_width", "map_height")

    def __init__(self, room_count_min=5, room_count_max=8,
                 enemy_chance=0.3, loot_chance=0.4,
                 min_room_size=100, map_width=800, map_height=600):
        self.room_count_min = room_count_min
        self.room_count_max = room_count_max
        self.enemy_chance = enemy_chance
        self.loot_chance = loot_chance
        self.min_room_size = min_room_size
        self.map_width = map_width
        self.map_height = map_height


DIFFICULTY_PRESETS = {
    "easy":   DifficultyConfig(5, 8, 0.2, 0.5, 120, 800, 600),
    "normal": DifficultyConfig(8, 12, 0.4, 0.4, 100, 1000, 800),
    "hard":   DifficultyConfig(12, 18, 0.6, 0.3, 80, 1200, 1000),
}


# ========================================
# BSP 트리
# ========================================

class BSPNode:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.left = None
        self.right = None
        self.room = None  # {"id", "x", "y", "width", "height", "type"}

    def split(self, min_size):
        """재귀 분할. 분할 성공 시 True."""
        if self.width < min_size * 2 and self.height < min_size * 2:
            return False

        if self.width > self.height * 1.25:
            vertical = True
        elif self.height > self.width * 1.25:
            vertical = False
        else:
            vertical = random.random() > 0.5

        ratio = random.uniform(0.35, 0.65)

        if vertical:
            split_pos = int(self.width * ratio)
            if split_pos < min_size or (self.width - split_pos) < min_size:
                return False
            self.left = BSPNode(self.x, self.y, split_pos, self.height)
            self.right = BSPNode(self.x + split_pos, self.y,
                                 self.width - split_pos, self.height)
        else:
            split_pos = int(self.height * ratio)
            if split_pos < min_size or (self.height - split_pos) < min_size:
                return False
            self.left = BSPNode(self.x, self.y, self.width, split_pos)
            self.right = BSPNode(self.x, self.y + split_pos,
                                 self.width, self.height - split_pos)
        return True

    def is_leaf(self):
        return self.left is None and self.right is None

    def get_leaves(self):
        if self.is_leaf():
            return [self]
        leaves = []
        if self.left:
            leaves.extend(self.left.get_leaves())
        if self.right:
            leaves.extend(self.right.get_leaves())
        return leaves


def _build_bsp(width, height, min_size, max_rooms):
    """BSP 트리 생성 → 리프 노드 반환"""
    root = BSPNode(0, 0, width, height)
    nodes = [root]

    # 리프가 max_rooms 이하가 될 때까지 분할
    for _ in range(max_rooms * 2):
        leaves = root.get_leaves()
        if len(leaves) >= max_rooms:
            break
        # 가장 큰 리프부터 분할 시도
        leaves.sort(key=lambda n: n.width * n.height, reverse=True)
        split_done = False
        for leaf in leaves:
            if len(root.get_leaves()) >= max_rooms:
                break
            if leaf.split(min_size):
                split_done = True
        if not split_done:
            break

    return root


def _place_rooms(root, max_rooms):
    """리프 노드에 방 배치, rooms 리스트 반환"""
    leaves = root.get_leaves()
    if len(leaves) > max_rooms:
        leaves = leaves[:max_rooms]

    rooms = []
    for i, leaf in enumerate(leaves):
        # 방 크기: 리프의 65~90%
        w_ratio = random.uniform(0.65, 0.90)
        h_ratio = random.uniform(0.65, 0.90)
        rw = max(40, int(leaf.width * w_ratio))
        rh = max(40, int(leaf.height * h_ratio))

        # 리프 내 랜덤 위치
        rx = leaf.x + random.randint(0, max(0, leaf.width - rw))
        ry = leaf.y + random.randint(0, max(0, leaf.height - rh))

        room_type = "room"
        if i == 0:
            room_type = "entrance"
        elif i == len(leaves) - 1:
            room_type = "objective"

        room = {
            "id": i,
            "x": rx, "y": ry,
            "width": rw, "height": rh,
            "type": room_type,
        }
        leaf.room = room
        rooms.append(room)

    return rooms


def _connect_rooms(root, rooms):
    """형제 노드 간 연결 생성"""
    connections = []
    _connect_siblings(root, connections, rooms)
    return connections


def _connect_siblings(node, connections, rooms):
    """재귀적으로 형제 리프 간 연결"""
    if node.is_leaf():
        return

    if node.left and node.right:
        # 좌우 서브트리의 가장 가까운 방 쌍 연결
        left_rooms = [l.room for l in node.left.get_leaves() if l.room]
        right_rooms = [r.room for r in node.right.get_leaves() if r.room]

        if left_rooms and right_rooms:
            best_pair = None
            best_dist = float("inf")
            for lr in left_rooms:
                for rr in right_rooms:
                    cx1 = lr["x"] + lr["width"] // 2
                    cy1 = lr["y"] + lr["height"] // 2
                    cx2 = rr["x"] + rr["width"] // 2
                    cy2 = rr["y"] + rr["height"] // 2
                    dist = abs(cx1 - cx2) + abs(cy1 - cy2)
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (lr["id"], rr["id"])

            if best_pair:
                connections.append({
                    "from": best_pair[0],
                    "to": best_pair[1],
                    "corridor_length": max(40, best_dist // 5),
                })

    if node.left:
        _connect_siblings(node.left, connections, rooms)
    if node.right:
        _connect_siblings(node.right, connections, rooms)


# ========================================
# 맵 생성 API
# ========================================

# 모듈 상태 (탐사 데이터)
_expeditions = {}  # {region_id: {"rooms", "connections"}}

THREAT_CODES = ["P", "R", "B", "W"]
ROOM_NAMES = {
    "entrance": "입구",
    "corridor": "통로",
    "room": "구역",
    "objective": "목표 지점",
}


def generate_expedition(region_id, difficulty="easy", seed=None):
    """탐사 지역 동적 생성

    Args:
        region_id: 할당할 Region ID (예: 100)
        difficulty: "easy" / "normal" / "hard"
        seed: 랜덤 시드 (None = 랜덤)

    Returns:
        (rooms, connections)
    """
    if seed is not None:
        random.seed(seed)

    cfg = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["easy"])
    target_rooms = random.randint(cfg.room_count_min, cfg.room_count_max)

    # 1. BSP 레이아웃
    root = _build_bsp(cfg.map_width, cfg.map_height,
                      cfg.min_room_size, target_rooms)

    # 2. 방 배치
    rooms = _place_rooms(root, target_rooms)

    # 3. 연결 생성
    connections = _connect_rooms(root, rooms)

    # 연결이 없으면 최소한 순차 연결 보장
    if not connections and len(rooms) > 1:
        for i in range(len(rooms) - 1):
            connections.append({
                "from": i, "to": i + 1,
                "corridor_length": 60,
            })

    # 4. morld에 Region/Location/Gate 생성
    morld.add_region(region_id, f"탐사구역-{region_id}")

    for room in rooms:
        name = ROOM_NAMES.get(room["type"], f"구역-{room['id']}")
        morld.add_location(
            region_id, room["id"], name,
            is_indoor=True, length=room["width"],
        )

    gate_id = 0
    for conn in connections:
        room_a = rooms[conn["from"]]
        room_b = rooms[conn["to"]]

        morld.add_gate(
            region_id, conn["from"], gate_id,
            room_a["width"], region_id, conn["to"], 0,
        )
        gate_id += 1

        morld.add_gate(
            region_id, conn["to"], gate_id,
            0, region_id, conn["from"], room_b["width"],
        )
        gate_id += 1

    # 5. 콘텐츠 배치
    _populate_rooms(region_id, rooms, cfg)

    # 저장
    _expeditions[region_id] = {
        "rooms": rooms,
        "connections": connections,
    }

    print(f"[mapgen] Generated expedition R{region_id}: "
          f"{len(rooms)} rooms, {len(connections)} connections "
          f"(difficulty={difficulty})")

    return rooms, connections


def _populate_rooms(region_id, rooms, cfg):
    """방에 위협/전리품 배치"""
    for room in rooms:
        if room["type"] == "entrance":
            continue

        # 위협 배치
        if random.random() < cfg.enemy_chance:
            threat = random.choice(THREAT_CODES)
            morld.set_unit_prop(
                _room_prop_key(region_id, room["id"]),
                f"threat:{threat}", 1,
            )
            room["threat"] = threat

        # 전리품 배치
        if random.random() < cfg.loot_chance:
            room["has_loot"] = True


def _room_prop_key(region_id, location_id):
    """Location prop 저장용 키 (unit prop 에뮬레이션)

    MockMorld에 set_location_prop이 없으므로,
    rooms 딕셔너리에 직접 저장하고 조회 API 제공.
    """
    # 실제로는 room dict에 저장 (populate에서 직접 설정)
    return None


def cleanup_expedition(region_id):
    """탐사 완료 후 Region 정리"""
    data = _expeditions.pop(region_id, None)
    if not data:
        return

    rooms = data["rooms"]
    for room in rooms:
        # 해당 location의 유닛 제거
        units = morld.get_units_at_location(region_id, room["id"])
        for uid in units:
            morld.remove_unit(uid)
        morld.remove_location(region_id, room["id"])

    print(f"[mapgen] Cleaned up expedition R{region_id}")


def get_expedition_data(region_id):
    """탐사 데이터 조회"""
    return _expeditions.get(region_id)


def get_room_info(region_id, room_id):
    """특정 방 정보 조회"""
    data = _expeditions.get(region_id)
    if not data:
        return None
    for room in data["rooms"]:
        if room["id"] == room_id:
            return room
    return None


def get_rooms_with_threat(region_id):
    """위협이 있는 방 목록"""
    data = _expeditions.get(region_id)
    if not data:
        return []
    return [r for r in data["rooms"] if r.get("threat")]


def get_rooms_with_loot(region_id):
    """전리품이 있는 방 목록"""
    data = _expeditions.get(region_id)
    if not data:
        return []
    return [r for r in data["rooms"] if r.get("has_loot")]


def get_connected_rooms(region_id, room_id):
    """특정 방에서 연결된 방 ID 목록"""
    data = _expeditions.get(region_id)
    if not data:
        return []
    result = []
    for conn in data["connections"]:
        if conn["from"] == room_id:
            result.append(conn["to"])
        elif conn["to"] == room_id:
            result.append(conn["from"])
    return result


def reset():
    """챕터 전환 시 초기화"""
    _expeditions.clear()
