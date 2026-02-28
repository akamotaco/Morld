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
LV_TRANSIT = _fsm.LV_TRANSIT

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
