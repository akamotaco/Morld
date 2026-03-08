"""이벤트 import 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()


class TestPrologueImport(_T):
    def test_import(self):
        from events import prologue
        assert hasattr(prologue, 'handle_contract')
        assert hasattr(prologue, 'trigger_prologue')

    def test_trigger_prologue(self):
        from events.prologue import trigger_prologue
        # Should not crash
        trigger_prologue()


class TestTutorialImport(_T):
    def test_import(self):
        from events import tutorial
        assert hasattr(tutorial, 'handle_build_tutorial')
        assert hasattr(tutorial, 'handle_reinforcement')


class TestFirstMissionImport(_T):
    def test_import(self):
        from events import first_mission
        assert hasattr(first_mission, 'handle_mission_briefing')
        assert hasattr(first_mission, 'handle_mission_complete')
        assert hasattr(first_mission, 'start_expedition')
        assert hasattr(first_mission, 'retreat_expedition')
