# test_environment.py — 엔진 환경 시스템 직접 단위 테스트
#
# 목적: temperature/humidity/pollution/sound/congestion을 시나리오 통합 테스트가
# 아닌 엔진 위치에서 직접 검증. P3(C# 승격) 전후 동일 동작을 보증하는 안전망.
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import morld  # run_tests.py가 주입한 mock


def _make_world(locations=((0, 0),), length=100):
    """Region 0 + 지정 location들 생성"""
    morld.add_region(0, "테스트지역")
    for r, l in locations:
        morld.add_location(r, l, f"장소{l}", 0, True, None, None, None,
                           "line", length)


def _link(r1, l1, r2, l2, gate_id_base=0):
    """양방향 gate 연결"""
    morld.add_gate(r1, l1, gate_id_base, 90, r2, l2, 10)
    morld.add_gate(r2, l2, gate_id_base + 1, 10, r1, l1, 90)


class _T:
    def setUp(self):
        from engine import region_registry
        region_registry.reset()


# ============================================
# pollution — 오염 수치 조작
# ============================================

class TestPollution(_T):
    def setUp(self):
        super().setUp()
        from engine import pollution
        pollution.reset()
        _make_world()
        pollution.register_location(0, 0, max_pollution=100, rate=5)

    def test_set_get_location_pollution(self):
        from engine import pollution
        pollution.set_location_pollution(0, 0, 40)
        assert pollution.get_location_pollution(0, 0) == 40

    def test_clean_location_reduces(self):
        from engine import pollution
        pollution.set_location_pollution(0, 0, 40)
        pollution.clean_location(0, 0, 15)
        assert pollution.get_location_pollution(0, 0) == 25

    def test_unit_pollution_roundtrip(self):
        from engine import pollution
        morld.register_unit(1, name="유닛")
        pollution.set_unit_pollution(1, 30)
        assert pollution.get_unit_pollution(1) == 30
        pollution.clean_unit(1, 10)
        assert pollution.get_unit_pollution(1) == 20


# ============================================
# congestion — 인구/수용량/혼잡도
# ============================================

class TestCongestion(_T):
    def setUp(self):
        super().setUp()
        from engine import congestion
        _make_world(length=100)
        congestion.reset()

    def test_capacity_from_length(self):
        from engine import congestion
        assert congestion.get_capacity(0, 0) >= 1

    def test_reach_and_leave_population(self):
        from engine import congestion
        # lazy-init 인구 스캔에 잡히지 않도록 등록 외 위치에서 출발
        morld.register_unit(1, name="유닛", location=(9, 9))
        congestion.on_unit_reach(1, 0, 0)
        assert congestion.get_population(0, 0) == 1
        congestion.on_unit_leave(1, 0, 0)
        assert congestion.get_population(0, 0) == 0

    def test_congestion_ratio(self):
        from engine import congestion
        cap = congestion.get_capacity(0, 0)
        for uid in range(1, cap + 1):
            morld.register_unit(uid, name=f"유닛{uid}", location=(0, 0))
            congestion.on_unit_reach(uid, 0, 0)
        assert congestion.get_congestion(0, 0) >= 1.0


# ============================================
# sound — BFS 전파 + 청취
# ============================================

class TestSound(_T):
    def setUp(self):
        super().setUp()
        from engine import sound
        _make_world(locations=((0, 0), (0, 1)), length=50)
        _link(0, 0, 0, 1)
        sound.reset()
        # reset()은 _hearing/_heard_events를 보존하므로 테스트 간 명시 정리
        for uid in (1, 2, 3):
            sound.unregister_hearing(uid)
        sound.flush()
        morld.register_unit(1, name="발신자", location=(0, 0))
        morld.register_unit(2, name="청취자", location=(0, 1))
        morld.register_unit(3, name="동석자", location=(0, 0))

    def test_adjacent_location_hears(self):
        from engine import sound
        sound.register_hearing(2, "normal")
        sound.emit_sound(1, "테스트음", intensity=90)
        heard = sound.get_heard(2)
        assert heard, "인접 location 청취자가 소리를 못 들음"

    def test_same_location_hears(self):
        from engine import sound
        sound.register_hearing(3, "normal")
        sound.emit_sound(1, "테스트음", intensity=90)
        assert sound.get_heard(3), "같은 location 청취자가 소리를 못 들음"

    def test_unregistered_does_not_hear(self):
        from engine import sound
        sound.emit_sound(1, "테스트음", intensity=90)
        assert not sound.get_heard(2), "미등록 유닛이 소리를 들음"

    def test_source_does_not_hear_self(self):
        from engine import sound
        sound.register_hearing(1, "normal")
        sound.emit_sound(1, "테스트음", intensity=90)
        assert not sound.get_heard(1), "발신자가 자기 소리를 들음"


# ============================================
# temperature — 체온/장소 온도
# ============================================

class TestTemperature(_T):
    def setUp(self):
        super().setUp()
        from engine import temperature
        temperature.reset()
        _make_world()

    def test_body_temperature_roundtrip(self):
        from engine import temperature
        morld.register_unit(1, name="유닛", location=(0, 0))
        temperature.register_character(1)
        temperature.set_body_temperature(1, 36)
        assert temperature.get_body_temperature(1) == 36

    def test_dynamic_location_temperature_numeric(self):
        from engine import temperature
        temperature.register_dynamic_location(0, 0, is_indoor=True)
        t = temperature.get_temperature(0, 0)
        assert isinstance(t, (int, float)), f"온도가 숫자가 아님: {t!r}"


# ============================================
# humidity — 습도/젖음
# ============================================

class TestHumidity(_T):
    def setUp(self):
        super().setUp()
        from engine import humidity
        humidity.reset()
        _make_world()

    def test_unit_wetness_default_zero(self):
        from engine import humidity
        morld.register_unit(1, name="유닛", location=(0, 0))
        assert humidity.get_unit_wetness(1) == 0

    def test_dry_unit_no_crash(self):
        from engine import humidity
        morld.register_unit(1, name="유닛", location=(0, 0))
        humidity.dry_unit(1, 10)
        assert humidity.get_unit_wetness(1) == 0


# ============================================
# reset 계약 — 엔진 전 모듈 준수 강제
# ============================================

class TestResetContract:
    def test_all_engine_modules_have_reset(self):
        """pi-world 계약: engine/ 모든 모듈은 reset()을 제공해야 한다."""
        import importlib
        engine_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "engine"))
        missing = []
        for fname in sorted(os.listdir(engine_dir)):
            if not fname.endswith(".py"):
                continue
            name = fname[:-3]
            if name.startswith("__") or name.startswith("test_"):
                continue
            mod = importlib.import_module(f"engine.{name}")
            if not hasattr(mod, "reset") or not callable(mod.reset):
                missing.append(name)
        assert not missing, f"reset() 누락 모듈: {missing}"

    def test_quest_reporter_reset_restores_baseline(self):
        from engine import quest_reporter
        quest_reporter.register_confirm_action("테스트액션", lambda *a: None)
        quest_reporter.reset()
        handlers = quest_reporter._confirm_action_handlers
        assert "consume_item" in handlers, "기본 consume_item이 사라짐"
        assert "테스트액션" not in handlers, "시나리오 핸들러가 reset 후 잔존"

    def test_body_state_reset_keeps_human(self):
        from engine import body_state
        body_state.register_layout("늑대", {"부위": []})
        body_state.reset()
        assert "human" in body_state._LAYOUTS
        assert "늑대" not in body_state._LAYOUTS
