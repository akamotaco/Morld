# test_fsm.py — FSM (Gate Transit / BFS pathfinding) 단위 테스트
"""
스택 기반 FSM의 핵심 로직을 검증한다:
- _find_path(): BFS 경로 탐색
- _find_gate_x(): Gate x좌표 탐색
- GateTransitState: multi-hop Gate 이동 (approaching → transiting)
- LifeState: root 상태 (항상 False)
"""
import sys
import os

# ============================================
# 1. 경로 설정
# ============================================

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

# ============================================
# 2. morld mock (run_tests.py가 이미 주입한 것 사용)
# ============================================

import morld

# ============================================
# 3. 테스트용 FakeAgent
# ============================================

class FakeAgent:
    """GateTransitState가 필요로 하는 최소 Agent 인터페이스"""

    def __init__(self, unit_id, location=(0, 0), name="TestNPC"):
        self.unit_id = unit_id
        self._location = location
        self._name = name
        self._action_taken = False
        self._fsm_stack = []
        self._popped_states = []

    def get_info(self):
        return morld.get_unit_info(self.unit_id) or {"name": self._name}

    def get_location(self):
        return morld.get_unit_location(self.unit_id) or self._location

    def _fsm_push(self, state):
        self._fsm_stack.append(state)
        state.enter(self)

    def _fsm_pop(self):
        if self._fsm_stack:
            state = self._fsm_stack.pop()
            state.exit(self)
            self._popped_states.append(state)
            return state
        return None

    def _fsm_top(self):
        return self._fsm_stack[-1] if self._fsm_stack else None


# ============================================
# 4. 맵 구축 헬퍼
# ============================================

def build_linear_map():
    """직선형 맵: R0:L0 ↔ R0:L1 ↔ R0:L2 ↔ R0:L3

    Gate 구조:
      L0(x=100) ↔ L1(x=0)
      L1(x=200) ↔ L2(x=0)
      L2(x=200) ↔ L3(x=0)
    """
    morld.add_region(0, "테스트리전")
    morld.add_location(0, 0, "방A", length=100)
    morld.add_location(0, 1, "방B", length=200)
    morld.add_location(0, 2, "방C", length=200)
    morld.add_location(0, 3, "방D", length=100)

    # L0 ↔ L1
    morld.add_gate(0, 0, 1, 100, 0, 1, 0)
    morld.add_gate(0, 1, 2, 0, 0, 0, 100)

    # L1 ↔ L2
    morld.add_gate(0, 1, 3, 200, 0, 2, 0)
    morld.add_gate(0, 2, 4, 0, 0, 1, 200)

    # L2 ↔ L3
    morld.add_gate(0, 2, 5, 200, 0, 3, 0)
    morld.add_gate(0, 3, 6, 0, 0, 2, 200)


def build_branching_map():
    r"""분기형 맵:

        L1
       / |
     L0  |
       \ |
        L2 — L3

    Gate 구조:
      L0(x=50) ↔ L1(x=0)
      L0(x=100) ↔ L2(x=0)
      L1(x=100) ↔ L2(x=100)
      L2(x=200) ↔ L3(x=0)
    """
    morld.add_region(0, "분기리전")
    morld.add_location(0, 0, "중앙홀", length=100)
    morld.add_location(0, 1, "왼쪽방", length=100)
    morld.add_location(0, 2, "오른쪽방", length=200)
    morld.add_location(0, 3, "끝방", length=100)

    # L0 ↔ L1
    morld.add_gate(0, 0, 1, 50, 0, 1, 0)
    morld.add_gate(0, 1, 2, 0, 0, 0, 50)
    # L0 ↔ L2
    morld.add_gate(0, 0, 3, 100, 0, 2, 0)
    morld.add_gate(0, 2, 4, 0, 0, 0, 100)
    # L1 ↔ L2
    morld.add_gate(0, 1, 5, 100, 0, 2, 100)
    morld.add_gate(0, 2, 6, 100, 0, 1, 100)
    # L2 ↔ L3
    morld.add_gate(0, 2, 7, 200, 0, 3, 0)
    morld.add_gate(0, 3, 8, 0, 0, 2, 200)


def build_cross_region_map():
    """크로스 리전 맵:

    R0:L0 ↔ R0:L1 ↔ R1:L0 ↔ R1:L1
    """
    morld.add_region(0, "리전A")
    morld.add_region(1, "리전B")
    morld.add_location(0, 0, "A-방1", length=100)
    morld.add_location(0, 1, "A-방2", length=100)
    morld.add_location(1, 0, "B-방1", length=100)
    morld.add_location(1, 1, "B-방2", length=100)

    # R0:L0 ↔ R0:L1
    morld.add_gate(0, 0, 1, 100, 0, 1, 0)
    morld.add_gate(0, 1, 2, 0, 0, 0, 100)
    # R0:L1 ↔ R1:L0 (cross-region)
    morld.add_gate(0, 1, 3, 100, 1, 0, 0)
    morld.add_gate(1, 0, 4, 0, 0, 1, 100)
    # R1:L0 ↔ R1:L1
    morld.add_gate(1, 0, 5, 100, 1, 1, 0)
    morld.add_gate(1, 1, 6, 0, 1, 0, 100)


# ============================================
# 5. fsm.py 직접 import (think/__init__.py 순환 import 우회)
# ============================================

import importlib.util

_fsm_path = os.path.join(_python_dir, "think", "fsm.py")
_spec = importlib.util.spec_from_file_location("think.fsm", _fsm_path)
_fsm = importlib.util.module_from_spec(_spec)
sys.modules["think.fsm"] = _fsm
_spec.loader.exec_module(_fsm)

_find_path = _fsm._find_path
_find_gate_x = _fsm._find_gate_x
GateTransitState = _fsm.GateTransitState
LifeState = _fsm.LifeState
LV_LIFE = _fsm.LV_LIFE
LV_COMBAT = _fsm.LV_COMBAT
LV_COMBAT_SUB = _fsm.LV_COMBAT_SUB
LV_TRANSIT = _fsm.LV_TRANSIT
CombatState = _fsm.CombatState
FleeState = _fsm.FleeState
ResignationState = _fsm.ResignationState
DesperateState = _fsm.DesperateState

