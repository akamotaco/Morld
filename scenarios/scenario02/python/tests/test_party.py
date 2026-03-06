# test_party.py — 파티(분대) 시스템 단위 테스트
"""
party.py + think/party_config.py + FSM pass-through 테스트

테스트 범위:
- Phase 1: 데이터 구조, 생명주기, 멤버/리더, 지휘/지시, party_config, FSM pass-through
- Phase 2: Order 핸들러 (follow/이동/대기/경계/수색/수집), FSM push/pop 통합
- Phase 3: Follow 스케줄, Gate 동기화, Order 전환, 귀환 메커니즘
- Phase 4: 플레이어 UI (can: props, update_party_props, 모집 판정)
"""
import sys
import os
import importlib.util

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

import morld  # MockMorld (run_tests.py가 주입)


# ============================================
# think.fsm / think.party_config 직접 로드
# (think/__init__.py 순환 import 우회)
# ============================================

def _load_module(name, file_path):
    """importlib으로 모듈 직접 로드"""
    spec = importlib.util.spec_from_file_location(name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_fsm = _load_module("think.fsm", os.path.join(_python_dir, "think", "fsm.py"))
_party_config = _load_module(
    "think.party_config",
    os.path.join(_python_dir, "think", "party_config.py"),
)

# order_handlers 로드
_order_handlers = _load_module(
    "think.order_handlers",
    os.path.join(_python_dir, "think", "order_handlers.py"),
)

# needs stub (StandbyPhase가 lazy import)
class _NeedsStub:
    def get_excretion(self, uid): return 0
    def get_fatigue(self, uid): return 0
    def get_cleanliness(self, uid): return 0

sys.modules.setdefault("needs", _NeedsStub())

# think.registry stub (party._get_agent 연동용)
import types as _types
_registry = _types.ModuleType("think.registry")
_registry._agents = {}
_registry.get_agent = lambda uid: _registry._agents.get(uid)
sys.modules["think.registry"] = _registry

# party stub도 StandbyPhase/CommandPhase가 lazy import하므로 등록
import party as _party_mod
sys.modules.setdefault("party", _party_mod)

# 클래스/함수 바인딩
FSMState = _fsm.FSMState
LifeState = _fsm.LifeState
StandbyPhase = _fsm.StandbyPhase
CommandPhase = _fsm.CommandPhase
LV_LIFE = _fsm.LV_LIFE
LV_STANDBY = _fsm.LV_STANDBY
LV_COMMAND = _fsm.LV_COMMAND

OrderHandlerMixin = _order_handlers.OrderHandlerMixin

Squad = _party_mod.Squad
Order = _party_mod.Order


# ============================================
# 테스트 공통 셋업
# ============================================

class _T:
    """테스트 기반 클래스 — 각 테스트 전 자동 초기화"""
    def __init__(self):
        _setup()


def _setup():
    """테스트 상태 초기화"""
    morld.reset()
    _party_mod.reset()
    _registry._agents.clear()

    # 기본 유닛 등록 (플레이어 + NPC 6명)
    morld._player_id = 1
    morld.register_unit(1, name="플레이어", location=(0, 0),
                        props={"unique_id": "player"})
    morld.register_unit(10, name="세라", location=(0, 0),
                        props={"unique_id": "sera"})
    morld.register_unit(11, name="밀라", location=(0, 0),
                        props={"unique_id": "mila"})
    morld.register_unit(12, name="리나", location=(0, 0),
                        props={"unique_id": "lina"})
    morld.register_unit(13, name="유키", location=(0, 0),
                        props={"unique_id": "yuki"})
    morld.register_unit(14, name="엘라", location=(0, 0),
                        props={"unique_id": "ella"})
    morld.register_unit(15, name="페이", location=(0, 0),
                        props={"unique_id": "faye"})


# ============================================
# FakeAgent (FSM 테스트용)
# ============================================

class FakeAgent:
    """FSM 테스트용 최소 Agent"""

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self._action_taken = False
        self._fsm_stack = [LifeState()]
        self._memory = {}

    def get_info(self):
        return morld.get_unit_info(self.unit_id) or {"name": "test"}

    def get_location(self):
        return morld.get_unit_location(self.unit_id) or (0, 0)

    def _fsm_push(self, state):
        while self._fsm_stack[-1].level >= state.level:
            self._fsm_pop()
        self._fsm_stack.append(state)
        state.enter(self)

    def _fsm_pop(self):
        if len(self._fsm_stack) <= 1:
            raise RuntimeError("FSM stack empty")
        state = self._fsm_stack.pop()
        state.exit(self)
        return state

    def _fsm_top(self):
        return self._fsm_stack[-1]

    def _fsm_pop_by_type(self, state_type):
        for i in range(len(self._fsm_stack) - 1, 0, -1):
            if self._fsm_stack[i].state_type == state_type:
                state = self._fsm_stack.pop(i)
                state.exit(self)
                return state
        return None

    def _insert_idle_job(self, name, duration):
        morld.insert_job(self.unit_id, {
            "name": name, "action": "stay", "duration": duration,
        })
        self._action_taken = True


# ============================================
# 분대 생명주기 테스트
# ============================================

class TestSquadLifecycle(_T):

    def test_create_squad(self):
        sid = _party_mod.create_squad()
        assert sid == 0, f"첫 분대 ID는 0이어야 함, got {sid}"
        squad = _party_mod.get_squad(sid)
        assert squad is not None
        assert squad.leader_id is None
        assert squad.members == []
        assert squad.player_directive == "auto"

    def test_create_multiple_squads(self):
        s0 = _party_mod.create_squad()
        s1 = _party_mod.create_squad()
        assert s0 != s1
        assert len(_party_mod.get_all_squads()) == 2

    def test_disband_squad(self):
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)

        _party_mod.disband_squad(sid)

        assert _party_mod.get_squad(sid) is None
        assert not _party_mod.is_in_squad(1)
        assert not _party_mod.is_in_squad(10)
        assert not _party_mod.is_in_squad(11)

    def test_reset(self):
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        _party_mod.reset()

        assert _party_mod.get_squad(sid) is None
        assert not _party_mod.is_in_squad(1)
        assert not _party_mod.is_in_squad(10)
        assert len(_party_mod.get_all_squads()) == 0


