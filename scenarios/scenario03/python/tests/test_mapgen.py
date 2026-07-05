"""동적 맵 생성 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()


# 구 BSPNode 클래스는 BSP 공통화 리팩터로 소멸 (dungeon.generator 내부 _BSPNode
# + 모듈 함수로 대체). 내부 노드 대신 공개 API generate_dungeon 동작을 검증한다.
class TestGenerateDungeon(_T):
    def test_generates_rooms_and_corridors(self):
        from dungeon.generator import generate_dungeon
        rooms, corridors = generate_dungeon(400, 400, min_size=100, seed=42)
        assert len(rooms) >= 2
        # 복도는 방들을 연결 (형제 연결 방식 → 방-1개 이상)
        assert len(corridors) >= len(rooms) - 1

    def test_small_space_single_room(self):
        from dungeon.generator import generate_dungeon
        # min_size보다 작은 공간 → 분할 불가 → 방 1개
        rooms, corridors = generate_dungeon(80, 80, min_size=100, seed=42)
        assert len(rooms) == 1
        assert corridors == []

    def test_seed_reproducibility(self):
        from dungeon.generator import generate_dungeon
        rooms1, _ = generate_dungeon(800, 600, min_size=100, seed=123)
        rooms2, _ = generate_dungeon(800, 600, min_size=100, seed=123)
        assert [(r.x, r.y, r.w, r.h) for r in rooms1] == \
               [(r.x, r.y, r.w, r.h) for r in rooms2]

    def test_rooms_minimum_size(self):
        from dungeon.generator import generate_dungeon
        rooms, _ = generate_dungeon(800, 600, min_size=100, seed=7)
        for r in rooms:
            assert r.w >= 20 and r.h >= 20


class TestDifficultyConfig(_T):
    def test_presets_exist(self):
        from mapgen import DIFFICULTY_PRESETS
        assert "easy" in DIFFICULTY_PRESETS
        assert "normal" in DIFFICULTY_PRESETS
        assert "hard" in DIFFICULTY_PRESETS

    def test_easy_has_fewer_rooms(self):
        from mapgen import DIFFICULTY_PRESETS
        easy = DIFFICULTY_PRESETS["easy"]
        hard = DIFFICULTY_PRESETS["hard"]
        assert easy.room_count_max <= hard.room_count_max


# BSP 공통화 리팩터 이후 API: generate_expedition → (rooms, corridors, bridges)
# rooms = dungeon.generator.Room 객체 (r.id/r.w/r.room_type),
# corridors = Corridor 객체 (c.room_a/c.room_b).
class TestGenerateExpedition(_T):
    def setUp(self):
        import mapgen
        mapgen.reset()

    def test_generate_creates_region(self):
        import mapgen
        rooms, conns, bridges = mapgen.generate_expedition(100, "easy", seed=42)
        assert len(rooms) >= 3
        info = morld.get_region_info(100)
        assert info is not None

    def test_generate_creates_locations(self):
        import mapgen
        rooms, conns, bridges = mapgen.generate_expedition(100, "easy", seed=42)
        for room in rooms:
            loc = morld.get_location_info(100, room.id)
            assert loc is not None, f"Location {room.id} not found"
            assert loc["length"] == room.w

    def test_generate_creates_gates(self):
        import mapgen
        rooms, conns, bridges = mapgen.generate_expedition(100, "easy", seed=42)
        assert len(conns) >= 1
        # Each connection creates 2 gates (bidirectional)
        for conn in conns:
            gates_from = morld.get_location_gates(100, conn.room_a)
            found = any(g["connected_location"] == conn.room_b
                        for g in gates_from)
            assert found, f"Gate {conn.room_a} -> {conn.room_b} not found"

    def test_entrance_is_first(self):
        import mapgen
        rooms, _, _ = mapgen.generate_expedition(100, "easy", seed=42)
        assert rooms[0].room_type == "entrance"

    def test_objective_is_last(self):
        import mapgen
        rooms, _, _ = mapgen.generate_expedition(100, "easy", seed=42)
        assert rooms[-1].room_type == "objective"

    def test_seed_reproducibility(self):
        import mapgen
        rooms1, conns1, _ = mapgen.generate_expedition(100, "easy", seed=123)
        mapgen.reset()
        morld.reset()
        rooms2, conns2, _ = mapgen.generate_expedition(100, "easy", seed=123)
        assert len(rooms1) == len(rooms2)
        for r1, r2 in zip(rooms1, rooms2):
            assert r1.id == r2.id
            assert r1.w == r2.w

    def test_all_rooms_connected(self):
        """모든 방이 연결 그래프에서 도달 가능한지 확인"""
        import mapgen
        rooms, conns, bridges = mapgen.generate_expedition(100, "easy", seed=42)
        if len(rooms) <= 1:
            return
        # BFS from entrance
        adj = {}
        for r in rooms:
            adj[r.id] = []
        for c in conns:
            adj[c.room_a].append(c.room_b)
            adj[c.room_b].append(c.room_a)
        visited = set()
        queue = [rooms[0].id]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        assert len(visited) == len(rooms), (
            f"Not all rooms reachable: {visited} vs {[r.id for r in rooms]}"
        )


class TestExpeditionData(_T):
    def setUp(self):
        import mapgen
        mapgen.reset()

    def test_get_expedition_data(self):
        import mapgen
        mapgen.generate_expedition(100, "easy", seed=42)
        data = mapgen.get_expedition_data(100)
        assert data is not None
        assert "rooms" in data
        assert "corridors" in data
        assert "bridges" in data

    def test_cleanup(self):
        import mapgen
        rooms, _, _ = mapgen.generate_expedition(100, "easy", seed=42)
        mapgen.cleanup_expedition(100)
        assert mapgen.get_expedition_data(100) is None
        # Locations should be removed
        for room in rooms:
            loc = morld.get_location_info(100, room.id)
            assert loc is None, f"Location {room.id} not cleaned up"


class TestPopulateRooms(_T):
    def setUp(self):
        import mapgen
        mapgen.reset()

    def test_content_generated(self):
        import mapgen
        rooms, _, _ = mapgen.generate_expedition(100, "easy", seed=42)
        content = mapgen.get_room_content(100)
        assert set(content.keys()) == {r.id for r in rooms}
        for entry in content.values():
            assert "threat" in entry and "loot" in entry

    def test_entrance_always_safe(self):
        import mapgen
        for seed in range(10):
            mapgen.reset()
            rooms, _, _ = mapgen.generate_expedition(100, "hard", seed=seed)
            content = mapgen.get_room_content(100)
            entrance = next(r for r in rooms if r.room_type == "entrance")
            assert content[entrance.id]["threat"] is None
            assert content[entrance.id]["loot"] == {}

    def test_objective_has_threat_and_loot(self):
        import mapgen
        rooms, _, _ = mapgen.generate_expedition(100, "easy", seed=7)
        content = mapgen.get_room_content(100)
        objective = next(r for r in rooms if r.room_type == "objective")
        assert content[objective.id]["threat"] in mapgen.THREAT_CODES
        assert content[objective.id]["loot"]

    def test_threat_codes_match_difficulty_pool(self):
        import mapgen
        allowed = {c for c, _ in mapgen.THREAT_WEIGHTS["easy"]}
        for seed in range(10):
            mapgen.reset()
            mapgen.generate_expedition(100, "easy", seed=seed)
            for entry in mapgen.get_room_content(100).values():
                if entry["threat"]:
                    assert entry["threat"] in allowed
