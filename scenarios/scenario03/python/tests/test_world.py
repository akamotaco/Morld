"""World 초기화 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()


class TestPlatformRegion(_T):
    def test_terrain_init(self):
        from world.platform import initialize_terrain, REGION_ID
        initialize_terrain()
        # Region exists
        assert morld.region_exists(REGION_ID)
        # 3 locations
        assert morld.get_location_info(REGION_ID, 0) is not None  # 승강장
        assert morld.get_location_info(REGION_ID, 1) is not None  # 통로
        assert morld.get_location_info(REGION_ID, 2) is not None  # 통신실

    def test_location_lengths(self):
        from world.platform import initialize_terrain, REGION_ID
        initialize_terrain()
        assert morld.get_location_info(REGION_ID, 0)["length"] == 200  # 승강장
        assert morld.get_location_info(REGION_ID, 1)["length"] == 100  # 통로
        assert morld.get_location_info(REGION_ID, 2)["length"] == 40   # 통신실

    def test_gates_registered(self):
        from world.platform import initialize_terrain, GATES
        initialize_terrain()
        # GATES should have 6 entries (3 bidirectional pairs)
        assert len(GATES) == 6


class TestTrainRegion(_T):
    def test_terrain_init(self):
        from world.train import initialize_terrain, REGION_ID
        initialize_terrain()
        assert morld.region_exists(REGION_ID)
        assert morld.get_location_info(REGION_ID, 0) is not None  # 객차

    def test_train_car_length(self):
        from world.train import initialize_terrain, REGION_ID
        initialize_terrain()
        assert morld.get_location_info(REGION_ID, 0)["length"] == 150


class TestWorldInit(_T):
    def test_initialize_world(self):
        from world import initialize_world
        initialize_world()
        # Both regions exist
        assert morld.region_exists(0)  # 플랫폼
        assert morld.region_exists(1)  # 지저철
        # All locations exist
        assert morld.get_location_info(0, 0) is not None
        assert morld.get_location_info(0, 1) is not None
        assert morld.get_location_info(0, 2) is not None
        assert morld.get_location_info(1, 0) is not None
