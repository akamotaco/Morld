# think/order_handlers.py — 분대 지시(Order) 핸들러 Mixin
#
# CommandPhase가 Order.main_type()에 따라 dispatch하는 핸들러.
# BaseAgent에 mixin되어 agent._{handler}(order) 형태로 호출됨.
#
# 핸들러 규칙:
#   return True  → 지시 처리 완료 (하위 phase 차단)
#   return False → 지시 처리 불가, 아래로 위임
#
# Phase 2: follow / 이동 / 대기 / 경계 / 수색 / 수집 (기본 구현)

import morld


class OrderHandlerMixin:
    """분대 지시 핸들러 — BaseAgent에 mixin"""

    def _handle_order_follow(self, order):
        """리더 따라가기 — 리더와 같은 location 유지"""
        import party as _party

        squad = _party.get_squad_by_unit(self.unit_id)
        if not squad or not squad.leader_id:
            return False

        leader_loc = morld.get_unit_location(squad.leader_id)
        if not leader_loc:
            return False

        my_loc = self.get_location()
        if my_loc and my_loc[0] == leader_loc[0] and my_loc[1] == leader_loc[1]:
            # 같은 location → 대기
            self._insert_idle_job("대기", 5 * 60_000)
            self._action_taken = True
            return True

        # 다른 location → 이동 (_move_to가 cross-location도 처리)
        self._move_to(
            {"region_id": leader_loc[0], "location_id": leader_loc[1]},
            "이동")
        self._action_taken = True
        return True

    def _handle_order_move(self, order):
        """목표 지점 이동"""
        if not order.target:
            return False

        if self._is_at(order.target):
            # 도착 → 대기
            self._insert_idle_job("대기", 5 * 60_000)
            self._action_taken = True
            return True

        self._move_to(order.target, "이동")
        self._action_taken = True
        return True

    def _handle_order_wait(self, order):
        """대기 — 현위치 정지"""
        sub = order.sub_type()
        if sub == "휴식":
            return False  # 생활 phase로 위임 (욕구 해소 허용)

        self._insert_idle_job("대기", 5 * 60_000)
        self._action_taken = True
        return True

    def _handle_order_guard(self, order):
        """경계 — 현위치 idle + 적 감지 (전투 합류는 Phase 5)"""
        self._insert_idle_job("경계", 5 * 60_000)
        self._action_taken = True
        return True

    def _handle_order_search(self, order):
        """수색 — 현위치 수색 (상세 로직은 후속 Phase)"""
        self._insert_idle_job("수색", 5 * 60_000)
        self._action_taken = True
        return True

    def _handle_order_collect(self, order):
        """수집 — 현위치 수집 (상세 로직은 후속 Phase)"""
        self._insert_idle_job("수집", 5 * 60_000)
        self._action_taken = True
        return True