# ============================================
# 리더 관리 테스트
# ============================================

class TestLeaderManagement(_T):

    def test_assign_leader(self):
        sid = _party_mod.create_squad()
        result = _party_mod.assign_leader(sid, 1)
        assert result is True
        squad = _party_mod.get_squad(sid)
        assert squad.leader_id == 1
        assert _party_mod.is_in_squad(1)
        assert _party_mod.is_squad_leader(1)

    def test_assign_leader_traits(self):
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 10)  # 세라
        squad = _party_mod.get_squad(sid)
        assert squad.leader_traits["aggression"] == 0.7
        assert squad.leader_traits["focus"] == 0.3
        assert squad.leader_traits["unique_id"] == "sera"

    def test_assign_leader_duplicate(self):
        """이미 다른 분대 소속이면 실패"""
        s0 = _party_mod.create_squad()
        s1 = _party_mod.create_squad()
        _party_mod.assign_leader(s0, 1)
        result = _party_mod.assign_leader(s1, 1)
        assert result is False

    def test_remove_leader(self):
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.remove_leader(sid)

        squad = _party_mod.get_squad(sid)
        assert squad.leader_id is None
        assert squad.leader_traits == {}
        assert not _party_mod.is_in_squad(1)

    def test_change_leader(self):
        """리더 교체: 이전 리더 → 멤버, 새 리더(멤버) → 리더"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)  # 세라

        _party_mod.change_leader(sid, 10)  # 세라가 리더로

        squad = _party_mod.get_squad(sid)
        assert squad.leader_id == 10
        assert 1 in squad.members       # 이전 리더가 멤버로
        assert 10 not in squad.members   # 새 리더는 멤버가 아님
        assert squad.leader_traits["unique_id"] == "sera"

    def test_change_leader_order_cleanup(self):
        """리더 교체 시 새 리더의 기존 order 제거"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("경계"))

        _party_mod.change_leader(sid, 10)

        squad = _party_mod.get_squad(sid)
        assert 10 not in squad.orders  # 리더가 된 후 order 제거됨


# ============================================
# 멤버 관리 테스트
# ============================================