# ============================================
# 6. 테스트 클래스
# ============================================


class TestFindPath:
    """_find_path() BFS 경로 탐색 테스트"""

    def test_same_location_returns_empty(self):
        """출발지 == 목적지 → 빈 리스트"""
        build_linear_map()
        result = _find_path(0, 0, 0, 0)
        assert result == [], f"같은 위치인데 경로 반환: {result}"

    def test_direct_neighbor(self):
        """인접 location 1-hop"""
        build_linear_map()
        result = _find_path(0, 0, 0, 1)
        assert len(result) == 1, f"1-hop인데 {len(result)}개: {result}"
        assert result[0]["region_id"] == 0
        assert result[0]["location_id"] == 1

    def test_two_hop(self):
        """2-hop: L0 → L1 → L2"""
        build_linear_map()
        result = _find_path(0, 0, 0, 2)
        assert len(result) == 2, f"2-hop인데 {len(result)}개: {result}"
        assert result[0]["location_id"] == 1, f"첫 hop이 L1이 아님: {result}"
        assert result[1]["location_id"] == 2, f"두번째 hop이 L2가 아님: {result}"

    def test_three_hop(self):
        """3-hop: L0 → L1 → L2 → L3"""
        build_linear_map()
        result = _find_path(0, 0, 0, 3)
        assert len(result) == 3, f"3-hop인데 {len(result)}개: {result}"
        locs = [h["location_id"] for h in result]
        assert locs == [1, 2, 3], f"경로 순서 불일치: {locs}"

    def test_reverse_direction(self):
        """역방향: L3 → L2 → L1 → L0"""
        build_linear_map()
        result = _find_path(0, 3, 0, 0)
        assert len(result) == 3, f"3-hop 역방향인데 {len(result)}개: {result}"
        locs = [h["location_id"] for h in result]
        assert locs == [2, 1, 0], f"역방향 경로 불일치: {locs}"

    def test_branching_shortest_path(self):
        """분기형에서 최단 경로 선택: L0 → L2 (직행) vs L0 → L1 → L2"""
        build_branching_map()
        result = _find_path(0, 0, 0, 2)
        # L0→L2 직접 연결 (1-hop) 또는 L0→L1→L2 (2-hop)
        # BFS이므로 1-hop이 먼저 발견됨
        assert len(result) <= 2, f"분기형에서 경로가 너무 김: {result}"
        # 최종 목적지 확인
        assert result[-1]["location_id"] == 2

    def test_branching_to_end(self):
        """분기형에서 끝방까지: L0 → L2 → L3"""
        build_branching_map()
        result = _find_path(0, 0, 0, 3)
        assert len(result) >= 2, f"최소 2-hop인데 {len(result)}개: {result}"
        assert result[-1]["location_id"] == 3

    def test_cross_region(self):
        """크로스 리전: R0:L0 → R1:L1"""
        build_cross_region_map()
        result = _find_path(0, 0, 1, 1)
        assert len(result) == 3, f"3-hop인데 {len(result)}개: {result}"
        # R0:L0 → R0:L1 → R1:L0 → R1:L1
        assert result[0] == {"region_id": 0, "location_id": 1}
        assert result[1] == {"region_id": 1, "location_id": 0}
        assert result[2] == {"region_id": 1, "location_id": 1}

    def test_no_path_raises(self):
        """연결 없는 목적지 → RuntimeError"""
        morld.add_region(0, "고립리전")
        morld.add_region(9, "다른리전")
        morld.add_location(0, 0, "고립방", length=50)
        morld.add_location(9, 0, "다른방", length=50)
        # gate 없음

        try:
            _find_path(0, 0, 9, 0)
            assert False, "연결 없는 경로인데 에러 안 남"
        except RuntimeError as e:
            assert "경로 없음" in str(e), f"에러 메시지 불일치: {e}"


class TestFindGateX:
    """_find_gate_x() Gate x좌표 탐색 테스트"""

    def test_direct_gate_x(self):
        """직접 연결된 Gate의 x좌표 반환"""
        build_linear_map()
        npc_id = 10
        morld.register_unit(npc_id, "테스트NPC", location=(0, 0))
        agent = FakeAgent(npc_id, location=(0, 0))

        target = {"region_id": 0, "location_id": 1}
        x = _find_gate_x(agent, target)
        assert x == 100, f"L0→L1 gate x가 100이 아님: {x}"

    def test_reverse_gate_x(self):
        """역방향 Gate의 x좌표"""
        build_linear_map()
        npc_id = 11
        morld.register_unit(npc_id, "테스트NPC2", location=(0, 1))
        agent = FakeAgent(npc_id, location=(0, 1))

        target = {"region_id": 0, "location_id": 0}
        x = _find_gate_x(agent, target)
        assert x == 0, f"L1→L0 gate x가 0이 아님: {x}"

    def test_no_gate_raises(self):
        """직접 Gate가 없으면 RuntimeError"""
        build_linear_map()
        npc_id = 12
        morld.register_unit(npc_id, "테스트NPC3", location=(0, 0))
        agent = FakeAgent(npc_id, location=(0, 0))

        # L0 → L3 직접 gate 없음 (L1, L2 경유 필요)
        target = {"region_id": 0, "location_id": 3}
        try:
            _find_gate_x(agent, target)
            assert False, "직접 gate 없는데 에러 안 남"
        except RuntimeError as e:
            assert "Gate 없음" in str(e), f"에러 메시지 불일치: {e}"

    def test_cross_region_gate_x(self):
        """크로스 리전 Gate x좌표"""
        build_cross_region_map()
        npc_id = 13
        morld.register_unit(npc_id, "테스트NPC4", location=(0, 1))
        agent = FakeAgent(npc_id, location=(0, 1))

        target = {"region_id": 1, "location_id": 0}
        x = _find_gate_x(agent, target)
        assert x == 100, f"R0:L1→R1:L0 gate x가 100이 아님: {x}"


