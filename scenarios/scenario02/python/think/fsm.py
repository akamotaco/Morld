# think/fsm.py  - S02 FSM 상태 (전투/분대/도주)
#
# 엔진 코어 (FSMState, LifeState, GateTransitState, 경로 탐색)는
# engine/fsm.py에서 제공. 여기는 S02 전용 상태만 정의.
#
# 레벨 계층:
#   LV_LIFE        =  0  생활 (root, 불변)         — engine
#   LV_STANDBY     =  3  분대 대기                 — S02
#   LV_COMMAND     =  5  분대 지시                 — S02
#   LV_COMBAT      = 10  전투                      — S02
#   LV_COMBAT_SUB  = 20  전투 하위 (도주/체념/필사) — S02
#   LV_TRANSIT     = 30  Gate 이동                 — engine

import morld
import random

# 엔진 코어 임포트 + 하위 호환 re-export
from engine.fsm import (
    FSMState,
    LifeState,
    LV_LIFE,
    LV_TRANSIT,
    find_gate_x as _find_gate_x,
    find_path as _find_path,
    GateTransitState,
)

# S02 전용 레벨 상수
LV_STANDBY = 3
LV_COMMAND = 5
LV_COMBAT = 10
LV_COMBAT_SUB = 20


# ── S02 전투 헬퍼 ─────────────────────────────────────────

def _log_fsm(tag, agent, detail, phase=None):
    """FSM 디버그 로그 (전투 계열 공용)"""
    info = morld.get_unit_info(agent.unit_id)
    name = info.get("name", "?") if info else "?"
    phase_str = " phase=" + str(phase) if phase else ""
    print("[" + tag + "] " + str(name) + "(id=" + str(agent.unit_id) + ")" + phase_str + " | " + detail)


def _check_incapacitated(agent):
    """기절/탈진/사망 체크.

    Returns:
        "dead"      - 사망 (호출자가 pop 해야 함)
        "fainted"   - 기절 (idle job 삽입됨)
        "exhausted" - 탈진 (idle job 삽입됨)
        None        - 정상
    """
    import survival as _surv

    if morld.get_unit_prop(agent.unit_id, "상태:사망"):
        return "dead"
    if _surv.is_npc_fainted(agent.unit_id):
        remain = _surv.get_faint_remaining_millis(agent.unit_id)
        agent._insert_idle_job("기절", max(remain, 1_000))
        agent._action_taken = True
        return "fainted"
    if _surv.is_npc_exhausted(agent.unit_id):
        remain = _surv.get_exhaustion_remaining_millis(agent.unit_id)
        agent._insert_idle_job("탈진", max(remain, 1_000))
        agent._action_taken = True
        return "exhausted"
    return None


# ── CombatState ───────────────────────────────────────────