class TestMemberManagement(_T):

    def test_add_member(self):
        sid = _party_mod.create_squad()
        result = _party_mod.add_member(sid, 10)
        assert result is True
        assert _party_mod.is_in_squad(10)
        assert not _party_mod.is_squad_leader(10)
        assert _party_mod.get_squad_members(sid) == [10]

    def test_add_member_full(self):
        """정원 초과 시 실패"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)
        _party_mod.add_member(sid, 12)
        result = _party_mod.add_member(sid, 13)  # 4번째
        assert result is False

    def test_add_member_duplicate_squad(self):
        """이미 다른 분대 소속이면 실패"""
        s0 = _party_mod.create_squad()
        s1 = _party_mod.create_squad()
        _party_mod.add_member(s0, 10)
        result = _party_mod.add_member(s1, 10)
        assert result is False

    def test_remove_member(self):
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("경계"))

        _party_mod.remove_member(sid, 10)

        assert not _party_mod.is_in_squad(10)
        assert 10 not in _party_mod.get_squad(sid).orders

    def test_get_all_unit_ids(self):
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)

        ids = _party_mod.get_all_unit_ids(sid)
        assert ids == [1, 10, 11]  # 리더 먼저

    def test_get_squad_by_unit(self):
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        assert _party_mod.get_squad_by_unit(1).squad_id == sid
        assert _party_mod.get_squad_by_unit(10).squad_id == sid
        assert _party_mod.get_squad_by_unit(99) is None


# ============================================
# 지휘/지시 테스트
# ============================================

class TestDirectiveOrder(_T):

    def test_set_directive(self):
        sid = _party_mod.create_squad()
        result = _party_mod.set_directive(sid, "combat_aggressive")
        assert result is True
        assert _party_mod.get_directive(sid) == "combat_aggressive"

    def test_set_directive_invalid(self):
        sid = _party_mod.create_squad()
        result = _party_mod.set_directive(sid, "invalid_value")
        assert result is False
        assert _party_mod.get_directive(sid) == "auto"  # 변경 안 됨

    def test_set_order(self):
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        order = Order("수집:재료", priority=-0.5)
        result = _party_mod.set_order(sid, 10, order)
        assert result is True

        got = _party_mod.get_order(sid, 10)
        assert got is not None
        assert got.order_type == "수집:재료"
        assert got.main_type() == "수집"
        assert got.sub_type() == "재료"
        assert got.priority == -0.5

    def test_set_order_non_member(self):
        """비소속 유닛에 지시 시 실패"""
        sid = _party_mod.create_squad()
        result = _party_mod.set_order(sid, 99, Order("대기"))
        assert result is False

    def test_clear_order(self):
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("경계"))
        _party_mod.clear_order(sid, 10)

        assert _party_mod.get_order(sid, 10) is None

    def test_get_order_for_unit(self):
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("follow"))

        got = _party_mod.get_order_for_unit(10)
        assert got is not None
        assert got.order_type == "follow"

        # 비소속
        assert _party_mod.get_order_for_unit(99) is None


# ============================================
# Order 데이터 테스트
# ============================================

class TestOrderData(_T):

    def test_order_main_sub_type(self):
        o1 = Order("수색:적")
        assert o1.main_type() == "수색"
        assert o1.sub_type() == "적"

        o2 = Order("대기")
        assert o2.main_type() == "대기"
        assert o2.sub_type() == "*"

    def test_order_defaults(self):
        o = Order("follow")
        assert o.priority == 0.0
        assert o.stealth == 0.0
        assert o.target is None


# ============================================
# party_config 테스트
# ============================================

class TestPartyConfig(_T):

    def test_get_disposition_known(self):
        agg, foc = _party_config.get_disposition("sera")
        assert agg == 0.7
        assert foc == 0.3

    def test_get_disposition_unknown(self):
        agg, foc = _party_config.get_disposition("unknown_npc")
        assert agg == 0.0
        assert foc == 0.0

    def test_get_recruit_condition_default(self):
        cond = _party_config.get_recruit_condition("mila")  # 오버라이드 없음
        assert cond["affection"] == 40
        assert cond["submission"] == 50
        assert cond["rebellion_max"] == 50

    def test_get_recruit_condition_override(self):
        cond = _party_config.get_recruit_condition("sera")
        assert cond["affection"] == 50  # sera 오버라이드
        assert cond["submission"] == 50  # 기본값 유지

    def test_can_recruit_affection(self):
        """호감 충족 시 모집 성공"""
        # 세라: affection >= 50
        morld.set_unit_prop(10, "관계:플레이어:호감", 50)
        assert _party_config.can_recruit(10, 1) is True

    def test_can_recruit_submission(self):
        """복종 충족 시 모집 성공"""
        morld.set_unit_prop(10, "관계:플레이어:복종", 50)
        assert _party_config.can_recruit(10, 1) is True

    def test_can_recruit_rebellion_block(self):
        """반발 초과 시 모집 실패"""
        morld.set_unit_prop(10, "관계:플레이어:호감", 99)
        morld.set_unit_prop(10, "관계:플레이어:반발", 50)
        assert _party_config.can_recruit(10, 1) is False

    def test_can_recruit_insufficient(self):
        """호감/복종 모두 부족 시 실패"""
        morld.set_unit_prop(10, "관계:플레이어:호감", 10)
        morld.set_unit_prop(10, "관계:플레이어:복종", 10)
        assert _party_config.can_recruit(10, 1) is False

    def test_check_disobedience_absolute_submission(self):
        """복종 >= 80이면 절대 복종"""
        morld.set_unit_prop(10, "관계:플레이어:복종", 80)
        morld.set_unit_prop(10, "관계:플레이어:반발", 99)
        order = Order("전투")  # 높은 위험도
        # 100번 시도해도 거부 안 함
        for _ in range(100):
            assert _party_config.check_disobedience(10, 1, order) is False

    def test_check_disobedience_retreat_never_refused(self):
        """후퇴 지시는 거부하지 않음"""
        morld.set_unit_prop(10, "관계:플레이어:반발", 99)
        morld.set_unit_prop(10, "관계:플레이어:복종", 0)
        order = Order("후퇴")
        for _ in range(100):
            assert _party_config.check_disobedience(10, 1, order) is False

    def test_build_leader_traits(self):
        traits = _party_config.build_leader_traits("ella")
        assert traits["aggression"] == 0.4
        assert traits["focus"] == 0.7
        assert traits["unique_id"] == "ella"


# ============================================
# FSM Pass-Through 테스트
# ============================================

class TestFSMPassThrough(_T):

    def test_life_state_returns_false(self):
        """LifeState는 항상 False (pass-through 아래로 위임)"""
        agent = FakeAgent(10)
        state = LifeState()
        assert state.update(agent) is False

    def test_stack_traversal_order(self):
        """스택 위→아래 순회: 첫 True에서 멈춤"""
        class TrueState(FSMState):
            state_type = "true_test"
            level = 5
            called = False
            def update(self, agent):
                self.called = True
                return True

        class FalseState(FSMState):
            state_type = "false_test"
            level = 3
            called = False
            def update(self, agent):
                self.called = True
                return False

        agent = FakeAgent(10)
        true_s = TrueState()
        false_s = FalseState()
        agent._fsm_stack = [agent._fsm_stack[0], false_s, true_s]

        # 위→아래 순회
        handled = False
        for state in reversed(list(agent._fsm_stack)):
            if state.update(agent):
                handled = True
                break

        assert handled is True
        assert true_s.called is True
        assert false_s.called is False  # true가 먼저 처리했으므로

    def test_pass_through_to_bottom(self):
        """모든 State가 False → 최하위까지 도달"""
        class PassState(FSMState):
            state_type = "pass"
            level = 5
            def update(self, agent):
                return False

        agent = FakeAgent(10)
        pass_s = PassState()
        agent._fsm_stack = [agent._fsm_stack[0], pass_s]

        handled = False
        for state in reversed(list(agent._fsm_stack)):
            if state.update(agent):
                handled = True
                break

        assert handled is False  # 모든 state가 False

    def test_fsm_pop_by_type(self):
        """state_type으로 특정 State 제거"""
        agent = FakeAgent(10)
        standby = StandbyPhase()
        command = CommandPhase()
        agent._fsm_stack.append(standby)
        agent._fsm_stack.append(command)

        popped = agent._fsm_pop_by_type("standby")
        assert popped is standby
        assert len(agent._fsm_stack) == 2  # LifeState + CommandPhase

    def test_fsm_pop_by_type_not_found(self):
        """없는 state_type이면 None"""
        agent = FakeAgent(10)
        result = agent._fsm_pop_by_type("nonexistent")
        assert result is None

    def test_auto_pop_same_level(self):
        """동일 레벨 push 시 기존 auto-pop"""
        agent = FakeAgent(10)
        s1 = StandbyPhase()
        s2 = StandbyPhase()
        agent._fsm_push(s1)
        agent._fsm_push(s2)

        assert s1 not in agent._fsm_stack
        assert s2 in agent._fsm_stack

    def test_level_constants(self):
        """레벨 상수 순서 확인"""
        assert LV_LIFE < LV_STANDBY < LV_COMMAND
        assert LV_COMMAND < _fsm.LV_COMBAT
        assert _fsm.LV_COMBAT < _fsm.LV_COMBAT_SUB
        assert _fsm.LV_COMBAT_SUB < _fsm.LV_TRANSIT


# ============================================
# StandbyPhase 테스트
# ============================================

class TestStandbyPhase(_T):

    def test_standby_not_in_squad(self):
        """분대 미소속 → False (생활로 위임)"""
        agent = FakeAgent(10)
        phase = StandbyPhase()
        result = phase.update(agent)
        assert result is False

    def test_standby_in_squad_idle(self):
        """분대 소속 → True (idle 유지)"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgent(10)
        phase = StandbyPhase()
        result = phase.update(agent)
        assert result is True
        assert agent._action_taken is True