class TestLifeState:
    """LifeState — FSM root 상태"""

    def test_level(self):
        """LifeState.level == LV_LIFE(0)"""
        state = LifeState()
        assert state.level == LV_LIFE

    def test_update_returns_false(self):
        """update()는 항상 False (Life 로직으로 진행)"""
        state = LifeState()
        agent = FakeAgent(99)
        result = state.update(agent)
        assert result is False, f"LifeState.update()가 True 반환: {result}"


class TestGateTransitState:
    """GateTransitState — multi-hop Gate 이동"""

    def _setup_npc_at(self, npc_id, location, name="테스트NPC"):
        """NPC를 특정 위치에 배치하고 FakeAgent 반환"""
        morld.register_unit(npc_id, name, location=location)
        agent = FakeAgent(npc_id, location=location, name=name)
        return agent

    def test_single_hop_enter(self):
        """1-hop: enter() → approaching 단계, move job 삽입"""
        build_linear_map()
        # 플레이어 등록 (행동 로그용)
        morld.register_unit(1, "플레이어", location=(0, 0))

        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target, name="이동")
        agent._fsm_push(state)

        # enter() 검증
        assert state.stage == "approaching"
        assert len(state.hops) == 1, f"1-hop인데 {len(state.hops)}개: {state.hops}"
        assert state.hop_index == 0
        assert agent._action_taken is True

        # move job 삽입 확인
        jobs = morld.get_all_jobs(10)
        assert len(jobs) >= 1, "enter에서 move job 미삽입"
        last_job = jobs[-1]
        assert last_job["action"] == "move"
        assert last_job["target_x"] == 100  # L0→L1 gate x

    def test_single_hop_approaching_to_transiting(self):
        """approaching → Gate 도달 → transiting 전환"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 0))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # approaching 중 — move job 활성
        morld.clear_jobs(10)
        morld.insert_job(10, {"action": "move", "name": "이동"})
        agent._action_taken = False
        result = state.update(agent)
        assert result is True, "approaching 중인데 False 반환"
        assert state.stage == "approaching"

        # Gate 도달 — move job 완료 (job 없음)
        morld.clear_jobs(10)
        agent._action_taken = False
        result = state.update(agent)
        assert result is True, "transiting 전환인데 False 반환"
        assert state.stage == "transiting"

        # 상태:이동중 prop 확인
        assert morld.get_unit_prop(10, "상태:이동중") == 1

    def test_single_hop_arrival(self):
        """transiting → 상태:이동중=0 → pop (도착)"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 1))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # approaching → transiting 빠르게 진행
        morld.clear_jobs(10)  # approaching move job 제거 (Gate 도달)
        state.update(agent)  # → transiting

        # DES가 이동 완료 처리 시뮬레이션
        morld.set_unit_prop(10, "상태:이동중", 0)
        morld.set_unit_location(10, 0, 1)

        agent._action_taken = False
        result = state.update(agent)
        assert result is False, "도착인데 True 반환 (Life 로직 차단 중)"

        # pop 확인
        assert len(agent._fsm_stack) == 0, "도착했는데 스택에 남아있음"
        assert len(agent._popped_states) == 1

    def test_multi_hop_three_locations(self):
        """3-hop: L0 → L1 → L2 → L3"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 3))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 3, "x": 50, "length": 100}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # enter: 3 hops, approaching
        assert len(state.hops) == 3, f"3-hop인데 {len(state.hops)}개"
        assert state.stage == "approaching"
        assert state.hop_index == 0

        # === Hop 0: L0 → L1 (approaching → transiting) ===
        morld.clear_jobs(10)
        state.update(agent)  # approaching → Gate 도달 → transiting
        assert state.stage == "transiting"
        assert morld.get_unit_prop(10, "상태:이동중") == 1

        # DES 이동 완료: L1 도착
        morld.set_unit_prop(10, "상태:이동중", 0)
        morld.set_unit_location(10, 0, 1)

        # === Hop 1: L1 → L2 (중간 경유지, transiting only) ===
        agent._action_taken = False
        state.update(agent)  # hop_index 1 → 즉시 transiting
        assert state.hop_index == 1
        assert state.stage == "transiting"
        assert morld.get_unit_prop(10, "상태:이동중") == 1

        # DES 이동 완료: L2 도착
        morld.set_unit_prop(10, "상태:이동중", 0)
        morld.set_unit_location(10, 0, 2)

        # === Hop 2: L2 → L3 (최종 hop, transiting) ===
        agent._action_taken = False
        state.update(agent)  # hop_index 2 → 즉시 transiting
        assert state.hop_index == 2
        assert state.stage == "transiting"

        # DES 이동 완료: L3 도착 (최종)
        morld.set_unit_prop(10, "상태:이동중", 0)
        morld.set_unit_location(10, 0, 3)

        agent._action_taken = False
        result = state.update(agent)
        assert result is False, "최종 도착인데 True 반환"
        assert len(agent._fsm_stack) == 0

    def test_cross_region_transit(self):
        """크로스 리전 이동: R0:L0 → R1:L1"""
        build_cross_region_map()
        morld.register_unit(1, "플레이어", location=(1, 1))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 1, "location_id": 1, "x": 50, "length": 100}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # 3 hops: R0:L0 → R0:L1 → R1:L0 → R1:L1
        assert len(state.hops) == 3
        assert state.hops[0] == {"region_id": 0, "location_id": 1}
        assert state.hops[1] == {"region_id": 1, "location_id": 0}
        assert state.hops[2] == {"region_id": 1, "location_id": 1}

    def test_departure_log_same_location(self):
        """출발 로그: 플레이어와 같은 location일 때만"""
        build_linear_map()
        # 플레이어가 NPC와 같은 위치
        morld.register_unit(1, "플레이어", location=(0, 0))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        morld._logs.clear()
        state = GateTransitState(target)
        agent._fsm_push(state)

        assert len(morld._logs) >= 1, "같은 위치인데 출발 로그 없음"
        assert "이동을 시작" in morld._logs[-1], f"출발 로그 내용 불일치: {morld._logs[-1]}"

    def test_departure_log_different_location(self):
        """출발 로그: 플레이어와 다른 location이면 로그 없음"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 3))  # 다른 위치
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        morld._logs.clear()
        state = GateTransitState(target)
        agent._fsm_push(state)

        assert len(morld._logs) == 0, f"다른 위치인데 출발 로그 있음: {morld._logs}"

    def test_arrival_log_same_location(self):
        """도착 로그: 플레이어와 같은 목적지일 때"""
        build_linear_map()
        # 플레이어가 목적지에 있음
        morld.register_unit(1, "플레이어", location=(0, 1))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # approaching → transiting
        morld.clear_jobs(10)
        state.update(agent)

        # 도착
        morld.set_unit_prop(10, "상태:이동중", 0)
        morld.set_unit_location(10, 0, 1)

        morld._logs.clear()
        state.update(agent)

        arrival_logs = [l for l in morld._logs if "도착" in l]
        assert len(arrival_logs) >= 1, f"도착 로그 없음: {morld._logs}"

    def test_arrival_log_different_location(self):
        """도착 로그: 플레이어가 다른 곳이면 로그 없음"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 3))  # 다른 위치
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # approaching → transiting
        morld.clear_jobs(10)
        state.update(agent)

        # 도착
        morld.set_unit_prop(10, "상태:이동중", 0)
        morld.set_unit_location(10, 0, 1)

        morld._logs.clear()
        state.update(agent)

        arrival_logs = [l for l in morld._logs if "도착" in l]
        assert len(arrival_logs) == 0, f"다른 위치인데 도착 로그 있음: {morld._logs}"

    def test_exit_clears_traveling_prop(self):
        """exit()에서 상태:이동중 정리"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 0))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # 강제로 이동중 상태에서 pop
        morld.set_unit_prop(10, "상태:이동중", 1)
        agent._fsm_pop()

        prop = morld.get_unit_prop(10, "상태:이동중")
        assert prop == 0, f"exit() 후 상태:이동중 미정리: {prop}"

    def test_already_at_destination(self):
        """이미 목적지에 있으면 즉시 pop"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 0))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        # 같은 위치를 목적지로 지정
        target = {"region_id": 0, "location_id": 0, "x": 50, "length": 100}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # _find_path가 빈 리스트 반환 → enter()에서 즉시 pop
        assert len(agent._fsm_stack) == 0, "이미 목적지인데 스택에 남아있음"

    def test_level_constant(self):
        """GateTransitState.level == LV_TRANSIT(30)"""
        state = GateTransitState({"region_id": 0, "location_id": 0})
        assert state.level == LV_TRANSIT

    def test_transiting_blocks_think(self):
        """transiting 중 update() → True (think 차단)"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 0))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 50, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # approaching → transiting
        morld.clear_jobs(10)
        state.update(agent)  # → transiting

        # transiting 중 update
        agent._action_taken = False
        result = state.update(agent)
        assert result is True, "transiting 중인데 False 반환 (think 차단 안 됨)"
        assert agent._action_taken is True

    def test_final_hop_uses_target_x(self):
        """최종 hop의 move job은 target의 x 사용"""
        build_linear_map()
        morld.register_unit(1, "플레이어", location=(0, 0))
        agent = self._setup_npc_at(10, (0, 0), "세라")
        target = {"region_id": 0, "location_id": 1, "x": 77, "length": 200}

        state = GateTransitState(target)
        agent._fsm_push(state)

        # approaching → transiting (최종 hop)
        morld.clear_jobs(10)
        state.update(agent)

        # transiting move job 확인
        jobs = morld.get_all_jobs(10)
        transit_job = jobs[-1]
        assert transit_job["target_x"] == 77, \
            f"최종 hop target_x가 77이 아님: {transit_job['target_x']}"


