# think_base.py — BaseAgent 골격
#
# 모든 NPC Agent의 기반 클래스.
# FSM 스택 + 감각 수집 + Job 삽입 + safety net + 기본 유틸리티 제공.
# 시나리오별 서브클래스에서 _on_think()을 구현하여 행동 결정.
#
# think 파이프라인:
#   1. FSM 스택 역순회 → update()=True면 차단
#   2. _perceive() → 감각 정보 수집 (self.perception에 저장)
#   3. _evaluate() → 상황 평가 (위험도 등 self.evaluation에 저장)
#   4. _on_think() → 행동 결정 (perception/evaluation 참조)
#
# 실행 순서: ThinkSystem → Agent.think() → Job 삽입 → JobBehaviorSystem 실행

import morld
from engine.fsm import LifeState


class BaseAgent:
    """NPC AI 기반 클래스

    FSM 스택으로 행동 컨텍스트를 관리.
    _perceive → _evaluate → _on_think 파이프라인.
    think()가 끝난 후 _action_taken이 False면 safety net job 삽입.
    """

    # 서브클래스에서 오버라이드: 행동별 소요 시간 (ms)
    ACTION_DURATION = {}

    # 기본 safety net 시간 (10분)
    SAFETY_NET_DURATION = 600_000

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self._action_taken = False
        self._fsm_stack = [LifeState()]
        self.perception = {}    # _perceive()에서 채워짐
        self.evaluation = {}    # _evaluate()에서 채워짐

    def think(self):
        """매 Step 호출 — FSM → perceive → evaluate → _on_think"""
        self._action_taken = False

        # 1. FSM 스택 역순회 (최상위 → 최하위)
        for _state in reversed(list(self._fsm_stack)):
            if _state.update(self):
                if not self._action_taken:
                    self._insert_idle_job("할 일 없음", self.SAFETY_NET_DURATION)
                return

        # 2. 감각 수집
        self.perception = self._perceive()

        # 3. 상황 평가
        self.evaluation = self._evaluate()

        # 4. 행동 결정 (5-tier 등)
        self._on_think()
        if not self._action_taken:
            self._insert_idle_job("할 일 없음", self.SAFETY_NET_DURATION)

    def _perceive(self):
        """감각 수집. 서브클래스에서 확장 가능.

        기본: engine/perception.py의 perceive_all() 호출.

        Returns:
            dict: {"hearing": [...], "sight": [...], "intuition": [...]}
        """
        try:
            from engine import perception
            return perception.perceive_all(self.unit_id)
        except (ImportError, Exception):
            return {}

    def _evaluate(self):
        """상황 평가. 서브클래스에서 확장 가능.

        기본: 청각 이벤트로 위험도 판정.

        Returns:
            dict: {"danger_level": 0~100, "heard_combat": bool, ...}
        """
        danger = 0
        heard_combat = False

        hearing = self.perception.get("hearing", [])
        for h in hearing:
            if h.get("category") == "전투":
                heard_combat = True
                danger = max(danger, 50)
            elif h.get("category") == "사고":
                danger = max(danger, 30)

        intuition = self.perception.get("intuition", [])
        for i in intuition:
            if i.get("subtype") == "danger":
                danger = max(danger, 70)

        return {
            "danger_level": danger,
            "heard_combat": heard_combat,
        }

    def _on_think(self):
        """서브클래스에서 구현: 행동 결정 로직

        self.perception과 self.evaluation을 참조하여 판단.
        """
        pass

    # ========================================
    # FSM 스택 관리
    # ========================================

    def _fsm_push(self, state):
        """FSM 상태를 스택에 push (동일 이상 레벨 자동 pop)"""
        while self._fsm_stack[-1].level >= state.level:
            self._fsm_pop()
        self._fsm_stack.append(state)
        state.enter(self)

    def _fsm_pop(self):
        """FSM 스택 최상위 pop (LifeState 보호)"""
        if len(self._fsm_stack) <= 1:
            info = self.get_info()
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            raise RuntimeError(
                "[FSM] " + str(name) + " — 스택 비어짐 (pop 불가). stack=" + str(self._fsm_stack))
        state = self._fsm_stack.pop()
        state.exit(self)
        return state

    def _fsm_top(self):
        """FSM 스택 최상위 상태 반환"""
        return self._fsm_stack[-1]

    def _fsm_pop_by_type(self, state_type):
        """특정 state_type의 State를 스택에서 제거"""
        for i in range(len(self._fsm_stack) - 1, 0, -1):
            if self._fsm_stack[i].state_type == state_type:
                state = self._fsm_stack.pop(i)
                state.exit(self)
                return state
        return None

    # ========================================
    # Focus Hold (대화/harass/romance 등 상호작용 동결)
    # ========================================

    def begin_hold(self):
        """Focus 상호작용 시작 — HoldState를 스택 최상위에 push.

        NPC의 모든 FSM 행동 및 think() 생존/스케줄 로직 차단.
        GateTransit 중이었으면 취소되고 현재 위치에 고정.
        """
        from engine.fsm import HoldState
        self._fsm_push(HoldState())

    def end_hold(self):
        """Focus 상호작용 종료 — HoldState pop."""
        self._fsm_pop_by_type("hold")

    # ========================================
    # Job 삽입 헬퍼
    # ========================================

    def _insert_idle_job(self, name, duration_ms):
        """대기 Job 삽입 (action=stay)"""
        morld.insert_job(self.unit_id, {
            "name": name,
            "action": "stay",
            "duration": duration_ms,
        })
        self._action_taken = True

    def _move_to(self, region_id, location_id):
        """이동 Job 삽입 (duration=0, C#이 자동 계산)"""
        loc = morld.get_unit_location(self.unit_id)
        if loc and loc[0] == region_id and loc[1] == location_id:
            return  # 이미 목적지에 있음
        morld.insert_job(self.unit_id, {
            "name": "이동",
            "action": "move",
            "target_region": region_id,
            "target_location": location_id,
            "duration": 0,
        })
        self._action_taken = True

    def _do_instant_action(self, name, duration_key=None):
        """이름 기반 행동 실행 (ACTION_DURATION 테이블 조회)"""
        duration = self._get_action_duration(duration_key or name)
        self._insert_idle_job(name, duration)

    def _get_action_duration(self, key):
        """행동별 소요 시간 조회 (서브클래스 오버라이드 가능)"""
        # 서브클래스 ACTION_DURATION 우선
        if key in self.ACTION_DURATION:
            return self.ACTION_DURATION[key]
        # safety net 키
        if key == "safety_net":
            return self.SAFETY_NET_DURATION
        # 기본 10분
        return self.SAFETY_NET_DURATION

    # ========================================
    # 유틸리티
    # ========================================

    def get_info(self):
        """유닛 정보 조회"""
        return morld.get_unit_info(self.unit_id)

    def get_location(self):
        """현재 위치 (region_id, location_id) 또는 None"""
        return morld.get_unit_location(self.unit_id)

    def get_name(self):
        """유닛 이름"""
        return morld.get_unit_name(self.unit_id) or str(self.unit_id)


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