# ============================================
# CommandPhase 테스트
# ============================================

class TestCommandPhase(_T):

    def test_command_no_order(self):
        """지시 없음 → False (아래로 위임)"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgent(10)
        phase = CommandPhase()
        result = phase.update(agent)
        assert result is False

    def test_command_with_order_no_handler(self):
        """핸들러 없는 order → False"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("알수없는지시"))

        agent = FakeAgent(10)
        phase = CommandPhase()
        result = phase.update(agent)
        assert result is False

    def test_command_with_handler(self):
        """핸들러 존재 시 호출"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("대기"))

        agent = FakeAgent(10)
        agent._handle_order_wait = lambda order: True
        phase = CommandPhase()
        result = phase.update(agent)
        assert result is True

    def test_command_follow_handler(self):
        """follow 핸들러 테스트"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("follow"))

        agent = FakeAgent(10)
        follow_called = [False]
        def mock_follow(order):
            follow_called[0] = True
            return True
        agent._handle_order_follow = mock_follow

        phase = CommandPhase()
        result = phase.update(agent)
        assert follow_called[0] is True
        assert result is True

    def test_command_exit_clears_memory(self):
        """CommandPhase exit 시 order_ 메모리 정리"""
        agent = FakeAgent(10)
        agent._memory["order_phase"] = "going"
        agent._memory["order_target"] = {"region_id": 0, "location_id": 1}
        agent._memory["unrelated"] = "keep"

        phase = CommandPhase()
        phase.exit(agent)

        assert agent._memory["order_phase"] is None
        assert agent._memory["order_target"] is None
        assert agent._memory["unrelated"] == "keep"


# ============================================
# 전체 흐름 통합 테스트
# ============================================