class TestIsCreature:
    """morld API 기반 is_creature 판별 테스트"""

    def test_character_not_creature(self):
        """캐릭터(is_creature=False) → get_unit_info 확인"""
        morld.register_unit(10, "세라", is_creature=False)
        info = morld.get_unit_info(10)
        assert info is not None
        assert info.get("is_creature") is False or not info.get("is_creature")

    def test_creature_is_creature(self):
        """크리처(is_creature=True) → get_unit_info 확인"""
        morld.register_unit(20, "고블린", is_creature=True)
        info = morld.get_unit_info(20)
        assert info is not None
        assert info["is_creature"] is True

    def test_object_not_creature(self):
        """오브젝트(is_object=True) → creature 아님"""
        morld.register_unit(30, "의자", is_object=True)
        info = morld.get_unit_info(30)
        assert info is not None
        assert not info.get("is_creature")


# ============================================
# 7. 전투 FSM 테스트 인프라
# ============================================

import types

# -- combat stub ---
_combat_stub = types.ModuleType("combat")
_combat_stub._emit_combat_line = lambda uid, kind: None
_combat_stub._in_range = {}  # {(uid, tid): bool}
_combat_stub._attack_result = {}  # uid -> dict
_combat_stub._combat_stats = {}  # (uid, stat) -> val
_combat_stub._enemies_at = {}  # (uid, r, l) -> bool


def _stub_is_in_range(uid, tid):
    return _combat_stub._in_range.get((uid, tid), True)


def _stub_execute_attack(uid, tid):
    return _combat_stub._attack_result.get(uid, {"message": "공격"})


def _stub_get_combat_stat(uid, stat):
    return _combat_stub._combat_stats.get((uid, stat), 1.0)