class CombatState(FSMState):
    """전투 상태 - engaging/attacking"""
    state_type = "combat"
    level = LV_COMBAT

    def __init__(self, target_id):
        self.target_id = target_id
        self.phase = "engaging"
        self.last_enemy_ms = 0
        self.discovered = False

    def enter(self, agent):
        import combat as _combat
        self.last_enemy_ms = agent.get_time()
        if not self.discovered:
            _combat._emit_combat_line(agent.unit_id, "discover")
            self.discovered = True
        _log_fsm("combat", agent, "전투 개시", self.phase)

    def update(self, agent):
        import combat as _combat
        import survival as _surv

        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True

        behavior = getattr(agent, 'BATTLE_BEHAVIOR', {})

        if self.target_id and not agent._is_valid_combat_target(self.target_id):
            self.target_id = None
        if not self.target_id:
            self.target_id = agent._scan_nearest_enemy()
        if self.target_id:
            self.last_enemy_ms = agent.get_time()

        if not self.target_id:
            if agent._should_end_combat(self.last_enemy_ms):
                _log_fsm("combat", agent, "전투 종료 (3-조건 충족)", self.phase)
                agent._fsm_pop()
                agent._insert_idle_job("전투 종료", 2_000)
                agent._action_taken = True
                return False
            agent._insert_idle_job("경계", 5_000)
            agent._action_taken = True
            return True

        style = behavior.get("combat_style", "aggressive")
        if style != "aggressive":
            threshold = behavior.get("retreat_threshold", 0.2)
            my_hp = _surv.get_health(agent.unit_id)
            my_max = _surv.get_max_health(agent.unit_id)
            if my_hp <= my_max * threshold:
                _combat._emit_combat_line(agent.unit_id, "flee")
                _log_fsm("combat", agent, "HP 기반 후퇴 -> FleeState push", self.phase)
                agent._fsm_push(FleeState())
                agent._action_taken = True
                return True

        if self.phase == "engaging":
            if _combat.is_in_range(agent.unit_id, self.target_id):
                self.phase = "attacking"
                _log_fsm("combat", agent, "사거리 진입 -> attacking", self.phase)
            else:
                target_loc = morld.get_unit_location(self.target_id)
                if target_loc:
                    target_info = agent._make_location_target(target_loc[0], target_loc[1])
                    if target_info:
                        agent._move_to(target_info, "교전")
                    else:
                        agent._insert_idle_job("대상 이탈", 2_000)
                else:
                    agent._insert_idle_job("대상 이탈", 2_000)
                agent._action_taken = True
                return True

        if self.phase == "attacking":
            if not _combat.is_in_range(agent.unit_id, self.target_id):
                self.phase = "engaging"
                _log_fsm("combat", agent, "사거리 이탈 -> engaging", self.phase)
                return self.update(agent)

            result = _combat.execute_attack(agent.unit_id, self.target_id)
            if result.get("message"):
                morld.add_action_log(result["message"])

            if result.get("target_fainted"):
                if agent._should_end_combat(self.last_enemy_ms):
                    _log_fsm("combat", agent, "전투 승리 (3-조건 충족)", self.phase)
                    agent._fsm_pop()
                    agent._insert_idle_job("전투 승리", 3_000)
                    agent._action_taken = True
                    return False
                agent._insert_idle_job("경계", 5_000)
            else:
                speed = (_combat.get_combat_stat(agent.unit_id, "전투:공격속도") or 1.0)
                duration = int(agent.COMBAT_ATTACK_DURATION / speed)
                agent._insert_idle_job("공격", max(1_000, duration))
            agent._action_taken = True
            return True

        return True

    def exit(self, agent):
        _log_fsm("combat", agent, "전투 상태 초기화", self.phase)

    def __repr__(self):
        return ("<CombatState(lv=" + str(self.level) + ", phase=" + str(self.phase)
                + ", target=" + str(self.target_id) + ")>")


# ── FleeState ─────────────────────────────────────────────