class TestIntegration(_T):

    def test_full_squad_lifecycle(self):
        """분대 생성 → 리더 → 멤버 추가 → 지시 → 해산"""
        # 분대 생성
        sid = _party_mod.create_squad()
        assert _party_mod.get_squad(sid) is not None

        # 리더 지정
        _party_mod.assign_leader(sid, 1)
        assert _party_mod.is_squad_leader(1)

        # 멤버 추가
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)
        assert len(_party_mod.get_squad_members(sid)) == 2

        # 지시 설정
        _party_mod.set_order(sid, 10, Order("follow"))
        _party_mod.set_order(sid, 11, Order("경계"))
        assert _party_mod.get_order_for_unit(10).order_type == "follow"
        assert _party_mod.get_order_for_unit(11).order_type == "경계"

        # 지휘 변경
        _party_mod.set_directive(sid, "combat_aggressive")
        assert _party_mod.get_directive(sid) == "combat_aggressive"

        # 멤버 제거
        _party_mod.remove_member(sid, 11)
        assert not _party_mod.is_in_squad(11)
        assert _party_mod.get_order_for_unit(11) is None

        # 해산
        _party_mod.disband_squad(sid)
        assert _party_mod.get_squad(sid) is None
        assert not _party_mod.is_in_squad(1)
        assert not _party_mod.is_in_squad(10)

    def test_party_fsm_stack_flow(self):
        """파티 NPC FSM 스택: [CommandPhase, StandbyPhase, LifeState]"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgent(10)
        agent._fsm_push(StandbyPhase())
        agent._fsm_push(CommandPhase())

        # 스택 확인
        assert len(agent._fsm_stack) == 3
        assert agent._fsm_stack[0].state_type == "life"
        assert agent._fsm_stack[1].state_type == "standby"
        assert agent._fsm_stack[2].state_type == "command"

        # order 없으면 Command → False, Standby → True (idle)
        handled = False
        for state in reversed(list(agent._fsm_stack)):
            if state.update(agent):
                handled = True
                break
        assert handled is True
        assert agent._action_taken is True  # StandbyPhase가 idle 삽입

    def test_party_fsm_with_order(self):
        """order가 있으면 CommandPhase가 처리"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)
        _party_mod.set_order(sid, 10, Order("대기"))

        agent = FakeAgent(10)
        agent._handle_order_wait = lambda order: True
        agent._fsm_push(StandbyPhase())
        agent._fsm_push(CommandPhase())

        handled = False
        for state in reversed(list(agent._fsm_stack)):
            if state.update(agent):
                handled = True
                break
        assert handled is True

    def test_disband_cleans_fsm(self):
        """해산 시 FSM에서 파티 phase 제거"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgent(10)
        agent._fsm_push(StandbyPhase())
        agent._fsm_push(CommandPhase())
        assert len(agent._fsm_stack) == 3

        # 수동 FSM 정리 (실제로는 remove_member에서 호출)
        agent._fsm_pop_by_type("command")
        agent._fsm_pop_by_type("standby")
        assert len(agent._fsm_stack) == 1
        assert agent._fsm_stack[0].state_type == "life"


# ============================================
# Phase 2: Order Handler 테스트용 Agent
# ============================================

class FakeAgentWithOrders(FakeAgent, OrderHandlerMixin):
    """Order 핸들러를 포함한 FakeAgent"""

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self._move_log = []  # 이동 기록 [(target, name), ...]
        self.schedule_stack = [[]]  # 기본 스케줄 (빈 리스트)

    def _move_to(self, target, name="이동"):
        """이동 기록 (실제 이동 대신)"""
        self._move_log.append((target, name))
        self._action_taken = True

    def _is_at(self, target):
        loc = self.get_location()
        return (loc and loc[0] == target["region_id"]
                and loc[1] == target["location_id"])

    def push_schedule(self, schedule):
        self.schedule_stack.append(schedule)
        morld.clear_jobs(self.unit_id)

    def pop_schedule(self):
        if len(self.schedule_stack) > 1:
            return self.schedule_stack.pop()
        return None


def _register_agent(agent):
    """테스트용 agent 레지스트리에 등록"""
    _registry._agents[agent.unit_id] = agent


# ============================================
# Phase 2: Order Handler 테스트
# ============================================

class TestOrderHandlerFollow(_T):

    def test_follow_same_location(self):
        """리더와 같은 location → idle 대기"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        order = Order("follow")
        result = agent._handle_order_follow(order)

        assert result is True
        assert agent._action_taken is True
        assert len(agent._move_log) == 0  # 이동 없음

    def test_follow_different_location(self):
        """리더와 다른 location → 이동"""
        morld.set_unit_location(1, 0, 5)  # 리더를 다른 location으로

        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        order = Order("follow")
        result = agent._handle_order_follow(order)

        assert result is True
        assert len(agent._move_log) == 1
        assert agent._move_log[0][0]["region_id"] == 0
        assert agent._move_log[0][0]["location_id"] == 5

    def test_follow_no_leader(self):
        """리더 없음 → False"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        order = Order("follow")
        result = agent._handle_order_follow(order)

        assert result is False


class TestOrderHandlerMove(_T):

    def test_move_to_target(self):
        """목표 지점 이동"""
        target = {"region_id": 0, "location_id": 3}
        agent = FakeAgentWithOrders(10)
        order = Order("이동", target=target)
        result = agent._handle_order_move(order)

        assert result is True
        assert len(agent._move_log) == 1
        assert agent._move_log[0][0] == target

    def test_move_at_target(self):
        """이미 목표 지점 → idle 대기"""
        target = {"region_id": 0, "location_id": 0}  # 세라 초기 위치
        agent = FakeAgentWithOrders(10)
        order = Order("이동", target=target)
        result = agent._handle_order_move(order)

        assert result is True
        assert len(agent._move_log) == 0  # 이동 없음

    def test_move_no_target(self):
        """target 없음 → False"""
        agent = FakeAgentWithOrders(10)
        order = Order("이동")
        result = agent._handle_order_move(order)

        assert result is False


class TestOrderHandlerWait(_T):

    def test_wait_basic(self):
        """대기 → idle"""
        agent = FakeAgentWithOrders(10)
        order = Order("대기")
        result = agent._handle_order_wait(order)

        assert result is True
        assert agent._action_taken is True

    def test_wait_rest(self):
        """대기:휴식 → False (생활 위임)"""
        agent = FakeAgentWithOrders(10)
        order = Order("대기:휴식")
        result = agent._handle_order_wait(order)

        assert result is False


class TestOrderHandlerGuard(_T):

    def test_guard(self):
        """경계 → idle"""
        agent = FakeAgentWithOrders(10)
        order = Order("경계")
        result = agent._handle_order_guard(order)

        assert result is True
        assert agent._action_taken is True


class TestOrderHandlerSearch(_T):

    def test_search(self):
        """수색 → idle"""
        agent = FakeAgentWithOrders(10)
        order = Order("수색")
        result = agent._handle_order_search(order)

        assert result is True

    def test_search_sub_type(self):
        """수색:적 → idle"""
        agent = FakeAgentWithOrders(10)
        order = Order("수색:적")
        result = agent._handle_order_search(order)

        assert result is True


class TestOrderHandlerCollect(_T):

    def test_collect(self):
        """수집 → idle"""
        agent = FakeAgentWithOrders(10)
        order = Order("수집:재료")
        result = agent._handle_order_collect(order)

        assert result is True


# ============================================
# Phase 2: FSM push/pop 통합 테스트
# ============================================

class TestFSMPushPop(_T):

    def test_set_order_pushes_phases(self):
        """set_order → StandbyPhase + CommandPhase push"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))

        types = [s.state_type for s in agent._fsm_stack]
        assert "standby" in types
        assert "command" in types

    def test_set_order_no_duplicate_push(self):
        """이미 phase가 있으면 중복 push 안 함"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))
        _party_mod.set_order(sid, 10, Order("경계"))  # 재설정

        # phase는 여전히 하나씩
        standby_count = sum(1 for s in agent._fsm_stack if s.state_type == "standby")
        command_count = sum(1 for s in agent._fsm_stack if s.state_type == "command")
        assert standby_count == 1
        assert command_count == 1

    def test_remove_member_pops_phases(self):
        """remove_member → Command/Standby phase pop"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))
        assert len(agent._fsm_stack) == 3

        _party_mod.remove_member(sid, 10)

        assert len(agent._fsm_stack) == 1
        assert agent._fsm_stack[0].state_type == "life"

    def test_disband_pops_all_members(self):
        """disband → 전체 멤버 FSM 정리"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)

        agent10 = FakeAgentWithOrders(10)
        agent11 = FakeAgentWithOrders(11)
        _register_agent(agent10)
        _register_agent(agent11)

        _party_mod.set_order(sid, 10, Order("follow"))
        _party_mod.set_order(sid, 11, Order("경계"))

        _party_mod.disband_squad(sid)

        assert len(agent10._fsm_stack) == 1
        assert len(agent11._fsm_stack) == 1

    def test_add_member_no_fsm_push(self):
        """add_member → FSM 변경 없음"""
        sid = _party_mod.create_squad()

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.add_member(sid, 10)

        assert len(agent._fsm_stack) == 1  # LifeState만

    def test_full_flow_with_handlers(self):
        """전체 흐름: set_order → CommandPhase dispatch → 핸들러 실행"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))

        # FSM 순회
        handled = False
        for state in reversed(list(agent._fsm_stack)):
            if state.update(agent):
                handled = True
                break

        assert handled is True
        assert agent._action_taken is True
        # CommandPhase → _handle_order_wait → idle job 삽입
        jobs = morld.get_all_jobs(10)
        assert len(jobs) >= 1
        assert jobs[-1]["name"] == "대기"

    def test_clear_order_passthrough(self):
        """clear_order → CommandPhase가 False 반환 → StandbyPhase가 처리"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))
        _party_mod.clear_order(sid, 10)

        # FSM 순회 — CommandPhase False → StandbyPhase True
        handled = False
        for state in reversed(list(agent._fsm_stack)):
            if state.update(agent):
                handled = True
                break

        assert handled is True  # StandbyPhase가 처리


# ============================================
# Phase 3: Follow 스케줄 테스트
# ============================================

class TestFollowSchedule(_T):

    def test_follow_order_pushes_schedule(self):
        """follow order → follow 스케줄 push"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("follow"))

        assert len(agent.schedule_stack) == 2
        assert agent.schedule_stack[-1] is _party_mod.PARTY_FOLLOW_SCHEDULE

    def test_non_follow_order_no_schedule(self):
        """non-follow order → 스케줄 push 없음"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))

        assert len(agent.schedule_stack) == 1  # 기본 스케줄만

    def test_order_change_follow_to_wait(self):
        """follow → 대기: follow 스케줄 pop"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("follow"))
        assert len(agent.schedule_stack) == 2

        _party_mod.set_order(sid, 10, Order("대기"))
        assert len(agent.schedule_stack) == 1

    def test_order_change_wait_to_follow(self):
        """대기 → follow: follow 스케줄 push"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))
        assert len(agent.schedule_stack) == 1

        _party_mod.set_order(sid, 10, Order("follow"))
        assert len(agent.schedule_stack) == 2

    def test_order_change_follow_to_follow(self):
        """follow → follow: 스케줄 변경 없음"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("follow"))
        assert len(agent.schedule_stack) == 2

        _party_mod.set_order(sid, 10, Order("follow"))
        assert len(agent.schedule_stack) == 2  # 변경 없음

    def test_clear_follow_order_pops_schedule(self):
        """follow order clear → follow 스케줄 pop"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("follow"))
        assert len(agent.schedule_stack) == 2

        _party_mod.clear_order(sid, 10)
        assert len(agent.schedule_stack) == 1

    def test_clear_non_follow_order_no_pop(self):
        """non-follow order clear → 스케줄 변경 없음"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))
        _party_mod.clear_order(sid, 10)
        assert len(agent.schedule_stack) == 1