def _stub_has_enemies_at_location(uid, r, l):
    return _combat_stub._enemies_at.get((uid, r, l), False)


_combat_stub.is_in_range = _stub_is_in_range
_combat_stub.execute_attack = _stub_execute_attack
_combat_stub.get_combat_stat = _stub_get_combat_stat
_combat_stub.has_enemies_at_location = _stub_has_enemies_at_location
sys.modules["combat"] = _combat_stub

# -- survival stub ---
_surv_stub = types.ModuleType("survival")
_surv_stub._fainted = {}    # uid -> bool
_surv_stub._faint_ms = {}   # uid -> remaining ms
_surv_stub._exhausted = {}  # uid -> bool
_surv_stub._exhaust_ms = {} # uid -> remaining ms
_surv_stub._health = {}     # uid -> hp
_surv_stub._max_hp = {}     # uid -> max_hp

_surv_stub.is_npc_fainted = lambda uid: _surv_stub._fainted.get(uid, False)
_surv_stub.get_faint_remaining_millis = lambda uid: _surv_stub._faint_ms.get(uid, 0)
_surv_stub.is_npc_exhausted = lambda uid: _surv_stub._exhausted.get(uid, False)
_surv_stub.get_exhaustion_remaining_millis = lambda uid: _surv_stub._exhaust_ms.get(uid, 0)
_surv_stub.get_health = lambda uid: _surv_stub._health.get(uid, 100)
_surv_stub.get_max_health = lambda uid: _surv_stub._max_hp.get(uid, 100)
sys.modules["survival"] = _surv_stub


def _reset_combat_stubs():
    """전투 stub 상태 초기화"""
    _combat_stub._in_range.clear()
    _combat_stub._attack_result.clear()
    _combat_stub._combat_stats.clear()
    _combat_stub._enemies_at.clear()
    _surv_stub._fainted.clear()
    _surv_stub._faint_ms.clear()
    _surv_stub._exhausted.clear()
    _surv_stub._exhaust_ms.clear()
    _surv_stub._health.clear()
    _surv_stub._max_hp.clear()


class CombatFakeAgent:
    """전투 FSM 테스트용 Agent — 컨트롤 가능한 메서드 제공"""

    BATTLE_BEHAVIOR = {"combat_style": "aggressive"}
    COMBAT_ATTACK_DURATION = 3_000
    COMBAT_REGROUP_HP_THRESHOLD = 0.5
    COMBAT_DESPERATE_CHANCE = 0.5
    COMBAT_END_COOLDOWN = 30_000

    def __init__(self, unit_id, location=(0, 0), name="테스트NPC"):
        self.unit_id = unit_id
        self._location = location
        self._name = name
        self._action_taken = False
        self._fsm_stack = []
        self._popped_states = []
        self._last_job = None
        self._time = 0

        # 테스트 컨트롤 필드
        self._valid_targets = set()       # 유효한 전투 대상 ID
        self._nearest_enemy = None        # _scan_nearest_enemy 반환값
        self._should_end = False          # _should_end_combat 반환값
        self._safe_location = None        # _pick_safe_location 반환값
        self._surrounded = False          # _is_surrounded 반환값
        self._location_target = None      # _make_location_target 반환값

    def get_time(self):
        return self._time

    def get_info(self):
        return morld.get_unit_info(self.unit_id) or {"name": self._name}

    def get_location(self):
        loc = morld.get_unit_location(self.unit_id)
        return loc if loc else self._location

    def _fsm_push(self, state):
        # 동일/상위 레벨 auto-pop
        while self._fsm_stack and self._fsm_stack[-1].level >= state.level:
            popped = self._fsm_stack.pop()
            popped.exit(self)
            self._popped_states.append(popped)
        self._fsm_stack.append(state)
        state.enter(self)

    def _fsm_pop(self):
        if self._fsm_stack:
            state = self._fsm_stack.pop()
            state.exit(self)
            self._popped_states.append(state)
            return state
        return None

    def _fsm_top(self):
        return self._fsm_stack[-1] if self._fsm_stack else None

    def _insert_idle_job(self, name, duration_millis):
        self._last_job = {"name": name, "duration": duration_millis,
                          "action": "stay"}
        if duration_millis > 0:
            morld.insert_job(self.unit_id, self._last_job)

    def _move_to(self, target, name="이동"):
        self._last_job = {"name": name, "action": "move",
                          "region_id": target["region_id"],
                          "location_id": target["location_id"]}
        morld.insert_job(self.unit_id, self._last_job)
        self._action_taken = True

    def _is_valid_combat_target(self, target_id):
        return target_id in self._valid_targets

    def _scan_nearest_enemy(self):
        return self._nearest_enemy

    def _should_end_combat(self, last_enemy_ms=None):
        return self._should_end

    def _make_location_target(self, region_id, location_id):
        if self._location_target:
            return self._location_target
        return {"region_id": region_id, "location_id": location_id}

    def _pick_safe_location(self):
        return self._safe_location

    def _is_surrounded(self):
        return self._surrounded


def _make_combat_agent(uid=10, location=(0, 0), name="전사"):
    """전투 agent 생성 + morld 등록"""
    morld.register_unit(uid, name, location=location)
    return CombatFakeAgent(uid, location=location, name=name)


# ============================================
# 8. 전투 FSM 테스트
# ============================================


class TestCombatStateProperties:
    """CombatState 속성/레벨 테스트"""

    def test_level(self):
        s = CombatState(20)
        assert s.level == LV_COMBAT

    def test_state_type(self):
        s = CombatState(20)
        assert s.state_type == "combat"

    def test_initial_phase(self):
        s = CombatState(20)
        assert s.phase == "engaging"
        assert s.target_id == 20

    def test_flee_level(self):
        assert FleeState.level == LV_COMBAT_SUB

    def test_resignation_level(self):
        assert ResignationState.level == LV_COMBAT_SUB

    def test_desperate_level(self):
        assert DesperateState.level == LV_COMBAT_SUB


