# test_party.py — 파티(분대) 시스템 단위 테스트
"""
party.py + think/party_config.py + FSM pass-through 테스트

테스트 범위:
- Squad/Order 데이터 구조
- 생명주기 API (create/disband)
- 멤버 관리 (add/remove)
- 리더 관리 (assign/remove/change)
- 지휘/지시 API (directive/order)
- 모집 조건 (party_config.can_recruit)
- 불복 판정 (party_config.check_disobedience)
- FSM pass-through 스택 순회
- StandbyPhase / CommandPhase 기본 동작
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

# needs stub (StandbyPhase가 lazy import)
class _NeedsStub:
    def get_excretion(self, uid): return 0
    def get_fatigue(self, uid): return 0
    def get_cleanliness(self, uid): return 0

sys.modules.setdefault("needs", _NeedsStub())

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