# ============================================
# Phase 3: 귀환 메커니즘 테스트 (E4)
# ============================================

class TestReturnToLife(_T):

    def test_remove_member_pops_follow_schedule(self):
        """remove_member → follow 스케줄 pop + FSM 정리"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("follow"))
        assert len(agent.schedule_stack) == 2
        assert len(agent._fsm_stack) == 3  # life + standby + command

        _party_mod.remove_member(sid, 10)

        assert len(agent.schedule_stack) == 1  # follow 스케줄 pop
        assert len(agent._fsm_stack) == 1  # FSM 정리
        assert agent._fsm_stack[0].state_type == "life"

    def test_disband_pops_follow_for_all(self):
        """disband → 전체 멤버 follow 스케줄 + FSM 정리"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)

        agent10 = FakeAgentWithOrders(10)
        agent11 = FakeAgentWithOrders(11)
        _register_agent(agent10)
        _register_agent(agent11)

        _party_mod.set_order(sid, 10, Order("follow"))
        _party_mod.set_order(sid, 11, Order("경계"))

        assert len(agent10.schedule_stack) == 2  # follow
        assert len(agent11.schedule_stack) == 1  # non-follow

        _party_mod.disband_squad(sid)

        assert len(agent10.schedule_stack) == 1
        assert len(agent10._fsm_stack) == 1
        assert len(agent11.schedule_stack) == 1
        assert len(agent11._fsm_stack) == 1

    def test_remove_non_follow_member(self):
        """non-follow 멤버 제거 → FSM만 정리, 스케줄 변경 없음"""
        sid = _party_mod.create_squad()
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("경계"))
        assert len(agent.schedule_stack) == 1
        assert len(agent._fsm_stack) == 3

        _party_mod.remove_member(sid, 10)

        assert len(agent.schedule_stack) == 1  # 변경 없음
        assert len(agent._fsm_stack) == 1


