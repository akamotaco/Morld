"""챕터 초기화 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()
        # Clear agent registry (chapters register agents)
        from think.registry import clear_all
        clear_all()


class TestDemoChapter(_T):
    def test_initialize(self):
        from chapters.demo import initialize
        initialize()
        # Regions created
        assert morld.region_exists(0)  # 플랫폼
        assert morld.region_exists(1)  # 지저철
        # Time frozen (프롤로그 전)
        assert morld.is_time_frozen() == True

    def test_secretary_placed(self):
        from chapters.demo import initialize
        initialize()
        # Secretary should be at comm_room (R0, L2)
        units = morld.get_units_at_location(0, 2)
        # At least secretary + CRT console
        assert len(units) >= 1

    def test_subway_train_placed(self):
        from chapters.demo import initialize
        initialize()
        # SubwayTrain at station (R0, L0)
        units = morld.get_units_at_location(0, 0)
        found_train = False
        for uid in units:
            info = morld.get_unit_info(uid)
            if info and info.get("unique_id") == "subway_train":
                found_train = True
                break
        assert found_train, "SubwayTrain not found at station"

    def test_time_settings(self):
        from chapters.demo import initialize
        initialize()
        # Time should be set (not 0)
        assert morld.get_game_time() > 0
