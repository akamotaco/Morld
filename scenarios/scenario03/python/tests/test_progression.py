"""데모 진행 시스템 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()


class TestProgressionBasic(_T):
    def setUp(self):
        from events.progression import reset
        reset()

    def test_initial_step_is_zero(self):
        from events.progression import get_current_step
        assert get_current_step() == 0

    def test_advance_to_step_1(self):
        from events.progression import advance_to, get_current_step
        result = advance_to(1)
        assert result is True
        assert get_current_step() == 1

    def test_advance_sequential(self):
        from events.progression import advance_to, get_current_step
        advance_to(1)
        advance_to(2)
        advance_to(3)
        assert get_current_step() == 3

    def test_advance_skip(self):
        """디버그용 — 중간 단계 건너뛰기"""
        from events.progression import advance_to, get_current_step
        advance_to(5)
        assert get_current_step() == 5

    def test_advance_backward_fails(self):
        from events.progression import advance_to, get_current_step
        advance_to(5)
        result = advance_to(3)
        assert result is False
        assert get_current_step() == 5

    def test_advance_same_step_fails(self):
        from events.progression import advance_to
        advance_to(5)
        result = advance_to(5)
        assert result is False

    def test_advance_invalid_step(self):
        from events.progression import advance_to
        assert advance_to(0) is False
        assert advance_to(15) is False
        assert advance_to(-1) is False


class TestProgressionComplete(_T):
    def setUp(self):
        from events.progression import reset
        reset()

    def test_complete_step(self):
        from events.progression import advance_to, complete_step, get_current_step
        advance_to(1)
        result = complete_step()
        assert result is True
        assert get_current_step() == 2

    def test_complete_specific_step(self):
        from events.progression import advance_to, complete_step, get_current_step
        advance_to(3)
        result = complete_step(3)
        assert result is True
        assert get_current_step() == 4

    def test_complete_wrong_step_ignored(self):
        from events.progression import advance_to, complete_step, get_current_step
        advance_to(3)
        result = complete_step(5)
        assert result is False
        assert get_current_step() == 3

    def test_complete_last_step(self):
        from events.progression import advance_to, complete_step, get_current_step
        advance_to(14)
        result = complete_step()
        assert result is False
        assert get_current_step() == 14


class TestProgressionQueries(_T):
    def setUp(self):
        from events.progression import reset
        reset()

    def test_get_step_name(self):
        from events.progression import advance_to, get_step_name
        advance_to(1)
        assert get_step_name() == "계약"

    def test_get_step_name_explicit(self):
        from events.progression import get_step_name
        assert get_step_name(14) == "엔딩"

    def test_is_step(self):
        from events.progression import advance_to, is_step
        advance_to(3)
        assert is_step(3) is True
        assert is_step(2) is False

    def test_is_step_at_least(self):
        from events.progression import advance_to, is_step_at_least
        advance_to(5)
        assert is_step_at_least(5) is True
        assert is_step_at_least(3) is True
        assert is_step_at_least(6) is False

    def test_get_demo_status(self):
        from events.progression import advance_to, get_demo_status
        advance_to(7)
        status = get_demo_status()
        assert status["step"] == 7
        assert status["name"] == "기본 건설"
        assert status["total"] == 14
        assert status["progress_pct"] == 50


class TestProgressionCallbacks(_T):
    def setUp(self):
        from events.progression import reset
        reset()

    def test_on_step_callback(self):
        from events.progression import advance_to, on_step
        called = []
        on_step(3, lambda s: called.append(s))
        advance_to(3)
        assert called == [3]

    def test_callback_not_called_for_other_step(self):
        from events.progression import advance_to, on_step
        called = []
        on_step(5, lambda s: called.append(s))
        advance_to(3)
        assert called == []

    def test_callback_cleared_on_reset(self):
        from events.progression import advance_to, on_step, reset
        called = []
        on_step(3, lambda s: called.append(s))
        reset()
        advance_to(3)
        assert called == []


class TestProgressionStepHandlers(_T):
    def setUp(self):
        from events.progression import reset
        reset()

    def test_trigger_step_event_returns_generator(self):
        from events.progression import advance_to, trigger_step_event
        advance_to(1)
        result = trigger_step_event()
        # Step 1 handler returns handle_contract() which is a generator
        import inspect
        assert inspect.isgenerator(result)

    def test_trigger_step_event_no_handler(self):
        from events.progression import advance_to, trigger_step_event
        advance_to(4)  # Step 4 has no handler (quest-based)
        result = trigger_step_event()
        assert result is None

    def test_trigger_step_event_explicit(self):
        from events.progression import trigger_step_event
        # Explicit step argument
        result = trigger_step_event(step=5)
        import inspect
        assert inspect.isgenerator(result)


class TestEndingImport(_T):
    def test_import(self):
        from events import ending
        assert hasattr(ending, 'handle_ending')

    def test_handle_ending_is_generator(self):
        from events.ending import handle_ending
        import inspect
        gen = handle_ending()
        assert inspect.isgenerator(gen)