# ============================================
# Phase 3: Leader Destination 테스트 (E3)
# ============================================

class TestLeaderDestination(_T):

    def test_on_leader_move_sets_destination(self):
        """on_leader_move → squad.leader_destination 설정"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        target = {"region_id": 3, "location_id": 0}
        _party_mod.on_leader_move(1, target)

        squad = _party_mod.get_squad(sid)
        assert squad.leader_destination is not None
        assert squad.leader_destination["region_id"] == 3
        assert squad.leader_destination["location_id"] == 0

    def test_on_leader_move_ensures_member_phases(self):
        """on_leader_move → 멤버에게 파티 phase 보장"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)
        assert len(agent._fsm_stack) == 1  # LifeState만

        target = {"region_id": 3, "location_id": 0}
        _party_mod.on_leader_move(1, target)

        # 멤버에게 StandbyPhase + CommandPhase push됨
        types = [s.state_type for s in agent._fsm_stack]
        assert "standby" in types
        assert "command" in types

    def test_on_leader_arrived_clears_destination(self):
        """on_leader_arrived → leader_destination 클리어"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)

        _party_mod.on_leader_move(1, {"region_id": 3, "location_id": 0})
        squad = _party_mod.get_squad(sid)
        assert squad.leader_destination is not None

        _party_mod.on_leader_arrived(1)
        assert squad.leader_destination is None

    def test_on_leader_move_non_leader_ignored(self):
        """non-leader의 on_leader_move → 무시"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        _party_mod.on_leader_move(10, {"region_id": 3, "location_id": 0})

        squad = _party_mod.get_squad(sid)
        assert squad.leader_destination is None

    def test_on_leader_arrived_non_leader_ignored(self):
        """non-leader의 on_leader_arrived → 무시"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        _party_mod.on_leader_move(1, {"region_id": 3, "location_id": 0})
        _party_mod.on_leader_arrived(10)  # 멤버가 도착 → 무시

        squad = _party_mod.get_squad(sid)
        assert squad.leader_destination is not None  # 클리어 안 됨


# ============================================
# Phase 3: FSM leader_destination 감지 테스트
# ============================================

class TestFSMLeaderDestination(_T):

    def test_command_phase_detects_leader_destination(self):
        """CommandPhase → leader_destination 감지 → 이동"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("경계"))

        # 리더가 다른 region으로 이동
        _party_mod.on_leader_move(1, {"region_id": 3, "location_id": 0})

        # CommandPhase update → leader_destination 감지
        cmd = [s for s in agent._fsm_stack if s.state_type == "command"][0]
        agent._action_taken = False
        result = cmd.update(agent)

        assert result is True
        assert agent._action_taken is True
        assert len(agent._move_log) == 1
        assert agent._move_log[0][0]["region_id"] == 3

    def test_standby_phase_detects_leader_destination(self):
        """StandbyPhase → leader_destination 감지 → 이동"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        # order 없이 phase만 있는 상태
        _party_mod.on_leader_move(1, {"region_id": 3, "location_id": 0})

        standby = [s for s in agent._fsm_stack if s.state_type == "standby"][0]
        agent._action_taken = False
        result = standby.update(agent)

        assert result is True
        assert len(agent._move_log) == 1
        assert agent._move_log[0][0]["region_id"] == 3

    def test_same_region_no_detection(self):
        """같은 region의 leader_destination → 감지 안 함"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("경계"))

        # 같은 region (0) 내 다른 location
        _party_mod.on_leader_move(1, {"region_id": 0, "location_id": 5})

        cmd = [s for s in agent._fsm_stack if s.state_type == "command"][0]
        agent._action_taken = False
        result = cmd.update(agent)

        # leader_destination 무시 → 경계 order 처리
        assert result is True
        assert len(agent._move_log) == 0  # 이동 아닌 idle

    def test_leader_not_affected_by_own_destination(self):
        """리더 자신은 leader_destination에 영향 안 받음"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 10)  # NPC가 리더
        _party_mod.add_member(sid, 11)

        agent_leader = FakeAgentWithOrders(10)
        _register_agent(agent_leader)

        _party_mod.set_order(sid, 10, Order("경계"))
        _party_mod.on_leader_move(10, {"region_id": 3, "location_id": 0})

        cmd = [s for s in agent_leader._fsm_stack if s.state_type == "command"][0]
        agent_leader._action_taken = False
        result = cmd.update(agent_leader)

        # 리더 자신은 경계 order 처리 (destination 무시)
        assert result is True
        assert len(agent_leader._move_log) == 0  # 이동 아닌 idle

    def test_no_destination_no_detection(self):
        """leader_destination 없음 → 정상 order 처리"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        agent = FakeAgentWithOrders(10)
        _register_agent(agent)

        _party_mod.set_order(sid, 10, Order("대기"))

        cmd = [s for s in agent._fsm_stack if s.state_type == "command"][0]
        agent._action_taken = False
        result = cmd.update(agent)

        assert result is True
        assert len(agent._move_log) == 0  # idle job, 이동 아님


# ============================================
# Phase 4: update_party_props 테스트
# ============================================