class FleeState(FSMState):
    """도주 상태 - 안전 구역 이동 + 정비"""
    state_type = "flee"
    level = LV_COMBAT_SUB

    def __init__(self):
        self.flee_target = None
        self.phase = "fleeing"

    def enter(self, agent):
        _log_fsm("flee", agent, "도주 개시", self.phase)

    def update(self, agent):
        import combat as _combat
        import survival as _surv

        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True

        if self.phase == "fleeing":
            return self._update_fleeing(agent, _combat, _surv)
        if self.phase == "regrouping":
            return self._update_regrouping(agent, _combat, _surv)
        return True

    def _update_fleeing(self, agent, _combat, _surv):
        if not self.flee_target:
            self.flee_target = agent._pick_safe_location()
            if self.flee_target:
                _log_fsm("flee", agent,
                         "도주 목적지: R" + str(self.flee_target["region_id"])
                         + "L" + str(self.flee_target["location_id"]), self.phase)
            else:
                if agent._is_surrounded():
                    self._resolve_surrounded(agent)
                else:
                    _log_fsm("flee", agent, "안전 구역 없음 -> 강제 전투", self.phase)
                    agent._fsm_pop()
                    top = agent._fsm_top()
                    if hasattr(top, 'phase'):
                        top.phase = "attacking"
                    agent._insert_idle_job("후퇴 실패", 2_000)
                    agent._action_taken = True
                return True

        my_loc = agent.get_location()
        at_target = (my_loc
                     and my_loc[0] == self.flee_target["region_id"]
                     and my_loc[1] == self.flee_target["location_id"])

        if at_target:
            if _combat.has_enemies_at_location(agent.unit_id, my_loc[0], my_loc[1]):
                if agent._is_surrounded():
                    self._resolve_surrounded(agent)
                    return True
                self.flee_target = None
                _log_fsm("flee", agent, "도착지에 적 -> 재탐색", self.phase)
                agent._insert_idle_job("후퇴", 2_000)
                agent._action_taken = True
                return True
            self.phase = "regrouping"
            _log_fsm("flee", agent, "안전 구역 도착 -> 정비", self.phase)
            return self._update_regrouping(agent, _combat, _surv)

        agent._move_to(self.flee_target, "후퇴")
        agent._action_taken = True
        return True

    def _update_regrouping(self, agent, _combat, _surv):
        behavior = getattr(agent, 'BATTLE_BEHAVIOR', {})
        style = behavior.get("combat_style", "aggressive")

        enemy_id = agent._scan_nearest_enemy()
        if enemy_id and style != "evasive":
            _log_fsm("flee", agent, "적 재감지 -> re-engage", self.phase)
            agent._fsm_pop()
            top = agent._fsm_top()
            if hasattr(top, 'target_id'):
                top.target_id = enemy_id
                top.phase = "engaging"
            return False

        my_hp = _surv.get_health(agent.unit_id)
        my_max = _surv.get_max_health(agent.unit_id)
        if my_hp >= my_max * agent.COMBAT_REGROUP_HP_THRESHOLD:
            _log_fsm("flee", agent, "정비 완료 (HP 회복) -> pop", self.phase)
            agent._fsm_pop()
            return False

        agent._insert_idle_job("정비", 30_000)
        agent._action_taken = True
        return True

    def _resolve_surrounded(self, agent):
        if random.random() < agent.COMBAT_DESPERATE_CHANCE:
            _log_fsm("flee", agent, "포위 -> 필사의 저항", self.phase)
            agent._fsm_push(DesperateState())
        else:
            _log_fsm("flee", agent, "포위 -> 체념", self.phase)
            agent._fsm_push(ResignationState())
        agent._action_taken = True

    def exit(self, agent):
        _log_fsm("flee", agent, "도주 종료", self.phase)

    def __repr__(self):
        return ("<FleeState(lv=" + str(self.level) + ", phase=" + str(self.phase)
                + ", target=" + str(self.flee_target) + ")>")


# ── ResignationState ──────────────────────────────────────

class ResignationState(FSMState):
    """체념 - 반격/이동 불가, 적 전멸 시 pop"""
    state_type = "resignation"
    level = LV_COMBAT_SUB

    def enter(self, agent):
        _log_fsm("resignation", agent, "체념 시작")

    def update(self, agent):
        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True

        enemy_id = agent._scan_nearest_enemy()
        if enemy_id is None:
            _log_fsm("resignation", agent, "적 전멸 -> pop")
            agent._fsm_pop()
            return False
        agent._insert_idle_job("체념", 10_000)
        agent._action_taken = True
        return True

    def exit(self, agent):
        _log_fsm("resignation", agent, "체념 종료")

    def __repr__(self):
        return "<ResignationState(lv=" + str(self.level) + ")>"


# ── DesperateState ────────────────────────────────────────

class DesperateState(FSMState):
    """필사의 저항 - 도주 불가, 적에게 공격 지속"""
    state_type = "desperate"
    level = LV_COMBAT_SUB

    def __init__(self):
        self.target_id = None

    def enter(self, agent):
        _log_fsm("desperate", agent, "필사의 저항 시작")

    def update(self, agent):
        import combat as _combat

        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True

        if self.target_id and not agent._is_valid_combat_target(self.target_id):
            self.target_id = None
        if not self.target_id:
            self.target_id = agent._scan_nearest_enemy()
        if not self.target_id:
            _log_fsm("desperate", agent, "적 전멸 -> pop")
            agent._fsm_pop()
            return False

        result = _combat.execute_attack(agent.unit_id, self.target_id)
        if result.get("message"):
            morld.add_action_log(result["message"])
        speed = (_combat.get_combat_stat(agent.unit_id, "전투:공격속도") or 1.0)
        duration = int(agent.COMBAT_ATTACK_DURATION / speed)
        agent._insert_idle_job("필사", max(1_000, duration))
        agent._action_taken = True
        return True

    def exit(self, agent):
        _log_fsm("desperate", agent, "필사의 저항 종료")

    def __repr__(self):
        return "<DesperateState(lv=" + str(self.level) + ", target=" + str(self.target_id) + ")>"


