# test_semen.py — 정액 게이지 시스템 테스트
"""
semen.py 모듈의 핵심 API 테스트.

NOTE: semen.py의 모듈 레벨 subscribe_time_elapsed 호출은
events 패키지의 전체 import chain을 유발하므로,
테스트에서는 events 모듈을 먼저 mock 처리한다.
"""
import sys
import os

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)


# events 모듈 mock — subscribe_time_elapsed만 제공
class _MockEvents:
    def subscribe_time_elapsed(self, callback, min_interval=None):
        pass

if "events" not in sys.modules:
    sys.modules["events"] = _MockEvents()


def _setup(unit_id=100, initial_semen=None, props=None):
    """테스트 공통 셋업: morld reset + semen reset + 유닛 등록"""
    import morld
    morld.reset()
    import semen
    semen.reset()

    base_props = dict(props or {})
    morld.register_unit(unit_id, name="테스트", props=base_props)

    # 직접 registry에 등록 (gender mock 불필요)
    semen._registry.add(unit_id)
    semen._accumulated[unit_id] = 0
    if initial_semen is not None:
        morld.set_unit_prop(unit_id, semen.PROP_SEMEN, initial_semen)
    else:
        morld.set_unit_prop(unit_id, semen.PROP_SEMEN, semen.SEMEN_MAX)

    return morld, semen


class TestSemenBasic:
    """기본 API 테스트"""

    def test_initial_state(self):
        """등록 시 정액 최대치 초기화"""
        morld, semen = _setup(100)
        assert semen.get_semen(100) == semen.SEMEN_MAX

    def test_consume_semen(self):
        """정액 소모 테스트"""
        morld, semen = _setup(100, initial_semen=50)
        actual = semen.consume_semen(100, 20)
        assert actual == 20
        assert semen.get_semen(100) == 30

    def test_consume_semen_insufficient(self):
        """정액 부족 시 남은 만큼만 소모"""
        morld, semen = _setup(100, initial_semen=5)
        actual = semen.consume_semen(100, 20)
        assert actual == 5
        assert semen.get_semen(100) == 0

    def test_can_erect(self):
        """발기 가능 여부 테스트"""
        morld, semen = _setup(100, initial_semen=5)
        assert semen.can_erect(100) is True

        morld.set_unit_prop(100, semen.PROP_SEMEN, 4)
        assert semen.can_erect(100) is False

    def test_can_ejaculate(self):
        """사정 가능 여부 테스트"""
        morld, semen = _setup(100, initial_semen=10)
        assert semen.can_ejaculate(100) is True

        morld.set_unit_prop(100, semen.PROP_SEMEN, 9)
        assert semen.can_ejaculate(100) is False

    def test_add_semen(self):
        """정액 회복 테스트 (상한 100)"""
        morld, semen = _setup(100, initial_semen=90)
        semen.add_semen(100, 20)
        assert semen.get_semen(100) == 100  # cap at SEMEN_MAX

    def test_unregistered_returns_max(self):
        """미등록 캐릭터는 SEMEN_MAX 반환"""
        import morld
        morld.reset()
        import semen
        semen.reset()

        assert semen.get_semen(999) == semen.SEMEN_MAX
        assert semen.can_erect(999) is True
        assert semen.can_ejaculate(999) is True

    def test_unregistered_consume_passthrough(self):
        """미등록 캐릭터는 소모 없이 amount 반환"""
        import morld
        morld.reset()
        import semen
        semen.reset()

        actual = semen.consume_semen(999, 50)
        assert actual == 50

    def test_reset(self):
        """reset 후 registry 비어야 함"""
        morld, semen = _setup(100)
        semen.reset()
        assert 100 not in semen._registry
        assert 100 not in semen._accumulated


class TestSemenWetDream:
    """몽정 테스트"""

    def test_process_wet_dream(self):
        """몽정: 정액 소모 + 성욕 감소 + 외부 정액 적용"""
        morld, semen = _setup(100, props={"상태:성욕": 50, "오염물:정액:음부": 0})

        semen.process_wet_dream(100)

        # 정액 소모
        assert semen.get_semen(100) == semen.SEMEN_MAX - semen.WET_DREAM_COST
        # 성욕 감소
        assert morld.get_unit_prop(100, "상태:성욕") == 30
        # 외부 정액
        assert morld.get_unit_prop(100, "오염물:정액:음부") == 20


class TestSemenRegen:
    """정액 회복 테스트"""

    def test_regen_hourly(self):
        """시간당 정액 회복"""
        morld, semen = _setup(100, initial_semen=50)
        semen._regen_hourly(100)
        assert semen.get_semen(100) == 55  # +5

    def test_regen_no_exceed_max(self):
        """회복으로 100 초과하지 않음"""
        morld, semen = _setup(100, initial_semen=98)
        semen._regen_hourly(100)
        assert semen.get_semen(100) == 100

    def test_process_accumulated(self):
        """밀리초 누적 → 1시간 단위 처리"""
        morld, semen = _setup(100, initial_semen=50)

        # 1시간 미만 → 변화 없음
        semen._process_accumulated(100, 3_000_000)
        assert semen.get_semen(100) == 50

        # 나머지 추가 → 1시간 완성
        semen._process_accumulated(100, 600_000)
        assert semen.get_semen(100) == 55  # 1시간 회복


class TestMasturbationTemplates:
    """목격 반응 템플릿 테스트"""

    def test_get_witness_reaction_all_types(self):
        """4가지 반응 유형 모두 텍스트 반환"""
        from masturbation_templates import get_witness_reaction

        for reaction_type in ("initiate", "intimate", "embarrassed", "disgusted"):
            text = get_witness_reaction("세라", "stoic", reaction_type)
            assert text is not None
            assert len(text) > 0
            assert "세라" in text

    def test_get_witness_reaction_all_archetypes(self):
        """10 아키타입 모두 텍스트 반환"""
        from masturbation_templates import get_witness_reaction

        archetypes = [
            "stoic", "gentle", "cheerful", "timid", "cold",
            "seductive", "fierce", "proud", "innocent", "devoted"
        ]
        for arch in archetypes:
            text = get_witness_reaction("밀라", arch, "embarrassed")
            assert text is not None
            assert len(text) > 0

    def test_unknown_archetype_fallback(self):
        """알 수 없는 아키타입 → stoic fallback"""
        from masturbation_templates import get_witness_reaction

        text = get_witness_reaction("리나", "unknown_arch", "disgusted")
        assert text is not None
        assert len(text) > 0
