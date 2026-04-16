# test_instant_dungeon.py — 인스턴트 던전 테스트
"""
BSP 생성 (common/dungeon) + builder + manager (v2) 통합 테스트.
"""

import sys
import os

_test_dir = os.path.dirname(os.path.abspath(__file__))
_s02_dir = os.path.join(_test_dir, "..")
_common_dir = os.path.join(_test_dir, "..", "..", "..", "common", "python")

if _s02_dir not in sys.path:
    sys.path.insert(0, _s02_dir)
if _common_dir not in sys.path:
    sys.path.insert(0, _common_dir)

from mock_morld import MockMorld

mock = MockMorld()
sys.modules["morld"] = mock


# 테스트용 Spec
_TEST_SPEC = {
    "name": "숲속 동굴",
    "max_floors": 3,
    "base": {
        "width": 400,
        "height": 400,
        "min_size": 60,
        "max_depth": 4,
    },
    "environment": {
        "indoor": True,
        "temperature_mod": -3,
    },
    "connections": {
        "type": "linear",
        "stairs_per_floor": 1,
        "bridges_per_floor": 2,
        "bridge_max_distance": 300,
    },
}

_TEST_ENTRANCE_GATE = {
    "region_id": 3,
    "location_id": 5,
    "distance": 60,
}


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
        from instant_dungeon import manager
        manager.reset()


# ========================================
# BSP 생성 테스트 (common/dungeon)
# ========================================