# ── 파티 Phase ────────────────────────────────────────────

_EXCLUDED_REGIONS = {10}


def _check_leader_destination(agent):
    """리더 목적지 확인 → 다른 region이면 따라감 (E3)"""
    import party as _party
    squad = _party.get_squad_by_unit(agent.unit_id)
    if not squad or not squad.leader_destination:
        return False
    if squad.leader_id == agent.unit_id:
        return False
    dest = squad.leader_destination
    if dest["region_id"] in _EXCLUDED_REGIONS:
        return False
    loc = agent.get_location()
    if loc and loc[0] == dest["region_id"]:
        return False
    agent._move_to(dest, "이동")
    agent._action_taken = True
    return True


class StandbyPhase(FSMState):
    """분대 대기 — 소속이지만 지시 없는 상태"""
    state_type = "standby"
    level = LV_STANDBY

    _NEEDS_THRESHOLDS = {
        "배변": 70,
        "피로": 80,
        "청결": 70,
    }

    def update(self, agent):
        import party as _party
        if not _party.is_in_squad(agent.unit_id):
            return False

        if _check_leader_destination(agent):
            return True

        if self._needs_critical(agent):
            return False

        agent._insert_idle_job("대기", 5 * 60_000)
        agent._action_taken = True
        return True

    def _needs_critical(self, agent):
        try:
            import needs as _needs
        except ImportError:
            return False
        npc_id = agent.unit_id
        for need_name, threshold in self._NEEDS_THRESHOLDS.items():
            if need_name == "배변":
                val = _needs.get_excretion(npc_id) if hasattr(_needs, 'get_excretion') else 0
            elif need_name == "피로":
                val = _needs.get_fatigue(npc_id) if hasattr(_needs, 'get_fatigue') else 0
            elif need_name == "청결":
                val = _needs.get_cleanliness(npc_id) if hasattr(_needs, 'get_cleanliness') else 0
            else:
                val = 0
            if val >= threshold:
                return True
        return False

    def __repr__(self):
        return "<StandbyPhase(lv=" + str(self.level) + ")>"


class CommandPhase(FSMState):
    """분대 지시 수행 — Order 기반 행동"""
    state_type = "command"
    level = LV_COMMAND

    _ORDER_HANDLERS = {
        "follow":  "_handle_order_follow",
        "수색":    "_handle_order_search",
        "경계":    "_handle_order_guard",
        "수집":    "_handle_order_collect",
        "이동":    "_handle_order_move",
        "대기":    "_handle_order_wait",
    }

    def update(self, agent):
        import party as _party

        if _check_leader_destination(agent):
            return True

        squad = _party.get_squad_by_unit(agent.unit_id)
        order = squad.orders.get(agent.unit_id) if squad else None
        if order is None:
            return False

        if squad.leader_id and squad.leader_id != agent.unit_id:
            from think.party_config import check_disobedience
            if check_disobedience(agent.unit_id, squad.leader_id, order):
                agent._insert_idle_job("불복", 5 * 60_000)
                agent._action_taken = True
                return True

        main_type = order.main_type()
        handler_name = self._ORDER_HANDLERS.get(main_type)
        if handler_name is None:
            return False
        handler = getattr(agent, handler_name, None)
        if handler is None:
            return False
        return handler(order)

    def exit(self, agent):
        for key in list(agent._memory):
            if key.startswith("order_"):
                agent._memory[key] = None

    def __repr__(self):
        return "<CommandPhase(lv=" + str(self.level) + ")>"