class TestCombatStateUpdate:
    """CombatState.update() 동작 테스트"""

    def setup(self):
        _reset_combat_stubs()

    def test_dead_pops_combat(self):
        """사망 시 CombatState pop"""
        self.setup()
        agent = _make_combat_agent()
        morld.set_unit_prop(10, "상태:사망", True)

        state = CombatState(20)
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_fainted_stays_in_combat(self):
        """기절 시 전투 유지 + idle job"""
        self.setup()
        agent = _make_combat_agent()
        _surv_stub._fainted[10] = True
        _surv_stub._faint_ms[10] = 5_000

        state = CombatState(20)
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert len(agent._fsm_stack) == 1  # 전투 유지
        assert agent._last_job["name"] == "기절"

    def test_exhausted_stays_in_combat(self):
        """탈진 시 전투 유지 + idle job"""
        self.setup()
        agent = _make_combat_agent()
        _surv_stub._exhausted[10] = True
        _surv_stub._exhaust_ms[10] = 3_000

        state = CombatState(20)
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert agent._last_job["name"] == "탈진"

    def test_no_enemy_end_combat(self):
        """적 없음 + _should_end_combat=True -> pop"""
        self.setup()
        agent = _make_combat_agent()
        agent._nearest_enemy = None
        agent._should_end = True

        state = CombatState(20)
        agent._fsm_push(state)
        state.target_id = None  # 대상 없음
        agent._action_taken = False
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0
        assert agent._last_job["name"] == "전투 종료"

    def test_no_enemy_alert_wait(self):
        """적 없음 + _should_end_combat=False -> 경계 대기"""
        self.setup()
        agent = _make_combat_agent()
        agent._nearest_enemy = None
        agent._should_end = False

        state = CombatState(20)
        agent._fsm_push(state)
        state.target_id = None
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert agent._last_job["name"] == "경계"

    def test_hp_retreat_pushes_flee(self):
        """HP 낮음 + 비공격적 -> FleeState push"""
        self.setup()
        agent = _make_combat_agent()
        agent.BATTLE_BEHAVIOR = {"combat_style": "defensive",
                                 "retreat_threshold": 0.3}
        agent._nearest_enemy = 20
        agent._valid_targets = {20}
        _surv_stub._health[10] = 20   # 20%
        _surv_stub._max_hp[10] = 100
        morld.register_unit(20, "적", location=(0, 0))

        state = CombatState(20)
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        # FleeState가 push됨
        top = agent._fsm_top()
        assert top.state_type == "flee"

    def test_aggressive_no_retreat(self):
        """aggressive 스타일 -> HP 낮아도 후퇴 안 함"""
        self.setup()
        agent = _make_combat_agent()
        agent.BATTLE_BEHAVIOR = {"combat_style": "aggressive"}
        agent._nearest_enemy = 20
        agent._valid_targets = {20}
        _surv_stub._health[10] = 10
        _surv_stub._max_hp[10] = 100
        morld.register_unit(20, "적", location=(0, 0))
        _combat_stub._in_range[(10, 20)] = True

        state = CombatState(20)
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        # FleeState가 아닌 공격
        top = agent._fsm_top()
        assert top.state_type == "combat"

    def test_engaging_moves_to_target(self):
        """engaging 단계: 사거리 밖 -> 이동"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = {20}
        agent._nearest_enemy = 20
        morld.register_unit(20, "적", location=(0, 1))
        _combat_stub._in_range[(10, 20)] = False

        state = CombatState(20)
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert state.phase == "engaging"
        assert agent._last_job["action"] == "move"

    def test_engaging_to_attacking(self):
        """engaging: 사거리 진입 -> attacking 전환"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = {20}
        agent._nearest_enemy = 20
        morld.register_unit(20, "적", location=(0, 0))
        _combat_stub._in_range[(10, 20)] = True
        _combat_stub._attack_result[10] = {"message": "공격", "target_fainted": False}

        state = CombatState(20)
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert state.phase == "attacking"
        assert agent._last_job["name"] == "공격"

    def test_attacking_target_fainted_end_combat(self):
        """attacking: 대상 기절 + 전투 종료 조건 -> pop"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = {20}
        agent._nearest_enemy = None  # 더 이상 적 없음
        agent._should_end = True
        morld.register_unit(20, "적", location=(0, 0))
        _combat_stub._in_range[(10, 20)] = True
        _combat_stub._attack_result[10] = {"message": "공격", "target_fainted": True}

        state = CombatState(20)
        state.phase = "attacking"
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0
        assert agent._last_job["name"] == "전투 승리"

    def test_attacking_out_of_range_re_engage(self):
        """attacking: 사거리 이탈 -> engaging 전환"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = {20}
        agent._nearest_enemy = 20
        morld.register_unit(20, "적", location=(0, 1))
        _combat_stub._in_range[(10, 20)] = False

        state = CombatState(20)
        state.phase = "attacking"
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert state.phase == "engaging"
        assert agent._last_job["action"] == "move"

    def test_invalid_target_rescans(self):
        """대상 무효 -> 새 적 탐색"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = set()  # 기존 대상 무효
        agent._nearest_enemy = 30  # 새 적
        morld.register_unit(30, "새적", location=(0, 0))
        _combat_stub._in_range[(10, 30)] = True
        _combat_stub._attack_result[10] = {"message": "", "target_fainted": False}

        state = CombatState(20)  # 기존 대상 20 (무효)
        state.phase = "attacking"
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert state.target_id == 30


class TestFleeState:
    """FleeState 동작 테스트"""

    def setup(self):
        _reset_combat_stubs()

    def test_flee_moves_to_safe_location(self):
        """도주: 안전 구역으로 이동"""
        self.setup()
        agent = _make_combat_agent()
        agent._safe_location = {"region_id": 0, "location_id": 2}

        state = FleeState()
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert state.flee_target == {"region_id": 0, "location_id": 2}
        assert agent._last_job["action"] == "move"

    def test_flee_arrival_starts_regrouping(self):
        """도주 도착 -> regrouping"""
        self.setup()
        agent = _make_combat_agent(location=(0, 2))
        agent._safe_location = {"region_id": 0, "location_id": 2}
        _surv_stub._health[10] = 30  # 낮은 HP
        _surv_stub._max_hp[10] = 100
        agent.COMBAT_REGROUP_HP_THRESHOLD = 0.5

        state = FleeState()
        state.flee_target = {"region_id": 0, "location_id": 2}
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert state.phase == "regrouping"
        assert agent._last_job["name"] == "정비"

    def test_regrouping_hp_recovery_pops(self):
        """정비 중 HP 회복 -> pop"""
        self.setup()
        agent = _make_combat_agent(location=(0, 2))
        _surv_stub._health[10] = 60
        _surv_stub._max_hp[10] = 100
        agent.COMBAT_REGROUP_HP_THRESHOLD = 0.5

        state = FleeState()
        state.phase = "regrouping"
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_regrouping_enemy_re_engage(self):
        """정비 중 적 재감지 -> CombatState re-engage"""
        self.setup()
        agent = _make_combat_agent(location=(0, 2))
        agent._nearest_enemy = 20
        agent.BATTLE_BEHAVIOR = {"combat_style": "defensive"}
        _surv_stub._health[10] = 30
        _surv_stub._max_hp[10] = 100
        agent.COMBAT_REGROUP_HP_THRESHOLD = 0.5

        # CombatState -> FleeState 스택
        combat_s = CombatState(20)
        combat_s.phase = "attacking"
        agent._fsm_stack.append(combat_s)
        state = FleeState()
        state.phase = "regrouping"
        agent._fsm_stack.append(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is False
        # FleeState가 pop되고 CombatState가 top
        top = agent._fsm_top()
        assert top.state_type == "combat"
        assert top.target_id == 20
        assert top.phase == "engaging"

    def test_no_safe_location_surrounded_resignation(self):
        """안전 구역 없음 + 포위 -> 체념/필사"""
        self.setup()
        import random
        old_random = random.random
        # COMBAT_DESPERATE_CHANCE=0 -> 항상 체념
        agent = _make_combat_agent()
        agent._safe_location = None
        agent._surrounded = True
        agent.COMBAT_DESPERATE_CHANCE = 0.0

        # CombatState -> FleeState
        combat_s = CombatState(20)
        agent._fsm_stack.append(combat_s)
        state = FleeState()
        agent._fsm_stack.append(state)
        agent._action_taken = False

        random.random = lambda: 0.5  # > 0.0 -> 체념
        result = state.update(agent)
        random.random = old_random

        assert result is True
        # FleeState가 auto-pop되고 ResignationState가 top
        top = agent._fsm_top()
        assert top.state_type == "resignation"

    def test_no_safe_location_surrounded_desperate(self):
        """안전 구역 없음 + 포위 -> 필사의 저항"""
        self.setup()
        import random
        old_random = random.random
        agent = _make_combat_agent()
        agent._safe_location = None
        agent._surrounded = True
        agent.COMBAT_DESPERATE_CHANCE = 1.0  # 항상 필사

        combat_s = CombatState(20)
        agent._fsm_stack.append(combat_s)
        state = FleeState()
        agent._fsm_stack.append(state)
        agent._action_taken = False

        random.random = lambda: 0.5  # < 1.0 -> 필사
        result = state.update(agent)
        random.random = old_random

        assert result is True
        top = agent._fsm_top()
        assert top.state_type == "desperate"

    def test_no_safe_not_surrounded_force_combat(self):
        """안전 구역 없음 + 미포위 -> 강제 전투 복귀"""
        self.setup()
        agent = _make_combat_agent()
        agent._safe_location = None
        agent._surrounded = False

        combat_s = CombatState(20)
        agent._fsm_stack.append(combat_s)
        state = FleeState()
        agent._fsm_stack.append(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        # FleeState pop -> CombatState가 top
        top = agent._fsm_top()
        assert top.state_type == "combat"
        assert top.phase == "attacking"

    def test_dead_during_flee(self):
        """도주 중 사망 -> pop"""
        self.setup()
        agent = _make_combat_agent()
        morld.set_unit_prop(10, "상태:사망", True)

        state = FleeState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0


class TestResignationState:
    """ResignationState 동작 테스트"""

    def setup(self):
        _reset_combat_stubs()

    def test_enemy_exists_waits(self):
        """적 생존 -> 대기"""
        self.setup()
        agent = _make_combat_agent()
        agent._nearest_enemy = 20

        state = ResignationState()
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert agent._last_job["name"] == "체념"

    def test_enemy_cleared_pops(self):
        """적 전멸 -> pop"""
        self.setup()
        agent = _make_combat_agent()
        agent._nearest_enemy = None

        state = ResignationState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_dead_pops(self):
        """사망 -> pop"""
        self.setup()
        agent = _make_combat_agent()
        morld.set_unit_prop(10, "상태:사망", True)

        state = ResignationState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_fainted_waits(self):
        """기절 -> 대기"""
        self.setup()
        agent = _make_combat_agent()
        _surv_stub._fainted[10] = True
        _surv_stub._faint_ms[10] = 5_000

        state = ResignationState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is True
        assert agent._last_job["name"] == "기절"


class TestDesperateState:
    """DesperateState 동작 테스트"""

    def setup(self):
        _reset_combat_stubs()

    def test_attacks_nearest_enemy(self):
        """적 공격"""
        self.setup()
        agent = _make_combat_agent()
        agent._nearest_enemy = 20
        agent._valid_targets = {20}
        _combat_stub._attack_result[10] = {"message": "공격"}
        morld.register_unit(20, "적", location=(0, 0))

        state = DesperateState()
        agent._fsm_push(state)
        agent._action_taken = False
        result = state.update(agent)

        assert result is True
        assert agent._last_job["name"] == "필사"
        assert state.target_id == 20

    def test_no_enemy_pops(self):
        """적 전멸 -> pop"""
        self.setup()
        agent = _make_combat_agent()
        agent._nearest_enemy = None

        state = DesperateState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_dead_pops(self):
        """사망 -> pop"""
        self.setup()
        agent = _make_combat_agent()
        morld.set_unit_prop(10, "상태:사망", True)

        state = DesperateState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_fainted_waits(self):
        """기절 -> 전투 유지 대기"""
        self.setup()
        agent = _make_combat_agent()
        _surv_stub._fainted[10] = True
        _surv_stub._faint_ms[10] = 5_000

        state = DesperateState()
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is True
        assert agent._last_job["name"] == "기절"

    def test_invalid_target_rescans(self):
        """대상 무효 -> 새 적 탐색"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = set()  # 기존 대상 무효
        agent._nearest_enemy = 30
        _combat_stub._attack_result[10] = {"message": ""}
        morld.register_unit(30, "새적", location=(0, 0))

        state = DesperateState()
        state.target_id = 20  # 무효 대상
        agent._fsm_push(state)
        result = state.update(agent)

        assert result is True
        assert state.target_id == 30