class TestUpdatePartyProps(_T):

    def test_create_squad_updates_props(self):
        """create_squad → can:disband_squad=1, can:recruit=1"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)

        props = morld.get_unit_props(1) or {}
        assert props.get("can:disband_squad") == 1
        assert props.get("can:set_order") == 1  # 플레이어 리더 분대
        assert props.get("can:recruit") == 1     # 빈자리 있음

    def test_create_squad_no_leader(self):
        """리더 없는 분대 → can:assign_leader=1"""
        _party_mod.create_squad()

        props = morld.get_unit_props(1) or {}
        assert props.get("can:assign_leader") == 1
        assert props.get("can:set_order") == 0  # 플레이어 리더 아님

    def test_disband_clears_props(self):
        """disband → can: props 초기화"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.disband_squad(sid)

        props = morld.get_unit_props(1) or {}
        assert props.get("can:disband_squad") == 0
        assert props.get("can:recruit") == 0
        assert props.get("can:set_order") == 0
        assert props.get("can:assign_leader") == 0

    def test_add_member_updates_recruit(self):
        """멤버 3명 추가 → can:recruit=0 (정원 초과)"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)
        _party_mod.add_member(sid, 12)

        props = morld.get_unit_props(1) or {}
        assert props.get("can:recruit") == 0  # 정원 초과

    def test_remove_member_updates_recruit(self):
        """멤버 제거 → can:recruit=1 (빈자리 생김)"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)
        _party_mod.add_member(sid, 12)

        props = morld.get_unit_props(1) or {}
        assert props.get("can:recruit") == 0

        _party_mod.remove_member(sid, 12)
        props = morld.get_unit_props(1) or {}
        assert props.get("can:recruit") == 1

    def test_npc_leader_squad_directive(self):
        """NPC 리더 분대 → can:set_directive=1"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 10)  # NPC 리더

        props = morld.get_unit_props(1) or {}
        assert props.get("can:set_directive") == 1
        assert props.get("can:set_order") == 0  # 플레이어 리더 아님

    def test_change_leader_updates_props(self):
        """리더 교체 → props 갱신"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)  # 플레이어 리더
        _party_mod.add_member(sid, 10)

        props = morld.get_unit_props(1) or {}
        assert props.get("can:set_order") == 1
        assert props.get("can:set_directive") == 0

        _party_mod.change_leader(sid, 10)  # NPC로 교체

        props = morld.get_unit_props(1) or {}
        assert props.get("can:set_order") == 0
        assert props.get("can:set_directive") == 1


# ============================================
# Phase 4: 모집 판정 통합 테스트
# ============================================

class TestRecruitFlow(_T):

    def test_recruit_success_with_affection(self):
        """호감 충분 → 모집 성공"""
        # 세라의 모집 조건: affection >= 50
        player_info = morld.get_unit_info(1)
        player_name = player_info.get("name", "")
        morld.set_unit_prop(10, f"관계:{player_name}:호감", 60)

        assert _party_config.can_recruit(10, 1) is True

    def test_recruit_fail_low_affection(self):
        """호감 부족 → 모집 실패"""
        player_info = morld.get_unit_info(1)
        player_name = player_info.get("name", "")
        morld.set_unit_prop(10, f"관계:{player_name}:호감", 20)

        assert _party_config.can_recruit(10, 1) is False

    def test_recruit_success_with_submission(self):
        """복종 충분 → 모집 성공 (호감 부족해도)"""
        player_info = morld.get_unit_info(1)
        player_name = player_info.get("name", "")
        morld.set_unit_prop(10, f"관계:{player_name}:호감", 10)
        morld.set_unit_prop(10, f"관계:{player_name}:복종", 60)

        assert _party_config.can_recruit(10, 1) is True

    def test_recruit_fail_high_rebellion(self):
        """반발 초과 → 모집 실패 (호감 충분해도)"""
        player_info = morld.get_unit_info(1)
        player_name = player_info.get("name", "")
        morld.set_unit_prop(10, f"관계:{player_name}:호감", 60)
        morld.set_unit_prop(10, f"관계:{player_name}:반발", 55)

        assert _party_config.can_recruit(10, 1) is False

    def test_recruit_already_in_squad(self):
        """이미 분대 소속 → 모집 불가"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)

        # add_member는 이미 소속이면 False
        assert _party_mod.add_member(sid, 10) is False

    def test_recruit_condition_override(self):
        """캐릭터별 오버라이드 확인 (유키: affection=30)"""
        # 유키(12) 모집 조건: affection >= 30
        condition = _party_config.get_recruit_condition("yuki")
        assert condition["affection"] == 30

    def test_recruit_full_squad(self):
        """정원 초과 → 모집 불가"""
        sid = _party_mod.create_squad()
        _party_mod.assign_leader(sid, 1)
        _party_mod.add_member(sid, 10)
        _party_mod.add_member(sid, 11)
        _party_mod.add_member(sid, 12)

        assert _party_mod.add_member(sid, 13) is False


# ============================================
# Phase 4: 불복 판정 테스트
# ============================================

class TestDisobedience(_T):

    def test_high_submission_no_disobey(self):
        """복종 80+ → 절대 복종"""
        player_info = morld.get_unit_info(1)
        player_name = player_info.get("name", "")
        morld.set_unit_prop(10, f"관계:{player_name}:복종", 85)
        morld.set_unit_prop(10, f"관계:{player_name}:반발", 50)

        order = Order("전투")
        # 100회 시행 — 한 번도 거부하지 않아야 함
        for _ in range(100):
            assert _party_config.check_disobedience(10, 1, order) is False

    def test_retreat_no_disobey(self):
        """후퇴 → 거부 안 함"""
        player_info = morld.get_unit_info(1)
        player_name = player_info.get("name", "")
        morld.set_unit_prop(10, f"관계:{player_name}:반발", 80)
        morld.set_unit_prop(10, f"관계:{player_name}:복종", 0)

        order = Order("후퇴")
        for _ in range(100):
            assert _party_config.check_disobedience(10, 1, order) is False

    def test_zero_rebellion_no_disobey(self):
        """반발 0 + 복종 0 → 거부 확률 0"""
        order = Order("대기")
        for _ in range(100):
            assert _party_config.check_disobedience(10, 1, order) is False
