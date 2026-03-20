# test_instant_dungeon.py — 인스턴트 던전 테스트
"""
BSP 생성 + builder + manager 통합 테스트.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mock_morld import MockMorld

mock = MockMorld()
sys.modules["morld"] = mock


def _setup():
    mock.reset()
    mock.register_unit(1, "주인공", location=(0, 0))
    mock._player_id = 1
    # 외부 지형 (숲)
    mock.add_region(3, "숲")
    mock.add_location(3, 5, "숲 깊은 곳", length=500)


class _T:
    def __init__(self):
        _setup()
        # manager 리셋
        from instant_dungeon import manager
        manager.reset()


# ========================================
# BSP 생성 테스트
# ========================================

class TestGenerator(_T):

    def test_basic_generation(self):
        """기본 BSP 생성 — 방과 복도가 만들어지는지"""
        from instant_dungeon.generator import generate_dungeon
        rooms, corridors = generate_dungeon(400, 400, min_size=60, max_depth=4, seed=42)

        assert len(rooms) >= 2, f"방이 2개 미만: {len(rooms)}"
        assert len(corridors) >= 1, f"복도가 없음"

    def test_room_types(self):
        """방 타입: start, boss, treasure 할당"""
        from instant_dungeon.generator import generate_dungeon
        rooms, _ = generate_dungeon(400, 400, min_size=60, max_depth=4, seed=42)

        types = {r.room_type for r in rooms}
        assert "start" in types, "시작방 없음"
        assert "boss" in types, "보스방 없음"

    def test_room_bounds(self):
        """모든 방이 전체 영역 내에 있는지"""
        from instant_dungeon.generator import generate_dungeon
        rooms, _ = generate_dungeon(400, 400, min_size=60, max_depth=4, seed=42)

        for room in rooms:
            assert room.x >= 0, f"Room {room.id} x={room.x} < 0"
            assert room.y >= 0, f"Room {room.id} y={room.y} < 0"
            assert room.x + room.w <= 400 + 20, f"Room {room.id} exceeds width"
            assert room.y + room.h <= 400 + 20, f"Room {room.id} exceeds height"

    def test_seed_determinism(self):
        """같은 시드 → 같은 결과"""
        from instant_dungeon.generator import generate_dungeon
        r1, c1 = generate_dungeon(400, 400, seed=123)
        r2, c2 = generate_dungeon(400, 400, seed=123)

        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.x == b.x and a.y == b.y

    def test_different_seeds(self):
        """다른 시드 → 다른 결과"""
        from instant_dungeon.generator import generate_dungeon
        r1, _ = generate_dungeon(400, 400, seed=1)
        r2, _ = generate_dungeon(400, 400, seed=2)

        # 모든 방이 동일할 확률은 거의 0
        coords1 = [(r.x, r.y) for r in r1]
        coords2 = [(r.x, r.y) for r in r2]
        assert coords1 != coords2

    def test_ascii_render(self):
        """ASCII 맵 렌더링 (크래시 없이 동작)"""
        from instant_dungeon.generator import generate_dungeon, render_ascii
        rooms, corridors = generate_dungeon(400, 400, seed=42)
        ascii_map = render_ascii(rooms, corridors, 400, 400, scale=10)

        assert len(ascii_map) > 0
        assert "S" in ascii_map  # 시작방
        assert "B" in ascii_map  # 보스방

    def test_depth_affects_room_count(self):
        """max_depth 높으면 방 더 많음"""
        from instant_dungeon.generator import generate_dungeon
        r_shallow, _ = generate_dungeon(400, 400, max_depth=2, seed=42)
        r_deep, _ = generate_dungeon(400, 400, max_depth=5, seed=42)

        assert len(r_deep) >= len(r_shallow)


# ========================================
# Builder 테스트
# ========================================

class TestBuilder(_T):

    def test_build_creates_locations(self):
        """builder가 Location을 생성하는지"""
        from instant_dungeon.generator import generate_dungeon
        from instant_dungeon.builder import build_dungeon

        rooms, corridors = generate_dungeon(300, 300, max_depth=3, seed=42)
        info = build_dungeon(rooms, corridors, 100, "테스트 던전")

        assert info["region_id"] == 100
        assert len(info["locations"]) == len(rooms)

    def test_build_with_entrance(self):
        """외부 입구 Gate 연결"""
        from instant_dungeon.generator import generate_dungeon
        from instant_dungeon.builder import build_dungeon

        rooms, corridors = generate_dungeon(300, 300, max_depth=3, seed=42)
        info = build_dungeon(rooms, corridors, 100, "테스트 던전",
                             entrance_gate={
                                 "region_id": 3,
                                 "location_id": 5,
                                 "gate_x": 400,
                                 "arrival_x": 10,
                             })

        assert info["entrance_location"] == 0


# ========================================
# Manager 테스트
# ========================================

class TestManager(_T):

    def test_create_dungeon(self):
        """던전 생성 + 조회"""
        from instant_dungeon.manager import create_dungeon, get_dungeon_info

        did = create_dungeon("숲속 동굴", seed=42,
                             entrance_gate={
                                 "region_id": 3,
                                 "location_id": 5,
                                 "gate_x": 400,
                                 "arrival_x": 10,
                             })

        info = get_dungeon_info(did)
        assert info is not None
        assert info["region_id"] >= 100
        assert len(info["rooms"]) >= 2

    def test_destroy_dungeon(self):
        """던전 삭제"""
        from instant_dungeon.manager import create_dungeon, destroy_dungeon, get_dungeon_info

        did = create_dungeon("임시 던전", seed=42)
        assert get_dungeon_info(did) is not None

        destroy_dungeon(did)
        assert get_dungeon_info(did) is None

    def test_multiple_dungeons(self):
        """여러 던전 동시 생성"""
        from instant_dungeon.manager import create_dungeon, get_active_dungeons

        create_dungeon("던전 A", seed=1)
        create_dungeon("던전 B", seed=2)

        active = get_active_dungeons()
        assert len(active) == 2

    def test_region_id_increment(self):
        """Region ID 자동 증가"""
        from instant_dungeon.manager import create_dungeon, get_dungeon_info

        did1 = create_dungeon("A", seed=1)
        did2 = create_dungeon("B", seed=2)

        info1 = get_dungeon_info(did1)
        info2 = get_dungeon_info(did2)

        assert info2["region_id"] == info1["region_id"] + 1

    def test_player_evacuation_on_destroy(self):
        """삭제 시 플레이어가 내부에 있으면 탈출"""
        from instant_dungeon.manager import create_dungeon, destroy_dungeon, get_dungeon_info

        did = create_dungeon("탈출 테스트", seed=42)
        info = get_dungeon_info(did)
        region_id = info["region_id"]

        # 플레이어를 던전 내부로 이동
        mock.set_unit_location(1, region_id, 0)

        destroy_dungeon(did)

        # 플레이어가 외부로 텔레포트되었는지
        loc = mock.get_unit_location(1)
        assert loc[0] != region_id, "플레이어가 아직 던전 내부"

    def test_dungeon_for_region(self):
        """Region ID로 던전 조회"""
        from instant_dungeon.manager import create_dungeon, get_dungeon_for_region

        did = create_dungeon("조회 테스트", seed=42)
        from instant_dungeon.manager import _active_dungeons
        region_id = _active_dungeons[did]["region_id"]

        found_id, found_info = get_dungeon_for_region(region_id)
        assert found_id == did

    def test_reset(self):
        """리셋 후 모든 던전 정보 초기화"""
        from instant_dungeon.manager import create_dungeon, reset, get_active_dungeons

        create_dungeon("A", seed=1)
        create_dungeon("B", seed=2)
        assert len(get_active_dungeons()) == 2

        reset()
        assert len(get_active_dungeons()) == 0