class TestCombatStackTransitions:
    """전투 스택 전이 통합 테스트"""

    def setup(self):
        _reset_combat_stubs()

    def test_full_combat_lifecycle(self):
        """전투 진입 -> 공격 -> 적 기절 -> 전투 종료"""
        self.setup()
        agent = _make_combat_agent()
        agent._valid_targets = {20}
        agent._nearest_enemy = 20
        morld.register_unit(20, "적", location=(0, 0))
        _combat_stub._in_range[(10, 20)] = True

        # 1. 전투 진입
        combat_s = CombatState(20)
        agent._fsm_push(combat_s)
        assert len(agent._fsm_stack) == 1

        # 2. 공격 (적 생존)
        _combat_stub._attack_result[10] = {"message": "공격", "target_fainted": False}
        result = combat_s.update(agent)
        assert result is True
        assert combat_s.phase == "attacking"

        # 3. 적 기절 + 전투 종료
        agent._should_end = True
        agent._nearest_enemy = None
        _combat_stub._attack_result[10] = {"message": "공격", "target_fainted": True}
        result = combat_s.update(agent)
        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_combat_to_flee_to_regroup(self):
        """전투 -> HP 후퇴 -> 도주 -> 정비 -> 복귀"""
        self.setup()
        agent = _make_combat_agent()
        agent.BATTLE_BEHAVIOR = {"combat_style": "defensive",
                                 "retreat_threshold": 0.3}
        agent._valid_targets = {20}
        agent._nearest_enemy = 20
        morld.register_unit(20, "적", location=(0, 0))
        _surv_stub._health[10] = 20
        _surv_stub._max_hp[10] = 100

        # 1. 전투 -> HP 후퇴 -> FleeState push
        combat_s = CombatState(20)
        agent._fsm_push(combat_s)
        result = combat_s.update(agent)
        assert result is True
        assert agent._fsm_top().state_type == "flee"

        # 2. 도주 -> 안전 구역으로 이동
        flee_s = agent._fsm_top()
        agent._safe_location = {"region_id": 0, "location_id": 2}
        flee_s.update(agent)
        assert flee_s.phase == "fleeing"

        # 3. 도착 -> regrouping
        agent._location = (0, 2)
        morld.set_unit_location(10, 0, 2)
        agent._nearest_enemy = None  # 안전 구역에 적 없음
        flee_s.update(agent)
        assert flee_s.phase == "regrouping"

        # 4. HP 회복 -> FleeState pop -> CombatState 복귀
        _surv_stub._health[10] = 60
        result = flee_s.update(agent)
        assert result is False
        assert agent._fsm_top().state_type == "combat"

    def test_flee_surrounded_resignation(self):
        """도주 중 포위 -> 체념 (FleeState auto-pop)"""
        self.setup()
        import random
        old_random = random.random
        agent = _make_combat_agent()
        agent._safe_location = None
        agent._surrounded = True
        agent.COMBAT_DESPERATE_CHANCE = 0.0

        combat_s = CombatState(20)
        agent._fsm_stack.append(combat_s)
        flee_s = FleeState()
        agent._fsm_stack.append(flee_s)

        random.random = lambda: 0.5
        flee_s.update(agent)
        random.random = old_random

        # 스택: [CombatState, ResignationState]
        assert len(agent._fsm_stack) == 2
        assert agent._fsm_stack[0].state_type == "combat"
        assert agent._fsm_stack[1].state_type == "resignation"

    def test_resignation_enemy_cleared_combat_ends(self):
        """체념 -> 적 전멸 -> CombatState -> 전투 종료"""
        self.setup()
        agent = _make_combat_agent()
        agent._should_end = True
        agent._nearest_enemy = None

        combat_s = CombatState(20)
        combat_s.target_id = None
        agent._fsm_stack.append(combat_s)
        resign_s = ResignationState()
        agent._fsm_stack.append(resign_s)

        # 1. 적 전멸 -> ResignationState pop
        result = resign_s.update(agent)
        assert result is False
        assert agent._fsm_top().state_type == "combat"

        # 2. CombatState: 적 없음 + should_end -> pop
        result = combat_s.update(agent)
        assert result is False
        assert len(agent._fsm_stack) == 0

    def test_level_auto_pop(self):
        """동일 레벨 push -> 기존 state auto-pop"""
        self.setup()
        agent = _make_combat_agent()

        # FleeState(20) push
        flee_s = FleeState()
        agent._fsm_push(flee_s)
        assert len(agent._fsm_stack) == 1

        # ResignationState(20) push -> FleeState auto-pop
        resign_s = ResignationState()
        agent._fsm_push(resign_s)
        assert len(agent._fsm_stack) == 1
        assert agent._fsm_top().state_type == "resignation"
        assert flee_s in agent._popped_states