class TestGenerator(_T):

    def test_basic_generation(self):
        """기본 BSP 생성 — 방과 복도가 만들어지는지"""
        from dungeon.generator import generate_dungeon
        rooms, corridors = generate_dungeon(400, 400, min_size=60, max_depth=4, seed=42)

        assert len(rooms) >= 2, "방이 2개 미만: " + str(len(rooms))
        assert len(corridors) >= 1, "복도가 없음"

    def test_room_types(self):
        """방 타입: generate_floor + assign_types 콜백으로 할당"""
        from dungeon.generator import generate_floor

        spec_base = {"width": 400, "height": 400, "min_size": 60, "max_depth": 4}

        def assign(rooms, fn):
            if rooms:
                rooms[0].room_type = "start"
                rooms[-1].room_type = "boss"
                if len(rooms) > 3:
                    rooms[len(rooms) // 2].room_type = "treasure"

        rooms, _, _ = generate_floor(spec_base, 0, seed=42, assign_types=assign)

        types = set()
        for r in rooms:
            types.add(r.room_type)
        assert "start" in types, "시작방 없음"
        assert "boss" in types, "보스방 없음"

    def test_room_bounds(self):
        """모든 방이 전체 영역 내에 있는지"""
        from dungeon.generator import generate_dungeon
        rooms, _ = generate_dungeon(400, 400, min_size=60, max_depth=4, seed=42)

        for room in rooms:
            assert room.x >= 0, "Room " + str(room.id) + " x=" + str(room.x) + " < 0"
            assert room.y >= 0, "Room " + str(room.id) + " y=" + str(room.y) + " < 0"
            assert room.x + room.w <= 400 + 20, "Room " + str(room.id) + " exceeds width"
            assert room.y + room.h <= 400 + 20, "Room " + str(room.id) + " exceeds height"

    def test_seed_determinism(self):
        """같은 시드 → 같은 결과"""
        from dungeon.generator import generate_dungeon
        r1, c1 = generate_dungeon(400, 400, seed=123)
        r2, c2 = generate_dungeon(400, 400, seed=123)

        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.x == b.x and a.y == b.y

    def test_different_seeds(self):
        """다른 시드 → 다른 결과"""
        from dungeon.generator import generate_dungeon
        r1, _ = generate_dungeon(400, 400, seed=1)
        r2, _ = generate_dungeon(400, 400, seed=2)

        coords1 = [(r.x, r.y) for r in r1]
        coords2 = [(r.x, r.y) for r in r2]
        assert coords1 != coords2

    def test_ascii_render(self):
        """ASCII 맵 렌더링 (크래시 없이 동작, 타입 할당 포함)"""
        from dungeon.generator import generate_floor, render_ascii

        spec_base = {"width": 400, "height": 400, "min_size": 60, "max_depth": 4}

        def assign(rooms, fn):
            if rooms:
                rooms[0].room_type = "start"
                rooms[-1].room_type = "boss"

        rooms, corridors, _ = generate_floor(spec_base, 0, seed=42, assign_types=assign)
        ascii_map = render_ascii(rooms, corridors, 400, 400, scale=10)

        assert len(ascii_map) > 0
        assert "S" in ascii_map  # 시작방
        assert "B" in ascii_map  # 보스방

    def test_depth_affects_room_count(self):
        """max_depth 높으면 방 더 많음"""
        from dungeon.generator import generate_dungeon
        r_shallow, _ = generate_dungeon(400, 400, max_depth=2, seed=42)
        r_deep, _ = generate_dungeon(400, 400, max_depth=5, seed=42)

        assert len(r_deep) >= len(r_shallow)


# ========================================
# Builder 테스트
# ========================================

class TestBuilder(_T):

    def test_build_creates_locations(self):
        """build_floor_interior가 Location을 생성하는지"""
        from dungeon.generator import generate_dungeon
        from instant_dungeon.builder import build_floor_interior

        rooms, corridors = generate_dungeon(300, 300, max_depth=3, seed=42)
        info = build_floor_interior(rooms, corridors, [], 100, "테스트 던전")

        assert info["region_id"] == 100
        assert len(info["locations"]) == len(rooms)

    def test_build_with_entrance_gate(self):
        """create_dungeon_entrance가 외부 Gate를 연결하는지"""
        from instant_dungeon.manager import create_dungeon_entrance, get_dungeon_info

        did = create_dungeon_entrance(
            _TEST_SPEC, seed=42, entrance_gate=_TEST_ENTRANCE_GATE)
        info = get_dungeon_info(did)

        assert info is not None
        assert info["entrance_location"] == 0
        assert info["_entrance_ext_region"] == 3
        assert info["_entrance_ext_location"] == 5


# ========================================
# Manager 테스트
# ========================================

class TestManager(_T):

    def test_create_dungeon(self):
        """던전 입구 생성 + 조회"""
        from instant_dungeon.manager import create_dungeon_entrance, get_dungeon_info

        did = create_dungeon_entrance(
            _TEST_SPEC, seed=42, entrance_gate=_TEST_ENTRANCE_GATE)

        info = get_dungeon_info(did)
        assert info is not None
        assert info["base_region_id"] >= 100
        # Phase 1은 입구만 생성 — rooms는 expand_floor 후에만 존재
        assert info["entrance_location"] == 0

    def test_destroy_dungeon(self):
        """던전 삭제"""
        from instant_dungeon.manager import create_dungeon_entrance, destroy_dungeon, get_dungeon_info

        did = create_dungeon_entrance(_TEST_SPEC, seed=42)
        assert get_dungeon_info(did) is not None

        destroy_dungeon(did)
        assert get_dungeon_info(did) is None

    def test_multiple_dungeons(self):
        """여러 던전 동시 생성"""
        from instant_dungeon.manager import create_dungeon_entrance, get_active_dungeons

        create_dungeon_entrance(_TEST_SPEC, seed=1)
        create_dungeon_entrance(_TEST_SPEC, seed=2)

        active = get_active_dungeons()
        assert len(active) == 2

    def test_region_id_increment(self):
        """Region ID 자동 증가"""
        from instant_dungeon.manager import create_dungeon_entrance, get_dungeon_info

        did1 = create_dungeon_entrance(_TEST_SPEC, seed=1)
        did2 = create_dungeon_entrance(_TEST_SPEC, seed=2)

        info1 = get_dungeon_info(did1)
        info2 = get_dungeon_info(did2)

        assert info2["base_region_id"] == info1["base_region_id"] + 1

    def test_player_evacuation_on_destroy(self):
        """삭제 시 플레이어가 내부에 있으면 탈출"""
        from instant_dungeon.manager import create_dungeon_entrance, destroy_dungeon, get_dungeon_info

        did = create_dungeon_entrance(
            _TEST_SPEC, seed=42, entrance_gate=_TEST_ENTRANCE_GATE)
        info = get_dungeon_info(did)
        region_id = info["base_region_id"]

        # 플레이어를 던전 내부로 이동
        mock.set_unit_location(1, region_id, 0)

        destroy_dungeon(did)

        # 플레이어가 외부로 텔레포트되었는지
        loc = mock.get_unit_location(1)
        assert loc[0] != region_id, "플레이어가 아직 던전 내부"

    def test_dungeon_for_region(self):
        """Region ID로 던전 조회"""
        from instant_dungeon.manager import create_dungeon_entrance, get_dungeon_for_region

        did = create_dungeon_entrance(_TEST_SPEC, seed=42)
        from instant_dungeon.manager import _active_dungeons
        region_id = _active_dungeons[did]["base_region_id"]

        found_id, found_info = get_dungeon_for_region(region_id)
        assert found_id == did

    def test_reset(self):
        """리셋 후 모든 던전 정보 초기화"""
        from instant_dungeon.manager import create_dungeon_entrance, reset, get_active_dungeons

        create_dungeon_entrance(_TEST_SPEC, seed=1)
        create_dungeon_entrance(_TEST_SPEC, seed=2)
        assert len(get_active_dungeons()) == 2

        reset()
        assert len(get_active_dungeons()) == 0

    def test_is_dungeon_occupied_empty(self):
        """빈 던전 → 비점유"""
        from instant_dungeon.manager import create_dungeon_entrance, is_dungeon_occupied

        did = create_dungeon_entrance(_TEST_SPEC, seed=42)
        assert is_dungeon_occupied(did) == False

    def test_is_dungeon_occupied_player(self):
        """플레이어가 내부에 있으면 점유 (expand 후)"""
        from instant_dungeon.manager import (
            create_dungeon_entrance, is_dungeon_occupied, expand_floor, get_dungeon_info)

        did = create_dungeon_entrance(_TEST_SPEC, seed=42)
        # Phase 2: 1층 확장 (floors_generated에 rooms/locations 등록)
        expand_floor(did, 1)
        info = get_dungeon_info(did)

        # 확장된 1층의 첫 location으로 이동
        floor_data = info["floors_generated"].get(1)
        if floor_data:
            region_id = floor_data["region_id"]
            first_loc = list(floor_data["locations"].values())[0]
            mock.set_unit_location(1, region_id, first_loc)
            assert is_dungeon_occupied(did) == True


# ========================================
# 스케줄러 테스트
# ========================================

class TestScheduler(_T):

    def setUp(self):
        from instant_dungeon import scheduler
        scheduler.reset()

    def test_create_at_9am(self):
        """09:00에 던전 생성"""
        from instant_dungeon import scheduler
        scheduler.reset()

        mock._time_info = {"hour": 9, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)

        assert scheduler.get_active_dungeon_id() is not None

    def test_no_create_before_9am(self):
        """09:00 전에는 생성 안 함"""
        from instant_dungeon import scheduler
        scheduler.reset()

        mock._time_info = {"hour": 8, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)

        assert scheduler.get_active_dungeon_id() is None

    def test_destroy_at_22pm_empty(self):
        """22:00에 빈 던전 삭제"""
        from instant_dungeon import scheduler
        scheduler.reset()

        mock._time_info = {"hour": 9, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        assert scheduler.get_active_dungeon_id() is not None

        mock._time_info = {"hour": 22, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        assert scheduler.get_active_dungeon_id() is None

    def test_no_destroy_if_occupied(self):
        """22:00이지만 내부에 플레이어 → 삭제 안 함 (expand 후 점유)"""
        from instant_dungeon import scheduler
        from instant_dungeon.manager import get_dungeon_info, expand_floor
        scheduler.reset()

        # 생성
        mock._time_info = {"hour": 9, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        did = scheduler.get_active_dungeon_id()
        # Phase 2 확장
        expand_floor(did, 1)
        info = get_dungeon_info(did)
        floor_data = info["floors_generated"].get(1)
        assert floor_data is not None, "expand_floor didn't generate floor 1"
        region_id = floor_data["region_id"]
        first_loc = list(floor_data["locations"].values())[0]

        # 플레이어 내부 이동
        mock.set_unit_location(1, region_id, first_loc)

        # 삭제 시도 → 점유 상태라 유지
        mock._time_info = {"hour": 22, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        assert scheduler.get_active_dungeon_id() == did

        # 플레이어 퇴장
        mock.set_unit_location(1, 0, 0)

        # 다시 시도 → 삭제
        mock._time_info = {"hour": 23, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        assert scheduler.get_active_dungeon_id() is None

    def test_no_duplicate_creation(self):
        """같은 날 중복 생성 방지"""
        from instant_dungeon import scheduler
        scheduler.reset()

        mock._time_info = {"hour": 9, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        did1 = scheduler.get_active_dungeon_id()

        mock._time_info = {"hour": 10, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        did2 = scheduler.get_active_dungeon_id()

        assert did1 == did2

    def test_new_day_new_dungeon(self):
        """다음 날 → 새 던전"""
        from instant_dungeon import scheduler
        scheduler.reset()

        mock._time_info = {"hour": 9, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        did1 = scheduler.get_active_dungeon_id()

        mock._time_info = {"hour": 22, "day": 1, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)

        mock._time_info = {"hour": 9, "day": 2, "month": 1, "year": 1, "minute": 0}
        scheduler._on_time_elapsed(3_600_000)
        did2 = scheduler.get_active_dungeon_id()

        assert did2 is not None
        assert did2 != did1
