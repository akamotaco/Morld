"""동적 맵 생성 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()


class TestBSPNode(_T):
    def test_leaf_node(self):
        from mapgen import BSPNode
        node = BSPNode(0, 0, 200, 200)
        assert node.is_leaf()
        assert len(node.get_leaves()) == 1

    def test_split(self):
        from mapgen import BSPNode
        node = BSPNode(0, 0, 400, 400)
        result = node.split(100)
        assert result is True
        assert not node.is_leaf()
        assert len(node.get_leaves()) == 2

    def test_split_too_small(self):
        from mapgen import BSPNode
        node = BSPNode(0, 0, 80, 80)
        result = node.split(100)
        assert result is False
        assert node.is_leaf()

    def test_recursive_split(self):
        from mapgen import BSPNode
        node = BSPNode(0, 0, 800, 600)
        node.split(100)
        if node.left:
            node.left.split(100)
        if node.right:
            node.right.split(100)
        leaves = node.get_leaves()
        assert len(leaves) >= 3


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


class TestGenerateExpedition(_T):
    def setUp(self):
        import mapgen
        mapgen.reset()

    def test_generate_creates_region(self):
        import mapgen
        rooms, conns = mapgen.generate_expedition(100, "easy", seed=42)
        assert len(rooms) >= 3
        info = morld.get_region_info(100)
        assert info is not None

    def test_generate_creates_locations(self):
        import mapgen
        rooms, conns = mapgen.generate_expedition(100, "easy", seed=42)
        for room in rooms:
            loc = morld.get_location_info(100, room["id"])
            assert loc is not None, f"Location {room['id']} not found"
            assert loc["length"] == room["width"]

    def test_generate_creates_gates(self):
        import mapgen
        rooms, conns = mapgen.generate_expedition(100, "easy", seed=42)
        assert len(conns) >= 1
        # Each connection creates 2 gates (bidirectional)
        for conn in conns:
            gates_from = morld.get_location_gates(100, conn["from"])
            found = any(g["connected_location"] == conn["to"] for g in gates_from)
            assert found, f"Gate {conn['from']} -> {conn['to']} not found"

    def test_entrance_is_first(self):
        import mapgen
        rooms, _ = mapgen.generate_expedition(100, "easy", seed=42)
        assert rooms[0]["type"] == "entrance"

    def test_objective_is_last(self):
        import mapgen
        rooms, _ = mapgen.generate_expedition(100, "easy", seed=42)
        assert rooms[-1]["type"] == "objective"

    def test_seed_reproducibility(self):
        import mapgen
        rooms1, conns1 = mapgen.generate_expedition(100, "easy", seed=123)
        mapgen.reset()
        morld.reset()
        rooms2, conns2 = mapgen.generate_expedition(100, "easy", seed=123)
        assert len(rooms1) == len(rooms2)
        for r1, r2 in zip(rooms1, rooms2):
            assert r1["id"] == r2["id"]
            assert r1["width"] == r2["width"]

    def test_all_rooms_connected(self):
        """모든 방이 연결 그래프에서 도달 가능한지 확인"""
        import mapgen
        rooms, conns = mapgen.generate_expedition(100, "easy", seed=42)
        if len(rooms) <= 1:
            return
        # BFS from entrance
        adj = {}
        for r in rooms:
            adj[r["id"]] = []
        for c in conns:
            adj[c["from"]].append(c["to"])
            adj[c["to"]].append(c["from"])
        visited = set()
        queue = [0]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        assert len(visited) == len(rooms), (
            f"Not all rooms reachable: {visited} vs {[r['id'] for r in rooms]}"
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
        assert "connections" in data

    def test_get_room_info(self):
        import mapgen
        mapgen.generate_expedition(100, "easy", seed=42)
        room = mapgen.get_room_info(100, 0)
        assert room is not None
        assert room["type"] == "entrance"

    def test_get_connected_rooms(self):
        import mapgen
        rooms, conns = mapgen.generate_expedition(100, "easy", seed=42)
        connected = mapgen.get_connected_rooms(100, 0)
        assert len(connected) >= 1

    def test_cleanup(self):
        import mapgen
        rooms, _ = mapgen.generate_expedition(100, "easy", seed=42)
        mapgen.cleanup_expedition(100)
        assert mapgen.get_expedition_data(100) is None
        # Locations should be removed
        for room in rooms:
            loc = morld.get_location_info(100, room["id"])
            assert loc is None, f"Location {room['id']} not cleaned up"
