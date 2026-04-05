# think_base.py — BaseAgent 골격
#
# 모든 NPC Agent의 기반 클래스.
# Job 삽입, safety net, 기본 유틸리티 제공.
# 시나리오별 서브클래스에서 _on_think()을 구현하여 행동 결정.
#
# 실행 순서: ThinkSystem → Agent.think() → Job 삽입 → JobBehaviorSystem 실행

import morld


class BaseAgent:
    """NPC AI 기반 클래스

    서브클래스에서 _on_think()을 오버라이드하여 행동 결정 로직 구현.
    think()가 끝난 후 _action_taken이 False면 safety net job 삽입.
    """

    # 서브클래스에서 오버라이드: 행동별 소요 시간 (ms)
    ACTION_DURATION = {}

    # 기본 safety net 시간 (10분)
    SAFETY_NET_DURATION = 600_000

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self._action_taken = False

    def think(self):
        """매 Step 호출 — 서브클래스는 _on_think()을 구현"""
        self._action_taken = False
        self._on_think()
        if not self._action_taken:
            self._insert_idle_job("할 일 없음", self.SAFETY_NET_DURATION)

    def _on_think(self):
        """서브클래스에서 구현: 행동 결정 로직"""
        pass

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
